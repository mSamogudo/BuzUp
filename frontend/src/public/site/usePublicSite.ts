/**
 * Leitura do site publicado (`/api/public/...`).
 *
 * O backend já serve com cache de cinco minutos, invalidada na publicação;
 * aqui guarda-se por sessão para a navegação entre páginas não repetir o
 * pedido do menu e dos planos.
 */
import { useEffect, useState } from "react";
import { apiPublic } from "../../lib/api";
import type { PublicBlock, PublicEcoSystem, PublicPlan, PublicPlanFeature } from "./blocks";

export interface SiteMenuItem {
  label: string;
  href: string;
  target: string;
}

export interface SiteData {
  locale: string;
  menus: Record<string, { label: string; items: SiteMenuItem[] }>;
  branding: {
    platform_name?: string;
    company_name?: string;
    company_address?: string;
    company_website?: string;
    support_email?: string;
    support_phone?: string;
    contact_phones?: string[];
  };
  pages: { slug: string; path: string; title: string }[];
}

export interface PageData {
  slug: string;
  path: string;
  template: string;
  title: string;
  locale: string;
  published_at: string | null;
  preview?: boolean;
  seo: {
    title: string;
    description: string;
    slug: string;
    keywords: string;
    og_image: string;
    no_index: boolean;
  } | null;
  blocks: PublicBlock[];
}

const memo = new Map<string, unknown>();

async function cached<T>(key: string, load: () => Promise<T>): Promise<T> {
  if (memo.has(key)) return memo.get(key) as T;
  const value = await load();
  memo.set(key, value);
  return value;
}

/** Depois de publicar, o editor limpa o que estiver guardado nesta sessão. */
export function clearSiteCache() {
  memo.clear();
}

export function useSite(locale: string) {
  const [site, setSite] = useState<SiteData | null>(null);
  useEffect(() => {
    let alive = true;
    cached<SiteData>(`site:${locale}`, () => apiPublic(`/api/public/site/${locale}/`))
      .then((data) => alive && setSite(data))
      .catch(() => alive && setSite(null));
    return () => {
      alive = false;
    };
  }, [locale]);
  return site;
}

export function usePlans(locale: string) {
  const [data, setData] = useState<{ plans: PublicPlan[]; features: PublicPlanFeature[] }>({
    plans: [],
    features: [],
  });
  useEffect(() => {
    let alive = true;
    cached<{ plans: PublicPlan[]; features: PublicPlanFeature[] }>(`plans:${locale}`, () =>
      apiPublic(`/api/public/plans/${locale}/`),
    )
      .then((value) => alive && setData(value))
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [locale]);
  return data;
}

export function useEcoSystems(locale: string) {
  const [systems, setSystems] = useState<PublicEcoSystem[]>([]);
  useEffect(() => {
    let alive = true;
    cached<{ systems: PublicEcoSystem[] }>(`eco:${locale}`, () =>
      apiPublic(`/api/public/eco-systems/?locale=${locale}`),
    )
      .then((value) => alive && setSystems(value.systems || []))
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [locale]);
  return systems;
}

export type PageState =
  | { state: "loading" }
  | { state: "ready"; page: PageData }
  | { state: "missing" }
  | { state: "error"; message: string };

export function usePage(slug: string, locale: string, previewToken?: string | null): PageState {
  const [value, setValue] = useState<PageState>({ state: "loading" });

  useEffect(() => {
    let alive = true;
    setValue({ state: "loading" });

    const path = slug
      ? `/api/public/pages/${slug}/${locale}/`
      : `/api/public/pages/${locale}/`;
    const url = previewToken ? `${path}?preview_token=${encodeURIComponent(previewToken)}` : path;

    // A pré-visualização nunca vem de cache: mostra sempre o rascunho actual.
    const load = previewToken
      ? apiPublic(url)
      : cached<PageData>(`page:${slug}:${locale}`, () => apiPublic(url));

    load
      .then((page: PageData) => alive && setValue({ state: "ready", page }))
      .catch((error: Error) => {
        if (!alive) return;
        const missing = /não encontrada|nao encontrada|not found|404/i.test(error.message);
        setValue(missing ? { state: "missing" } : { state: "error", message: error.message });
      });

    return () => {
      alive = false;
    };
  }, [slug, locale, previewToken]);

  return value;
}
