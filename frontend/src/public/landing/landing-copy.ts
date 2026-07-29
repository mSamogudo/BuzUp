import type { Lang } from "./useLandingPrefs";

/** Texto da landing em PT/EN. Estrutura igual nos dois idiomas — o
 *  componente lê sempre as mesmas chaves. */
export const COPY = {
  pt: {
    nav: { produto: "Produto", como: "Como funciona", solucoes: "Soluções", plataforma: "Plataforma", eco: "Ecossistema" },
    signIn: "Entrar",
    signInPortal: "Entrar no portal",
    buy: "Comprar bilhete",
    talkSales: "Falar com vendas",
    skip: "Saltar para o conteúdo",
    openMenu: "Abrir menu",
    closeMenu: "Fechar menu",
    themeLight: "Tema claro",
    themeDark: "Tema escuro",
    hero: {
      badge: "Bilhética digital · Moçambique",
      h1a: "Bilhetes, frota e receita",
      h1b: "numa só plataforma.",
      lead1: "digitaliza a venda e a validação de bilhetes no transporte de passageiros — do bairro à viagem internacional. O passageiro compra no telemóvel ou no agente; o operador vê",
      leadStrong: "cada viagem e cada metical",
      lead2: ", em tempo real.",
      chips: ["QR no telemóvel", "Cartão NFC", "M-Pesa", "e-Mola"],
    },
    stats: [
      { v: "3", l: "canais de venda e validação" },
      { v: "2", l: "carteiras móveis integradas" },
      { v: "100%", l: "da receita registada" },
      { v: "0", l: "obras na frota actual" },
    ],
    benefits: {
      kicker: "O que o BusUp resolve",
      h2: "Menos dinheiro na mão. Mais controlo na operação.",
      lead: "Substitui o dinheiro vivo por pagamento digital e dá ao operador a informação que hoje se perde entre o passageiro e a tesouraria.",
      items: [
        { title: "Fim do dinheiro na mão", text: "Sem troco nem notas a circular. Menos furtos, menos erros e mais higiene a bordo." },
        { title: "Receita rastreável", text: "Cada bilhete fica registado. Combate directo à evasão de receita e ao desvio de fundos." },
        { title: "Dados para decidir", text: "Fluxo de passageiros por rota, horário e viatura — informação real para planear." },
        { title: "Todos os meios", text: "Carteira digital, cartão NFC ou dinheiro no agente. O passageiro escolhe." },
      ],
    },
    how: {
      kicker: "Como funciona",
      h2: "Veja o produto a trabalhar.",
      steps: [
        {
          kicker: "Passo 1 · Comprar", h3: "Escolhe o dia, a partida e o lugar.",
          text: "No site ou na app, em menos de um minuto.",
          facts: ["Partidas com semanas de antecedência", "Planta do autocarro com lugares livres", "Pagamento M-Pesa ou e-Mola"],
        },
        {
          kicker: "Passo 2 · Receber", h3: "O bilhete chega ao telemóvel.",
          text: "PDF nominal com QR, lugar e hora de partida. Também por SMS.", facts: [],
        },
        {
          kicker: "Passo 3 · Embarcar", h3: "O agente valida em segundos.",
          text: "QR ou cartão NFC no terminal. Sem smartphone? Compra ali mesmo.", facts: [], live: "App real",
        },
        {
          kicker: "Passo 4 · Seguir", h3: "O autocarro no mapa, ao vivo.",
          text: "Quando o motorista inicia a viagem, o passageiro vê onde ele está.", facts: [], live: "GPS real",
        },
      ],
    },
    modules: {
      kicker: "Funcionalidades", h2: "Tudo o que a operação precisa.",
      items: [
        { title: "Bilhete digital", text: "QR no telemóvel ou impresso, com código curto para leitura manual." },
        { title: "Cartão NFC", text: "Cartão recarregável para quem não tem smartphone. Ninguém fica de fora." },
        { title: "Carteira e recargas", text: "Saldo em Meticais, carregado por M-Pesa, e-Mola ou num agente." },
        { title: "Venda antecipada", text: "Bilhetes para dias seguintes, com lugar marcado e lotação controlada." },
        { title: "Frota no mapa", text: "Posição real dos autocarros em viagem, visível ao passageiro." },
        { title: "Receita e relatórios", text: "Por rota, viagem, agente e método de pagamento. Exportável." },
        { title: "Rotas e horários", text: "Paragens, troços e horários recorrentes que geram as partidas do dia." },
        { title: "Auditoria", text: "Cada venda e validação com registo. A receita deixa de depender de confiança." },
        { title: "Preço por troço", text: "Tarifa entre paragens, do bairro à viagem internacional." },
      ],
    },
    platform: {
      kicker: "Portal de gestão", h2: "A operação inteira num ecrã.",
      lead: "Receita do dia, rotas, horários, frota, agentes e terminais. Com relatórios exportáveis e registo de auditoria de ponta a ponta.",
      pills: ["Painel de receita", "Rotas e paragens", "Horários", "Frota e livrete", "Motoristas",
        "Agentes e terminais", "Passageiros", "Cartões", "Tarifas e pacotes", "Bilhetes ocasionais",
        "Fecho de caixa", "Relatórios", "Auditoria", "Actualização das apps"],
    },
    security: {
      kicker: "Confiança", h2: "A receita deixa de depender de confiança.",
      lead: "Cada bilhete, validação e recarga fica registado com autor, terminal e hora. O que antes era palavra passa a ser dado auditável.",
      points: [
        "Cada bilhete tem QR assinado e código curto — não se reutiliza nem se falsifica.",
        "Dinheiro deixa de passar de mão em mão: a receita é registada na origem.",
        "Perfis e permissões por função: cada pessoa vê apenas o que lhe compete.",
        "Registo de auditoria de vendas, validações e alterações de configuração.",
        "Pagamentos pelas carteiras nacionais, sem guardar dados de cartão.",
        "Funciona com ligação instável: o terminal opera e sincroniza depois.",
      ],
    },
    audiences: {
      kicker: "Para quem é", h2: "Feito para quem move pessoas.",
      lead: "Operadores privados, empresas e instituições — a mesma plataforma, configurada para a realidade de cada frota.",
      items: [
        { name: "Operadores de transporte", text: "Urbano, interurbano e internacional. Venda antecipada com lugar marcado, controlo de lotação e receita rastreada por viagem." },
        { name: "Empresas", text: "Transporte de colaboradores com passes mensais, controlo de acesso ao autocarro e relatórios de utilização por departamento." },
        { name: "Escolas e instituições", text: "Passes de estudante, embarque validado por cartão e histórico de viagens para as famílias e para a direcção." },
        { name: "Passageiros", text: "Compram no telemóvel, pagam com a carteira que já usam e seguem o autocarro no mapa até à paragem." },
      ],
    },
    tools: {
      kicker: "Uma plataforma, três ferramentas", h2: "Do passageiro à direcção — tudo ligado.",
      download: "Descarregar as aplicações",
      items: [
        { name: "App Passageiro", tag: "Android", list: ["Carteira em Meticais", "Recarga M-Pesa e e-Mola", "Bilhete por QR Code", "Mapa da frota em tempo real"] },
        { name: "App POS", tag: "Agente e motorista", list: ["Venda e validação a bordo", "Leitura QR e cartão NFC", "Início e fecho de viagens", "Terminais SUNMI e Urovo"] },
        { name: "Portal de Gestão", tag: "Operação e direcção", list: ["Rotas, horários e frota", "Receita e reconciliação", "Relatórios exportáveis", "Auditoria e permissões"] },
      ],
    },
    eco: {
      kicker: "Ecossistema UpDigital", h2: "O BusUp não anda sozinho.",
      lead: "Faz parte de uma família de produtos que já opera em Moçambique — pagamentos, tesouraria, mobilidade, acessos e gestão.",
      visit: "Visitar",
    },
    cta: {
      h2: "Leve o BusUp para a sua frota.",
      lead: "Marcamos uma demonstração e mostramos a plataforma a operar com os seus dados.",
      commercial: "Comercial", address: "Endereço", website: "Website",
    },
    form: {
      kicker: "Fale connosco", h2: "Vamos ver isto na sua operação.",
      lead: "Preenchemos a plataforma com as suas rotas e horários e mostramos o fluxo completo — venda, embarque e fecho de contas.",
      facts: ["Demonstração com os seus dados", "Instalação sem obra na frota", "Suporte local em Moçambique"],
    },
    footer: {
      about: "Plataforma de bilhética digital para o transporte de passageiros. Desenvolvido em Moçambique.",
      product: "Produto", access: "Acesso", contact: "Contacto",
      features: "Funcionalidades", portal: "Portal de gestão", apps: "Descarregar apps",
      rights: "Todos os direitos reservados.",
    },
  },

  en: {
    nav: { produto: "Product", como: "How it works", solucoes: "Solutions", plataforma: "Platform", eco: "Ecosystem" },
    signIn: "Sign in",
    signInPortal: "Sign in to portal",
    buy: "Buy a ticket",
    talkSales: "Talk to sales",
    skip: "Skip to content",
    openMenu: "Open menu",
    closeMenu: "Close menu",
    themeLight: "Light theme",
    themeDark: "Dark theme",
    hero: {
      badge: "Digital ticketing · Mozambique",
      h1a: "Tickets, fleet and revenue",
      h1b: "on a single platform.",
      lead1: "digitises ticket sales and validation in passenger transport — from the neighbourhood route to the cross-border trip. Passengers buy on their phone or from an agent; the operator sees",
      leadStrong: "every trip and every metical",
      lead2: ", in real time.",
      chips: ["QR on the phone", "NFC card", "M-Pesa", "e-Mola"],
    },
    stats: [
      { v: "3", l: "sales and validation channels" },
      { v: "2", l: "mobile wallets integrated" },
      { v: "100%", l: "of revenue recorded" },
      { v: "0", l: "changes to your current fleet" },
    ],
    benefits: {
      kicker: "What BusUp solves",
      h2: "Less cash in hand. More control over the operation.",
      lead: "It replaces cash with digital payment and gives the operator the information that today gets lost between passenger and treasury.",
      items: [
        { title: "No more cash in hand", text: "No change, no notes going around. Fewer thefts, fewer errors, better hygiene on board." },
        { title: "Traceable revenue", text: "Every ticket is recorded. A direct answer to revenue leakage and diverted funds." },
        { title: "Data to decide with", text: "Passenger flow by route, time and vehicle — real information for planning." },
        { title: "Every payment method", text: "Digital wallet, NFC card or cash with an agent. The passenger chooses." },
      ],
    },
    how: {
      kicker: "How it works",
      h2: "See the product at work.",
      steps: [
        {
          kicker: "Step 1 · Buy", h3: "Pick the day, the departure and the seat.",
          text: "On the website or the app, in under a minute.",
          facts: ["Departures weeks in advance", "Bus seat map with free seats", "M-Pesa or e-Mola payment"],
        },
        {
          kicker: "Step 2 · Receive", h3: "The ticket arrives on the phone.",
          text: "A named PDF with QR, seat and departure time. By SMS too.", facts: [],
        },
        {
          kicker: "Step 3 · Board", h3: "The agent validates in seconds.",
          text: "QR or NFC card on the terminal. No smartphone? Buy right there.", facts: [], live: "Real app",
        },
        {
          kicker: "Step 4 · Follow", h3: "The bus on the map, live.",
          text: "Once the driver starts the trip, passengers see where it is.", facts: [], live: "Real GPS",
        },
      ],
    },
    modules: {
      kicker: "Features", h2: "Everything the operation needs.",
      items: [
        { title: "Digital ticket", text: "QR on the phone or printed, with a short code for manual reading." },
        { title: "NFC card", text: "A rechargeable card for those without a smartphone. Nobody is left out." },
        { title: "Wallet and top-ups", text: "Balance in Meticais, topped up by M-Pesa, e-Mola or an agent." },
        { title: "Advance sales", text: "Tickets for future days, with assigned seats and capacity control." },
        { title: "Fleet on the map", text: "Real position of buses on the road, visible to passengers." },
        { title: "Revenue and reports", text: "By route, trip, agent and payment method. Exportable." },
        { title: "Routes and schedules", text: "Stops, legs and recurring schedules that generate each day's departures." },
        { title: "Audit trail", text: "Every sale and validation recorded. Revenue no longer depends on trust." },
        { title: "Price per leg", text: "Fares between stops, from the neighbourhood to the international trip." },
      ],
    },
    platform: {
      kicker: "Management portal", h2: "The whole operation on one screen.",
      lead: "Today's revenue, routes, schedules, fleet, agents and terminals. With exportable reports and an end-to-end audit trail.",
      pills: ["Revenue dashboard", "Routes and stops", "Schedules", "Fleet and documents", "Drivers",
        "Agents and terminals", "Passengers", "Cards", "Fares and passes", "Guest tickets",
        "Cash close", "Reports", "Audit", "App updates"],
    },
    security: {
      kicker: "Trust", h2: "Revenue no longer depends on trust.",
      lead: "Every ticket, validation and top-up is recorded with author, terminal and time. What used to be someone's word becomes auditable data.",
      points: [
        "Every ticket carries a signed QR and short code — it cannot be reused or forged.",
        "Cash stops passing hand to hand: revenue is recorded at the source.",
        "Roles and permissions per function: each person sees only what concerns them.",
        "Audit log of sales, validations and configuration changes.",
        "Payments through national wallets, with no card data stored.",
        "Works on unstable connections: the terminal operates and syncs later.",
      ],
    },
    audiences: {
      kicker: "Who it is for", h2: "Built for those who move people.",
      lead: "Private operators, companies and institutions — the same platform, configured for each fleet's reality.",
      items: [
        { name: "Transport operators", text: "Urban, intercity and cross-border. Advance sales with assigned seats, capacity control and revenue tracked per trip." },
        { name: "Companies", text: "Staff transport with monthly passes, boarding control and usage reports by department." },
        { name: "Schools and institutions", text: "Student passes, card-validated boarding and trip history for families and management." },
        { name: "Passengers", text: "They buy on their phone, pay with the wallet they already use and follow the bus on the map." },
      ],
    },
    tools: {
      kicker: "One platform, three tools", h2: "From passenger to management — all connected.",
      download: "Download the apps",
      items: [
        { name: "Passenger App", tag: "Android", list: ["Wallet in Meticais", "M-Pesa and e-Mola top-ups", "QR Code ticket", "Live fleet map"] },
        { name: "POS App", tag: "Agent and driver", list: ["On-board sales and validation", "QR and NFC card reading", "Start and close trips", "SUNMI and Urovo terminals"] },
        { name: "Management Portal", tag: "Operations and management", list: ["Routes, schedules and fleet", "Revenue and reconciliation", "Exportable reports", "Audit and permissions"] },
      ],
    },
    eco: {
      kicker: "UpDigital ecosystem", h2: "BusUp does not stand alone.",
      lead: "It is part of a family of products already running in Mozambique — payments, treasury, mobility, access control and management.",
      visit: "Visit",
    },
    cta: {
      h2: "Bring BusUp to your fleet.",
      lead: "We set up a demo and show the platform running with your own data.",
      commercial: "Sales", address: "Address", website: "Website",
    },
    form: {
      kicker: "Talk to us", h2: "Let's see this in your operation.",
      lead: "We load the platform with your routes and schedules and walk through the full flow — sale, boarding and cash close.",
      facts: ["Demo with your own data", "Installation without modifying the fleet", "Local support in Mozambique"],
    },
    footer: {
      about: "Digital ticketing platform for passenger transport. Built in Mozambique.",
      product: "Product", access: "Access", contact: "Contact",
      features: "Features", portal: "Management portal", apps: "Download apps",
      rights: "All rights reserved.",
    },
  },
} as const;

export type Copy = (typeof COPY)["pt"];

export function copyFor(lang: Lang): Copy {
  return (COPY[lang] ?? COPY.pt) as Copy;
}
