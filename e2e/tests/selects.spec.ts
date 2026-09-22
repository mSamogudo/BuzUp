import { test, expect } from '@playwright/test'
import { irPara } from './apoio'

/** Os campos de escolha, agora Select do shadcn.
 *
 *  O que aqui se protege nao se ve numa captura:
 *
 *  O Radix reserva a string vazia para "sem seleccao" e recusa um item com
 *  `value=""`. Como `<option value="">Todas</option>` e o modo normal de
 *  limpar um filtro nesta aplicacao, o CampoSelect traduz esse valor para um
 *  sentinela e de volta. Se alguem tirar a traducao, o filtro passa a mandar
 *  `__vazio__` a API — ou deixa de ser possivel voltar a "Todas".
 *
 *  E o gatilho do Radix e um `<button>`, que nao e rotulavel: um `<label>`
 *  por fora deixava de lhe dar nome. Dai o `htmlFor` explicito. */

async function abrir(page: import('@playwright/test').Page, nome: RegExp) {
  await page.getByRole('combobox', { name: nome }).click()
  await expect(page.locator('[data-slot=select-content]')).toBeVisible()
}

test('o filtro volta a "Todas" sem mandar o sentinela a API', async ({ page }) => {
  const pedidos: string[] = []
  await irPara(page, '/app')
  page.on('request', (r) => {
    if (r.url().includes('/api/admin/analytics')) pedidos.push(r.url())
  })

  await expect(page.getByRole('combobox').first()).toBeVisible({ timeout: 20_000 })

  // Escolher uma rota concreta: a API tem de receber o id.
  await abrir(page, /rota|route/i)
  const itens = page.locator('[data-slot=select-content] [data-slot=select-item]')
  await expect.poll(() => itens.count()).toBeGreaterThan(1)
  await itens.nth(1).click()
  await expect.poll(() => pedidos.length, { timeout: 15_000 }).toBeGreaterThan(0)
  expect(pedidos[pedidos.length - 1]).toMatch(/route_id=\d+/)

  // E voltar a "Todas" tem de limpar o filtro, nao mandar o sentinela.
  pedidos.length = 0
  await abrir(page, /rota|route/i)
  await page.locator('[data-slot=select-content] [data-slot=select-item]').first().click()
  await expect.poll(() => pedidos.length, { timeout: 15_000 }).toBeGreaterThan(0)
  const ultimo = pedidos[pedidos.length - 1]
  expect(ultimo, 'o sentinela nao pode chegar a API').not.toContain('__vazio__')
  expect(ultimo).not.toMatch(/route_id=\d/)
})

test('o gatilho tem nome acessivel vindo da etiqueta', async ({ page }) => {
  await irPara(page, '/app/stops')
  await page.getByRole('button', { name: /nova paragem|new stop/i }).click()
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 15_000 })

  const gatilho = page.getByRole('dialog').getByRole('combobox')
  await expect(gatilho).toHaveAccessibleName(/estado|status/i)
})

test('um select dentro de um dialogo abre por cima dele', async ({ page }) => {
  await irPara(page, '/app/stops')
  await page.getByRole('button', { name: /nova paragem|new stop/i }).click()
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 15_000 })

  await page.getByRole('dialog').getByRole('combobox').click()
  const lista = page.locator('[data-slot=select-content]')
  await expect(lista).toBeVisible()

  // Visivel nao chega: o dialogo tem o seu proprio contexto de empilhamento,
  // e uma lista montada por baixo fica escondida sem deixar de estar "visivel".
  const porCima = await page.evaluate(() => {
    const c = document.querySelector('[data-slot=select-content]')!.getBoundingClientRect()
    const alvo = document.elementFromPoint(c.x + c.width / 2, c.y + 8)
    return alvo?.closest('[data-slot=select-content]') !== null
  })
  expect(porCima, 'a lista ficou por baixo do dialogo').toBe(true)

  await page.locator('[data-slot=select-item]').last().click()
  await expect(page.getByRole('dialog').getByRole('combobox')).toHaveText(/inactivo|inactive/i)
})

test('o tamanho de pagina muda o numero de linhas', async ({ page }) => {
  await irPara(page, '/app/passengers')
  const linhas = page.locator('.admin-table tbody tr')
  await expect.poll(() => linhas.count(), { timeout: 20_000 }).toBe(10)

  await page.locator('.admin-table-page-size').getByRole('combobox').click()
  await page.locator('[data-slot=select-content] [data-slot=select-item]').nth(1).click()
  await expect.poll(() => linhas.count(), { timeout: 10_000 }).toBe(25)
})
