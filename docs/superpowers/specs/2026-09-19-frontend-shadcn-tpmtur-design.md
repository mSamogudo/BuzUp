# Frontend BusUp — migração para shadcn com identidade TPM-TUR

Data: 2026-09-19 · Estado: aprovado, por executar

## O que se vai fazer

Substituir a fundação de estilos do `frontend/` — hoje 7 245 linhas de CSS à mão sobre
React 18 sem Tailwind — por Tailwind 4 e os componentes shadcn do template em
`~/GitHub/shadcn-dashboard-landing-template-main/vite-version`, trazendo o Theme
Customizer desse template e aplicando a identidade visual da TPM-TUR como preset
por omissão.

O backend não é tocado. Nenhuma alteração em Django, API, modelos ou base de dados.

### Ponto de partida medido

| | Frontend BusUp | Template |
|---|---|---|
| React | 18.3.1 | 19.2.3 |
| Tailwind | nenhum | 4.1 |
| Router | react-router-dom 6.30.3 | 7.11 |
| Estilos | 7 245 linhas CSS próprio | utilitários + 39 componentes |
| Código | 80 ficheiros, 18 565 linhas TS/TSX | 203 ficheiros |

Cores fora do sistema de tokens, a converter: **547 ocorrências** —
326 em `styles.css`, 61 em `auth/login.css`, 69 em `public/landing/landing.css`,
91 espalhadas por 11 ficheiros `.tsx`.

## Decisões tomadas

Todas do Edírcio, em conversa de 2026-09-19.

1. **Âmbito:** todo o frontend, as 80 páginas, até à última.
2. **Linguagem visual:** a do site TPM-TUR, que fica como referência e não é alterado.
3. **Cor de acção:** teal em todo o lado — portal e páginas públicas, sem excepções.
4. **Tema escuro:** mantém-se, com variante derivada do navy da TPM-TUR.
5. **Tipografia:** Manrope nos títulos, Inter na interface densa.
6. **Método:** tokens primeiro, depois conversão página a página.
7. **Verificação:** screenshots antes/depois *e* testes de fumo automatizados.

### Decisão anterior revista

Antes de o shadcn entrar no âmbito, tinha sido escolhido repintar o `styles.css`
substituindo as 547 cores soltas por tokens. Com a migração, esse ficheiro deixa de
ser repintado e passa a ser desmontado: as cores vivem nas variáveis do shadcn e o
`styles.css` encolhe à medida que as páginas convertem. A caça às 547 continua, mas
dentro da migração e não como tarefa autónoma.

## Arquitectura

### React 19 é obrigatório, não opcional

Nenhum dos 39 componentes do template usa `forwardRef`; todos dependem do `ref` como
prop, que só existe no React 19. Em React 18 o ref chega a `undefined` sem erro e os
primitivos Radix falham no posicionamento de popovers, na gestão de foco e na detecção
de clique fora.

Efeito lateral positivo: o `react-leaflet` 5.0.0 instalado declara
`peerDependencies.react: ^19.0.0` e corre hoje sobre 18.3.1. A página do mapa está
numa combinação não suportada pela própria biblioteca; a subida corrige-o.
`recharts` 3.8.1, `sonner` e `react-router-dom` 6.30.3 já aceitam React 19.

### O dourado não pode ser `--accent`

No shadcn, `--accent` é o fundo subtil de hover e item seleccionado, não a cor de
marca. Pôr lá o dourado da TPM-TUR tornaria dourado tudo o que o rato toca. O dourado
recebe variáveis próprias:

| Variável | Papel |
|---|---|
| `--primary` | acção — botões, ligações, estado activo |
| `--accent` | hover subtil, neutro, tingido de navy |
| `--warning` *(nova)* | atenção, pendentes, avisos — o dourado |
| `--success` *(nova)* | confirmações |

Sem esta separação, a única cor que o utilizador precisa de ler como "olha para aqui"
ficaria espalhada por toda a interface.

### Hierarquia de marca

Três entidades, três papéis, e nenhuma substitui a outra:

- **UpDigital, Lda** — quem desenvolve. Aparece como "powered by" no rodapé da
  autenticação e da barra lateral.
- **BusUp** — o produto. Identidade própria; logótipos a substituir pelos novos.
- **TPM-TUR, SA** — o operador cliente. O logótipo entra pelos slots da API de
  branding (`primary_logo_url`, `sidebar_logo_url`, `auth_logo_url`, …), que devolve
  apenas logótipos e contactos — nunca cores.

A grafia do produto é **BusUp**, com S. O repositório contém 577 ocorrências de
"BuzUp" (README, `pos_app`, backend) contra 94 de "BusUp"; a forma com S é a que o
frontend público e os ficheiros de logótipo usam, e é a correcta para texto visível.
A inconsistência no resto do repositório fica fora deste trabalho.

### Preset TPM-TUR

Os 28 pares foreground/background foram verificados: **todos passam WCAG AA**.
Regra que sai da verificação e fica escrita no preset: branco sobre dourado dá 2,02:1
e chumba — sobre dourado, o texto é sempre navy.

#### Claro

```
--background #eef3f8   --foreground #102d4f
--card #ffffff         --card-foreground #102d4f
--popover #ffffff      --popover-foreground #102d4f
--primary #087d99      --primary-foreground #ffffff
--secondary #e2ebf3    --secondary-foreground #102d4f
--muted #f1f6fa        --muted-foreground #5c6f83
--accent #e4ecf4       --accent-foreground #102d4f
--warning #e9ac35      --warning-foreground #3a2a06
--success #1d7a5f      --success-foreground #ffffff
--destructive #b3261e  --border #dbe5ee  --input #c3d2e0  --ring #087d99
--sidebar #102d4f              --sidebar-foreground #9dbbdd
--sidebar-primary #087d99      --sidebar-primary-foreground #ffffff
--sidebar-accent #1b3f66       --sidebar-accent-foreground #e8eef5
--sidebar-border #1e3a58       --sidebar-ring #35b9d8
```

#### Escuro

```
--background #081624   --foreground #e8eef5
--card #102943         --card-foreground #e8eef5
--popover #102943      --popover-foreground #e8eef5
--primary #35b9d8      --primary-foreground #062330
--secondary #16314f    --secondary-foreground #e8eef5
--muted #0d2137        --muted-foreground #93aac3
--accent #16314f       --accent-foreground #e8eef5
--warning #f0bc55      --warning-foreground #2b1f04
--success #4cc79f      --success-foreground #04241a
--destructive #ff6b6b  --border #22405e  --input #2c4d6f  --ring #35b9d8
--sidebar #050f1a              --sidebar-foreground #8fb0d4
--sidebar-primary #35b9d8      --sidebar-primary-foreground #062330
--sidebar-accent #12293f       --sidebar-accent-foreground #e8eef5
--sidebar-border #1a3550       --sidebar-ring #35b9d8
```

O texto de navegação da barra lateral é um tom de navy (48,5% de saturação), não um
cinzento. O portal usa hoje `#a1a1aa` sobre `#18181b` — 5% de saturação, cinzento
lavado sobre fundo colorido.

As séries `--chart-1` a `--chart-5` derivam da família teal/navy/dourado e são
definidas na fase 2, verificadas para distinguibilidade e não apenas para contraste.

### Tipografia

**Manrope** nos títulos e números de destaque; **Inter** em tabelas, formulários e
navegação. A escala do site TPM-TUR — Source Sans 3 a 18px — não transita: destruiria
a densidade das 40 páginas de tabelas. A cor faz o trabalho de marca, a tipografia de
interface faz o de legibilidade. Ambas alojadas localmente, sem pedido a terceiros.

## Fases

Cada fase fecha com testes de fumo verdes, screenshots comparados contra a base, e um
commit próprio. Se algo partir, sabe-se em que fase.

### Fase 0 — Rede de segurança

Não toca em código de produção. Escrever testes de fumo Playwright contra a aplicação
**actual, enquanto funciona**: autenticar, listar, filtrar, paginar, criar, abrir
detalhe, alternar tema, alternar idioma. Completar a base de screenshots de todas as
rotas, claro e escuro. Commit da base.

*Pronto quando:* os testes passam contra o código actual e a base cobre as rotas todas.

### Fase 1 — React 19, Tailwind 4, shadcn

Subir `react`, `react-dom` e `@types/react` para 19. O `sonner` 1.7.4 já declara
`react: ^18 || ^19` e não precisa de subir; fica opcional, à parte. Instalar Tailwind 4
via `@tailwindcss/vite`, a conviver com o `styles.css` existente. Adicionar
`components.json`, `lib/utils`, e os 39 componentes `ui/`.

*Pronto quando:* build e lint passam, os testes de fumo passam sem alteração, e os
screenshots são **iguais** aos da base. Nesta fase nada deve mudar visualmente.

### Fase 2 — Tema, preset e marcas

Portar `theme-provider`, `use-theme-manager`, os presets e o `theme-customizer`.
Escrever o preset TPM-TUR acima e torná-lo o definido por omissão. Ligar o
`html[data-theme]` actual ao `next-themes` sem partir a preferência guardada.
Substituir os quatro ficheiros em `frontend/public/assets/busup/` — `logo-light.png`
(fundo claro), `logo-dark.png` (fundo escuro), `mark.png` e `mark-light.png` (marca
reduzida, barra lateral recolhida). São lidos em seis sítios: `LoginPage`,
`LandingPage`, `CheckoutPage`, `BusPaymentPage` e `AdminLayout` (duas vezes), sempre
como fallback de `pickLogo()` — ou seja, o slot da API de branding ganha quando
preenchido, e é assim que a TPM-TUR aparece em produção. Esse comportamento mantém-se.
Instalar Manrope e Inter.

*Depende de:* ficheiros de logótipo fornecidos pelo Edírcio — BusUp claro e escuro,
UpDigital claro e escuro, de preferência SVG. Não estão no repositório: o
`assets/busup/logo-light.png` actual é "BUSUP" em maiúsculas e os novos são "BusUp"
em caixa mista.

*Pronto quando:* o Customizer troca presets, raio e variante de barra lateral em
tempo real; o preset TPM-TUR é o inicial; claro e escuro respeitam as tabelas acima.

### Fase 3 — A casca

`AdminLayout` para o `sidebar` do shadcn, com as variantes que o Customizer expõe
(`sidebar`/`floating`/`inset`, `offcanvas`/`icon`/`none`, esquerda/direita). Barra de
topo, migalhas, alternador de tema, perfil, notificações, gaveta móvel e navegação
inferior.

*Pronto quando:* a navegação funciona nas três variantes, em desktop e móvel, e os
testes de fumo continuam verdes.

### Fase 4 — Primitivas partilhadas

Botão, campo, select, textarea, checkbox, switch, tabela, diálogo, badge, separadores,
cartão, esqueleto, tooltip, popover, menu e toast. Os campos de data passam a
calendário em `dd/mm/aaaa`, como no site TPM-TUR — o portal sofre hoje do mesmo
problema, visível nos filtros do dashboard (`08/21/2026`).

*Pronto quando:* as primitivas estão convertidas e a maioria das páginas admin
herdou-as sem edição própria.

### Fase 5 — Páginas, em seis lotes

| Lote | Conteúdo |
|---|---|
| A | públicas: landing, login, comprar, checkout, bus, baixar |
| B | admin núcleo: dashboard, rotas, paragens, veículos, motoristas, viagens |
| C | financeiro: financeiro, carteiras, pagamentos, relatórios, receita de agentes |
| D | pessoas e cartões: passageiros, cartões físicos e digitais, pacotes, utilizadores, auditoria |
| E | operação: terminais, sessões POS, mapa, APKs, marca, termos |
| F | portais passageiro e motorista, perfil |

*Pronto quando:* cada lote fecha com testes verdes e screenshots revistos.

### Fase 6 — Limpeza

Apagar o CSS morto do `styles.css`, `login.css` e `landing.css`; varrer as cores
hardcoded que sobrarem das 547; auditoria final de contraste sobre o resultado real,
não sobre a tabela.

*Pronto quando:* zero cores hardcoded fora dos presets e o CSS próprio reduzido ao
que o Tailwind não cobre.

## Como isto se transforma em plano

Seis fases e 80 páginas não cabem num só plano de implementação executável. O plano a
escrever a seguir cobre **as fases 0 a 2** — rede de segurança, subida de fundação, e
tema com marcas — que é o bloco onde o risco se concentra e no fim do qual há algo
verificável. As fases 3 a 6 ganham plano próprio depois, já com o Customizer a
funcionar e com a base de comparação provada em uso.

## Riscos

- **A subida para React 19 mexe nas 80 páginas.** É o motivo da fase 0. Sem os testes
  de fumo escritos antes, uma regressão de comportamento passaria despercebida até
  produção.
- **O `styles.css` codifica comportamento responsivo conquistado a pulso.** A conversão
  por lotes, com screenshots, existe para o apanhar. Reescrever de uma vez foi
  ponderado e rejeitado por isso.
- **Migração longa com o produto a meio caminho.** Entre as fases 3 e 5 convivem
  páginas convertidas e por converter. É aceitável porque partilham os mesmos tokens:
  a cor e a tipografia ficam coerentes mesmo antes de a estrutura o estar.

## Fora de âmbito

- Backend, em qualquer forma.
- O site TPM-TUR em `output/tpm-tur-site/`, que fica como referência.
- A inconsistência BuzUp/BusUp fora do frontend.
- Tema por operador para além do preset TPM-TUR. O Theme Customizer torna-o possível
  e é a porta para o white-label, mas configurar um segundo operador não é deste
  trabalho.
