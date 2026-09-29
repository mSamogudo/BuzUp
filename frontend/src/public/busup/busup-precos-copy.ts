/** Texto da página de Preços do BusUp — o desenho "Céu".
 *
 * COPIADO VERBATIM do protótipo `Precos BusUp.dc.html`, em PT e EN, com uma
 * única alteração: "Falar com vendas" passa a "Entrar em contacto", como na
 * landing e a pedido.
 */

import type { Lang } from "../landing/useLandingPrefs";

const PT = {
  portalLogin: "Entrar no portal",
  navProduct: "Produto", navPricing: "Preços", navContact: "Contactos",
  navFeatures: "Funcionalidades", navWhy: "Porquê", navCases: "Casos",
  talkSales: "Entrar em contacto",
  badge: "Proposta em 2 dias úteis",
  h1a: "Preços por operação,", h1b: "não por tabela.",
  lead: "O valor depende da frota, dos canais de venda e do volume mensal. Não há licença por telemóvel de passageiro nem custo por bilhete emitido acima do combinado.",
  p1: "Urbano", p2: "Interurbano", p3: "Institucional",
  plans: [
    { name: "Urbano", price: "Sob consulta", who: "Frotas urbanas até 20 viaturas, com venda no agente e QR no telemóvel.", unit: "Mensalidade por viatura activa, com mínimo de frota.", cta: "Pedir proposta",
      items: ["Portal de gestão completo", "App POS para agentes e motoristas", "Pagamentos M-Pesa e e-Mola", "Relatórios diários e fecho de contas", "Suporte por telefone e email"] },
    { name: "Interurbano", featured: true, badge: "Mais procurado", price: "Sob consulta", who: "Rotas longas e internacionais, com lugar marcado e bilhete em PDF.", unit: "Mensalidade por viatura activa mais comissão por venda online.", cta: "Pedir proposta",
      items: ["Tudo do plano Urbano", "Lugar marcado e mapa de lugares", "Bilhete PDF com QR e reimpressão", "Cartões físicos NFC e digitais", "Programação automática de viagens", "Suporte prioritário"] },
    { name: "Institucional", price: "Sob consulta", who: "Empresas, escolas e frotas com contrato próprio ou transporte subsidiado.", unit: "Contrato anual, dimensionado ao número de utentes.", cta: "Entrar em contacto",
      items: ["Tudo do plano Interurbano", "Pacotes, subsídios e viagens gratuitas", "Perfis e permissões por função", "Integração com sistemas internos", "Gestor de conta dedicado"] },
  ],
  notes: [
    { h: "Instalação sem obra", p: "Não há equipamento a instalar nas viaturas. A validação corre em telemóveis Android comuns." },
    { h: "Arranque incluído", p: "Importação de rotas, paragens, horários e tarifas, formação da equipa e acompanhamento na primeira semana." },
    { h: "Sem custo para o passageiro", p: "Comprar e validar não tem taxa de plataforma para quem viaja. As taxas das carteiras móveis são as do operador de pagamento." },
  ],
  tableH2: "O que entra em cada plano",
  tableLead: "A diferença entre planos está nos canais de venda e na complexidade da operação, não em limites artificiais.",
  tableCol: "Funcionalidade", tableFoot: "Proposta para a sua frota", quote: "Pedir",
  rows: [
    { label: "Portal de gestão", a: "✓", b: "✓", c: "✓" },
    { label: "App POS (agente e motorista)", a: "✓", b: "✓", c: "✓" },
    { label: "M-Pesa e e-Mola", a: "✓", b: "✓", c: "✓" },
    { label: "Venda online ao passageiro", a: "QR", b: "QR + PDF", c: "QR + PDF" },
    { label: "Lugar marcado", a: "—", b: "✓", c: "✓" },
    { label: "Cartões NFC e digitais", a: "Digitais", b: "✓", c: "✓" },
    { label: "Pacotes e subsídios", a: "—", b: "Opcional", c: "✓" },
    { label: "GPS e mapa da frota", a: "✓", b: "✓", c: "✓" },
    { label: "Relatórios e auditoria", a: "Diários", b: "Completos", c: "Completos" },
    { label: "Suporte", a: "Email e telefone", b: "Prioritário", c: "Gestor dedicado" },
  ],
  faqH2: "Perguntas sobre preço",
  faqLead: "Se o seu caso não estiver aqui, diga-nos como funciona a sua operação e enviamos um número concreto.",
  faqs: [
    { q: "Porque é que não há uma tabela pública?", a: "Porque o valor justo depende do número de viaturas activas, dos canais de venda e do volume mensal. Uma tabela fixa cobraria a mais a frotas pequenas e a menos a operações grandes." },
    { q: "O que é cobrado: viatura, bilhete ou passageiro?", a: "A base é a viatura activa por mês. Em rotas com venda online há uma comissão por bilhete vendido nesse canal, acordada por escrito." },
    { q: "Há custo de instalação?", a: "O arranque está incluído: importação de rotas e tarifas, formação e acompanhamento na primeira semana. Cartões físicos NFC são cobrados à unidade." },
    { q: "O que acontece se a frota crescer?", a: "O contrato acompanha o número de viaturas activas. Novas viaturas entram no mês seguinte, sem taxa de adesão." },
    { q: "É possível fazer um piloto?", a: "Sim. Um piloto numa rota ou num conjunto de viaturas, com prazo definido e critérios de sucesso acordados antes de começar." },
  ],
  ctaH2: "Diga-nos como opera e devolvemos um número.",
  ctaLead: "Frota, rotas e volume mensal são o suficiente para uma proposta concreta em dois dias úteis.",
  ctaContact: "Pedir proposta", ctaProduct: "Ver a plataforma",
  footerAbout: "Plataforma de bilhética digital para o transporte de passageiros. Desenvolvido em Moçambique.",
  footerProduct: "Produto", footerContact: "Contacto",
  ecoLabel: "Desenvolvido por",
  ecoH2: "Quem constrói o BusUp",
  ecoLead: "O BusUp é desenvolvido pela UpDigital, Limitada — empresa moçambicana de software com sede na Matola. A mesma engenharia sustenta os outros produtos do grupo.",
  ecoNote: "Suporte local: quem escreve o software é quem atende o operador.",
  ecoItems: [
    { logo: "assets/logo-payup.png", name: "PayUp", url: "https://payup.updigital.co.mz" },
    { logo: "assets/logo-cashup.png", name: "CashUp", url: "https://cashup.updigital.co.mz" },
    { logo: "assets/logo-gateup.png", name: "GateUp", url: "https://gateup.updigital.co.mz" },
    { logo: "assets/logo-vura.png", name: "Vura", url: "https://vura.updigital.co.mz" },
    { logo: "assets/logo-ossoma.png", name: "Ossoma", url: "https://ossoma.updigital.co.mz" },
  ],
  poweredBy: "Desenvolvido por", footerEco: "Ecossistema",
  rights: "Todos os direitos reservados.",
};

const EN: typeof PT = {
  portalLogin: "Sign in to the portal",
  navProduct: "Product", navPricing: "Pricing", navContact: "Contact",
  navFeatures: "Features", navWhy: "Why BusUp", navCases: "Cases",
  talkSales: "Get in touch",
  badge: "Quote in 2 business days",
  h1a: "Priced per operation,", h1b: "not per table.",
  lead: "The figure depends on fleet size, sales channels and monthly volume. There is no licence per passenger phone and no per-ticket cost beyond what is agreed.",
  p1: "Urban", p2: "Intercity", p3: "Institutional",
  plans: [
    { name: "Urban", price: "On request", who: "Urban fleets up to 20 vehicles, with agent sales and QR on the phone.", unit: "Monthly fee per active vehicle, with a fleet minimum.", cta: "Request a quote",
      items: ["Full management portal", "POS app for agents and drivers", "M-Pesa and e-Mola payments", "Daily reports and cash close", "Phone and email support"] },
    { name: "Intercity", featured: true, badge: "Most requested", price: "On request", who: "Long and cross-border routes, with assigned seats and PDF tickets.", unit: "Monthly fee per active vehicle plus commission on online sales.", cta: "Request a quote",
      items: ["Everything in Urban", "Assigned seats and seat map", "PDF ticket with QR and reprint", "Physical NFC and digital cards", "Automatic trip scheduling", "Priority support"] },
    { name: "Institutional", price: "On request", who: "Companies, schools and fleets under contract or subsidised transport.", unit: "Annual contract, sized to the number of users.", cta: "Get in touch",
      items: ["Everything in Intercity", "Packages, subsidies and free trips", "Roles and permissions per function", "Integration with internal systems", "Dedicated account manager"] },
  ],
  notes: [
    { h: "No fleet retrofit", p: "Nothing is installed on the vehicles. Validation runs on ordinary Android phones." },
    { h: "Onboarding included", p: "Import of routes, stops, schedules and fares, team training and hands-on support in the first week." },
    { h: "No cost to the passenger", p: "Buying and validating carries no platform fee for travellers. Mobile wallet fees are the payment provider's own." },
  ],
  tableH2: "What each plan includes",
  tableLead: "The difference between plans is sales channels and operational complexity, not artificial limits.",
  tableCol: "Capability", tableFoot: "Quote for your fleet", quote: "Request",
  rows: [
    { label: "Management portal", a: "✓", b: "✓", c: "✓" },
    { label: "POS app (agent and driver)", a: "✓", b: "✓", c: "✓" },
    { label: "M-Pesa and e-Mola", a: "✓", b: "✓", c: "✓" },
    { label: "Online sales to passengers", a: "QR", b: "QR + PDF", c: "QR + PDF" },
    { label: "Assigned seats", a: "—", b: "✓", c: "✓" },
    { label: "NFC and digital cards", a: "Digital", b: "✓", c: "✓" },
    { label: "Packages and subsidies", a: "—", b: "Optional", c: "✓" },
    { label: "GPS and fleet map", a: "✓", b: "✓", c: "✓" },
    { label: "Reports and audit trail", a: "Daily", b: "Full", c: "Full" },
    { label: "Support", a: "Email and phone", b: "Priority", c: "Dedicated manager" },
  ],
  faqH2: "Questions about price",
  faqLead: "If your case is not here, tell us how your operation works and we will send a concrete figure.",
  faqs: [
    { q: "Why is there no public price table?", a: "Because a fair figure depends on active vehicles, sales channels and monthly volume. A fixed table would overcharge small fleets and undercharge large operations." },
    { q: "What is charged: vehicle, ticket or passenger?", a: "The base is the active vehicle per month. On routes with online sales there is a commission per ticket sold through that channel, agreed in writing." },
    { q: "Is there an installation cost?", a: "Onboarding is included: import of routes and fares, training and hands-on support in the first week. Physical NFC cards are charged per unit." },
    { q: "What happens if the fleet grows?", a: "The contract follows the number of active vehicles. New vehicles join the following month, with no joining fee." },
    { q: "Can we run a pilot?", a: "Yes. A pilot on one route or a set of vehicles, with a defined period and success criteria agreed up front." },
  ],
  ctaH2: "Tell us how you operate and we will send a figure.",
  ctaLead: "Fleet, routes and monthly volume are enough for a concrete quote in two business days.",
  ctaContact: "Request a quote", ctaProduct: "See the platform",
  footerAbout: "Digital ticketing platform for passenger transport. Built in Mozambique.",
  footerProduct: "Product", footerContact: "Contact",
  ecoLabel: "Built by",
  ecoH2: "Who builds BusUp",
  ecoLead: "BusUp is built by UpDigital, Limitada — a Mozambican software company based in Matola. The same engineering supports the group's other products.",
  ecoNote: "Local support: the people who write the software are the people who answer the operator.",
  ecoItems: [
    { logo: "assets/logo-payup.png", name: "PayUp", url: "https://payup.updigital.co.mz" },
    { logo: "assets/logo-cashup.png", name: "CashUp", url: "https://cashup.updigital.co.mz" },
    { logo: "assets/logo-gateup.png", name: "GateUp", url: "https://gateup.updigital.co.mz" },
    { logo: "assets/logo-vura.png", name: "Vura", url: "https://vura.updigital.co.mz" },
    { logo: "assets/logo-ossoma.png", name: "Ossoma", url: "https://ossoma.updigital.co.mz" },
  ],
  poweredBy: "Powered by", footerEco: "Ecosystem",
  rights: "All rights reserved.",
};

const DICIONARIOS: Record<Lang, typeof PT> = { pt: PT, en: EN };

export function copyPrecos(lang: Lang) {
  return DICIONARIOS[lang] ?? PT;
}

export type CopyPrecos = typeof PT;
