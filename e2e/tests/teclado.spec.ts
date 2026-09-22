import { test, expect } from '@playwright/test'
import { irPara } from './apoio'

/** O que a conversao para Tabs e Table do shadcn trouxe de novo.
 *
 *  Nenhuma destas propriedades aparece numa captura de ecra, e todas se
 *  perdem sem dar nas vistas numa refactorizacao futura. */

test('as abas navegam-se com as setas', async ({ page }) => {
  await irPara(page, '/app/reports')
  const abas = page.getByRole('tab')
  await expect(abas.first()).toBeVisible({ timeout: 20_000 })

  // A versao anterior era uma lista de `<button role=tab>` sem foco em
  // rotacao: o Tab passava por todas uma a uma e as setas nao faziam nada.
  await abas.first().focus()
  await page.keyboard.press('ArrowRight')
  await expect(abas.nth(1)).toBeFocused()
  await expect(abas.nth(1)).toHaveAttribute('aria-selected', 'true')

  await page.keyboard.press('ArrowLeft')
  await expect(abas.first()).toBeFocused()
})

test('as abas nao apontam para um painel que nao existe', async ({ page }) => {
  // Os paineis sao renderizados pelas paginas, fora do TabBar. Um
  // `aria-controls` a apontar para um id inexistente e pior do que a sua
  // ausencia, por isso e removido de proposito.
  await irPara(page, '/app/reports')
  await expect(page.getByRole('tab').first()).toBeVisible({ timeout: 20_000 })

  const pendentes = await page.evaluate(() =>
    [...document.querySelectorAll('[role=tab][aria-controls]')]
      .filter((t) => !document.getElementById(t.getAttribute('aria-controls')!))
      .length,
  )
  expect(pendentes, 'ha abas a apontar para paineis inexistentes').toBe(0)
})

test('a tabela ordena-se pelo teclado, e anuncia a direccao', async ({ page }) => {
  await irPara(page, '/app/passengers')
  const cabecalho = page.locator('.admin-table th').first()
  await expect(cabecalho).toBeVisible({ timeout: 20_000 })

  // Era um `<span onClick>`: nao recebia foco, nao respondia ao Enter, e
  // nenhum leitor de ecra o anunciava como accionavel.
  const botao = cabecalho.locator('button.sortable-header')
  await expect(botao).toHaveCount(1)

  await expect(cabecalho).not.toHaveAttribute('aria-sort', /.+/)
  await botao.focus()
  await page.keyboard.press('Enter')
  await expect(cabecalho).toHaveAttribute('aria-sort', 'ascending')
  await page.keyboard.press('Enter')
  await expect(cabecalho).toHaveAttribute('aria-sort', 'descending')
})

test('o filtro segmentado nao se deixa desligar', async ({ page }) => {
  await irPara(page, '/app/cards/physical')
  const grupo = page.locator('.segmented-control')
  await expect(grupo).toBeVisible({ timeout: 20_000 })

  // O ToggleGroup do Radix devolve string vazia ao carregar no item ja
  // escolhido. Sem guarda, a lista ficava sem filtro nenhum.
  const activo = grupo.locator('[data-state=on]')
  await expect(activo).toHaveCount(1)
  await activo.click()
  await expect(grupo.locator('[data-state=on]')).toHaveCount(1)
})
