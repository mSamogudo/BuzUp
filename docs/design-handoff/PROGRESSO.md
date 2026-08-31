# Estado da implementação do handoff

Checklist de `01-inventario-ecrans.md`, linha a linha, com o que está feito e
onde está. Actualizar sempre que um item mudar de estado.

Legenda: **✔** implementado · **~** implementado com desvio (explicado) ·
**✗** por fazer.

---

## A. Portal de operação

### A.0 Estrutura permanente

| # | Ecrã / elemento | Estado | Onde |
|---|---|---|---|
| A0.1 | Barra lateral colapsada (84px) | ✔ | `frontend/src/design/portal/PortalShell.tsx` + `portal.css` |
| A0.2 | Barra lateral expandida (264px), grupos | ✔ | idem, grupos em `design/portal/nav.ts` |
| A0.3 | Cartão de utilizador + `v0.1.0 · powered by UpDigital` | ✔ | `PortalShell.tsx` |
| A0.4 | Cabeçalho fixo (Auto 30s, papel, PT/EN, tema, sino, conta) | ✔ | `PortalShell.tsx` |
| A0.5 | Painel de notificações com marcação de lida | ✔ | `PortalShell.tsx` + `backend/apps/notifications/api/` |
| A0.6 | Selector de papel (8 papéis) que refiltra a navegação | ✔ | `PortalShell.tsx` + `ROLES` em `nav.ts` |
| A0.7 | Modal de formulário 720px, passos acima de 8 campos | ✔ | `design/ui/Modal.tsx` (`Modal`, `StepBar`, `autoSteps`) |
| A0.8 | Confirmação destrutiva com "Desfazer" 8s | ✔ | `ConfirmDestructive` + `useUndoWindow`; usado em `cms/PagesPage.tsx` |
| A0.9 | Estado vazio, esqueleto, barra de sem rede | ✔ | `design/ui/kit.tsx` (`EmptyState`, `TableSkeleton`, `.bz-offline`) |
| A0.10 | Erros 403/404/500 em ecrã inteiro, sem shell | ✔ | `public/errors/ErrorScreen.tsx`; rota `*` dentro de `/app` |

### A.1 Módulos

Todos os 24 módulos da navegação existem e estão ligados aos endpoints reais.
O vocabulário visual do handoff (tabelas de 54px, cabeçalho maiúsculo, pílulas
TONE, botões em pílula, modais de 720px) é aplicado a todos por
`frontend/src/design/portal/legacy-skin.css`, que reveste as classes `admin-*`
já existentes — ver a nota em **Desvios**.

| # | Módulo | Estado | Nota |
|---|---|---|---|
| A1.1 | Painel | ✔ | `admin/DashboardPage.tsx` + `dashboard/Charts.tsx` |
| A1.2 | Rotas (+ paragens da rota) | ✔ | `RoutesPage`, `RouteStopsPage` |
| A1.3 | Paragens | ✔ | `StopsPage` |
| A1.4 | Veículos (+ pré-visualizar lugares) | ✔ | `VehiclesPage`, `SeatLayoutPreview` |
| A1.5 | Motoristas | ✔ | `DriversPage` |
| A1.6 | Viagens, Programações, Agendador | ✔ | `OperationPage`, `SchedulesPage`, `TripSchedulerPage`, `TripCalendar` |
| A1.7 | Mapa | ~ | `MapPage.tsx` reescrito: pinos por estado e filtro do desenho, mas com **terminais reais** da API e viaturas em viagem, em vez dos sete terminais fixos do protótipo |
| A1.8 | Tarifas (matriz, regras, produtos, taxas, câmbio) | ✔ | `FaresPage` + `FareMatrixTab`; **novo** separador Simulador (`FareQuotePanel`) |
| A1.9 | Pacotes | ✔ | `PackagesPage` |
| A1.10 | Passageiros | ✔ | `PassengersPage` |
| A1.11 | Carteiras | ✔ | `WalletsPage` |
| A1.12 | Cartões Físicos | ✔ | `PhysicalCardsPage` |
| A1.13 | Carteiras Digitais | ✔ | `DigitalCardsPage` |
| A1.14 | Pagamentos, Recargas, Validações | ✔ | `FinancialPage`; **novo** separador Webhooks (`WebhookLogPage`) |
| A1.15 | Bilhetes Ocasionais | ✔ | `GuestCheckoutsPage` |
| A1.16 | Sessões POS | ✔ | `PosSessionsPage` |
| A1.17 | Receita de Agentes | ✔ | `AgentRevenuePage` |
| A1.18 | Relatórios, reconciliação, importações | ✔ | `ReportsPage` |
| A1.19 | Terminais | ✔ | `DevicesPage`; **novo** online/offline por heartbeat |
| A1.20 | APKs | ✔ | `ReleasesPage` |
| A1.21 | Utilizadores e papéis | ✔ | `SystemPage` |
| A1.22 | Auditoria | ✔ | `AuditPage` |
| A1.23 | Marca | ✔ | `BrandingPage` |
| A1.24 | Termos e Condições | ✔ | `TermsPage` |
| A1.25 | Definições (perfil, segurança, preferências, notificações) | ✔ | **novo** `admin/SettingsPage.tsx` + endpoint `POST /api/auth/me/2fa/` |

### A.3 Estados por lista

O padrão de lista está no componente partilhado `ui/common.tsx` (`DataTable`),
por isso vale para todos os módulos de uma vez: pesquisa, ordenação,
paginação com tamanho de página, **colunas configuráveis** (guardadas por
ecrã, neste dispositivo), esqueleto com a altura real das linhas, estado vazio
e estado de erro. Os filtros por estado, o detalhe em painel, o formulário em
modal e as exportações são de cada módulo, e estão nos módulos que os têm
declarados no inventário.

### A.2 Bloco Propostas

| # | Proposta | Estado | Onde |
|---|---|---|---|
| A2.1 | Agentes e turnos (`shifts`) | ✔ (como proposta) | `admin/ShiftsProposalPage.tsx`, com o aviso obrigatório e o que falta no backend |
| A2.2–A2.12 | CMS completo | ✔ | ver secção CMS abaixo |

---

## B. Site público

| # | Ecrã | Estado | Onde |
|---|---|---|---|
| B.1 | Landing (13 secções) | ✔ | `public/site/SitePage.tsx` + `blocks.tsx`, conteúdo do CMS |
| B.2 | Preços | ✔ | mesma página, `slug=precos` |
| B.3 | Contactos | ✔ | mesma página, `slug=contactos` |
| B.4 | Apps (5 produtos) | ✔ | `public/apps/AppsPage.tsx` |
| B.5 | Compra de bilhetes (6 passos + E1 + E2) | ✔ | `public/booking/BookingPage.tsx`; **novos** ecrãs E1 (esgotado) e E2 (falha de pagamento) |
| B.6 | Acesso (6 ecrãs) | ✔ | `auth/LoginPage.tsx` (painel de marca + cartão), `auth/SessionValidating.tsx`, `ui/SplashScreen.tsx` |
| B.7 | Erros (404/401/403/500/503/sem ligação) | ✔ | `public/errors/ErrorScreen.tsx`, rotas `/erro/*` e catch-all |
| B.8 | Mapa de terminais | ~ | integrado no módulo Mapa com dados reais (ver A1.7) |

Todo o site é bilingue (PT/EN) e responde ao tema claro/escuro. O conteúdo vem
do CMS; as frases da moldura (nav e rodapé) estão em
`public/site/chrome.ts`, portadas verbatim do protótipo.

---

## CMS (03-cms-especificacao.md)

### Backend — `backend/apps/cms/`

| Parte | Estado | Onde |
|---|---|---|
| Modelo de dados (1.1 a 1.11) | ✔ | `models.py` + migração `0001_initial` |
| Capacidades e papel `conteudo` (1.12) | ✔ | `apps/core/permissions/base.py` (`content.*`, `media.manage`, `menus.manage`, `seo.manage`, `plans.manage`, `requests.read`; papel `content_manager`) |
| `service_requests` no CMS (1.13) | ✔ | `apps/leads` passou a `requests.read` e ganhou `export.csv` |
| Endpoints `/api/cms/*` (2) | ✔ | `api/views.py`, `api/urls.py` |
| Entrega pública com cache (2, fim) | ✔ | `api/public.py` + `services.py` |
| Pré-visualização por token | ✔ | `preview-token` + `?preview_token=` |
| Fluxo de publicação (4) | ✔ | `services.publish_page`, `validate_publish`, `submit-review` |
| Versões e comparação (1.10) | ✔ | `services.create_version`, `restore_version`, `compare_versions` |
| Agendamento (1.11) | ✔ | `ScheduledPublication` + comando `cms_publish_scheduled` + rede de segurança na leitura pública |
| Seeds verbatim (5.2) | ✔ | `seeds/site_copy.json` + comando `seed_cms`; corre no arranque com `--if-empty` |
| Critérios de pronto (6) | ✔ | `apps/cms/tests.py` — 13 testes, todos a passar |
| Lacunas fechadas fora do CMS | ✔ | `apps/core/tests_lacunas_do_handoff.py` — 9 testes (2FA, webhooks, recuperações) |

### Front-end — `frontend/src/admin/cms/`

| # | Ecrã | Estado | Ficheiro |
|---|---|---|---|
| 3.1 | Páginas do site | ✔ | `PagesPage.tsx` |
| 3.2 | Editor de página (blocos, formulário, pré-visualização ao vivo) | ✔ | `PageEditorPage.tsx`, `BlockForm.tsx`, `blocks.ts` |
| 3.3 | Biblioteca de media | ✔ | `MediaPage.tsx`, `MediaPicker.tsx` |
| 3.4 | Menus e rodapé | ✔ | `MenusPage.tsx` |
| 3.5 | SEO e partilha | ✔ | `SeoPage.tsx` |
| 3.6 | Preços e planos | ✔ | `PlansPage.tsx` |
| 3.7 | Ecossistema UpDigital | ✔ | `EcoSystemsPage.tsx` |
| 3.8 | Pedidos recebidos | ✔ | `RequestsPage.tsx` |
| 3.9 | Publicações agendadas | ✔ | `SchedulesPage.tsx` |
| 3.10 | Histórico de versões | ✔ | `VersionsPage.tsx` |
| 3.11 | Utilizadores do CMS | ~ | `CmsUsersPage.tsx` — a API não tem convite por email; o ecrã cria a conta com senha temporária mostrada uma vez |

A pré-visualização do editor usa os **mesmos componentes** do site público
(`public/site/blocks.tsx`), por isso o que se vê no editor é o que vai ao ar.

---

## Lacunas da API (04-lacunas-backend.md, secção 1)

| Lacuna | Estado | Onde |
|---|---|---|
| Matriz de tarifas | ✔ | `FareMatrixTab` (já existia) |
| Simulador de tarifa | ✔ | **novo** `FareQuotePanel` |
| Viaturas no mapa | ✔ | **novo** em `MapPage` |
| Mapa de lugares | ✔ | `SeatLayoutPreview` (portal) e `booking/SeatMap` (compra) |
| Heartbeat nos terminais | ✔ | **novo** online/offline em `DevicesPage` |
| Registo de webhooks | ✔ | **novo** `WebhookLogPage` + `GET /api/payments/callback-log/` |
| Construtor de relatórios | ✔ | `ReportsPage` |
| Gráficos do painel | ✔ | `dashboard/Charts.tsx` |
| Segurança da conta (2FA, senha) | ✔ | **novo** `SettingsPage` + `POST /api/auth/me/2fa/`. Ligar é de quem quiser; **desligar continua a ser só de superadministrador**, como o modelo `User` já decidia |
| Recuperação de cartão (lista e histórico) | ✔ | **novo** separador Recuperações em Cartões Físicos + `GET /api/card-recoveries/`. Sem tabela nova: cada recuperação já fica inteira nos metadados da intenção de pagamento que cobra a taxa |
| Páginas públicas de bilhete/autocarro geridas no portal | ✗ | `public/ticket/{token}`, `public/bus/{uuid}` e os links curtos não têm gestão no portal |

---

## Varredura de consistência (ecrã a ecrã)

Passagem por todos os ecrãs à procura de sítios onde o desenho divergia. O que
estava errado e ficou corrigido:

| # | O que divergia | Onde estava | Como ficou |
|---|---|---|---|
| 1 | **Tema escuro a duas cores.** A secção 39 do `styles.css` pintava `.admin-*` com a rampa cinzenta (zinc) do desenho anterior. Como `html[data-theme="dark"] .admin-card` tem mais especificidade do que `.admin-card` do `legacy-skin.css`, os 24 módulos ficavam preto-cinza dentro de um shell navy | `styles.css` §39 | Os literais passaram a tokens; o portal inteiro é navy no escuro |
| 2 | **Paleta declarada em dois sítios.** O `:root` do `styles.css` declarava as mesmas `--app-*` que o `tokens.css` mapeia | `styles.css` §1 e §1b | Bloco removido; `tokens.css` é a única fonte |
| 3 | **Gráficos do painel em cinzento.** `theme.ts` desenhava grelha, eixos e fundo com zinc | `admin/dashboard/theme.ts` | Grelha/eixo/fundo passam a tokens navy; as cores das séries ficam (foram validadas para daltonismo e mantêm ≥3:1 sobre a superfície nova) |
| 4 | **A compra era uma ilha.** `.bzbk` tinha fonte do sistema e paleta própria, incluindo um escuro azul-quase-preto que não é o navy dos tokens | `public/booking/booking.css` | Fonte `--font-ui`; as variáveis locais passam a valer os tokens; avisos e pílulas usam TONE |
| 5 | **`/baixar` só existia em claro**, com paleta própria e sem fonte do produto | `public/DownloadPage.tsx` | Variáveis locais apontadas aos tokens; o título "Como instalar" usava `--navy` (fixo) e desaparecia no escuro — passou a `--navy-text` |
| 6 | **Paleta "areia" (bege/castanho) de outro desenho** — `#E7E1D4`, `#6B6356`, `#B4432B`, e `var(--success, #1FB04A)`/`var(--orange, …)` com variáveis que ninguém define | Pagamentos, Relatórios, Cartões Digitais, Passageiros, Portal do passageiro | Tudo mapeado sobre TONE |
| 7 | **Dois pedidos de fontes ao Google** com pesos diferentes | `styles.css` + `tokens.css` | Um só pedido, no `tokens.css`, com os pesos que o CSS usa mesmo (400–900) |
| 8 | **Famílias e tons soltos** — `Manrope, Inter, sans-serif` escrito à mão em ~20 regras, `#2A9D8F`/`#D62828` do desenho antigo em 30 sítios | `styles.css`, `login.css`, `MapPage.tsx` | `var(--font-display)`/`var(--font-ui)`/`var(--font-mono)` e TONE |

Verificado no browser: com `data-theme="dark"`, `.admin-card`/`.admin-section`/
`.admin-table-wrap`/`.admin-modal-card` dão `#0A2E50`, cabeçalho de tabela e
estado vazio `#0C3557`, corpo `#06203A`; em claro, `#FFFFFF`/`#F6F9FD`/
`#E7EDF5`. `/comprar` e `/baixar` conferidos nos dois temas.

### Limpeza do CSS órfão

Depois de apagar os ficheiros mortos, a folha `styles.css` foi podada família a
família, com cada uma verificada antes de sair:

- **Como se decidiu.** Uma classe só conta como morta se não aparecer em
  nenhum `.tsx`/`.ts`, em nenhuma outra folha, nem no `index.html`. Confirmou-se
  também que não há classes montadas em runtime que caiam nestas famílias: as
  únicas construções dinâmicas do projecto são `bz-btn-${variant}`,
  `bz-pill-${tone}` e `bzau-tab-${id}`, e nenhuma tem regras no `styles.css`.
  Não há classes em `innerHTML`, no `index.html` nem em templates do backend.
- **O que ficou de fora, de propósito.** `.recharts-legend-item-text` e
  `.recharts-cartesian-grid line` — os nomes são gerados pela biblioteca em
  runtime, por isso nunca apareceriam numa busca ao nosso código.
- **Famílias removidas** (todas verificadas uma a uma): `admin-login-*`,
  `admin-sidebar*`, `admin-nav-*`, `admin-mobile-*`, `admin-bottom-nav*`,
  `admin-brand-*`, `admin-user-*`, `admin-power*`, `admin-breadcrumbs`,
  `admin-topbar-left/right`, `admin-main`, `admin-tabbar`, `admin-tab-active`,
  `admin-chip-group`, `admin-detail-*`, `admin-definition-list`,
  `admin-inline-stat-card`, `admin-inline-filter-panel`, `admin-loader*`,
  `admin-two-column`, `admin-avatar-small`, `admin-section-actions`,
  `admin-header-actions`, `admin-submit-button`, `admin-version-label`,
  `checkout-*`, `login-*`, `otp-*`, `splash-*`, `locale-flag-*`,
  `topbar-popover*`, `sidebar-logo*`, `sidebar-collapse-btn`, `nav-chevron*`,
  `segmented-*`, `bztw-*`, `dashboard-route-*`, `dashboard-chart-grid*`,
  `dashboard-kpi-strip`, `dashboard-top-routes`, `dashboard-section*`,
  `muted-text`, `mobile-only`, `powered-by-logo`, `portal-qr-token`,
  `secondary-button-danger`, `icon-button-danger`.
  Os `-active`, `-danger` e afins saíram sozinhos: a classe base (`.admin-tab`,
  `.admin-chip-button`, `.secondary-button`) continua viva onde é usada.
- **Números.** 338 blocos apagados e 23 listas de selectores podadas (onde o
  bloco tinha partes vivas e mortas na mesma vírgula). `styles.css` passou de
  5886 para 3813 linhas; o CSS de arranque de **194,5 kB para 155,3 kB**
  (36,7 → 30,4 kB comprimido).
- **Verificado depois.** Sem erros na consola. Com `data-theme="dark"`, uma
  amostra montada no browser dá cartão/secção/modal/gráfico `#0A2E50`, cabeçalho
  de tabela e rodapé de tabela `#0C3557`, campo `#0E3A5E`, linha de 54px, botão
  em pílula de 999px, modal de 720px, cartão de raio 16px; em claro,
  `#FFFFFF`/`#F6F9FD`/`#FBFDFF`. `/login`, `/` e as nove rotas públicas
  respondem 200 e desenham na mesma.

---

### O que a varredura encontrou e não corrigiu

1. **Raios de canto.** Ainda há 8/10/11/13/14/18/30px espalhados, em vez da
   escala `--r-*` (12/16/20/22/999). Nos cartões, tabelas, modais, botões e
   campos o `legacy-skin.css` já normaliza; o resto são ecrãs secundários.
2. **Ecrãs com vocabulário de classes próprio** — `co-*` (checkout), `bus-pay-*`,
   `bzdl-*`, `driver-*`, `portal-*`. A cor e a fonte já são as do sistema; as
   formas (raios, alturas, sombras) ainda não passam pelo kit `bz-*`.

---

## Implementação exacta do protótipo — páginas públicas

O ZIP entregue (`Landing BusUp Design-handoff.zip`) é byte a byte igual ao que
já está em `docs/design-handoff/design/` — comparado por SHA-256 nos dez
ficheiros. Não foi preciso importar nada: o protótipo no repositório **é** a
fonte.

### B.1 Landing — feito

Comparada secção a secção com `Landing BusUp - Ceu.dc.html` (prancha
Desktop · 1440). O que faltava e passou a existir:

| Secção | O que faltava |
|---|---|
| Herói | O **terceiro botão** ("Ver a plataforma", `ctaSecondary`), que o seed não passava, e a **maqueta do portal** por baixo — 1016px de largura, cortada aos 430px, com as quatro etiquetas flutuantes (`tag1`–`tag4`) |
| Barra | Tinha um "Entrar no portal" a mais: o desenho põe só idioma, tema e "Falar com vendas". A entrada no portal fica no rodapé e no menu de telemóvel, como no protótipo. O logótipo encolhia até virar um risco (faltava `flex: none`) e o botão do menu aparecia no computador |
| Tira de logos | Era uma linha estática. Passa a ser a **tira em ciclo** do desenho: título `ecoStripTitle`, pílulas de 62px, máscara a esbater nas pontas, e a UpDigital à cabeça com variante por tema |
| Funcionalidades | Eram cinco cartões de texto. Passam a ser os cinco do desenho **com as miniaturas**: comprar bilhete, validação a bordo, cartões, receita da semana e frota — três em cima, e em baixo um estreito mais um largo com o painel do mapa |
| Começar em três passos | Estava guardado como texto corrido (`richtext`). Passa a bloco próprio (`passos`), com os três painéis numerados, duas miniaturas em cada e o painel do portal de gestão |
| Faixa final | Era um cartão de raio 28. Passa a **secção de largura inteira** com o gradiente navy do desenho, botões branco/translúcido e os três factos com visto, separados por um filete |
| Formulário | O desenho **não tem formulário na landing** — está na página de Contactos. O bloco saiu da landing |

Blocos da landing, pela ordem: `heroi · logos · recursos · porque · passos ·
casos · precos · faq · cta · eco`. É a ordem das secções do protótipo.

Tudo continua a vir do CMS: os campos novos (`cta3`, `tags`, `map_title`,
`map_note`, `panel_title`, `panel_text`, `steps`, `facts`, `h2` da tira) foram
acrescentados ao esquema do editor e ao seed. As miniaturas são decoração e
ficam no código (`public/site/mockups.tsx`), fora do CMS — o que o editor mexe é
a cópia, não o desenho das peças. `media_id_dark` é novo: permite a um logotipo
ter variante por tema.

Migração `cms.0002_alter_pageblock_type` acrescenta o tipo `passos`.

### Estado da ligação de cada módulo — verificado em 2026-08-31

Até esta data, tudo o que se segue existia escrito e **não estava ligado a rota
nenhuma**: os ficheiros compilavam, passavam no typecheck, e o Vite
eliminava-os do pacote porque ninguém lhes chegava. O mesmo defeito apanhado no
backend (`apps.cms` fora do `INSTALLED_APPS`, `apps.notifications.api` fora das
urls) repetia-se no frontend inteiro do desenho.

Ligado em `App.tsx` e verificado no browser ecrã a ecrã:

| rota | ecrã | antes |
|---|---|---|
| `/` `/precos` `/contactos` | `public/site/SitePage` (CMS) | `/` servia a landing antiga |
| `/apps` | `public/apps/AppsPage` | sem rota |
| `*` | `public/errors/ErrorScreen` (404) | reencaminhava tudo para `/` |
| `/app` | `design/portal/PortalShell` | `admin/AdminLayout` |
| `/app/settings` | `admin/SettingsPage` | sem rota |
| `/app/financial/webhooks` | `admin/WebhookLogPage` | sem rota |
| `/app/cards/recoveries` | `admin/CardRecoveriesTab` | sem rota |
| `/app/shifts` | `admin/ShiftsProposalPage` | sem rota |
| `/app/cms/*` (10 ecrãs) | `admin/cms/` | sem rota |

`WebhookLogPage` e `CardRecoveriesTab` foram escritos sem cabeçalho — eram
pensados como separadores; ganharam `PageFrame` para funcionarem como ecrã
próprio, e entradas em `design/portal/nav.ts`.

O pacote passou de 2368 para 2404 módulos: a diferença é exactamente o que
antes era eliminado por não ter quem lhe chegasse.

### Comparadas ecrã a ecrã em 2026-08-31

Cada `.dc.html` foi aberto no browser ao lado da rota que o implementa e o
conteúdo renderizado dos dois foi comparado.

| Desenho | Estado |
|---|---|
| `Landing BusUp - Ceu` | fiel |
| `Precos BusUp` | fiel |
| `Erros BusUp` | fiel — corrigida a referência técnica, que vinha fixa do protótipo |
| `Acesso BusUp` | corrigido: cópia, três provas, cabeçalho do painel, ajuda e manter-sessão |
| `Contactos BusUp` | corrigido: os oito campos e as pílulas "O que quer ver" |
| `Compra de Bilhetes BusUp` | corrigido: seis passos e os dois estados de excepção |
| `Portal BusUp v2` | cartões fiéis; título e sobretítulo corrigidos |
| `Apps BusUp` | fora de âmbito — é a especificação das apps móveis e POS, não uma página web |

**O fluxo de compra tem seis passos**, decidido pelo operador em 2026-08-31.
`Ecra Compra.dc.html` mostra um indicador de cinco e está desactualizado; o
`Compra de Bilhetes BusUp.dc.html` é que manda. Os dois estados de excepção
existem agora no ecrã:

- **E1 Esgotado** — só quando TODAS as partidas do dia estão sem lugar para o
  número de bilhetes pedido. Uma partida fechada por outro motivo (embarque por
  abrir) mantém a sua própria razão; chamar-lhe "esgotado" seria mentir.
- **E2 Falha no pagamento** — a primeira linha diz que nada foi cobrado, antes
  do motivo técnico. Quem viu o pagamento falhar a meio quer saber isso antes
  de tudo o resto. A tentativa fica retomável com o que já preencheu.

---

## Desvios assumidos

1. **`legacy-skin.css`.** Os 24 módulos do portal já estavam escritos com as
   classes `admin-*` de um desenho anterior. Reescrevê-los um a um arriscava a
   lógica de cada listagem sem mudar comportamento nenhum, por isso as medidas
   e formas do handoff são aplicadas por uma folha de estilos que reveste essas
   classes. À medida que cada módulo for portado para os componentes `bz-*`,
   as regras correspondentes deixam de ter alvo e saem.
2. **Frases da moldura do site em código.** A especificação do CMS modela
   páginas, blocos, menus, planos, ecossistema e SEO — não modela as frases da
   barra de navegação e do rodapé ("Falar com vendas", "Todos os direitos
   reservados."). Ficam em `public/site/chrome.ts`, num só sítio e nos dois
   idiomas, portadas verbatim do protótipo.
3. **Mapa com dados reais.** O protótipo `mapa-terminais.html` tem sete
   terminais fixos. O módulo Mapa mostra os terminais reais da API com a mesma
   linguagem visual — pinos de 30px coloridos por estado, filtro por estado e
   balão com identificador, estado, velocidade e último contacto.
4. **`frontend/src/public/LandingPage.tsx`, `public/landing/` e
   `admin/AdminLayout.tsx` foram apagados** — a landing passa a vir do CMS e o
   shell do portal passa a ser `design/portal/PortalShell.tsx`. São 10
   ficheiros e 1788 linhas, com paleta e fonte próprias.

   Apagados em 2026-08-31, depois de confirmado ficheiro a ficheiro que ninguém
   lhes chegava. O único que enganava era o `ServiceRequestForm`: existem duas
   cópias, e quem o usa é a do CMS (`public/site/ServiceRequestForm.tsx`), não
   a da landing. O pacote ficou nos mesmos 2404 módulos antes e depois — já
   eram eliminados por tree-shaking, e é por isso que estiveram tanto tempo sem
   dar nas vistas.

---

## Como pôr o CMS a correr

```bash
# Migrações e conteúdo inicial (idempotente)
python manage.py migrate
python manage.py seed_cms --publish

# Agendamentos (cron de minuto a minuto). Sem cron, a leitura pública trata
# dos agendamentos vencidos uma vez por minuto.
python manage.py cms_publish_scheduled
```

**O arranque do contentor NÃO corre `seed_cms`.** `backend/entrypoint.sh` corre
`migrate` e `seed_roles`, e mais nada — uma versão anterior deste documento
dizia o contrário. Num deploy novo o site nasce vazio até alguém correr o
comando à mão. Automatizá-lo (com `--if-empty`, para nunca sobrepor o que a
equipa editou) fica por fazer.
