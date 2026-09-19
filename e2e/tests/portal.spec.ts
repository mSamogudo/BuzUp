import { test, expect } from '@playwright/test'
import { irPara, navegacao } from './apoio'

/** A casca do portal: navegacao, tema e idioma.
 *  Tudo por papel e texto — as classes mudam na migracao, o comportamento nao. */

test('o dashboard abre com a navegacao e os indicadores', async ({ page }) => {
  await irPara(page, '/app')

  await expect(navegacao(page)).toBeVisible()
  await expect(navegacao(page).getByRole('link', { name: /passageiros/i })).toBeVisible()

  // Os cartoes de indicador tem de trazer numeros, nao so rotulos.
  await expect(page.locator('body')).toContainText(/MZN|\d/)
})

test('a barra lateral navega entre seccoes', async ({ page }) => {
  await irPara(page, '/app')

  for (const [rotulo, url] of [
    [/^rotas$/i, /\/app\/routes/],
    [/passageiros/i, /\/app\/passengers/],
    [/utilizadores/i, /\/app\/users/],
  ] as const) {
    await navegacao(page).getByRole('link', { name: rotulo }).first().click()
    await expect(page).toHaveURL(url)
    await page.waitForLoadState('networkidle')
  }
})

test('o tema alterna e sobrevive a um recarregamento', async ({ page }) => {
  await irPara(page, '/app')
  const html = page.locator('html')

  const inicial = await html.getAttribute('data-theme')
  await page.getByRole('button', { name: /tema|theme|escuro|claro|dark|light/i }).first().click()
  await expect
    .poll(() => html.getAttribute('data-theme'), { timeout: 10_000 })
    .not.toBe(inicial)

  const depois = await html.getAttribute('data-theme')
  await page.reload({ waitUntil: 'networkidle' })
  // A preferencia e do utilizador: tem de persistir.
  await expect.poll(() => html.getAttribute('data-theme'), { timeout: 15_000 }).toBe(depois)
})

test('o idioma alterna entre PT e EN', async ({ page }) => {
  await irPara(page, '/app/passengers')

  await page.getByRole('button', { name: 'EN', exact: true }).first().click()
  await expect(page.locator('body')).toContainText(/passengers|status|search/i, { timeout: 10_000 })

  await page.getByRole('button', { name: 'PT', exact: true }).first().click()
  await expect(page.locator('body')).toContainText(/passageiros|estado|pesquisar/i, { timeout: 10_000 })
})

test('a sessao sobrevive a um recarregamento', async ({ page }) => {
  await irPara(page, '/app')
  await page.reload({ waitUntil: 'networkidle' })
  await expect(page).toHaveURL(/\/app/)
  await expect(navegacao(page)).toBeVisible()
})
