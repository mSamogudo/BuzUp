import { expect, type Page } from '@playwright/test'

/** O portal abre num ecra de arranque enquanto carrega branding e dados.
 *  Ler a pagina antes de ele sair da frente da-nos o splash, nao a pagina —
 *  foi assim que o primeiro teste da landing falhou sem haver bug nenhum. */
export async function esperarAppPronta(page: Page, timeout = 30_000) {
  await expect(page.locator('.splash-screen')).toHaveCount(0, { timeout })
}

/** Os links da barra lateral, e so esses. Sem este limite, um link com o
 *  mesmo nome no corpo da pagina entra na conta e o teste clica no sitio errado. */
export function navegacao(page: Page) {
  return page.getByRole('navigation').first()
}

export async function irPara(page: Page, caminho: string) {
  await page.goto(caminho, { waitUntil: 'networkidle' })
  await esperarAppPronta(page)
}
