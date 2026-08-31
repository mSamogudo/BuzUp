/**
 * Cliente do CMS (`/api/cms/...`).
 *
 * Fonte dos endpoints: docs/design-handoff/03-cms-especificacao.md §2.
 */
import { apiDelete, apiFetch, apiPatch, apiPost, apiRequest, apiUpload } from "../../lib/api";

export type Locale = "pt" | "en";
export type I18n<T = string> = Record<Locale, T>;

export type PageStatus = "draft" | "review" | "scheduled" | "published";
export type PageTemplate = "landing" | "pricing" | "contact" | "apps" | "generic";

export interface CmsPage {
  id: number;
  uuid: string;
  slug: string;
  path: string;
  title: I18n;
  status: PageStatus;
  status_label: string;
  template: PageTemplate;
  template_label: string;
  locales: Locale[];
  published_at: string | null;
  scheduled_for: string | null;
  current_version: number | null;
  version_number: number;
  updated_by_name: string;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  blocks?: CmsBlock[];
  seo?: CmsSeo;
}

export interface CmsBlock {
  id?: number;
  uuid?: string;
  type: string;
  position: number;
  enabled: boolean;
  content: Record<string, unknown>;
}

export interface CmsSeo {
  id: number;
  page: number;
  title: I18n;
  description: I18n;
  slug: I18n;
  keywords: I18n;
  og_image: number | null;
  no_index: boolean;
}

export interface CmsMedia {
  id: number;
  uuid: string;
  filename: string;
  url: string;
  mime: string;
  width: number | null;
  height: number | null;
  bytes: number;
  alt: I18n;
  folder: string;
  used_in: { id: number; slug: string; title: I18n }[] | null;
  created_at: string;
  deleted_at: string | null;
}

export interface CmsMenuItem {
  id?: number;
  label: I18n;
  page: number | null;
  href: string;
  resolved_href?: string;
  position: number;
  target: string;
  visible: boolean;
}

export interface CmsMenu {
  id: number;
  key: "header" | "footer_product" | "footer_contact" | "footer_eco";
  label: I18n;
  items: CmsMenuItem[];
}

export interface CmsPlan {
  id: number;
  name: I18n;
  price_label: I18n;
  unit: I18n;
  cta_label: I18n;
  items: I18n<string[]>;
  position: number;
  highlighted: boolean;
  visible: boolean;
  deleted_at: string | null;
}

export interface CmsPlanFeature {
  id?: number;
  label: I18n;
  urban: I18n;
  intercity: I18n;
  institutional: I18n;
  position: number;
}

export interface CmsEcoSystem {
  id: number;
  name: string;
  logo: number | null;
  logo_url: string;
  url: string;
  note: I18n;
  status: "draft" | "published";
  status_label: string;
  position: number;
  deleted_at: string | null;
}

export interface CmsVersion {
  id: number;
  page: number;
  page_slug: string;
  number: number;
  author_name: string;
  note: string;
  restored_from: number | null;
  created_at: string;
  snapshot?: Record<string, unknown>;
}

export interface CmsSchedule {
  id: number;
  target_type: "page" | "plan" | "eco_system";
  target_id: number;
  target_label: string;
  run_at: string;
  status: "scheduled" | "done" | "failed" | "cancelled";
  status_label: string;
  result: string;
  created_at: string;
}

export interface ServiceRequest {
  id: number;
  uuid: string;
  name: string;
  organization: string;
  phone: string;
  email: string;
  interest: string;
  interest_label: string;
  fleet_size: string;
  message: string;
  status: "new" | "contacted" | "qualified" | "closed";
  status_label: string;
  source: string;
  created_at: string;
}

interface Paginated<T> {
  count?: number;
  results?: T[];
}

/** A API pagina umas listas e devolve outras cruas; normaliza-se aqui. */
export function rows<T>(data: Paginated<T> | T[] | null): T[] {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  return data.results || [];
}

export function total<T>(data: Paginated<T> | T[] | null, fallback = 0): number {
  if (!data) return fallback;
  if (Array.isArray(data)) return data.length;
  return data.count ?? (data.results?.length || fallback);
}

function qs(params: Record<string, string | number | undefined | null>) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

/* -------------------------------------------------------------------------- */
/* Páginas                                                                     */
/* -------------------------------------------------------------------------- */

export const cmsPages = {
  list: (token: string, params: Record<string, string | number | undefined> = {}) =>
    apiFetch(`/api/cms/pages/${qs(params)}`, token),
  get: (token: string, id: number) => apiFetch(`/api/cms/pages/${id}/`, token),
  create: (token: string, body: unknown) => apiPost("/api/cms/pages/", token, body),
  update: (token: string, id: number, body: unknown) => apiPatch(`/api/cms/pages/${id}/`, token, body),
  archive: (token: string, id: number) => apiDelete(`/api/cms/pages/${id}/`, token),
  restore: (token: string, id: number) => apiPost(`/api/cms/pages/${id}/restore/`, token, {}),
  blocks: (token: string, id: number) => apiFetch(`/api/cms/pages/${id}/blocks/`, token),
  saveBlocks: (token: string, id: number, blocks: CmsBlock[]) =>
    apiRequest(`/api/cms/pages/${id}/blocks/`, token, { method: "PUT", body: JSON.stringify(blocks) }),
  publish: (token: string, id: number, locales?: Locale[]) =>
    apiPost(`/api/cms/pages/${id}/publish/`, token, locales ? { locales } : {}),
  unpublish: (token: string, id: number) => apiPost(`/api/cms/pages/${id}/unpublish/`, token, {}),
  submitReview: (token: string, id: number) => apiPost(`/api/cms/pages/${id}/submit-review/`, token, {}),
  schedule: (token: string, id: number, runAt: string) =>
    apiPost(`/api/cms/pages/${id}/schedule/`, token, { run_at: runAt }),
  duplicate: (token: string, id: number) => apiPost(`/api/cms/pages/${id}/duplicate/`, token, {}),
  previewToken: (token: string, id: number) => apiFetch(`/api/cms/pages/${id}/preview-token/`, token),
  versions: (token: string, id: number) => apiFetch(`/api/cms/pages/${id}/versions/`, token),
};

/* -------------------------------------------------------------------------- */
/* Versões, media, menus, SEO, planos, ecossistema, agendamentos               */
/* -------------------------------------------------------------------------- */

export const cmsVersions = {
  list: (token: string, pageId?: number) => apiFetch(`/api/cms/versions/${qs({ page: pageId })}`, token),
  get: (token: string, id: number) => apiFetch(`/api/cms/versions/${id}/`, token),
  restore: (token: string, id: number) => apiPost(`/api/cms/versions/${id}/restore/`, token, {}),
  compare: (token: string, a: number, b: number) => apiFetch(`/api/cms/versions/compare/${qs({ a, b })}`, token),
};

export const cmsMedia = {
  list: (token: string, params: Record<string, string | undefined> = {}) =>
    apiFetch(`/api/cms/media/${qs(params)}`, token),
  get: (token: string, id: number) => apiFetch(`/api/cms/media/${id}/`, token),
  upload: (token: string, form: FormData) => apiUpload("/api/cms/media/", token, form),
  replace: (token: string, id: number, form: FormData) => apiUpload(`/api/cms/media/${id}/`, token, form, "PATCH"),
  update: (token: string, id: number, body: unknown) => apiPatch(`/api/cms/media/${id}/`, token, body),
  remove: (token: string, id: number) => apiDelete(`/api/cms/media/${id}/`, token),
};

export const cmsMenus = {
  list: (token: string) => apiFetch("/api/cms/menus/", token),
  saveItems: (token: string, key: string, items: CmsMenuItem[]) =>
    apiRequest(`/api/cms/menus/${key}/items/`, token, { method: "PUT", body: JSON.stringify(items) }),
};

export const cmsSeo = {
  get: (token: string, pageId: number) => apiFetch(`/api/cms/seo/${pageId}/`, token),
  save: (token: string, pageId: number, body: unknown) =>
    apiRequest(`/api/cms/seo/${pageId}/`, token, { method: "PUT", body: JSON.stringify(body) }),
};

export const cmsPlans = {
  list: (token: string) => apiFetch("/api/cms/plans/", token),
  create: (token: string, body: unknown) => apiPost("/api/cms/plans/", token, body),
  update: (token: string, id: number, body: unknown) => apiPatch(`/api/cms/plans/${id}/`, token, body),
  archive: (token: string, id: number) => apiDelete(`/api/cms/plans/${id}/`, token),
  order: (token: string, ids: number[]) =>
    apiRequest("/api/cms/plans/order/", token, { method: "PUT", body: JSON.stringify({ ids }) }),
  features: (token: string) => apiFetch("/api/cms/plan-features/", token),
  saveFeatures: (token: string, features: CmsPlanFeature[]) =>
    apiRequest("/api/cms/plan-features/", token, { method: "PUT", body: JSON.stringify(features) }),
};

export const cmsEco = {
  list: (token: string) => apiFetch("/api/cms/eco-systems/", token),
  create: (token: string, body: unknown) => apiPost("/api/cms/eco-systems/", token, body),
  update: (token: string, id: number, body: unknown) => apiPatch(`/api/cms/eco-systems/${id}/`, token, body),
  archive: (token: string, id: number) => apiDelete(`/api/cms/eco-systems/${id}/`, token),
  order: (token: string, ids: number[]) =>
    apiRequest("/api/cms/eco-systems/order/", token, { method: "PUT", body: JSON.stringify({ ids }) }),
};

export const cmsSchedules = {
  list: (token: string, params: Record<string, string | undefined> = {}) =>
    apiFetch(`/api/cms/schedules/${qs(params)}`, token),
  create: (token: string, body: unknown) => apiPost("/api/cms/schedules/", token, body),
  cancel: (token: string, id: number) => apiDelete(`/api/cms/schedules/${id}/`, token),
};

export const cmsRequests = {
  list: (token: string, params: Record<string, string | undefined> = {}) =>
    apiFetch(`/api/admin/service-requests/${qs(params)}`, token),
  update: (token: string, id: number, body: unknown) => apiPatch(`/api/admin/service-requests/${id}/`, token, body),
  exportUrl: "/api/admin/service-requests/export.csv",
};

/* -------------------------------------------------------------------------- */
/* Utilitários i18n                                                            */
/* -------------------------------------------------------------------------- */

export const EMPTY_I18N: I18n = { pt: "", en: "" };

export function i18nGet(value: unknown, locale: Locale): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "object") {
    const record = value as Partial<I18n>;
    return record[locale] || record.pt || "";
  }
  return String(value);
}

export function i18nList(value: unknown, locale: Locale): string[] {
  if (Array.isArray(value)) return value as string[];
  if (value && typeof value === "object") {
    const record = value as Partial<I18n<string[]>>;
    return record[locale] || record.pt || [];
  }
  return [];
}

export function i18nSet<T>(value: unknown, locale: Locale, next: T): I18n<T> {
  const base = (value && typeof value === "object" && !Array.isArray(value) ? value : {}) as Partial<I18n<T>>;
  return { pt: base.pt as T, en: base.en as T, [locale]: next } as I18n<T>;
}
