# Especificação do CMS (a construir de raiz)

O CMS gere o **site público do BusUp**. Não existe no backend actual: nem tabelas,
nem endpoints. Esta especificação é a fonte de verdade para o construir — API e
front-end. Os ecrãs estão desenhados em `design/Portal BusUp.dc.html` (bloco
Conteúdo/Comercial/Publicação/Sistema) e listados no bloco Propostas de
`design/Portal BusUp v2.dc.html`.

Princípio: **o site público não tem texto no código.** Cada bloco, rótulo, preço,
pergunta de FAQ e ligação de rodapé vem do CMS, em PT e EN.

---

## 1. Modelo de dados

Todos os recursos têm `id` (UUID), `created_at`, `updated_at`, `created_by`,
`updated_by` e apagamento lógico (`archived_at`), como o resto da API.

### 1.1 `pages`
| Campo | Tipo | Notas |
|---|---|---|
| `slug` | string única | `""` para a página inicial |
| `title` | i18n `{pt, en}` | nome interno e H1 por omissão |
| `status` | enum | `draft`, `review`, `scheduled`, `published` |
| `template` | enum | `landing`, `pricing`, `contact`, `apps`, `generic` |
| `locales` | array | idiomas com conteúdo completo |
| `published_at`, `scheduled_for` | datetime | |
| `current_version_id` | FK `page_versions` | |
| `seo_id` | FK `seo_meta` | |

### 1.2 `page_blocks`
Um bloco por secção da página, ordenado.

| Campo | Tipo | Notas |
|---|---|---|
| `page_id` | FK | |
| `type` | enum | `heroi`, `logos`, `recursos`, `porque`, `casos`, `precos`, `faq`, `form`, `eco`, `cta`, `richtext`, `media` |
| `position` | int | ordem no ecrã |
| `enabled` | bool | bloco pode existir e estar desligado |
| `content` | JSON i18n | esquema por tipo (ver 1.3) |

### 1.3 Esquema de conteúdo por tipo de bloco

- `heroi`: `badge`, `h1a`, `h1b` (linha a azul), `lead`, `cta1`, `cta2`,
  `chips[]`. Limites de caracteres usados no editor: badge 40, h1a 40, h1b 40,
  lead 180, cta 24, chips 80.
- `logos`: `lead`, `items[]` → `{media_id, alt, href}`.
- `recursos`: `h2`, `lead`, `items[]` → `{title, text, bullets[]}` (5 no desenho).
- `porque`: `h2`, `lead`, `stats[]` → `{value, label}`.
- `casos`: `h2`, `lead`, `items[]` → `{kind, quote, who}`.
- `precos`: `h2`, `lead`, `plan_ids[]` (referência a `plans`).
- `faq`: `h2`, `lead`, `items[]` → `{q, a}`.
- `form`: `h2`, `lead`, `facts[]`, `fields[]`, `submit`, `sent_title`, `sent_text`.
- `eco`: `label`, `h2`, `lead`, `note`, `system_ids[]` (referência a `eco_systems`).
- `cta`: `h2`, `lead`, `cta1`, `cta2`.
- `richtext`: HTML restrito (h2, h3, p, ul, ol, a, strong, em).
- `media`: `media_id`, `caption`, `width` (`content` | `full`).

### 1.4 `media_assets`
`filename`, `url`, `mime`, `width`, `height`, `bytes`, `alt` (i18n), `folder`,
`used_in[]` (páginas que referenciam), `uploaded_by`.
Formatos aceites: PNG, JPG, WEBP, SVG, PDF. Limite 10 MB.
Gerar variantes 1x/2x e WEBP no upload.

### 1.5 `menus` e `menu_items`
`menus`: `key` (`header`, `footer_product`, `footer_contact`, `footer_eco`), `label`.
`menu_items`: `menu_id`, `label` (i18n), `href` (interno por `page_id` ou URL
externo), `position`, `target`, `visible`.

### 1.6 `seo_meta`
`page_id`, `title` (60 car.), `description` (160), `slug` (40), `keywords` (90),
`og_image_id`, `no_index`. Todos i18n. O editor mostra pré-visualização de
resultado de pesquisa (`busup.updigital.co.mz › slug`) e contadores de caracteres.

### 1.7 `plans`
`name` (i18n), `price_label` (i18n, ex.: "Sob consulta"), `unit` (i18n),
`cta_label`, `items[]` (i18n), `position`, `highlighted` (bool), `visible`.
Alimenta a landing e a página de preços.

### 1.8 `plan_features` (tabela comparativa da página de preços)
`label` (i18n), `urban`, `intercity`, `institutional` (string: `✓`, `—` ou texto),
`position`.

### 1.9 `eco_systems`
`name`, `logo_media_id`, `url`, `status` (`published`, `draft`), `position`.
Os seis do desenho: PayUp, CashUp, GateUp, Vura, Ossoma, BusUp.

### 1.10 `page_versions`
`page_id`, `number` (incremental), `snapshot` (JSON com blocos + SEO),
`author_id`, `note`, `created_at`, `restored_from`.
Cada gravação cria versão. Restauro cria nova versão a partir da antiga (nunca
apaga histórico). Comparação entre duas versões campo a campo.

### 1.11 `scheduled_publications`
`target_type` (`page`, `plan`, `eco_system`), `target_id`, `run_at`, `status`
(`scheduled`, `done`, `failed`, `cancelled`), `created_by`, `result`.
Um worker publica no momento marcado e regista o resultado.

### 1.12 `cms_users` / papéis
Reutilizar `users` e `roles` da API. Acrescentar capacidades:
`content.read`, `content.write`, `content.publish`, `media.manage`,
`menus.manage`, `seo.manage`, `plans.manage`, `requests.read`.
O papel `conteudo` (Gestor de conteúdo) agrega todas menos as de operação.

### 1.13 `service_requests`
Já existe no backend (formulário público). O CMS mostra a lista "Pedidos
recebidos" com estados `new`, `contacted`, `qualified`, `closed` e exportação CSV.

---

## 2. Endpoints a criar

Prefixo `/api/cms/`. Autenticação e paginação iguais ao resto da API; erros 422
por campo.

```
GET    /api/cms/pages/                     lista, filtros: status, locale, q
POST   /api/cms/pages/
GET    /api/cms/pages/{id}/
PATCH  /api/cms/pages/{id}/
DELETE /api/cms/pages/{id}/                arquiva
POST   /api/cms/pages/{id}/restore/
POST   /api/cms/pages/{id}/publish/        body: {locales[]}
POST   /api/cms/pages/{id}/unpublish/
POST   /api/cms/pages/{id}/schedule/       body: {run_at}
POST   /api/cms/pages/{id}/duplicate/
GET    /api/cms/pages/{id}/preview-token/  devolve token de pré-visualização

GET    /api/cms/pages/{id}/blocks/
PUT    /api/cms/pages/{id}/blocks/         grava a lista inteira (ordem incluída)
PATCH  /api/cms/blocks/{id}/

GET    /api/cms/pages/{id}/versions/
GET    /api/cms/versions/{id}/
POST   /api/cms/versions/{id}/restore/
GET    /api/cms/versions/compare/?a=&b=

GET    /api/cms/media/                     filtros: folder, mime, q
POST   /api/cms/media/                     multipart
PATCH  /api/cms/media/{id}/                alt, folder
DELETE /api/cms/media/{id}/                bloqueia se estiver em uso

GET    /api/cms/menus/
PUT    /api/cms/menus/{key}/items/         grava ordem e itens de uma vez

GET    /api/cms/seo/{page_id}/
PUT    /api/cms/seo/{page_id}/

GET    /api/cms/plans/            POST /api/cms/plans/
PATCH  /api/cms/plans/{id}/       DELETE /api/cms/plans/{id}/
PUT    /api/cms/plans/order/
GET    /api/cms/plan-features/    PUT /api/cms/plan-features/

GET    /api/cms/eco-systems/      POST /api/cms/eco-systems/
PATCH  /api/cms/eco-systems/{id}/ PUT /api/cms/eco-systems/order/

GET    /api/cms/schedules/        POST /api/cms/schedules/
DELETE /api/cms/schedules/{id}/   cancela
```

Entrega ao site público (leitura, sem autenticação, com cache):

```
GET /api/public/site/{locale}/           menus + marca + definições globais
GET /api/public/pages/{slug}/{locale}/   página publicada com blocos e SEO
GET /api/public/plans/{locale}/
GET /api/public/eco-systems/
```

Pré-visualização: `GET /api/public/pages/{slug}/{locale}/?preview_token=…`
devolve o rascunho.

---

## 3. Ecrãs do CMS

Todos dentro do Portal, no grupo Conteúdo (hoje no bloco Propostas), com o mesmo
shell, tabelas, modais e pílulas do resto do portal.

### 3.1 Páginas do site
Tabela: Página (nome + slug em mono) · Estado (pílula) · Idiomas (PT/EN) ·
Última edição (autor + data) · acções. Acção principal "+ Nova página".
Acções por linha: editar, pré-visualizar, duplicar, agendar, arquivar.

### 3.2 Editor de página
Duas colunas: lista de blocos à esquerda (arrastar para reordenar, ligar/desligar,
adicionar bloco por tipo), formulário do bloco seleccionado ao centro,
pré-visualização ao vivo à direita, com alternador PT/EN e desktop/mobile.
Campos com contador de caracteres e limite. Barra de acções: "Guardar rascunho",
"Publicar", estado da versão, indicador "alterações por gravar".
Regra: gravar cria versão; publicar altera `status` e `published_at`.

### 3.3 Biblioteca de media
Grelha de cartões com miniatura, nome, dimensões, peso e "usado em N páginas".
Carregamento por arrastar. Painel de detalhe com alt por idioma e substituição de
ficheiro. Eliminar bloqueado quando está em uso, com a lista de onde está.

### 3.4 Menus e rodapé
Quatro listas (cabeçalho, rodapé produto, rodapé contacto, rodapé ecossistema)
com itens arrastáveis, rótulo por idioma, destino (página interna ou URL) e
visibilidade. Gravação de uma vez por menu.

### 3.5 SEO e partilha
Formulário por página e idioma: título, descrição, slug, palavras-chave, imagem de
partilha. Pré-visualização do resultado de pesquisa e do cartão social.
Contadores com limite (60/160/40/90).

### 3.6 Preços e planos
Lista de planos ordenável com nome, preço, unidade, itens incluídos, destaque e
visibilidade. Segundo separador: tabela comparativa (`plan_features`), editável
linha a linha, três colunas de valor.

### 3.7 Ecossistema UpDigital
Lista ordenável de sistemas com logótipo, nome, URL e estado.

### 3.8 Pedidos recebidos
Lista dos `service_requests`, filtro por estado, detalhe com a mensagem e as
acções "Marcar como contactado", "Qualificar", "Fechar". Exportar CSV.

### 3.9 Publicações agendadas
Lista com o que publica, alvo, quando e estado. Cancelar agendamento. Falhas
mostram o motivo.

### 3.10 Histórico de versões
Lista por página: versão, estado, autor, data. Ver versão, comparar duas versões
(diferenças campo a campo) e restaurar (com confirmação).

### 3.11 Utilizadores do CMS
Lista de quem tem acesso ao conteúdo, papel e último acesso; convite por email.
Matriz de capacidades por papel, só de leitura para papéis de sistema.

---

## 4. Fluxo de publicação

```
rascunho ──gravar──> rascunho (nova versão)
rascunho ──enviar para revisão──> em revisão
em revisão ──publicar (content.publish)──> publicado
em revisão ──agendar──> agendado ──worker no run_at──> publicado
publicado ──despublicar──> rascunho
qualquer ──restaurar versão──> rascunho com o conteúdo antigo
```

Regras:
- Publicar exige `content.publish`. Quem só tem `content.write` envia para revisão.
- Publicar valida: todos os blocos obrigatórios preenchidos nos idiomas marcados em
  `locales`, SEO com título e descrição, sem media em falta.
- A publicação invalida a cache das rotas públicas afectadas.
- Toda a acção fica na auditoria existente (`audit_logs`), com o diff.

---

## 5. Ligação ao site público

O site público passa a ler o CMS: a landing, os preços, os contactos e as apps
deixam de ter conteúdo no código. Ordem recomendada:

1. Construir os endpoints públicos e um cliente com cache (ISR/SSG ou cache HTTP de
   5 minutos com revalidação na publicação).
2. Migrar o conteúdo actual dos protótipos para seeds do CMS — os textos PT e EN
   estão nos objectos `PT`/`EN` de cada ficheiro de design e devem ser importados
   verbatim.
3. Só depois retirar os textos embutidos.

## 6. Critérios de pronto

- Editar um bloco, gravar, ver a versão nova no histórico e a alteração no site
  após publicar.
- Agendar uma publicação para daí a 5 minutos e vê-la ir ao ar sozinha.
- Restaurar uma versão anterior e confirmar que o histórico não perdeu nada.
- Trocar a ordem de um menu e ver o rodapé mudar em PT e EN.
- Substituir uma imagem na biblioteca e vê-la trocada em todas as páginas que a usam.
- Um utilizador com papel `conteudo` não abre nenhum módulo de operação (403).
