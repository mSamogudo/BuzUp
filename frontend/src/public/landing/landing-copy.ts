import type { Lang } from "./useLandingPrefs";

/** Texto da landing em PT/EN. Estrutura igual nos dois idiomas — o
 *  componente lê sempre as mesmas chaves. */
export const COPY = {
  pt: {
    nav: { produto: "Produto", como: "Como funciona", solucoes: "Soluções", plataforma: "Plataforma", eco: "Ecossistema" },
    // Nota: a landing é deliberadamente RESERVADA sobre o funcionamento da
    // plataforma — mostra o resultado comercial, não o manual do produto.
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
      h2: "Simples para o passageiro. Sólido para o operador.",
      steps: [
        {
          kicker: "Comprar", h3: "O bilhete compra-se no telemóvel.",
          text: "No site ou na app, pago com M-Pesa ou e-Mola, em menos de um minuto.",
          facts: [],
        },
      ],
    },
    platform: {
      kicker: "Portal de gestão", h2: "A operação inteira num ecrã.",
      lead: "A direcção vê a receita e a frota em tempo real, com relatórios e auditoria de ponta a ponta.",
      pills: ["Receita em tempo real", "Frota e rotas", "Relatórios", "Auditoria"],
    },
    security: {
      kicker: "Confiança", h2: "A receita deixa de depender de confiança.",
      lead: "Cada bilhete, validação e recarga fica registado. O que antes era palavra passa a ser dado auditável.",
      points: [
        "Receita registada na origem — sem dinheiro a passar de mão em mão.",
        "Pagamentos pelas carteiras nacionais, sem dados de cartão guardados.",
        "Perfis e permissões por função, com registo de quem fez o quê.",
      ],
    },
    audiences: {
      kicker: "Para quem é", h2: "Feito para quem move pessoas.",
      lead: "Operadores privados, empresas e instituições — a mesma plataforma, configurada para a realidade de cada frota.",
      items: [
        { name: "Operadores de transporte", text: "Urbano, interurbano e internacional — do bairro à travessia de fronteira." },
        { name: "Empresas", text: "Transporte de colaboradores, organizado e com contas certas." },
        { name: "Escolas e instituições", text: "Transporte escolar com o embarque controlado." },
        { name: "Passageiros", text: "Compram no telemóvel e pagam com a carteira que já usam." },
      ],
    },
    tools: {
      kicker: "Uma plataforma, três ferramentas", h2: "Do passageiro à direcção — tudo ligado.",
      download: "Descarregar as aplicações",
      items: [
        { name: "App Passageiro", tag: "Android", list: ["Comprar, pagar e viajar com o telemóvel."] },
        { name: "App POS", tag: "Agente e motorista", list: ["Vender e validar bilhetes a bordo."] },
        { name: "Portal de Gestão", tag: "Operação e direcção", list: ["Receita, frota e relatórios num só lugar."] },
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
      h2: "Simple for passengers. Solid for operators.",
      steps: [
        {
          kicker: "Buy", h3: "Tickets are bought on the phone.",
          text: "On the website or the app, paid with M-Pesa or e-Mola, in under a minute.",
          facts: [],
        },
      ],
    },
    platform: {
      kicker: "Management portal", h2: "The whole operation on one screen.",
      lead: "Management sees revenue and the fleet in real time, with reports and an end-to-end audit trail.",
      pills: ["Real-time revenue", "Fleet and routes", "Reports", "Audit"],
    },
    security: {
      kicker: "Trust", h2: "Revenue no longer depends on trust.",
      lead: "Every ticket, validation and top-up is recorded. What used to be someone's word becomes auditable data.",
      points: [
        "Revenue recorded at the source — no cash passing hand to hand.",
        "Payments through national wallets, with no card data stored.",
        "Roles and permissions per function, with a record of who did what.",
      ],
    },
    audiences: {
      kicker: "Who it is for", h2: "Built for those who move people.",
      lead: "Private operators, companies and institutions — the same platform, configured for each fleet's reality.",
      items: [
        { name: "Transport operators", text: "Urban, intercity and cross-border — from the neighbourhood to the border crossing." },
        { name: "Companies", text: "Staff transport, organised and with the books straight." },
        { name: "Schools and institutions", text: "School transport with boarding under control." },
        { name: "Passengers", text: "They buy on their phone and pay with the wallet they already use." },
      ],
    },
    tools: {
      kicker: "One platform, three tools", h2: "From passenger to management — all connected.",
      download: "Download the apps",
      items: [
        { name: "Passenger App", tag: "Android", list: ["Buy, pay and travel with your phone."] },
        { name: "POS App", tag: "Agent and driver", list: ["Sell and validate tickets on board."] },
        { name: "Management Portal", tag: "Operations and management", list: ["Revenue, fleet and reports in one place."] },
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
