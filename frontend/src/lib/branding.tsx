import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { apiPublic } from "./api";

// Espelha os slots do backend (apps/branding). Cada um e uma URL absoluta ou "".
export interface Branding {
  platform_name: string;
  primary_logo_url: string;
  sidebar_logo_url: string;
  sidebar_mark_url: string;
  auth_logo_url: string;
  pos_logo_url: string;
  mobile_logo_url: string;
  report_logo_url: string;
  powered_by_logo_url: string;
  favicon_url: string;

  // Identificação e contactos do operador. O rodapé da compra, o bilhete e as
  // apps mostram-nos: quem compra tem de saber a quem está a comprar, e a quem
  // telefonar quando algo corre mal na estrada.
  company_name: string;
  company_address: string;
  company_website: string;
  contact_phones: string[];
  support_phone: string;
  support_email: string;
  emergency_phone: string;

  // Termos e Condições, publicados pelo operador.
  terms_sections: { title: string; items: string[] }[];
  terms_intro: string;
  terms_closing: string;
  terms_sections_en: { title: string; items: string[] }[];
  terms_intro_en: string;
  terms_closing_en: string;
  terms_version: string;
  terms_updated_at: string | null;
}

const EMPTY: Branding = {
  platform_name: "BusUp",
  primary_logo_url: "", sidebar_logo_url: "", sidebar_mark_url: "",
  auth_logo_url: "", pos_logo_url: "", mobile_logo_url: "",
  report_logo_url: "", powered_by_logo_url: "", favicon_url: "",
  company_name: "", company_address: "", company_website: "",
  contact_phones: [], support_phone: "", support_email: "", emergency_phone: "",
  terms_sections: [], terms_intro: "", terms_closing: "",
  terms_sections_en: [], terms_intro_en: "", terms_closing_en: "",
  terms_version: "", terms_updated_at: null,
};

interface BrandingState {
  branding: Branding;
  reload: () => void;
}

const BrandingContext = createContext<BrandingState>({ branding: EMPTY, reload: () => {} });

export function BrandingProvider({ children }: { children: ReactNode }) {
  const [branding, setBranding] = useState<Branding>(EMPTY);

  const reload = () => {
    apiPublic("/api/branding/")
      .then((d) => setBranding({ ...EMPTY, ...(d || {}) }))
      .catch(() => {/* mantém os estaticos por defeito */});
  };

  useEffect(() => { reload(); }, []);

  // Favicon dinamico quando definido.
  useEffect(() => {
    if (!branding.favicon_url) return;
    let link = document.querySelector<HTMLLinkElement>("link[rel~='icon']");
    if (!link) { link = document.createElement("link"); link.rel = "icon"; document.head.appendChild(link); }
    link.href = branding.favicon_url;
  }, [branding.favicon_url]);

  return (
    <BrandingContext.Provider value={{ branding, reload }}>
      {children}
    </BrandingContext.Provider>
  );
}

export function useBranding() {
  return useContext(BrandingContext);
}

/** Primeira URL nao-vazia (slots remotos), senao o fallback estatico. */
export function pickLogo(...candidates: (string | undefined)[]): string {
  for (const c of candidates) {
    if (c) return c;
  }
  return "";
}
