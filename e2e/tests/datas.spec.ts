import { test, expect } from '@playwright/test'
import { irPara } from './apoio'

/** Os campos de data.
 *
 *  O `<input type="date">` nativo mostrava a data na locale do BROWSER, nao
 *  na da aplicacao: um telemovel em ingles mostrava `mm/dd/aaaa` a quem
 *  espera o contrario, e nos filtros do dashboard isso troca o intervalo sem
 *  ninguem reparar.
 *
 *  O que aqui se protege e a fronteira: dd/mm/aaaa para quem le, AAAA-MM-DD
 *  para a API. Se alguem trocar o componente e usar `toISOString()`, o teste
 *  do fuso apanha-o. */

test.beforeEach(async ({ page }) => {
  await irPara(page, '/app')
  await expect(page.locator('.campo-data-botao').first()).toBeVisible({ timeout: 20_000 })
})

test('mostra as datas em dd/mm/aaaa', async ({ page }) => {
  const textos = await page.locator('.campo-data-botao').allTextContents()
  expect(textos.length).toBeGreaterThan(0)
  for (const texto of textos) {
    expect(texto.trim(), 'formato do campo').toMatch(/^\d{2}\/\d{2}\/\d{4}$/)
  }
})

test('o calendario abre em portugues, com a semana a comecar a segunda', async ({ page }) => {
  await page.locator('.campo-data-botao').first().click()
  const dias = page.locator('[data-slot=popover-content] .rdp-weekday, [data-slot=popover-content] thead th')
  await expect(dias.first()).toHaveText('seg')
  await expect(page.locator('[data-slot=popover-content]')).toContainText(
    /janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro/i,
  )
})

test('escolher um dia actualiza o ecra e envia ISO a API', async ({ page }) => {
  const pedidos: string[] = []
  page.on('request', (r) => {
    if (r.url().includes('date_from=')) pedidos.push(r.url())
  })

  await page.locator('.campo-data-botao').first().click()
  await page.locator('[data-slot=popover-content] button[data-day]').filter({ hasText: /^10$/ }).first().click()

  // Quem le ve dd/mm/aaaa...
  await expect
    .poll(async () => (await page.locator('.campo-data-botao').first().innerText()).trim(), { timeout: 10_000 })
    .toMatch(/^10\/\d{2}\/\d{4}$/)

  // ...e a API recebe AAAA-MM-DD, com o dia 10 e nao o 9.
  // (`toISOString()` converteria para UTC e, ao fim da tarde em Maputo,
  //  mandaria o dia anterior. E o erro classico deste componente.)
  await expect.poll(() => pedidos.length, { timeout: 15_000 }).toBeGreaterThan(0)
  const ultimo = pedidos[pedidos.length - 1]
  expect(ultimo).toMatch(/date_from=\d{4}-\d{2}-10\b/)
})
