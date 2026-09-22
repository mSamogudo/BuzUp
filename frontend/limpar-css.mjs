// Remove regras CSS cujos selectores só vestem classes mortas.
//
// Usa PostCSS. Duas tentativas anteriores falharam por não usar um parser:
// uma com expressões regulares, que ao remover uma regra de dentro de um
// `@media` deixou um `}` órfão; outra a contar chaves à mão, que desalinha
// porque há chaves dentro de comentários. CSS tem gramática; tratá-lo como
// texto dá build partido.
//
//   node limpar-css.mjs src/styles.css --classe=foo --classe=bar
//   node limpar-css.mjs src/styles.css --classe=foo --aplicar

import { readFileSync, writeFileSync } from 'node:fs'
import postcss from 'postcss'

const ficheiro = process.argv[2]
const aplicar = process.argv.includes('--aplicar')
const mortas = new Set(
  process.argv.filter((a) => a.startsWith('--classe=')).map((a) => a.slice(9)),
)

if (!ficheiro || mortas.size === 0) {
  console.error('uso: node limpar-css.mjs <ficheiro.css> --classe=<nome> [...] [--aplicar]')
  process.exit(1)
}

/** Um selector só é removível se TODAS as classes que cita estiverem mortas.
 *  Um selector sem classes nenhumas (`body`, `*`) nunca é tocado. */
function soVesteMortas(seletor) {
  const classes = [...seletor.matchAll(/\.(-?[_a-zA-Z][\w-]*)/g)].map((m) => m[1])
  return classes.length > 0 && classes.every((c) => mortas.has(c))
}

const css = readFileSync(ficheiro, 'utf8')
const raiz = postcss.parse(css, { from: ficheiro })

let removidas = 0
let podadas = 0
const removidosPorNome = new Map()

raiz.walkRules((regra) => {
  // Dentro de @keyframes os "selectores" são `from`/`to`/percentagens.
  if (regra.parent?.type === 'atrule' && /keyframes/.test(regra.parent.name)) return

  const partes = regra.selectors ?? []
  const mortasAqui = partes.filter(soVesteMortas)
  if (mortasAqui.length === 0) return

  for (const s of mortasAqui) {
    removidosPorNome.set(s, (removidosPorNome.get(s) ?? 0) + 1)
  }

  if (mortasAqui.length === partes.length) {
    regra.remove()
    removidas++
  } else {
    regra.selectors = partes.filter((s) => !mortasAqui.includes(s))
    podadas++
  }
})

// At-rules que ficaram sem nada dentro (um @media que só continha regras mortas).
let vazias = 0
raiz.walkAtRules((at) => {
  if (['media', 'supports', 'layer', 'container'].includes(at.name) && at.nodes?.length === 0) {
    at.remove()
    vazias++
  }
})

const saida = raiz.toString()
console.log(`regras removidas por inteiro : ${removidas}`)
console.log(`selectores podados de grupos : ${podadas}`)
console.log(`at-rules que ficaram vazias  : ${vazias}`)
console.log(`linhas                       : ${css.split('\n').length} -> ${saida.split('\n').length}`)
console.log('\nselectores afectados:')
for (const [s, n] of [...removidosPorNome].sort()) console.log(`   ${n}x  ${s}`)

if (aplicar) {
  writeFileSync(ficheiro, saida)
  console.log('\nescrito.')
} else {
  console.log('\n(simulacao — usar --aplicar para escrever)')
}
