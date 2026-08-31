# Design tokens e padrões partilhados

Tudo aqui é comum ao Portal, ao site público, ao CMS, ao POS e à app mobile.

## 1. Cor

Variáveis CSS, tema claro (`:root`) e escuro (`html[data-theme="dark"]`):

| Token | Claro | Escuro | Uso |
|---|---|---|---|
| `--bg` | `#E7EDF5` | `#06203A` | fundo da página |
| `--surface` | `#FFFFFF` | `#0A2E50` | cartões, barra lateral, cabeçalho |
| `--surface2` | `#F6F9FD` | `#0C3557` | área de conteúdo, cabeçalhos de tabela |
| `--surface3` | `#FBFDFF` | `#0E3A5E` | campos de formulário |
| `--border` | `#E4EBF3` | `#1A4368` | linhas de 1px |
| `--border2` | `#D7E2EF` | `#22527A` | contorno de campos e botões |
| `--text` | `#0F1B2D` | `#EAF1F8` | texto principal |
| `--muted` | `#5B6B7F` | `#A9C2DC` | texto secundário |
| `--muted2` | `#8A9AAD` | `#8AA6C2` | metadados |
| `--faint` | `#A8B7C8` | `#6F8CAA` | rótulos, marcas de água |
| `--navy-text` | `#0D3B66` | `#CFE6FB` | títulos sobre azul claro |
| `--accent` | `#2D8CF0` | `#2D8CF0` | azul de acção |
| `--accent-dk` | `#1D5FA7` | `#5BA3F5` | links, ícones activos |
| `--sky1` | `#CFE6FB` | `#0C3557` | fundos de destaque |
| `--sky2` | `#E8F2FC` | `#10406A` | fundos suaves, avatares |

Cores fixas fora dos tokens: azul de acção `#2D8CF0` (botões primários e barra
activa), azul escuro `#0D3B66` (superfícies e botões escuros, painéis navy),
branco `#FFFFFF` sobre azul.

Sobre painéis navy (`#0D3B66`) o texto usa `rgba(234,241,248,…)`: `.66` para corpo,
`.5` para rótulos, `.12` para linhas.

## 2. Estados (paleta TONE)

Sempre em pílula de raio 999px, altura 24–26px, `font: 700 11px Inter`.

| Tom | Fundo | Texto | Usa-se para |
|---|---|---|---|
| `ok` | `#E8F7EE` | `#2E7D4F` | activo, concluído, confirmado, publicado |
| `warn` | `#FDF6EA` | `#8A6111` | pendente, em revisão, pausa, manutenção |
| `bad` | `#FDF1EF` | `#8E2A19` | cancelado, falhado, bloqueado, negado |
| `info` | `#E8F2FC` | `#1D5FA7` | em curso, embarque, agendado com data |
| `mute` | `#EEF3F9` | `#5B6B7F` | inactivo, rascunho, sem estado |

Pílulas de publicação do CMS: publicado `ok` ("Publicado"), em revisão `warn`
("Em revisão"), rascunho `mute` ("Rascunho"), agendado `info` ("Agendado").

## 3. Tipografia

Três famílias, carregadas do Google Fonts:

```
Manrope:      500, 700, 800
Inter:        400, 500, 600, 700
IBM Plex Mono:400, 500
```

- **Manrope 700/800** — títulos, números grandes, nomes em cartões.
  H1 landing `800 56px/1.05`, `letter-spacing: -.035em`.
  H2 de secção `800 38px/1.14`, `-.025em`.
  Título de ecrã do portal `800 26–28px/1.15`, `-.02em`.
  Valor de métrica `800 30px/1`, `-.02em`.
- **Inter 400/500/600/700** — interface e corpo.
  Corpo `400 15–16.5px/1.6`. Corpo denso do portal `400 13–14px/1.55`.
  Botões `700 13–15px/1`. Rótulos maiúsculos `800 10–11px/1`,
  `letter-spacing: .14em`, `text-transform: uppercase`.
  Célula de tabela `500 13px/1.4`; cabeçalho de tabela `800 10.5px/1` maiúsculas.
- **IBM Plex Mono 400/500** — identificadores, matrículas, códigos, datas-hora,
  referências e valores técnicos. `500 11–13px`.

Regra: nunca escrever um identificador (UUID, código de rota, matrícula, referência
de pagamento) em Inter. Nunca escrever prosa em mono.

`text-wrap: pretty` em parágrafos, `text-wrap: balance` em títulos grandes.

## 4. Forma e profundidade

- Cartões: raio 16–20px (22px nos cartões grandes do site).
- Campos de formulário: raio 11–13px, altura 44–50px.
- Botões e pílulas: raio 999px, altura 40–52px.
- Molduras de ecrã (mockups de telemóvel/portal): raio 28–34px.
- Ícone em quadrado arredondado: 30×30px, raio 9px.
- Sombras: cartões elevados `0 40px 90px rgba(13,59,102,.16)`; sobreposições
  (modal) `0 30px 80px rgba(13,59,102,.28)`. Nada de sombras difusas em cartões
  de lista — usam borda de 1px.
- Linhas: sempre 1px `--border`.

## 5. Espaçamento

Escala de 4px: 4, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 48, 64, 80.
- Grelhas de cartões: `gap: 16–20px`.
- Secções do site: `padding: 80px 0` (desktop), `30px 20px` (mobile).
- Cabeçalho do portal: `padding: 16px 28px`.
- Conteúdo do portal: `padding: 24px 28px`.

Layout com flex/grid e `gap`, nunca com margens entre irmãos.

## 6. Estrutura do Portal

Moldura de 1440×1120, raio 28px, `overflow: hidden`, grelha
`grid-template-columns: <barra> 1fr`.

**Barra lateral** — largura fixa: 84px colapsada, 264px expandida. Não expande ao
passar o rato; abre por clique. Colapsada mostra a marca (`busup-mark.png`) como
botão de expandir; expandida mostra o logótipo BusUp e um botão `⟨`. Fundo
`--surface`, borda direita 1px. Navegação com scroll próprio e barra de scroll
invisível. No fim, cartão de utilizador com avatar, nome, papel, botão de terminar
sessão e a linha `v0.1.0 · powered by · UpDigital`.

Itens de navegação: altura 40px, ícone 30×30 raio 9px, rótulo Inter, contagem à
direita em mono 10.5px. Activo: barra vertical de 3px em `#2D8CF0` à esquerda,
fundo `--sky2`, texto `--navy-text`. Grupos com rótulo maiúsculo 10px/`.14em`.

**Cabeçalho** — `position: sticky; top: 0`, fundo `--surface`, borda inferior 1px,
altura ~72px. Contém: indicador de actualização automática (Auto 30s), selector de
papel, selector PT/EN quando aplicável, alternador de tema, sino de notificações e
menu de conta.

**Conteúdo** — `--surface2`, com migalhas (`Domínio · Ecrã`), título, descrição de
uma linha, barra de acções à direita, filtros por estado em pílulas, e a lista.

## 7. Tabelas

- Cabeçalho `--surface2`, texto `800 10.5px` maiúsculas `--muted`.
- Linhas de 52–56px, separadas por 1px `--border`, hover `--sky2`.
- Primeira coluna: identificador em mono + nome em Inter 600 por baixo.
- Coluna de estado: pílula TONE.
- Última coluna: acções (ver, editar, arquivar) alinhadas à direita.
- Rodapé: contagem total, arquivados, e paginação.
- Estado vazio: ícone, frase objectiva, botão da acção principal.
- Carregamento: esqueletos com a altura real das linhas (animação `bzpulse`,
  opacidade 1 → .35, 1.4s).
- Arquivar é destrutivo mas reversível: confirmação + aviso com "Desfazer" durante
  8 segundos; restauro por acção própria.

## 8. Formulários em modal (padrão do Portal v2)

Os formulários não são páginas: abrem em modal sobre a lista.
- Largura 720px, raio 20px, cabeçalho fixo com título e botão de fechar, corpo com
  scroll, rodapé fixo com acções.
- Acima de 8 campos, o formulário faz-se em passos automaticamente. Os passos são
  clicáveis; um passo com erro fica vermelho.
- O botão de guardar muda de texto conforme o contexto: "Criar" ou "Guardar
  alterações".
- Erro 422 do backend: mapear por campo, mostrar debaixo do campo e saltar para o
  passo do primeiro erro.
- Erros 403/404/500: ecrã inteiro, sem shell (ver `Erros BusUp.dc.html`).
- Campos obrigatórios marcados no rótulo; validação ao sair do campo e ao submeter.

## 9. Permissões por papel

Oito papéis, definidos no protótipo (`ROLES`). A navegação e as acções filtram-se
pelo papel activo; um módulo fora do papel devolve o ecrã 403.

| Papel | Acesso |
|---|---|
| `admin` Administração | tudo |
| `ops` Operações | painel, rotas, paragens, veículos, motoristas, viagens, passageiros, cartões físicos, carteiras digitais, terminais, mapa, definições |
| `fin` Financeiro | painel, tarifas, pacotes, carteiras, pagamentos, ocasionais, POS, receita de agentes, relatórios, definições |
| `agente` Agente | painel, viagens, passageiros, cartões físicos, carteiras digitais, ocasionais, definições |
| `motorista` Motorista | viagens, definições |
| `suporte` Suporte | passageiros, carteiras, cartões físicos, carteiras digitais, ocasionais, definições |
| `auditor` Auditor | painel, auditoria, relatórios, definições |
| `conteudo` Gestor de conteúdo | marca, termos e todo o CMS (páginas, editor, media, menus, SEO, planos, ecossistema, pedidos, agendamento, versões), definições |

## 10. Enums e traduções

Os rótulos PT dos enums da API estão no objecto `EN` de `Portal BusUp v2.dc.html`
e têm de ser reutilizados tal e qual (viagens, cartões, pagamentos, dispositivos,
importações, validações, etc.). `design/api-enums.txt` tem a lista completa dos
enums do backend. Regra: o valor do enum vem da API; o rótulo e o tom da pílula
vêm desta tabela do front-end.

## 11. Tema claro/escuro

`theme.js` põe `data-theme` em `<html>`, persiste a escolha e responde ao botão
`[data-bz-theme-toggle]`. Todos os ecrãs suportam os dois temas. Imagens de
logótipo em par `data-logo="light"`/`"dark"`.

## 12. Responsividade

- Portal: desenhado para 1440. Abaixo de 1200 a barra lateral fica colapsada por
  omissão; abaixo de 900 vira gaveta sobreposta. Tabelas ganham scroll horizontal
  com a primeira coluna fixa.
- Site público: desenhado em desktop (1280–1440) e mobile (390). Breakpoint em
  768px. Grelhas de 3 colunas passam a 1; a tabela de preços passa a cartões
  empilhados.
- Alvos de toque em mobile e POS: mínimo 44px.

## 13. Movimento

Discreto. Transições de 120–180ms `ease-out` em hover e foco; 220ms na abertura de
modal (fade + 8px de subida); esqueletos com `bzpulse` 1.4s. Sem paralaxe, sem
animação de entrada em scroll no portal.
