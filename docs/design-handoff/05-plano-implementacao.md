# Plano de implementação

Ordem sugerida para o Claude Code. Cada fase termina com critérios verificáveis.

## Fase 0 — Fundações (antes de qualquer ecrã)

1. Escolher/confirmar a stack. Se não houver front-end: React + TypeScript + Vite,
   react-router, TanStack Query, Zod, Tailwind ou CSS Modules.
2. Tokens de `02-tokens-e-padroes.md` como variáveis CSS, com tema claro e escuro
   por `data-theme` em `<html>` (portar a lógica de `design/theme.js`).
3. Fontes Manrope, Inter e IBM Plex Mono.
4. Camada de API: cliente com autenticação, tratamento de 401/403/404/422/500,
   paginação e filtros normalizados. Erros 422 devolvidos por campo.
5. Componentes base, todos com estado normal/hover/foco/desactivado:
   `Button`, `Pill`, `Input`, `Select`, `Textarea`, `Checkbox`, `Switch`,
   `Table`, `EmptyState`, `Skeleton`, `Modal`, `SteppedForm`, `Toast`,
   `ConfirmDestructive`, `Tabs`, `Breadcrumb`, `Logo`.
6. Shell do portal: barra lateral colapsável de largura fixa, cabeçalho fixo,
   navegação agrupada, filtragem por papel.

**Pronto quando**: o shell abre em claro e escuro, a navegação reflecte o papel e
uma tabela de exemplo mostra esqueleto, dados, vazio e erro.

## Fase 1 — Portal, módulos ligados a endpoints existentes

Por ordem de valor operacional:
1. Painel, Rotas, Paragens, Veículos, Motoristas.
2. Viagens (+ Programações, Agendador, Dias de operação), Mapa.
3. Tarifas (Tabela de preços, Regras, Produtos, Taxas, Câmbio) e Pacotes.
4. Passageiros, Carteiras, Cartões Físicos, Carteiras Digitais.
5. Pagamentos, Bilhetes Ocasionais, Sessões POS, Receita de Agentes, Relatórios.
6. Terminais, APKs, Utilizadores, Auditoria, Marca, Termos, Definições.

Cada módulo: lista com filtros, pesquisa, colunas, paginação, arquivados, detalhe,
formulário em modal (faseado acima de 8 campos), acções próprias e exportações.

**Pronto quando**: cada linha de A1 do inventário existe, com os enums traduzidos e
as acções ligadas aos endpoints reais.

## Fase 2 — Site público

1. Landing, Preços, Contactos, Apps — desktop e mobile, PT e EN.
2. Fluxo de compra de bilhetes (6 passos + esgotado + falha de pagamento).
3. Acesso (pessoal, reposição, OTP de passageiro, sessão a validar).
4. Erros 404/401/403/500/503/sem-ligação.

Nesta fase o conteúdo pode ficar em ficheiros de tradução; a Fase 4 move-o para o
CMS.

**Pronto quando**: as quatro páginas e todos os ecrãs de B do inventário passam em
claro/escuro e PT/EN, com Lighthouse acima de 90 em acessibilidade.

## Fase 3 — Backend do CMS

Seguir `03-cms-especificacao.md`: tabelas, endpoints `/api/cms/*`, endpoints
públicos, worker de agendamento, capacidades novas, auditoria.

**Pronto quando**: todos os critérios da secção 6 da especificação passam por API,
sem interface.

## Fase 4 — Front-end do CMS e ligação do site

1. Os onze ecrãs do CMS (3.1 a 3.11 da especificação).
2. Editor de blocos com pré-visualização ao vivo, PT/EN e desktop/mobile.
3. Migrar o conteúdo dos protótipos para seeds do CMS, verbatim.
4. Site público passa a ler os endpoints públicos, com cache invalidada na
   publicação.

**Pronto quando**: uma alteração feita no editor aparece no site sem tocar em
código, e o histórico de versões permite voltar atrás.

## Fase 5 — Lacunas da API já existentes

Implementar os ecrãs da secção 1 de `04-lacunas-backend.md`: matriz de tarifas
completa, simulador de quote, viaturas no mapa, mapa de lugares, heartbeat nos
terminais, recuperação de cartão, registo de webhooks, construtor de relatórios,
gráficos do painel, segurança da conta.

## Fase 6 — Propostas

Turnos de agente (`shifts`), com o backend correspondente. Manter o aviso de
proposta até os endpoints existirem.

---

## Regras transversais

- Nenhum texto novo inventado: o conteúdo dos protótipos é para usar tal e qual,
  em PT e EN.
- Cada ecrã tem de responder aos quatro estados: carregamento, vazio, erro e cheio.
- Nada de bibliotecas de UI que tragam a sua própria linguagem visual sem
  reconfiguração completa dos tokens.
- Acessibilidade: contraste AA, navegação por teclado em modais e tabelas, foco
  visível, `aria-label` em botões só de ícone (os protótipos já os trazem).
- Testes: um teste de integração por fluxo crítico (entrar, criar registo com erro
  422, arquivar e desfazer, comprar bilhete, publicar página).
