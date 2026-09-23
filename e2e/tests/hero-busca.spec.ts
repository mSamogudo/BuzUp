import { test, expect } from '@playwright/test'

/** A compra comeca no hero da landing do operador.
 *
 *  O que aqui se protege e a fronteira entre as duas paginas: o formulario
 *  nao compra nada, monta o link que o `/comprar` ja sabe ler. Se alguem
 *  mudar o nome de um parametro de um dos lados, a pesquisa deixa de chegar
 *  ao outro e ninguem da por isso ate tentar comprar um bilhete. */

const ESPERA = { timeout: 20_000 }

async function abrirHero(page: import('@playwright/test').Page) {
  await page.goto('/tpm-tur', { waitUntil: 'networkidle' })
  await expect(page.locator('.tpm-busca')).toBeVisible(ESPERA)
}

/** Escreve no combo e aceita a primeira sugestao. */
async function escolherParagem(page: import('@playwright/test').Page, campo: string, texto: string) {
  await page.locator(campo).fill(texto)
  const sugestao = page.locator('.bzbk-combo-opt').first()
  await expect(sugestao).toBeVisible({ timeout: 10_000 })
  await sugestao.click()
}

/** Abre o calendario e aceita o primeiro dia que nao esteja desactivado. */
async function escolherPrimeiroDia(page: import('@playwright/test').Page, campo: string) {
  await page.locator(campo).click()
  const dia = page.locator('[data-slot=popover-content] button[data-day]:not([disabled])').first()
  await expect(dia).toBeVisible({ timeout: 10_000 })
  await dia.click()
}

test('o formulario do hero entrega a pesquisa ao /comprar', async ({ page }) => {
  await abrirHero(page)

  await escolherParagem(page, '#busca-origem', 'bai')
  await escolherParagem(page, '#busca-destino', 'zim')
  await escolherPrimeiroDia(page, '#busca-data')
  await page.locator('.tpm-busca-btn').click()

  await expect(page).toHaveURL(/\/comprar\?/, ESPERA)
  const url = new URL(page.url())
  expect(url.searchParams.get('origem'), 'origem').toMatch(/^\d+$/)
  expect(url.searchParams.get('destino'), 'destino').toMatch(/^\d+$/)
  expect(url.searchParams.get('data'), 'data em AAAA-MM-DD').toMatch(/^\d{4}-\d{2}-\d{2}$/)
  expect(url.searchParams.get('pax')).toBe('1')

  // Com percurso e data completos o `/comprar` pesquisa sozinho: quem
  // preencheu no hero nao repete nada deste lado.
  await expect(page.locator('.bzbk-step').nth(1)).toHaveClass(/is-active/, ESPERA)
})

test('a ida e volta atravessa para o outro lado', async ({ page }) => {
  await abrirHero(page)
  await page.locator('.tpm-busca-tipo-btn', { hasText: 'Ida e volta' }).click()
  await expect(page.locator('#busca-volta')).toBeVisible()

  await escolherParagem(page, '#busca-origem', 'bai')
  await escolherParagem(page, '#busca-destino', 'zim')
  await escolherPrimeiroDia(page, '#busca-data')
  await escolherPrimeiroDia(page, '#busca-volta')
  await page.locator('.tpm-busca-btn').click()

  await expect(page).toHaveURL(/volta=\d{4}-\d{2}-\d{2}/, ESPERA)

  // O assistente ganha as duas etapas do regresso. Sem isto, a escolha do
  // passageiro perdia-se na fronteira e ele so compraria a ida.
  const passos = page.locator('.bzbk-step')
  await expect(passos).toHaveCount(7, ESPERA)
  await expect(passos.nth(3)).toContainText(/volta/i)
})

test('recusa um percurso impossivel antes de sair da pagina', async ({ page }) => {
  await abrirHero(page)
  await escolherParagem(page, '#busca-origem', 'bai')

  // Sem destino nem data: nao vale mandar a pessoa para a pagina seguinte
  // descobrir la que falta preencher coisas.
  await page.locator('.tpm-busca-btn').click()
  await expect(page.locator('.tpm-busca-erro')).toBeVisible()
  await expect(page).toHaveURL(/\/tpm-tur/)
})

test('o botao de inverter troca origem e destino', async ({ page }) => {
  await abrirHero(page)
  await escolherParagem(page, '#busca-origem', 'bai')
  await escolherParagem(page, '#busca-destino', 'zim')

  const origem = await page.locator('#busca-origem').inputValue()
  const destino = await page.locator('#busca-destino').inputValue()
  expect(origem).not.toBe(destino)

  await page.locator('.tpm-busca-inverter').click()
  await expect(page.locator('#busca-origem')).toHaveValue(destino)
  await expect(page.locator('#busca-destino')).toHaveValue(origem)
})
