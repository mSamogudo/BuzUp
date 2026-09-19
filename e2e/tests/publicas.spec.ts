import { test, expect } from '@playwright/test'
import { esperarAppPronta, irPara } from './apoio'

/** Paginas que o passageiro ve sem autenticacao.
 *  Verificam que renderizam e nao rebentam — nao o aspecto, que vai mudar. */

const ROTAS = [
  { nome: 'landing', caminho: '/', marca: /busup/i },
  { nome: 'login', caminho: '/login', marca: /iniciar sess|sign in/i },
  { nome: 'descarregar apps', caminho: '/baixar', marca: /android|descarregar|instal/i },
]

for (const { nome, caminho, marca } of ROTAS) {
  test(`${nome} abre e mostra conteudo`, async ({ page }) => {
    const errosDeConsola: string[] = []
    page.on('console', (m) => {
      if (m.type() === 'error') errosDeConsola.push(m.text())
    })
    page.on('pageerror', (e) => errosDeConsola.push(`pageerror: ${e.message}`))

    await irPara(page, caminho)

    await expect(page.locator('body')).toContainText(marca)
    // Uma pagina em branco tambem "carrega": exigir substancia.
    await expect
      .poll(async () => (await page.locator('body').innerText()).trim().length, { timeout: 20_000 })
      .toBeGreaterThan(120)

    // Excepcoes: recursos externos e ruido de desenvolvimento, nada mais.
    //
    // O aviso `fetchPriority` esteve aqui tolerado enquanto a app corria em
    // React 18. Saiu da lista na fase 1, com a subida para o React 19, que
    // reconhece a prop. Se voltar a aparecer, e regressao — nao ruido.
    const graves = errosDeConsola.filter(
      (e) => !/favicon|manifest|sw\.js|ResizeObserver|Download the React DevTools/i.test(e),
    )
    expect(graves, `erros de consola em ${caminho}:\n${graves.join('\n')}`).toHaveLength(0)
  })
}

test('a compra de bilhete sugere paragens vindas do backend', async ({ page }) => {
  await page.goto('/comprar', { waitUntil: 'networkidle' })
  await esperarAppPronta(page)

  // O assistente comeca no passo "Viagem"; origem e destino sao campos de
  // sugestao (input[role=combobox]), nao selects nativos.
  await expect(page.getByText(/para onde vai/i)).toBeVisible({ timeout: 20_000 })

  const origem = page.getByRole('combobox').first()
  await origem.click()
  await origem.fill('a')

  // As sugestoes provam que a rota publica /api fala com o backend.
  const sugestoes = page.getByRole('option').or(page.locator('[class*=suggest] li, [class*=option]'))
  await expect(sugestoes.first()).toBeVisible({ timeout: 15_000 })

  await expect(page.getByRole('button', { name: /procurar partidas/i })).toBeVisible()
})
