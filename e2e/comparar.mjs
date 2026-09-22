// Compara duas pastas de capturas e ordena por percentagem de pixeis
// diferentes. Tamanhos diferentes contam como "altura mudou" e nao como
// diferenca de pixeis — a pagina cresceu ou encolheu, que e outra coisa.
import { readdirSync, readFileSync } from 'node:fs'
import { PNG } from 'pngjs'
import pixelmatch from 'pixelmatch'

const [a, b] = process.argv.slice(2)
if (!a || !b) { console.error('uso: node comparar.mjs <pastaA> <pastaB>'); process.exit(1) }

const linhas = []
for (const nome of readdirSync(a).filter((f) => f.endsWith('.png'))) {
  let pa, pb
  try { pa = PNG.sync.read(readFileSync(`${a}/${nome}`)); pb = PNG.sync.read(readFileSync(`${b}/${nome}`)) }
  catch { linhas.push([Infinity, nome, 'em falta']); continue }
  if (pa.width !== pb.width || pa.height !== pb.height) {
    linhas.push([Infinity, nome, `${pa.width}x${pa.height} -> ${pb.width}x${pb.height}`])
    continue
  }
  const n = pixelmatch(pa.data, pb.data, null, pa.width, pa.height, { threshold: 0.12 })
  linhas.push([(n / (pa.width * pa.height)) * 100, nome, ''])
}

linhas.sort((x, y) => y[0] - x[0])
for (const [pct, nome, nota] of linhas) {
  if (pct === Infinity) console.log(`  ——      ${nome.padEnd(34)} ${nota}`)
  else if (pct > 0.05) console.log(`  ${pct.toFixed(2).padStart(6)}%  ${nome}`)
}
const finitos = linhas.filter((l) => l[0] !== Infinity)
const media = finitos.reduce((s, l) => s + l[0], 0) / finitos.length
console.log(`\n${finitos.length} comparadas, media ${media.toFixed(2)}%; ${linhas.length - finitos.length} com tamanho diferente`)
