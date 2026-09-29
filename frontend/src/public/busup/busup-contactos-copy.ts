/** Texto da página de Contactos do BusUp — o desenho "Céu".
 *
 * COPIADO VERBATIM do protótipo `Contactos BusUp.dc.html`, em PT e EN. Tem
 * dicionário próprio e não partilha com a landing: as chaves são outras e o
 * protótipo também as separa.
 */

import type { Lang } from "../landing/useLandingPrefs";

const PT = {
  portalLogin: "Entrar no portal",
  navProduct: "Produto", navPricing: "Preços", navContact: "Contactos",
  navFeatures: "Funcionalidades", navWhy: "Porquê", navCases: "Casos",
  callNow: "Ligar agora",
  badge: "Resposta no mesmo dia útil",
  h1: "Fale connosco.",
  lead: "Respondemos a pedidos de proposta, dúvidas técnicas e suporte comercial. A equipa que constrói o BusUp é a mesma que atende.",
  formTitle: "Pedido de contacto",
  formSub: "Preenchemos a plataforma com as suas rotas e horários antes da reunião.",
  g1: "1 · Quem contacta", g2: "2 · A operação", g3: "3 · O que quer ver",
  fName: "Nome", fRole: "Cargo", fCompany: "Empresa", fPhone: "Telefone", fEmail: "Email",
  fFleet: "Viaturas na frota", fType: "Tipo de operação", fInterest: "O que quer ver", fMsg: "Mensagem",
  types: ["Urbano", "Interurbano", "Internacional", "Empresa ou escola"],
  interests: ["Venda online", "Validação a bordo", "Cartões NFC", "Relatórios", "Pacotes e subsídios"],
  formCta: "Enviar pedido",
  formNote: "Respondemos em dias úteis, das 08h00 às 17h00 (CAT). Os dados servem apenas para o contacto comercial.",
  sentTitle: "Pedido enviado.", sentText: "A equipa comercial responde no próximo dia útil, pelo contacto que indicou.",
  sendAnother: "Enviar outro pedido",
  directTitle: "Directo", commercial: "Comercial", emailNote: "Propostas e suporte",
  hoursTitle: "Horário", hours: "Segunda a sexta, 08h00 – 17h00",
  addressTitle: "Endereço", mapNote: "Matola, Província de Maputo",
  mapPlaceholder: "Mapa incorporado a inserir",
  quickTitle: "Atalhos", apps: "Descarregar as aplicações",
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
  footerAbout: "Plataforma de bilhética digital para o transporte de passageiros. Desenvolvido em Moçambique.",
  footerProduct: "Produto", footerContact: "Contacto",
  poweredBy: "Desenvolvido por", footerEco: "Ecossistema",
  rights: "Todos os direitos reservados.",
};

const EN: typeof PT = {
  portalLogin: "Sign in to the portal",
  navProduct: "Product", navPricing: "Pricing", navContact: "Contact",
  navFeatures: "Features", navWhy: "Why BusUp", navCases: "Cases",
  callNow: "Call now",
  badge: "Answered the same business day",
  h1: "Talk to us.",
  lead: "We answer quote requests, technical questions and commercial support. The team that builds BusUp is the team that replies.",
  formTitle: "Contact request",
  formSub: "We load the platform with your routes and schedules before the meeting.",
  g1: "1 · Who is contacting", g2: "2 · The operation", g3: "3 · What you want to see",
  fName: "Name", fRole: "Role", fCompany: "Company", fPhone: "Phone", fEmail: "Email",
  fFleet: "Vehicles in fleet", fType: "Type of operation", fInterest: "What you want to see", fMsg: "Message",
  types: ["Urban", "Intercity", "Cross-border", "Company or school"],
  interests: ["Online sales", "On-board validation", "NFC cards", "Reports", "Packages and subsidies"],
  formCta: "Send request",
  formNote: "We reply on business days, 08:00 to 17:00 (CAT). Your details are used only for commercial contact.",
  sentTitle: "Request sent.", sentText: "The sales team replies on the next business day, through the contact you gave.",
  sendAnother: "Send another request",
  directTitle: "Direct", commercial: "Sales", emailNote: "Quotes and support",
  hoursTitle: "Opening hours", hours: "Monday to Friday, 08:00 – 17:00",
  addressTitle: "Address", mapNote: "Matola, Maputo Province",
  mapPlaceholder: "Embedded map to be added",
  quickTitle: "Shortcuts", apps: "Download the apps",
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
  footerAbout: "Digital ticketing platform for passenger transport. Built in Mozambique.",
  footerProduct: "Product", footerContact: "Contact",
  poweredBy: "Powered by", footerEco: "Ecosystem",
  rights: "All rights reserved.",
};

const DICIONARIOS: Record<Lang, typeof PT> = { pt: PT, en: EN };

export function copyContactos(lang: Lang) {
  return DICIONARIOS[lang] ?? PT;
}

export type CopyContactos = typeof PT;
