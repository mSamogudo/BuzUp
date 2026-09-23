// Uma imagem horizontal por seccao, a partir da pagina a serio.
//
// Nao sao comps desenhados: e o que o browser renderiza, com os tokens do
// operador e as fotografias reais. Serve de referencia de desenho e de prova
// de que o desenho existe em codigo.
//
//   node seccoes.mjs /tpm-tur antes
//   node seccoes.mjs /tpm-tur depois
import { mkdir, writeFile } from 'node:fs/promises'
import { chromium } from '@playwright/test'

const BASE = process.env.BUZUP_BASE_URL ?? 'http://localhost:3008'
const ROTA = process.argv[2] ?? '/tpm-tur'
const ETIQUETA = process.argv[3]
if (!ETIQUETA) {
  console.error('uso: node seccoes.mjs <rota> <etiqueta>')
  process.exit(1)
}

const LARGURA = 1600
const DESTINO = `capturas/seccoes/${ETIQUETA}`
await mkdir(DESTINO, { recursive: true })

const navegador = await chromium.launch()
const ctx = await navegador.newContext({
  viewport: { width: LARGURA, height: 900 },
  deviceScaleFactor: 2,
})
await ctx.addInitScript(() => localStorage.setItem('busup_landing_theme', 'light'))
const p = await ctx.newPage()

await p.goto(BASE + ROTA, { waitUntil: 'networkidle' })

// As seccoes aparecem por IntersectionObserver: rolar ate ao fim monta-as
// todas antes de medir. Sem isto, metade sai vazia.
await p.evaluate(async () => {
  const passo = window.innerHeight * 0.8
  for (let y = 0; y < document.body.scrollHeight; y += passo) {
    window.scrollTo(0, y)
    await new Promise((r) => setTimeout(r, 120))
  }
  window.scrollTo(0, 0)
})

// E esperar pelas imagens, que sao o material principal desta pagina.
await p.evaluate(async () => {
  const imgs = [...document.images]
  imgs.forEach((i) => { i.loading = 'eager' })
  await Promise.all(imgs.map((i) => i.complete ? null : new Promise((r) => {
    i.addEventListener('load', r, { once: true })
    i.addEventListener('error', r, { once: true })
  })))
})
await p.waitForTimeout(1200)

const seccoes = await p.evaluate(() => {
  const alvos = [...document.querySelectorAll('main > section, main > div > section')]
  return alvos.map((s, i) => {
    const r = s.getBoundingClientRect()
    const nome = s.id || s.className.split(' ').find((c) => c.startsWith('tpm-') || c.startsWith('bzlp-')) || `seccao-${i}`
    return { nome, y: Math.round(r.y + window.scrollY), altura: Math.round(r.height) }
  })
})

console.log(`${seccoes.length} seccoes em ${ROTA}\n`)

/** Dispara quando dois disparos seguidos saem iguais.
 *
 *  As seccoes entram com uma animacao de revelacao (opacidade e escala). Uma
 *  captura a meio mostra cartoes estreitos com o texto cortado — cheguei a
 *  tomar isso por dois defeitos da pagina que nao existem: o "team building"
 *  cortado parecia um erro de escrita, e o transbordo medido ao vivo e zero.
 *  Nao se julga desenho a partir de um fotograma em movimento. */
async function disparoEstavel(caixa) {
  let anterior = null
  for (let tentativa = 0; tentativa < 12; tentativa++) {
    const agora = await p.screenshot({ clip: caixa })
    if (anterior && Buffer.compare(anterior, agora) === 0) return { imagem: agora, tentativas: tentativa }
    anterior = agora
    await p.waitForTimeout(250)
  }
  return { imagem: anterior, tentativas: -1 }
}

let n = 0
for (const s of seccoes) {
  n++
  // Enquadramento horizontal: nunca mais alto do que a janela, para a imagem
  // continuar a ler-se como uma faixa de pagina e nao como um poster.
  const altura = Math.min(s.altura, 900)
  await p.evaluate((y) => window.scrollTo(0, y), s.y)
  await p.waitForTimeout(350)

  // Onde e que a seccao ficou DENTRO da janela. No fim da pagina o scroll ja
  // nao avanca, e recortar sempre a partir de y=0 dava o fim da seccao
  // anterior: a faixa de contacto mostrava a cauda do FAQ.
  const topo = await p.evaluate((sel) => {
    const el = sel.startsWith('#') ? document.querySelector(sel) : null
    return el ? Math.max(0, Math.round(el.getBoundingClientRect().y)) : 0
  }, s.nome.startsWith('bzlp') || s.nome.startsWith('tpm') ? '' : `#${s.nome}`)
  const caber = Math.min(altura, 900 - topo)

  const { imagem, tentativas } = await disparoEstavel({ x: 0, y: topo, width: LARGURA, height: caber })
  const ficheiro = `${DESTINO}/${String(n).padStart(2, '0')}-${s.nome}.png`
  await writeFile(ficheiro, imagem)
  const nota = tentativas < 0 ? '  (nao assentou!)' : ''
  console.log(`  ${String(n).padStart(2, '0')}  ${s.nome.padEnd(22)} ${s.altura}px -> ${caber}px (topo ${topo})${nota}`)
}

await navegador.close()
console.log(`\nEscrito em ${DESTINO}`)
