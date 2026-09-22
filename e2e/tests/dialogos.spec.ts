import { test, expect } from '@playwright/test'
import { irPara } from './apoio'

/** O que os modais ganharam ao passar para o Dialog do shadcn.
 *
 *  Estas propriedades nao se veem numa captura de ecra: sem teste, perdem-se
 *  numa refactorizacao qualquer e ninguem da por isso ate alguem tentar usar
 *  o portal so com o teclado. */

test.beforeEach(async ({ page }) => {
  await irPara(page, '/app/passengers')
  await page.getByRole('button', { name: /novo passageiro/i }).click()
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 15_000 })
})

test('o dialogo abre em portal, fora da arvore da pagina', async ({ page }) => {
  // Montado onde e usado, um `position: fixed` dentro de um ascendente com
  // `backdrop-filter` ou `transform` resolve contra esse ascendente e o
  // dialogo sai do sitio. Em portal, nao ha ascendente nenhum.
  const foraDoConteudo = await page.evaluate(() => {
    const d = document.querySelector('[role=dialog]')!
    return !d.closest('.admin-content') && !d.closest('[data-slot=sidebar-inset]')
  })
  expect(foraDoConteudo).toBe(true)
})

test('o foco nao sai do dialogo', async ({ page }) => {
  for (let i = 0; i < 30; i++) {
    await page.keyboard.press('Tab')
    const dentro = await page.evaluate(() => {
      const d = document.querySelector('[role=dialog]')
      return d ? d.contains(document.activeElement) : false
    })
    expect(dentro, `o foco saiu do dialogo a tabulacao ${i + 1}`).toBe(true)
  }
})

test('o fundo nao rola com o dialogo aberto, e volta a rolar depois', async ({ page }) => {
  await expect
    .poll(() => page.evaluate(() => getComputedStyle(document.body).overflow))
    .toBe('hidden')

  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect
    .poll(() => page.evaluate(() => getComputedStyle(document.body).overflow))
    .not.toBe('hidden')
})

test('o dialogo tem nome acessivel', async ({ page }) => {
  // Sem nome, um leitor de ecra anuncia "dialogo" e mais nada.
  await expect(page.getByRole('dialog')).toHaveAccessibleName(/passageiro/i)
})
