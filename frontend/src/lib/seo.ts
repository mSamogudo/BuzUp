/* ============================================================
   BuzUp — SEO config for public marketing pages.
   Per-page titles/descriptions (PT + EN), canonical/hreflang
   URLs and JSON-LD structured-data builders.
   ============================================================ */

export type Lang = "pt" | "en";

/** Production origin. Override at build time with VITE_SITE_URL. */
export const SITE_URL =
  (import.meta.env.VITE_SITE_URL as string | undefined)?.replace(/\/$/, "") ||
  "https://buzup.updigital.co.mz";

export const OG_IMAGE = `${SITE_URL}/assets/buzup/hero-person.png`;

export interface PageSeo {
  /** PT (canonical) path, e.g. "/tarifas" */
  ptPath: string;
  /** EN path, e.g. "/en/tarifas" */
  enPath: string;
  title: Record<Lang, string>;
  description: Record<Lang, string>;
}

/** abs("/tarifas") -> "https://.../tarifas" ; abs("/") -> "https://.../" */
export function abs(path: string): string {
  return `${SITE_URL}${path === "/" ? "/" : path}`;
}

/**
 * Prefix an internal marketing route with /en when rendering the English
 * version, so EN pages link to EN pages (crawl discovery + UX). Hash anchors,
 * /login and external links are left untouched.
 */
export function localizedPath(path: string, lang: Lang): string {
  if (lang !== "en") return path;
  if (path === "/") return "/en";
  if (path === "/tarifas" || path === "/contacto") return `/en${path}`;
  return path;
}

export const PAGES = {
  landing: {
    ptPath: "/",
    enPath: "/en",
    title: {
      pt: "BuzUp — Pague a sua viagem com um toque",
      en: "BuzUp — Pay for your ride with a tap",
    },
    description: {
      pt: "BuzUp é a bilhética cashless de Moçambique: pague o transporte público com um toque. Recarregue por M-Pesa ou e-Mola, toque o cartão ou telemóvel e viaje sem filas.",
      en: "BuzUp is Mozambique's cashless transit ticketing: pay for public transport with a tap. Top up via M-Pesa or e-Mola, tap your card or phone and travel without queues.",
    },
  },
  pricing: {
    ptPath: "/tarifas",
    enPath: "/en/tarifas",
    title: {
      pt: "Tarifas e planos BuzUp — preços para passageiros e operadores",
      en: "BuzUp pricing & plans — for passengers and operators",
    },
    description: {
      pt: "Preços simples e transparentes da BuzUp. Bilhetes diários, semanais e mensais para passageiros e planos escaláveis para operadores de transporte. Sem taxas escondidas.",
      en: "Simple, transparent BuzUp pricing. Daily, weekly and monthly tickets for passengers and scalable plans for transport operators. No hidden fees.",
    },
  },
  contact: {
    ptPath: "/contacto",
    enPath: "/en/contacto",
    title: {
      pt: "Contacto BuzUp — fale com a equipa em Maputo",
      en: "Contact BuzUp — talk to the team in Maputo",
    },
    description: {
      pt: "Fale com a equipa BuzUp em Maputo, Moçambique. Peça uma demonstração para a sua operação de transporte ou tire dúvidas — resposta em menos de 24 horas.",
      en: "Talk to the BuzUp team in Maputo, Mozambique. Request a demo for your transport operation or ask questions — reply in under 24 hours.",
    },
  },
} satisfies Record<string, PageSeo>;

/* ---------- JSON-LD builders ---------- */

export function organizationLd() {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "BuzUp",
    url: SITE_URL,
    logo: `${SITE_URL}/icons/icon-512.png`,
    description:
      "Plataforma de bilhética cashless e pagamentos sem contacto para o transporte público em Moçambique.",
    parentOrganization: { "@type": "Organization", name: "UpDigital" },
    areaServed: { "@type": "Country", name: "Mozambique" },
    contactPoint: {
      "@type": "ContactPoint",
      contactType: "sales",
      areaServed: "MZ",
      availableLanguage: ["Portuguese", "English"],
    },
  };
}

export function websiteLd() {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "BuzUp",
    url: SITE_URL,
    inLanguage: ["pt-MZ", "en"],
  };
}

export function breadcrumbLd(items: { name: string; path: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((it, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: it.name,
      item: abs(it.path),
    })),
  };
}

export function faqLd(qa: { q: string; a: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: qa.map((it) => ({
      "@type": "Question",
      name: it.q,
      acceptedAnswer: { "@type": "Answer", text: it.a },
    })),
  };
}
