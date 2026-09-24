// Auditoria de contraste sobre o que o browser desenha, nao sobre a tabela
// de tokens.
//
// Uma tabela de pares foreground/background diz o que se pretendeu; isto diz
// o que saiu. Percorre cada pagina nos dois temas, apanha todo o texto
// visivel, resolve o fundo real subindo a arvore ate encontrar um opaco, e
// compara contra o limite da WCAG AA que se aplica AQUELE tamanho de letra.
//
//   node contraste.mjs            todas as rotas
//   node contraste.mjs /app       so uma
import { chromium } from '@playwright/test'

const BASE = process.env.BUZUP_BASE_URL ?? 'http://localhost:3008'

const PUBLICAS = ['/', '/tpm-tur', '/tpm-tur/sobre-nos', '/tpm-tur/servicos',
  '/tpm-tur/frota', '/tpm-tur/nossas-politicas', '/tpm-tur/contactos', '/login', '/comprar', '/checkout', '/baixar']
const PRIVADAS = [
  '/app', '/app/routes', '/app/stops', '/app/vehicles', '/app/drivers', '/app/trips',
  '/app/fares', '/app/packages', '/app/passengers', '/app/wallets', '/app/cards/physical',
  '/app/financial', '/app/guest-checkouts', '/app/devices', '/app/pos-sessions', '/app/map',
  '/app/releases', '/app/users', '/app/reports', '/app/agent-revenue', '/app/audit',
  '/app/branding', '/app/terms', '/portal', '/driver', '/profile',
]

/** Executado dentro da pagina: junta cada texto visivel ao seu fundo real. */
function recolher() {
  const lum = ([r, g, b]) => {
    const c = [r, g, b].map((v) => {
      const x = v / 255
      return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4
    })
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
  }
  const razao = (a, b) => {
    const [la, lb] = [lum(a), lum(b)]
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
  }
  /** Aceita `rgb()`, `rgba()` e `color(srgb ...)`.
   *  A ultima traz os canais de 0 a 1 — lidos como 0-255 davam quase preto,
   *  e a auditoria inventava falhas de contraste que nao existiam. */
  const rgb = (s) => {
    const m = s.match(/[\d.]+/g)
    if (!m) return null
    const esc = s.startsWith('color(')
    const k = esc ? 255 : 1
    const v = [+m[0] * k, +m[1] * k, +m[2] * k].map((x) => Math.min(255, Math.round(x)))
    return { v, a: m[3] === undefined ? 1 : +m[3] }
  }
  /** O fundo efectivo: sobe ate encontrar um opaco, compondo o que for
   *  translucido pelo caminho. Um `rgba(0,0,0,0)` nao e preto — e o que
   *  estiver por tras. */
  const fundoDe = (el) => {
    const pilha = []
    for (let n = el; n; n = n.parentElement) {
      const cs = getComputedStyle(n)
      // Um degrade ou uma imagem deixam `backgroundColor` transparente. Se
      // continuasse a subir, media-se o texto contra o fundo da PAGINA e
      // inventavam-se falhas: os avatares e os botoes com degrade davam
      // "branco sobre branco" quando por baixo tinham teal.
      if (cs.backgroundImage !== 'none') return null
      // E o mesmo vale quando quem pinta e um pseudo-elemento. O hero da
      // TPM-TUR poe a fotografia e o veu navy num `::after` com
      // `z-index: -1`: o elemento nao tem fundo nenhum, e o texto branco
      // aparecia como "branco sobre branco".
      for (const pseudo of ['::before', '::after']) {
        const ps = getComputedStyle(n, pseudo)
        if (ps.content === 'none') continue
        if (ps.backgroundImage !== 'none') return null
        const pc = rgb(ps.backgroundColor)
        if (pc && pc.a > 0.05) return null
      }
      const c = rgb(cs.backgroundColor)
      if (!c || c.a === 0) continue
      pilha.push(c)
      if (c.a === 1) break
    }
    if (!pilha.length) return [255, 255, 255]
    let f = pilha[pilha.length - 1].v
    for (let i = pilha.length - 2; i >= 0; i--) {
      const { v, a } = pilha[i]
      f = f.map((x, k) => Math.round(v[k] * a + x * (1 - a)))
    }
    return f
  }

  const achados = []
  const vistos = new Set()
  for (const el of document.querySelectorAll('body *')) {
    // So elementos com texto proprio; senao contava-se o mesmo texto uma vez
    // por cada ascendente.
    const texto = [...el.childNodes]
      .filter((n) => n.nodeType === 3)
      .map((n) => n.textContent.trim())
      .join(' ')
      .trim()
    if (!texto) continue

    const cs = getComputedStyle(el)
    if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) continue
    const cx = el.getBoundingClientRect()
    if (cx.width < 2 || cx.height < 2) continue

    const cor = rgb(cs.color)
    if (!cor || cor.a < 0.95) continue          // texto quase transparente: e decoracao
    const fundo = fundoDe(el)
    if (!fundo) continue                        // fundo pintado por imagem ou degrade
    const r = razao(cor.v, fundo)

    const px = parseFloat(cs.fontSize)
    const peso = parseInt(cs.fontWeight, 10) || 400
    const grande = px >= 24 || (px >= 18.66 && peso >= 700)
    const limite = grande ? 3 : 4.5
    if (r >= limite) continue

    const chave = `${el.className}|${texto.slice(0, 20)}|${r.toFixed(2)}`
    if (vistos.has(chave)) continue
    vistos.add(chave)

    achados.push({
      texto: texto.slice(0, 44),
      classe: (typeof el.className === 'string' ? el.className : '').slice(0, 52),
      cor: cs.color,
      fundo: `rgb(${fundo.join(', ')})`,
      px: Math.round(px),
      peso,
      razao: +r.toFixed(2),
      limite,
    })
  }
  return achados
}

const navegador = await chromium.launch()
const rotas = process.argv[2] ? [process.argv[2]] : [...PUBLICAS, ...PRIVADAS]
let total = 0

for (const tema of ['light', 'dark']) {
  const ctx = await navegador.newContext({
    storageState: 'playwright/.auth/admin.json',
    viewport: { width: 1440, height: 900 },
  })
  await ctx.addInitScript((t) => {
    localStorage.setItem('buzup_theme', t)
    localStorage.setItem('busup_landing_theme', t)
  }, tema)

  for (const rota of rotas) {
    const p = await ctx.newPage()
    try {
      await p.goto(BASE + rota, { waitUntil: 'domcontentloaded', timeout: 30_000 })
      await p.waitForTimeout(3500)
      const achados = await p.evaluate(recolher)
      if (achados.length) {
        console.log(`\n${tema.toUpperCase()}  ${rota}`)
        for (const a of achados.sort((x, y) => x.razao - y.razao)) {
          console.log(
            `  ${a.razao.toFixed(2)}:1 (min ${a.limite})  ${a.px}px/${a.peso}  ` +
            `${a.cor} sobre ${a.fundo}\n      "${a.texto}"  .${a.classe}`,
          )
        }
        total += achados.length
      }
    } catch (e) {
      console.log(`\n${tema.toUpperCase()}  ${rota}  — nao abriu: ${String(e).slice(0, 70)}`)
    }
    await p.close()
  }
  await ctx.close()
}

await navegador.close()
console.log(`\n${total} pares abaixo do minimo AA em ${rotas.length} rotas x 2 temas.`)
process.exit(total ? 1 : 0)
