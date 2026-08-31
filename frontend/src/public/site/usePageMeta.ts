/**
 * Meta da página vindo do CMS (SEO e partilha, 3.5).
 *
 * A SPA partilha o `index.html` com o portal, por isso tudo o que se injecta
 * aqui é reposto quando a página sai — o título de marketing não pode ficar
 * preso na tab de quem foi para o portal de gestão.
 */
import { useEffect } from "react";

export interface PageMeta {
  title: string;
  description: string;
  keywords?: string;
  image?: string;
  noIndex?: boolean;
  path: string;
  locale: string;
}

export function usePageMeta(meta: PageMeta | null) {
  useEffect(() => {
    if (!meta) return;

    const previousTitle = document.title;
    document.title = meta.title || previousTitle;

    const added: Element[] = [];
    const replaced: { el: HTMLMetaElement; prev: string }[] = [];

    const setMeta = (attr: "name" | "property", key: string, content: string) => {
      if (!content) return;
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

    setMeta("name", "description", meta.description);
    if (meta.keywords) setMeta("name", "keywords", meta.keywords);
    if (meta.noIndex) setMeta("name", "robots", "noindex, nofollow");
    setMeta("property", "og:title", meta.title);
    setMeta("property", "og:description", meta.description);
    setMeta("property", "og:type", "website");
    setMeta("property", "og:locale", meta.locale === "en" ? "en" : "pt_PT");
    setMeta("property", "og:url", abs(meta.path));
    if (meta.image) setMeta("property", "og:image", abs(meta.image));
    setMeta("name", "twitter:card", "summary_large_image");

    let canonical = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
    let canonicalAdded = false;
    const previousHref = canonical?.href;
    if (!canonical) {
      canonical = document.createElement("link");
      canonical.rel = "canonical";
      document.head.appendChild(canonical);
      canonicalAdded = true;
    }
    canonical.href = abs(meta.path);

    return () => {
      document.title = previousTitle;
      for (const el of added) el.remove();
      for (const { el, prev } of replaced) el.content = prev;
      if (canonicalAdded) canonical?.remove();
      else if (canonical && previousHref) canonical.href = previousHref;
    };
  }, [meta]);
}
