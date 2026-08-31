# Handoff: Front-end BusUp (Portal de operação + Site público + CMS)

## Visão geral

Este pacote descreve, ao detalhe, o front-end completo do BusUp — plataforma
moçambicana de bilhética digital para transporte de passageiros, desenvolvida pela
UpDigital, Limitada. Cobre três blocos:

1. **Portal de operação** (desktop 1440) — 24 módulos ligados aos endpoints
   existentes da API, mais um bloco de propostas.
2. **Site público** — landing, preços, contactos, apps, compra de bilhetes (mobile),
   ecrãs de acesso e ecrãs de erro.
3. **CMS** — gestão de conteúdo do site público. **Não existe no backend.** A
   especificação completa (modelo de dados, endpoints, ecrãs, fluxo de publicação)
   está em `03-cms-especificacao.md` e faz parte do trabalho a implementar.

O objectivo do handoff: implementar exactamente este desenho, sem deixar nenhum ecrã
de fora. O inventário em `01-inventario-ecrans.md` é a lista de verificação —
cada linha tem de ficar implementada.

## Sobre os ficheiros de design

Os ficheiros em `design/` são **referências de design escritas em HTML** —
protótipos que mostram aparência e comportamento pretendidos, não código de
produção para copiar. Abrem directamente no browser. A tarefa é **recriar estes
ecrãs no ambiente do repositório alvo** (React/Next, Vue, o que existir), com os
padrões e bibliotecas já estabelecidos aí. Se ainda não existir front-end, escolher
a stack adequada (recomendação: React + TypeScript + Vite ou Next.js, react-router
ou app router, TanStack Query para dados, Zod para validação) e implementar lá.

Os protótipos usam um runtime próprio (`support.js`) que **não deve ser portado**.
O que interessa é: estrutura, medidas, cores, tipografia, conteúdo, estados,
comportamento e regras — tudo documentado nos ficheiros deste pacote.

## Fidelidade

**Alta fidelidade (hifi).** Cores, tipografia, espaçamentos, raios, estados e
conteúdo estão finais. A implementação deve ser fiel ao pixel dentro das
convenções do repositório alvo. Onde o desenho não define um breakpoint
intermédio, seguir a regra de responsividade em `02-tokens-e-padroes.md`.

Excepções — placeholders assumidos, a substituir por material real:
- Depoimentos de clientes na landing (`cases`) estão marcados como texto a
  preencher.
- Screenshots do produto na landing e o painel do mapa são caixas de placeholder.
- Não há fotografia; nenhum ecrã depende de imagem gerada.

## Documentos deste pacote

| Ficheiro | Conteúdo |
|---|---|
| `01-inventario-ecrans.md` | Todos os ecrãs, um a um, com propósito, layout e estados. Lista de verificação. |
| `02-tokens-e-padroes.md` | Design tokens, tipografia, formas, componentes partilhados, padrões de tabela, modais faseados, permissões, erros, tema claro/escuro, i18n. |
| `03-cms-especificacao.md` | O CMS completo: modelo de dados, endpoints a criar, ecrãs, fluxo de publicação, versões, agendamento, permissões. |
| `04-lacunas-backend.md` | O que a API já expõe e o front-end ainda não usa, e o que falta no backend para o desenho ficar completo. |
| `05-plano-implementacao.md` | Ordem de trabalho sugerida, por fases, com critérios de pronto. |
| `design/` | Os protótipos HTML, o mapa Leaflet, os assets e os dumps da API (`api-paths.txt`, `api-enums.txt`, `api-schemas.txt`). |

## Contexto de produto

- **Idiomas**: português de Portugal (pt-PT, variante moçambicana) por omissão e
  inglês. Todo o site público e os ecrãs de acesso, compra e erro são bilingues,
  com selector PT/EN. O portal de operação é apenas em PT.
- **Moeda**: metical (MZN), formatado `1 250,00 MT`.
- **Pagamentos**: M-Pesa e e-Mola.
- **Fuso**: CAT (UTC+2). Datas em `DD MMM YYYY, HH:mm`.
- **Tema**: claro e escuro, alternável, persistido (ver `design/theme.js`).

## Regra de consistência entre produtos

A app mobile (passageiro, motorista, agente) e o POS partilham o mesmo design do
Portal. Não criar linguagens visuais separadas por produto. O que muda entre
produtos é a densidade e o alvo de toque, não o vocabulário: POS e mobile usam
alvos de 44px ou mais e tipos maiores; o Portal é mais denso.

## Assets

Em `design/assets/`:
- `busup-logo-light.png`, `busup-logo-dark.png` — logótipo BusUp para tema claro e escuro.
- `busup-mark.png` — marca isolada, usada na barra lateral colapsada.
- `logo-updigital-dark.png` (letra preta + azul), `logo-updigital-white.png` (letra branca + azul) — logótipo UpDigital, fundo transparente, um por tema.
- `logo-payup|cashup|gateup|vura|ossoma.png`, `eco-*.webp` — ecossistema UpDigital.
- `mpesa.png`, `emola.png` — provedores de pagamento.
- `tpm-light.png`, `updigital-light.png` — logos de operador/parceiro.

Troca por tema: as imagens de logótipo aparecem em par, uma com
`data-logo="light"` e outra com `data-logo="dark"`; o CSS mostra a certa conforme
`html[data-theme]`. Reproduzir com a mesma lógica (ou com um único componente
`<Logo />` que lê o tema).

## Ficheiros de design (em `design/`)

| Ficheiro | O que contém |
|---|---|
| `Portal BusUp v2.dc.html` | Portal de operação completo — a referência principal. |
| `Portal BusUp.dc.html` | Versão anterior do portal, com os ecrãs de CMS mais desenvolvidos (editor de páginas, media, menus, SEO, planos, ecossistema, versões). Usar como referência do CMS. |
| `Landing BusUp - Ceu.dc.html` | Landing pública, desktop e mobile. |
| `Precos BusUp.dc.html` | Página de preços. |
| `Contactos BusUp.dc.html` | Página de contactos. |
| `Apps BusUp.dc.html` | Fluxos das apps mobile e POS. |
| `Compra de Bilhetes BusUp.dc.html` | Fluxo de compra, 6 passos + 2 estados de erro. |
| `Ecra Compra.dc.html` | Ecrã de compra isolado (componente do fluxo acima). |
| `Acesso BusUp.dc.html` | Login, recuperação de senha, OTP de passageiro, sessão a validar. |
| `Erros BusUp.dc.html` | 404, 401, 403, 500, 503 e sem-ligação, em desktop e mobile. |
| `mapa-terminais.html` | Mapa Leaflet de Maputo com sete terminais reais. |
| `theme.js` | Alternador de tema claro/escuro com persistência. |
| `support.js` | Runtime dos protótipos. **Não portar.** |

Abrir os `.dc.html` directamente no browser para ver cada ecrã ao vivo.
