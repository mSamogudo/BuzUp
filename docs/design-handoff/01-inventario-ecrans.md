# Inventário de ecrãs — lista de verificação

Nenhuma linha desta lista pode ficar por implementar. A coluna **Ficheiro** indica
onde ver o desenho.

---

## A. Portal de operação — `Portal BusUp v2.dc.html`

Moldura 1440×1120. Barra lateral agrupada por domínio, cabeçalho fixo, conteúdo com
migalhas + título + descrição + acções + filtros + lista.

### A.0 Estrutura permanente

| # | Ecrã / elemento | Detalhe |
|---|---|---|
| A0.1 | Barra lateral colapsada (84px) | Marca `busup-mark.png` como botão de expandir; só ícones, com tooltip |
| A0.2 | Barra lateral expandida (264px) | Logótipo + botão `⟨`; grupos Transporte, Operação, Tarifação, Passageiros, Financeiro, Sistema, Propostas |
| A0.3 | Cartão de utilizador | Avatar, nome, papel, terminar sessão, `v0.1.0 · powered by UpDigital` |
| A0.4 | Cabeçalho fixo | Auto 30s, selector de papel, PT/EN (nos módulos de conteúdo), tema, sino, conta |
| A0.5 | Painel de notificações | Lista do sino, com marcação de lida |
| A0.6 | Selector de papel | Troca o papel activo e refiltra a navegação (8 papéis) |
| A0.7 | Modal de formulário | 720px, cabeçalho fixo, passos automáticos acima de 8 campos, rodapé com Criar / Guardar alterações |
| A0.8 | Confirmação destrutiva | Arquivar/eliminar com aviso e "Desfazer" 8s |
| A0.9 | Estado vazio, esqueleto de carregamento, barra de sem rede | Padrões partilhados |
| A0.10 | Erros no portal | 403, 404, 500 em ecrã inteiro, sem shell, com a linha do pedido que falhou |

### A.1 Módulos (24 na navegação)

Módulos com separadores (`MODTABS`) abrem várias listas no mesmo ecrã.

| # | Módulo (navegação) | Recursos / separadores | Notas |
|---|---|---|---|
| A1.1 | **Painel** | métricas + gráficos | Cartões de métrica, receita do dia, viagens em curso, alertas |
| A1.2 | **Rotas** | `routes` (+ `route_stops` por acção) | Código gerado pelo backend; acção "Definir paragens" grava a sequência de uma vez, com inversão para a volta |
| A1.3 | **Paragens** | `stops` | Coordenadas; contagem de rotas em que entra |
| A1.4 | **Veículos** | `vehicles` | Lotação sentada/de pé, layout de lugares, livrete; acção "Pré-visualizar lugares" |
| A1.5 | **Motoristas** | `drivers` | Utilizador criado no mesmo pedido; carta de condução |
| A1.6 | **Viagens** | `trips`, `schedules`, `scheduler` | Acções Partir, Iniciar, Pausar, Retomar, Fechar; exportar Manifesto PDF; agendador em calendário mensal; `schedule_days` para os dias de operação |
| A1.7 | **Mapa** | mapa Leaflet | Sete terminais reais de Maputo, filtro por estado, iframe de `mapa-terminais.html` |
| A1.8 | **Tarifas** | `matrix`, `fare_rules`, `fare_products`, `admin_fees`, `exchange_rates` | Tabela de preços origem–destino com preenchimento em massa, importação por modelo e espelho para a volta |
| A1.9 | **Pacotes** | `packages`, `passenger_packages` | Desconto por percentagem, valor fixo ou viagens grátis, limitado a rotas |
| A1.10 | **Passageiros** | `passengers` | Documento, telefone, conta de utilizador opcional, extracto PDF |
| A1.11 | **Carteiras** | `wallets`, `wallet_transactions` | Saldos só de leitura; livro com saldo antes/depois |
| A1.12 | **Cartões Físicos** | `cards` | Lote, fabricante, UID; acções Activar, Atribuir, Bloquear, Substituir |
| A1.13 | **Carteiras Digitais** | `cards_digital` | QR gerado na app; acções Bloquear, Regenerar QR |
| A1.14 | **Pagamentos** | `payment_intents`, `topups`, `validations` | Finalidade, provedor, idempotência; consultar estado, ver callbacks, marcar para revisão |
| A1.15 | **Bilhetes Ocasionais** | `guest_checkouts` (+ `tickets`) | Compra sem conta; bilhete público por token; reenviar SMS |
| A1.16 | **Sessões POS** | `pos_sessions` | Agente + dispositivo + rota; forçar fecho |
| A1.17 | **Receita de Agentes** | `agent_revenue` | Consolidado por intervalo; exportar PDF/XLSX |
| A1.18 | **Relatórios** | `reports`, `reconciliation`, `imports` | Catálogo + construtor (tipo, intervalo, filtros); importações com erros por linha e modelo CSV |
| A1.19 | **Terminais** | `devices`, `device_activations`, `device_app_updates` | Auto-registo → código de activação → configuração; aprovar/rejeitar; forçar actualização |
| A1.20 | **APKs** | `app_releases` | Por tipo de app; publicar, suspender, ver descargas |
| A1.21 | **Utilizadores** | `users`, `roles` (+ `capabilities`) | Papéis por identificador; redefinir palavra-passe; catálogo de capacidades só de leitura |
| A1.22 | **Auditoria** | `audit_logs` | Entidade, acção, actor, data e IP, diferenças |
| A1.23 | **Marca** | `branding_keys` | Recurso único: 9 chaves (nome, cores, logos, contactos, moeda, rodapé do bilhete); pré-visualizar e repor |
| A1.24 | **Termos e Condições** | versão actual + histórico | Publicação de nova versão |
| A1.25 | **Definições** | perfil, segurança, preferências, notificações | Dados de conta, alteração de senha, 2FA, idioma e tema |

Recursos adicionais que existem no desenho e têm de ser implementados dentro dos
módulos acima: `day_closes` (Agentes · Fechos de dia), `service_requests`
(Pedidos de serviço), `broadcasts` (Difusões), `shifts` (proposta, ver A.2),
`route_stops`, `schedule_days`, `tickets`, `capabilities`.

### A.2 Bloco Propostas (não existe no backend)

Aparece no fim da navegação, com aviso no topo do ecrã: "Este módulo não existe no
sistema. Está desenhado como proposta — não há endpoints nem ecrãs correspondentes
no repositório."

| # | Proposta | O que exige do backend |
|---|---|---|
| A2.1 | Agentes e turnos (`shifts`) | `/shifts` listar, abrir, fechar, conferir, reabrir + `shift_id` em bilhetes e validações |
| A2.2 – A2.12 | Todo o CMS: Páginas do site, Editor de página, Media, Menus e rodapé, SEO e partilha, Preços e planos, Ecossistema, Pedidos, Agendamento, Versões, Utilizadores do CMS | Ver `03-cms-especificacao.md` |

### A.3 Estados por lista

Para **cada** recurso: lista com filtros por estado, pesquisa, selecção múltipla,
colunas configuráveis, paginação, vista de arquivados, detalhe em painel, formulário
em modal, exportações declaradas (PDF/XLSX/CSV/Manifesto/Modelo CSV) e as acções
próprias do recurso.

---

## B. Site público

### B.1 Landing — `Landing BusUp - Ceu.dc.html` (desktop + mobile 390)

| # | Secção | Conteúdo |
|---|---|---|
| B1.1 | Barra de navegação | Logo, Produto, Funcionalidades, Porquê BusUp, Casos, Preços, Contactos, PT/EN, tema, "Entrar no portal", "Falar com vendas" |
| B1.2 | Herói | Etiqueta "Bilhética digital · Moçambique", H1 em duas linhas (segunda a azul), lead, dois CTA, chips (QR no telemóvel, Cartão NFC, M-Pesa, e-Mola) |
| B1.3 | Faixa de logos | "Construído sobre o ecossistema UpDigital" |
| B1.4 | Funcionalidades | 5 blocos (venda em três canais, validação, cartões, receita, frota e rotas no mapa) |
| B1.5 | Porquê BusUp | 4 números de produto |
| B1.6 | Começar em três passos | Painel do portal ilustrado por passo |
| B1.7 | Casos | 3 depoimentos (placeholder assumido) |
| B1.8 | Resumo de preços | 3 planos: Urbano, Interurbano, Institucional |
| B1.9 | FAQ | 6 perguntas |
| B1.10 | Formulário de contacto | Campos + estado "Pedido enviado" |
| B1.11 | CTA final | "Leve o BusUp para a sua frota" |
| B1.12 | Ecossistema / Quem constrói | UpDigital, Matola, suporte local |
| B1.13 | Rodapé | Produto, Contacto, ecossistema, "Desenvolvido por" + logo UpDigital, © 2026 |

### B.2 Preços — `Precos BusUp.dc.html` (desktop + mobile)

Herói ("Preços por operação, não por tabela"), três planos, cartões de política,
tabela comparativa de 4 colunas (Funcionalidade / Urbano / Interurbano /
Institucional) com linha final de proposta, FAQ de preço, CTA, rodapé.
Em mobile a tabela passa a lista de notas.

### B.3 Contactos — `Contactos BusUp.dc.html` (desktop + mobile)

Formulário de contacto comercial, dados da empresa (Av. Alberto Massavanhane 1265,
sales@updigital.co.mz, www.updigital.co.mz), bloco de ecossistema com logo
UpDigital, rodapé navy.

### B.4 Apps — `Apps BusUp.dc.html`

Fluxos completos das apps mobile e POS ("Os cinco produtos, com o vocabulário do
Portal"): passageiro, motorista, agente, POS e validação. Mesmos tipos, paleta,
pílulas de estado e traduções de enums do Portal. Alvos de toque ≥ 44px.

### B.5 Compra de bilhetes — `Compra de Bilhetes BusUp.dc.html` + `Ecra Compra.dc.html`

Mobile 390, 6 passos + 2 estados de excepção, bilingue:

| Passo | Ecrã | Conteúdo |
|---|---|---|
| 01 | Pesquisa | percurso, data e nº de bilhetes |
| 02 | Partidas | hora, viatura, lugares e preço |
| 03 | Lugares | planta 2+2 com fila corrida no fundo |
| 04 | Passageiros | bilhete nominal, um cartão por lugar |
| 05 | Pagamento | M-Pesa, e-Mola, carteira ou agente |
| 06 | Bilhete emitido | referência, QR e PDF |
| E1 | Esgotado | sem lugares na data escolhida |
| E2 | Falha no pagamento | nada foi cobrado, retomar |

### B.6 Acesso — `Acesso BusUp.dc.html`

| # | Ecrã | Detalhe |
|---|---|---|
| B6.1 | Entrada de pessoal (portal/POS) | Utilizador ou telefone, senha com mostrar/ocultar, manter sessão, esqueci a senha |
| B6.2 | Reposição de senha | Telefone; nova senha enviada por SMS |
| B6.3 | Entrada de passageiro por OTP | Passo telefone → passo código |
| B6.4 | Sessão a validar | "A validar a sua sessão" com três passos: credenciais confirmadas, a carregar permissões, a preparar o painel |
| B6.5 | Arranque do portal | "A preparar o portal…" |
| B6.6 | Painel lateral de marca | Versões desktop e mobile, tema claro e escuro, PT/EN |

### B.7 Erros — `Erros BusUp.dc.html` (desktop + mobile, PT/EN)

404 Página não encontrada · 401 Sessão terminada · 403 Sem permissão ·
500 Erro do servidor · 503 Manutenção programada · ⚡ Sem ligação.
Cada um com: código grande, título, lead, dois CTA, três cartões de ajuda e a
referência técnica em mono (`ref. 500 · incidente INC-2026-0804-17`).

### B.8 Mapa de terminais — `mapa-terminais.html`

Leaflet/OpenStreetMap centrado em Maputo, sete terminais nas coordenadas reais,
marcadores por estado, filtro por estado, popup com nome, estado e contagem.
Embebido no módulo Mapa do portal por iframe.

---

## C. Contagem final

- Portal: 25 ecrãs de módulo + 10 elementos estruturais + 12 propostas (CMS e turnos).
- Site público: 4 páginas + 8 ecrãs de compra + 6 ecrãs de acesso + 6 ecrãs de erro + mapa.
- Cada ecrã em tema claro **e** escuro; site público, compra, acesso e erros também
  em PT **e** EN.
