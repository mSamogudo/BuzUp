import { test, expect } from '@playwright/test'
import { irPara } from './apoio'

/** Tabelas: render, pesquisa, paginacao e detalhe.
 *  E o comportamento de que as 40 paginas admin dependem — se sobreviver
 *  a migracao, a maior parte do portal sobreviveu com ele. */

test.beforeEach(async ({ page }) => {
  await irPara(page, '/app/passengers')
  await expect(page.getByRole('table')).toBeVisible({ timeout: 20_000 })
})

test('a tabela traz linhas do backend', async ({ page }) => {
  const linhas = page.getByRole('row')
  // Cabecalho mais pelo menos uma linha de dados.
  await expect.poll(() => linhas.count()).toBeGreaterThan(1)

  // Os dados semeados sao mocambicanos: numeros +258.
  await expect(page.getByRole('table')).toContainText(/\+258/)
})

test('a pesquisa filtra as linhas', async ({ page }) => {
  const linhas = page.getByRole('row')
  const antes = await linhas.count()

  const pesquisa = page.getByPlaceholder(/pesquisar|search/i).first()
  await pesquisa.fill('zzzznaoexiste')
  await expect.poll(() => linhas.count(), { timeout: 10_000 }).toBeLessThan(antes)

  await pesquisa.fill('')
  await expect.poll(() => linhas.count(), { timeout: 10_000 }).toBe(antes)
})

test('a paginacao avanca e recua', async ({ page }) => {
  const primeiraCelula = () => page.getByRole('row').nth(1).innerText()
  const pagina1 = await primeiraCelula()

  const seguinte = page.getByRole('button', { name: /seguinte|next/i }).first()
  test.skip(!(await seguinte.isEnabled()), 'so ha uma pagina de dados')

  await seguinte.click()
  await expect.poll(primeiraCelula, { timeout: 10_000 }).not.toBe(pagina1)

  await page.getByRole('button', { name: /anterior|previous/i }).first().click()
  await expect.poll(primeiraCelula, { timeout: 10_000 }).toBe(pagina1)
})

test('o detalhe de uma linha abre', async ({ page }) => {
  await page.getByRole('button', { name: /^ver$|detalhe|view/i }).first().click()

  // O painel de detalhe e um dialogo ou uma gaveta, conforme a pagina.
  const painel = page.getByRole('dialog').or(page.locator('[class*=drawer], [class*=detail]')).first()
  await expect(painel).toBeVisible({ timeout: 10_000 })
})

test('o formulario de criacao abre', async ({ page }) => {
  await page.getByRole('button', { name: /novo passageiro|new passenger/i }).first().click()

  const formulario = page.getByRole('dialog').or(page.locator('form')).first()
  await expect(formulario).toBeVisible({ timeout: 10_000 })
  await expect(page.locator('body')).toContainText(/nome|name/i)
})
