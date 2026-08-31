/**
 * Textos da moldura do site (barra de navegacao e rodape).
 *
 * Portados verbatim de docs/design-handoff/design/Landing BusUp - Ceu.dc.html.
 * O CMS gere o CONTEUDO das paginas (blocos, planos, menus, SEO); estas frases
 * sao da moldura e nao tem recurso correspondente na especificacao do CMS
 * (03-cms-especificacao.md, seccao 1) — por isso vivem aqui, num so sitio, nos
 * dois idiomas.
 */
export const CHROME = {
  "pt": {
    "portalLogin": "Entrar no portal",
    "talkSales": "Falar com vendas",
    "buyTicket": "Comprar bilhete",
    "navProduct": "Produto",
    "navFeatures": "Funcionalidades",
    "navWhy": "Porquê BusUp",
    "navCases": "Casos",
    "navPricing": "Preços",
    "navContact": "Contactos",
    "footerAbout": "Plataforma de bilhética digital para o transporte de passageiros. Desenvolvido em Moçambique.",
    "footerProduct": "Produto",
    "footerAccess": "Acesso",
    "footerContact": "Contacto",
    "footerPortal": "Portal de gestão",
    "footerApps": "Descarregar apps",
    "poweredBy": "Desenvolvido por",
    "footerEco": "Ecossistema",
    "rights": "Todos os direitos reservados."
  },
  "en": {
    "portalLogin": "Sign in to the portal",
    "talkSales": "Talk to sales",
    "buyTicket": "Buy a ticket",
    "navProduct": "Product",
    "navFeatures": "Features",
    "navWhy": "Why BusUp",
    "navCases": "Cases",
    "navPricing": "Pricing",
    "navContact": "Contact",
    "footerAbout": "Digital ticketing platform for passenger transport. Built in Mozambique.",
    "footerProduct": "Product",
    "footerAccess": "Access",
    "footerContact": "Contact",
    "footerPortal": "Management portal",
    "footerApps": "Download apps",
    "poweredBy": "Powered by",
    "footerEco": "Ecosystem",
    "rights": "All rights reserved."
  }
} as const;

export type ChromeKey = keyof typeof CHROME.pt;
