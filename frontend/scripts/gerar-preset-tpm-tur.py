"""Regenera themes/presets/tpm-tur.ts a partir de themes/tpm-tur.css.

O CSS e a fonte de verdade. Este espelho existe so para o customizador poder
VOLTAR ao tema depois de experimentar outro — se divergir, o botao "repor"
repoe uma coisa diferente da que a aplicacao arranca.
"""
import re
from pathlib import Path

# Relativo ao proprio ficheiro, e nao ao directorio de onde se corre: assim o
# script funciona de qualquer sitio.
TEMAS = Path(__file__).resolve().parent.parent / 'src' / 'themes'
css = (TEMAS / 'tpm-tur.css').read_text(encoding='utf-8')

def bloco(inicio):
    i = css.index(inicio) + len(inicio)
    return css[i:css.index('\n}', i)]

# `color-mix(...)` nao viaja para um mapa de hexes: resolve-se aqui, com os
# mesmos numeros que o CSS faria.
def resolver(valor, vars_do_bloco):
    m = re.fullmatch(r'color-mix\(in srgb, var\((--[\w-]+)\) (\d+)%, var\((--[\w-]+)\)\)', valor)
    if m:
        a = vars_do_bloco[m.group(1)]; p = int(m.group(2))/100; b = vars_do_bloco[m.group(3)]
        out = []
        for i in (1,3,5):
            ca, cb = int(a[i:i+2],16), int(b[i:i+2],16)
            out.append(round(ca*p + cb*(1-p)))
        return '#%02x%02x%02x' % tuple(out)
    m = re.fullmatch(r'var\((--[\w-]+)\)', valor)
    if m: return vars_do_bloco[m.group(1)]
    return valor

def ler(texto):
    brutos = dict(re.findall(r'^\s*(--[\w-]+):\s*([^;]+);', texto, re.M))
    return {k: resolver(v.strip(), brutos) for k, v in brutos.items()}

claro = ler(bloco(':root {'))
escuro_bruto = ler(bloco(".dark {"))
# O escuro so redeclara o que muda; o resto herda do claro.
escuro = {**claro, **escuro_bruto}

# As chaves que o customizador conhece, pela ordem em que ja estavam.
ORDEM = ['background','foreground','card','card-foreground','popover','popover-foreground',
 'primary','primary-foreground','secondary','secondary-foreground','muted','muted-foreground',
 'accent','accent-foreground','warning','warning-foreground','success','success-foreground',
 'destructive','destructive-foreground','border','input','ring',
 'chart-1','chart-2','chart-3','chart-4','chart-5',
 'sidebar','sidebar-foreground','sidebar-primary','sidebar-primary-foreground',
 'sidebar-accent','sidebar-accent-foreground','sidebar-border','sidebar-ring']

def corpo(m):
    linhas = []
    for k in ORDEM:
        v = m['--' + k]
        chave = k if re.fullmatch(r'[a-z]+', k) else f'"{k}"'
        linhas.append(f'        {chave}: "{v}",')
    return '\n'.join(linhas)

saida = f'''import type {{ ThemePreset }} from "../tipos";

/** O preset da TPM-TUR no formato do customizador.
 *
 * GERADO a partir de `themes/tpm-tur.css`, que e a fonte de verdade: e de la
 * que sai o estado inicial da aplicacao. Este objecto existe para o
 * customizador poder VOLTAR a este tema depois de experimentar outro.
 *
 * Nao editar a mao. Correr:
 *
 *     python3 frontend/scripts/gerar-preset-tpm-tur.py
 *
 * de qualquer directorio. Os `color-mix()` do CSS ficam aqui resolvidos
 * em hexadecimal, porque o customizador trabalha com um mapa de cores e nao
 * com expressoes.
 */
export const tpmTurPreset: ThemePreset = {{
  label: "TPM-TUR",
  styles: {{
    light: {{
{corpo(claro)}
    }},
    dark: {{
{corpo(escuro)}
    }},
  }},
}};
'''
(TEMAS / 'presets' / 'tpm-tur.ts').write_text(saida, encoding='utf-8')
print(f"{TEMAS / 'presets' / 'tpm-tur.ts'} regenerado")
