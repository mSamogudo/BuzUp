import { test, expect, type Page, type Request } from '@playwright/test'

/** O caminho do dinheiro, do link ao bilhete.
 *
 *  O que aqui se protege e o PEDIDO: os campos que o servidor recebe quando
 *  alguem compra. Uma refactorizacao do formulario que perca `trip_id`, ou
 *  que mande o telefone com espacos, so daria erro na caixa — e no ambiente
 *  de desenvolvimento nem isso, porque o fornecedor de pagamento responde
 *  502 e o erro passa por "falha ao iniciar pagamento".
 *
 *  Por isso a resposta e simulada. Nao se testa aqui o gateway; testa-se o
 *  que o portal lhe manda, e o que mostra a quem comprou. */

const PERCURSO = '/comprar?origem=1&destino=6&data=2026-09-25&pax=1'

const RESPOSTA = {
  checkout_reference: 'GC-TESTE-0001',
  payment_reference: 'PAY-TESTE-0001',
  payment_status: 'confirmed',
  total_amount: '250.00',
  tickets: [{ ticket_code: 'TK-TESTE-0001', passenger_name: 'Ana Maria Cossa', seat_label: '' }],
}

/** Intercepta a compra e devolve um bilhete. Guarda o corpo que saiu. */
async function simularPagamento(page: Page) {
  const enviados: Record<string, unknown>[] = []
  await page.route('**/api/guest-checkouts/', async (rota, pedido: Request) => {
    if (pedido.method() !== 'POST') return rota.fallback()
    enviados.push(JSON.parse(pedido.postData() || '{}'))
    await rota.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(RESPOSTA) })
  })
  return enviados
}

/** Da pesquisa ao checkout. Quem viaja e o pagamento vivem na mesma pagina:
 *  eram dois passos de um assistente, e a pessoa preenchia os nomes sem
 *  nunca ver o preco. */
async function irAtePagamento(page: Page, nome: string) {
  await page.goto(PERCURSO, { waitUntil: 'networkidle' })
  await expect(page.locator('.bzbk-trip').first()).toBeVisible({ timeout: 25_000 })
  await page.locator('.bzbk-trip').first().click()

  await expect(page).toHaveURL(/\/checkout/, { timeout: 15_000 })
  await expect(page.locator('.bzbk-checkout')).toBeVisible()
  await page.locator('.bzbk-pax .bzbk-input').first().fill(nome)
  await expect(page.locator('#ph')).toBeVisible()
}

test('o pedido de compra leva tudo o que o servidor precisa', async ({ page }) => {
  const enviados = await simularPagamento(page)
  await irAtePagamento(page, 'Ana Maria Cossa')

  await page.locator('#ph').fill('84 123 4567')     // com espaços de propósito
  const email = page.locator('input[type=email]')
  if (await email.count()) await email.first().fill('ana@exemplo.mz')
  const termos = page.locator('.bzbk-accept [data-slot=checkbox], .bzbk-accept input[type=checkbox]')
  if (await termos.count()) await termos.first().click()

  await page.locator('.bzbk-checkout-pagar').click()
  await expect.poll(() => enviados.length, { timeout: 20_000 }).toBe(1)

  const corpo = enviados[0] as Record<string, never>
  // O telefone vai sem espaços: o servidor guarda nove dígitos e o comprador
  // escreve como lhe apetece.
  expect(corpo.payer_phone, 'telefone só com dígitos').toBe('841234567')
  expect(corpo.buyer_name).toBe('Ana Maria Cossa')
  expect(Number(corpo.trip_id), 'partida escolhida').toBeGreaterThan(0)
  expect(Number(corpo.origin_stop_id)).toBe(1)
  expect(Number(corpo.destination_stop_id)).toBe(6)
  expect(Number(corpo.quantity)).toBe(1)
  expect(corpo.route_code, 'a carreira viaja com o pedido').toBeTruthy()
  expect(corpo.origin_stop, 'nomes das paragens, para o bilhete').toBeTruthy()
  expect(corpo.destination_stop).toBeTruthy()
  expect(Array.isArray(corpo.passengers)).toBe(true)
  expect((corpo.passengers as unknown as { name: string }[])[0].name).toBe('Ana Maria Cossa')
  expect(corpo.accept_terms, 'termos aceites').toBe(true)
  expect(corpo.terms_version, 'versão dos termos que a pessoa viu').toBeTruthy()
  expect(corpo.payment_method).toBe('mobile_wallet')
  expect(corpo.display_currency).toBeTruthy()
})

test('o bilhete aparece depois de pagar', async ({ page }) => {
  await simularPagamento(page)
  await irAtePagamento(page, 'Ana Maria Cossa')

  await page.locator('#ph').fill('841234567')
  const termos = page.locator('.bzbk-accept [data-slot=checkbox], .bzbk-accept input[type=checkbox]')
  if (await termos.count()) await termos.first().click()
  await page.locator('.bzbk-checkout-pagar').click()

  // A referência é o que a pessoa leva consigo: sem ela não há como
  // reclamar um pagamento que o operador não vê.
  await expect(page.getByText(RESPOSTA.checkout_reference)).toBeVisible({ timeout: 20_000 })
})

test('nao deixa pagar sem o telefone certo', async ({ page }) => {
  await simularPagamento(page)
  await irAtePagamento(page, 'Ana Maria Cossa')

  const termos = page.locator('.bzbk-accept [data-slot=checkbox], .bzbk-accept input[type=checkbox]')
  if (await termos.count()) await termos.first().click()
  const pagar = page.locator('.bzbk-checkout-pagar')

  // Oito dígitos: um número moçambicano tem nove. O botão fica desactivado
  // em vez de deixar sair um pedido que a caixa vai recusar — e é assim que
  // deve ser, por isso é isso que se afirma.
  await page.locator('#ph').fill('84123456')
  await expect(pagar).toBeDisabled()

  await page.locator('#ph').fill('841234567')
  await expect(pagar).toBeEnabled()
})
