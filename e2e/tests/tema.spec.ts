import { test, expect } from '@playwright/test'
import { irPara } from './apoio'

/** O personalizador de tema.
 *
 *  Verifica o mecanismo, nao a aparencia: que trocar de preset muda mesmo as
 *  variaveis do documento, que repor devolve o tema TPM-TUR, e que a escolha
 *  sobrevive a um recarregamento. Sao as tres coisas que a migracao das fases
 *  seguintes nao pode partir. */

/** O ciano oficial da TPM-TUR. Fixado de proposito: e um contrato de
 *  marca, e se mudar sem querer alguem tem de dar por isso. */
const ciano = '#00a1cd'

async function lerPrimary(page: import('@playwright/test').Page) {
  return page.evaluate(() =>
    getComputedStyle(document.documentElement).getPropertyValue('--primary').trim(),
  )
}

test.beforeEach(async ({ page }) => {
  await irPara(page, '/app/passengers')
  await page.getByRole('button', { name: /personalizar tema/i }).click()
  await expect(page.locator('.tc-painel')).toBeVisible({ timeout: 15_000 })
})

test('abre com o tema TPM-TUR e mostra a lista de presets', async ({ page }) => {
  expect(await lerPrimary(page)).toBe(ciano)

  await page.locator('.tc-listbox-botao').click()
  const opcoes = page.locator('.tc-listbox [role=option]')
  // TPM-TUR mais os presets do template; o numero exacto pode crescer.
  await expect.poll(() => opcoes.count()).toBeGreaterThan(10)
  await expect(opcoes.first()).toContainText('TPM-TUR')
})

test('trocar de preset repinta, e repor devolve o TPM-TUR', async ({ page }) => {
  await page.locator('.tc-listbox-botao').click()
  await page.locator('.tc-listbox [role=option]').nth(4).click()

  await expect.poll(() => lerPrimary(page), { timeout: 10_000 }).not.toBe(ciano)

  // A barra lateral tem de acompanhar: muitos presets nao trazem variaveis de
  // barra e sao derivadas do proprio preset. Sem isso ficava navy num tema
  // vermelho, que e o oposto de mostrar o produto noutro operador.
  const barra = await page.evaluate(
    () => getComputedStyle(document.querySelector('.admin-sidebar')!).backgroundColor,
  )
  expect(barra).not.toBe('rgb(3, 49, 107)')  // o marinho oficial

  await page.getByRole('button', { name: /repor tpm-tur/i }).click()
  await expect.poll(() => lerPrimary(page), { timeout: 10_000 }).toBe(ciano)
})

test('a escolha sobrevive a um recarregamento', async ({ page }) => {
  await page.locator('.tc-listbox-botao').click()
  await page.locator('.tc-listbox [role=option]').nth(4).click()
  await expect.poll(() => lerPrimary(page), { timeout: 10_000 }).not.toBe(ciano)
  const escolhido = await lerPrimary(page)

  await page.reload({ waitUntil: 'networkidle' })
  await expect.poll(() => lerPrimary(page), { timeout: 20_000 }).toBe(escolhido)

  // Nao deixar o ambiente sujo para os testes seguintes.
  await page.getByRole('button', { name: /personalizar tema/i }).click()
  await page.getByRole('button', { name: /repor tpm-tur/i }).click()
  await expect.poll(() => lerPrimary(page), { timeout: 10_000 }).toBe(ciano)
})

test('o arredondamento muda e fica marcado', async ({ page }) => {
  const raio = () =>
    page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--radius').trim())

  await page.locator('.tc-raio', { hasText: '1,0' }).click()
  await expect.poll(raio, { timeout: 10_000 }).toBe('1rem')
  await expect(page.locator('.tc-raio', { hasText: '1,0' })).toHaveAttribute('aria-pressed', 'true')

  await page.getByRole('button', { name: /repor tpm-tur/i }).click()
  await expect.poll(raio, { timeout: 10_000 }).toBe('0.5rem')
})

test('o painel abre inteiro, e nao preso na barra de topo', async ({ page }) => {
  // O `.admin-topbar` tem backdrop-filter, que cria bloco de contencao: um
  // `position: fixed` montado la dentro resolve contra a barra de 70px e o
  // painel sai so com o cabecalho. Dai o portal para o body.
  const caixa = await page.locator('.tc-painel').boundingBox()
  const janela = page.viewportSize()!
  expect(caixa!.height).toBeGreaterThan(janela.height * 0.9)

  const pai = await page.evaluate(
    () => document.querySelector('.tc-overlay')!.parentElement!.tagName,
  )
  expect(pai).toBe('BODY')
})

test('as opcoes de barra lateral aplicam-se, e o lado troca a folga', async ({ page }) => {
  const geometria = () =>
    page.evaluate(() => {
      const sb = document.querySelector('[data-slot=sidebar]')!
      const ix = document.querySelector('[data-slot=sidebar-inset]')!.getBoundingClientRect()
      return {
        lado: sb.getAttribute('data-side'),
        variante: sb.getAttribute('data-variant'),
        esquerda: Math.round(ix.x),
        direita: Math.round(window.innerWidth - ix.right),
      }
    })

  await page.locator('.tc-opcao-btn', { hasText: 'Flutuante' }).click()
  await expect.poll(async () => (await geometria()).variante, { timeout: 10_000 }).toBe('floating')

  // A ordem no DOM decide de que lado fica a folga: o Sidebar reserva o espaco
  // com uma div irma. Declarado antes do conteudo mas posto a direita, deixava
  // um vazio a esquerda e tapava o conteudo do outro lado.
  await page.locator('.tc-modo-btn', { hasText: 'Direita' }).click()
  await expect.poll(async () => (await geometria()).lado, { timeout: 10_000 }).toBe('right')
  const direita = await geometria()
  expect(direita.direita).toBeGreaterThan(200)
  expect(direita.esquerda).toBe(0)

  await page.getByRole('button', { name: /repor tpm-tur/i }).click()
  await expect.poll(async () => (await geometria()).lado, { timeout: 10_000 }).toBe('left')
  const esquerda = await geometria()
  expect(esquerda.esquerda).toBeGreaterThan(200)
  expect(esquerda.direita).toBe(0)
  expect(esquerda.variante).toBe('sidebar')
})
