import { test, expect } from '@playwright/test'
import { irPara } from './apoio'

/** O portal num telemovel.
 *
 *  As capturas correm a 1440px e nunca apanham nada disto. Sao duas coisas
 *  que se partiram durante a migracao para o shadcn e que voltariam a
 *  partir-se sem teste. */

test.use({ viewport: { width: 390, height: 844 } })

test('a barra de topo nao transborda nem se sobrepoe', async ({ page }) => {
  await irPara(page, '/app/audit')
  await expect(page.locator('.admin-topbar')).toBeVisible({ timeout: 20_000 })

  const caixas = await page.evaluate(() => {
    const e = document.querySelector('.admin-topbar-left')!.getBoundingClientRect()
    // Elementos escondidos devolvem rectangulo nulo; contar o x=0 deles
    // falsificava a medicao.
    const filhos = [...document.querySelectorAll('.admin-topbar-right > *')]
      .map((c) => c.getBoundingClientRect())
      .filter((r) => r.width > 0)
      .map((r) => Math.round(r.x))
    return {
      esquerdaAcaba: Math.round(e.right),
      primeiroDaDireita: Math.min(...filhos),
      transbordo: document.documentElement.scrollWidth - window.innerWidth,
    }
  })

  // O grupo da direita tem `justify-content: flex-end`: quando o conteudo nao
  // cabe, os filhos saem pela esquerda da propria caixa e aterram por cima do
  // titulo. Medir a caixa nao chega — ha que medir o primeiro filho.
  expect(caixas.primeiroDaDireita, 'os controlos tapam o titulo').toBeGreaterThanOrEqual(
    caixas.esquerdaAcaba,
  )
  expect(caixas.transbordo, 'a pagina rola na horizontal').toBe(0)
})

test('a tabela vira cartoes, e o texto quebra dentro deles', async ({ page }) => {
  await irPara(page, '/app/audit')
  const celula = page.locator('.admin-table tbody td').first()
  await expect(celula).toBeVisible({ timeout: 20_000 })

  // O TableCell do shadcn traz `whitespace-nowrap`. Em ecra largo o contentor
  // rola e esta tudo bem; aqui cada linha e um cartao sem rolamento nenhum, e
  // um texto que nao quebra sai pela borda fora.
  await expect(celula).toHaveCSS('white-space', 'normal')

  // O nome da coluna vem do `data-label`, que e o que faz o cartao legivel.
  await expect(celula).toHaveAttribute('data-label', /.+/)
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBe(0)
})
