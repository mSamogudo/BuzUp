// Captura todas as rotas do portal em claro e escuro, para comparacao humana.
//
// Nao sao testes de regressao visual: o redesenho vai mudar TUDO de proposito,
// portanto uma assercao de imagem falharia sempre. Isto produz artefactos para
// olhar lado a lado.
//
//   node capturar.mjs antes
//   node capturar.mjs fase-1
//   node capturar.mjs fase-3
//
// Depois compara-se `capturas/antes/` com `capturas/fase-N/`.

import { chromium } from '@playwright/test'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'

const BASE = process.env.BUZUP_BASE_URL ?? 'http://localhost:3008'
const ETIQUETA = process.argv[2] ?? 'antes'
const DESTINO = path.join('capturas', ETIQUETA)

const PUBLICAS = [
  ['landing', '/'],
  ['login', '/login'],
  ['comprar', '/comprar'],
  ['checkout', '/checkout'],
  ['baixar', '/baixar'],
]

const PORTAL = [
  ['dashboard', '/app'],
  ['rotas', '/app/routes'],
  ['paragens', '/app/stops'],
  ['viagens', '/app/trips'],
  ['veiculos', '/app/vehicles'],
  ['motoristas', '/app/drivers'],
  ['tarifas', '/app/fares'],
  ['pacotes', '/app/packages'],
  ['passageiros', '/app/passengers'],
  ['carteiras', '/app/wallets'],
  ['cartoes-fisicos', '/app/cards/physical'],
  ['cartoes-digitais', '/app/cards/digital'],
  ['financeiro', '/app/financial'],
  ['bilhetes-ocasionais', '/app/guest-checkouts'],
  ['sessoes-pos', '/app/pos-sessions'],
  ['terminais', '/app/devices'],
  ['mapa', '/app/map'],
  ['apks', '/app/releases'],
  ['utilizadores', '/app/users'],
  ['relatorios', '/app/reports'],
  ['receita-agentes', '/app/agent-revenue'],
  ['auditoria', '/app/audit'],
  ['marca', '/app/branding'],
  ['termos', '/app/terms'],
]

// O splash e o fallback de Suspense das rotas lazy. Em Vite de desenvolvimento
// a primeira visita compila o chunk, e isso pode demorar.
//
// Esta funcao ATIRA em vez de engolir o timeout, de proposito: era o `.catch`
// silencioso que deixava passar capturas do proprio splash. Oito imagens da
// primeira base eram ecras de arranque, e comparavam como iguais entre si —
// seguranca falsa, que e pior do que nenhuma.
async function semSplash(page, timeout = 45_000) {
  await page.waitForFunction(() => !document.querySelector('.splash-screen'), null, { timeout })
}

async function estabilizar(page) {
  await semSplash(page)
  // Ja sem splash: garantir que ha conteudo a serio antes de fotografar.
  await page.waitForFunction(() => document.body.innerText.trim().length > 60, null, { timeout: 20_000 })
  // Percorre a pagina para disparar lazy-loading de imagens e graficos.
  await page.evaluate(async () => {
    for (let y = 0; y < document.body.scrollHeight; y += 500) {
      window.scrollTo(0, y)
      await new Promise((r) => setTimeout(r, 70))
    }
    window.scrollTo(0, 0)
  })
  // As imagens `loading="lazy"` so comecam a descarregar perto da janela, e os
  // cartoes da landing so sao montados por um IntersectionObserver. Esperar por
  // elas nao chega — e preciso obriga-las a comecar.
  //
  // (Uma primeira versao desta espera aceitava `currentSrc === ''` como
  // "completa", o que dava por carregada precisamente a imagem que ainda nem
  // tinha comecado. Dois cartoes da landing sairam vazios por causa disso.)
  await page.evaluate(() => {
    for (const img of document.images) img.loading = 'eager'
  })
  await page
    .waitForFunction(() => [...document.images].every((i) => i.complete), null, { timeout: 30_000 })
    .catch(() => {})

  // Os graficos Recharts animam as barras a crescer (~1500ms). Esperar um
  // tempo fixo apanha-os a meio e produz "diferencas" que sao so animacao —
  // foi assim que o dashboard apareceu com barras a 20% do valor real.
  // Em vez de adivinhar, esperar ate a pagina parar de mudar.
  await estabilizarAnimacoes(page)
}

/** Fotografa repetidamente ate duas capturas seguidas serem iguais. */
async function estabilizarAnimacoes(page, maxTentativas = 12, intervalo = 450) {
  let anterior = null
  for (let i = 0; i < maxTentativas; i++) {
    await page.waitForTimeout(intervalo)
    const actual = await page.screenshot({ type: 'jpeg', quality: 40 })
    if (anterior && Buffer.compare(anterior, actual) === 0) return
    anterior = actual
  }
}

// O Vite de desenvolvimento compila cada rota na primeira visita, e reoptimiza
// tudo quando o lockfile muda. A primeira tentativa paga essa compilacao e pode
// estourar; a segunda ja encontra o modulo em cache. Sem esta repeticao, uma
// captura logo a seguir a um `npm install` perde metade das paginas.
async function capturar(page, nome, caminho, tema, tentativas = 2) {
  for (let i = 1; i <= tentativas; i++) {
    try {
      await page.goto(BASE + caminho, { waitUntil: 'networkidle', timeout: 90_000 })
      await estabilizar(page)
      await page.screenshot({
        path: path.join(DESTINO, `${nome}-${tema}.png`),
        fullPage: true,
        timeout: 60_000,
      })
      process.stdout.write(`  ${tema.padEnd(6)} ${nome}${i > 1 ? ' (2a tentativa)' : ''}\n`)
      return
    } catch (e) {
      if (i === tentativas) {
        process.stdout.write(`  ${tema.padEnd(6)} ${nome}  <<< FALHOU: ${e.message.split('\n')[0]}\n`)
      }
    }
  }
}

const navegador = await chromium.launch()
const contexto = await navegador.newContext({
  viewport: { width: 1440, height: 900 },
  locale: 'pt-PT',
  timezoneId: 'Africa/Maputo',
})
const page = await contexto.newPage()
await mkdir(DESTINO, { recursive: true })

console.log(`\nA capturar para capturas/${ETIQUETA}/  (${BASE})\n`)

console.log('Publicas:')
for (const [nome, caminho] of PUBLICAS) await capturar(page, nome, caminho, 'claro')

// Autenticar uma vez para o portal.
await page.goto(BASE + '/login', { waitUntil: 'networkidle' })
await semSplash(page)
await page.locator('input').first().fill(process.env.BUZUP_USER ?? 'admin')
await page.locator('input[type=password]').fill(process.env.BUZUP_PASS ?? 'admin')
await page.getByRole('button', { name: /entrar/i }).first().click()
await page.waitForURL(/\/app/, { timeout: 30_000 })

for (const tema of ['claro', 'escuro']) {
  console.log(`\nPortal (${tema}):`)
  await page.goto(BASE + '/app', { waitUntil: 'networkidle' })
  await semSplash(page)
  // A chave e `buzup_theme` (ui/UiPreferences.tsx). Forcar so o atributo
  // data-theme nao chega: a app rele a preferencia a cada navegacao e repoe-o.
  await page.evaluate((t) => {
    localStorage.setItem('buzup_theme', t === 'escuro' ? 'dark' : 'light')
  }, tema)
  await page.reload({ waitUntil: 'networkidle' })
  await semSplash(page)
  for (const [nome, caminho] of PORTAL) await capturar(page, nome, caminho, tema)
}

await navegador.close()
console.log(`\nPronto. ${DESTINO}\n`)
