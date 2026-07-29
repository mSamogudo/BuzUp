import { useEffect } from "react";

const TITLE = "BusUp · Bilhética digital para transporte de passageiros";
const DESCRIPTION =
  "Venda e valide bilhetes de autocarro em Moçambique: compra online com lugar marcado, carteira digital, " +
  "QR e cartão NFC, recargas M-Pesa e e-Mola, terminal POS para agentes e motoristas, e portal de gestão " +
  "com receita, frota e relatórios em tempo real.";

/**
 * Injeta title/description/OG/Twitter/JSON-LD enquanto a landing está montada
 * e REPÕE tudo no unmount — a SPA partilha o index.html com o portal de
 * gestão, e o título de marketing não deve ficar preso na tab do admin.
 */
export function useLandingMeta(_lang?: string) {
  useEffect(() => {
    const prevTitle = document.title;
    document.title = TITLE;

    const added: Element[] = [];
    const replaced: { el: HTMLMetaElement; prev: string }[] = [];

    const setMeta = (attr: "name" | "property", key: string, content: string) => {
      let el = document.head.querySelector<HTMLMetaElement>(`meta[${attr}="${key}"]`);
      if (el) {
        replaced.push({ el, prev: el.content });
        el.content = content;
      } else {
        el = document.createElement("meta");
        el.setAttribute(attr, key);
        el.content = content;
        document.head.appendChild(el);
        added.push(el);
      }
    };

    const abs = (path: string) => new URL(path, window.location.origin).toString();

    setMeta("name", "description", DESCRIPTION);
    setMeta("property", "og:title", TITLE);
    setMeta("property", "og:description", DESCRIPTION);
    setMeta("property", "og:type", "website");
    setMeta("property", "og:url", abs("/"));
    setMeta("property", "og:image", abs("/landing/og.jpg"));
    setMeta("property", "og:image:width", "1200");
    setMeta("property", "og:image:height", "630");
    setMeta("name", "twitter:card", "summary_large_image");

    const ld = document.createElement("script");
    ld.type = "application/ld+json";
    ld.text = JSON.stringify({
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      name: "BusUp",
      applicationCategory: "BusinessApplication",
      operatingSystem: "Android, Web",
      description: DESCRIPTION,
      offers: { "@type": "Offer", price: "0", priceCurrency: "MZN" },
      publisher: { "@type": "Organization", name: "UpDigital", url: "https://updigital.co.mz" },
    });
    document.head.appendChild(ld);
    added.push(ld);

    return () => {
      document.title = prevTitle;
      for (const el of added) el.remove();
      for (const { el, prev } of replaced) el.content = prev;
    };
  }, []);
}
