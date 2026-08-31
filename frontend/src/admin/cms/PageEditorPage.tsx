/**
 * CMS 3.2 — Editor de página.
 *
 * Três colunas: blocos à esquerda (arrastar para reordenar, ligar/desligar,
 * acrescentar por tipo), formulário do bloco ao centro e pré-visualização ao
 * vivo à direita, com PT/EN e desktop/mobile.
 *
 * A pré-visualização usa os mesmos componentes do site público — o que se vê
 * aqui é literalmente o que vai para o ar.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Eye, GripVertical, Plus, Save, Send, Trash2, Upload } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { showToast } from "../../lib/toast";
import { usePortal } from "../../design/portal/PortalShell";
import {
  Button,
  ConfirmDestructive,
  EnumPill,
  IconButton,
  InlineError,
  Modal,
  PageHeader,
  Segmented,
  Skeleton,
  Switch,
} from "../../design/ui";
import { BlockRenderer, SiteDataProvider } from "../../public/site/blocks";
import "../../public/site/site.css";
import { BLOCK_DEFS, blockDef, emptyContent, sanitizeRichText } from "./blocks";
import { BlockForm } from "./BlockForm";
import {
  cmsEco,
  cmsPages,
  cmsPlans,
  i18nGet,
  rows,
  type CmsBlock,
  type CmsEcoSystem,
  type CmsMedia,
  type CmsPage,
  type CmsPlan,
  type CmsPlanFeature,
  type Locale,
} from "./api";
import { cmsMedia } from "./api";
import "./cms.css";

const LOCALES: [Locale, string][] = [
  ["pt", "PT"],
  ["en", "EN"],
];

/** Reduz a árvore i18n ao idioma pedido — o mesmo que o backend faz ao servir. */
function localize(node: unknown, locale: Locale): unknown {
  if (Array.isArray(node)) return node.map((item) => localize(item, locale));
  if (node && typeof node === "object") {
    const keys = Object.keys(node as Record<string, unknown>);
    const isI18n = keys.length > 0 && keys.every((k) => k === "pt" || k === "en");
    if (isI18n) {
      const record = node as Record<string, unknown>;
      const value = record[locale];
      if (value !== undefined && value !== null && value !== "") return value;
      const fallback = record.pt;
      return fallback === undefined || fallback === null ? "" : fallback;
    }
    return Object.fromEntries(
      Object.entries(node as Record<string, unknown>).map(([k, v]) => [k, localize(v, locale)]),
    );
  }
  return node;
}

/** Troca `media_id` pelo endereço do ficheiro, como o endpoint público faz. */
function resolveMedia(node: unknown, urls: Map<number, string>): unknown {
  if (Array.isArray(node)) return node.map((item) => resolveMedia(item, urls));
  if (node && typeof node === "object") {
    const record = node as Record<string, unknown>;
    const out: Record<string, unknown> = Object.fromEntries(
      Object.entries(record).map(([k, v]) => [k, resolveMedia(v, urls)]),
    );
    if (typeof record.media_id === "number") out.url = urls.get(record.media_id) || "";
    return out;
  }
  return node;
}

export default function PageEditorPage() {
  const { pageId } = useParams();
  const id = Number(pageId);
  const { token } = useAuth();
  const { can } = usePortal();
  const navigate = useNavigate();

  const [page, setPage] = useState<CmsPage | null>(null);
  const [blocks, setBlocks] = useState<CmsBlock[]>([]);
  const [selected, setSelected] = useState(0);
  const [locale, setLocale] = useState<Locale>("pt");
  const [device, setDevice] = useState<"desktop" | "mobile">("desktop");
  const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [publishErrors, setPublishErrors] = useState<string[]>([]);
  const [adding, setAdding] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState<number | null>(null);

  const [plans, setPlans] = useState<CmsPlan[]>([]);
  const [features, setFeatures] = useState<CmsPlanFeature[]>([]);
  const [systems, setSystems] = useState<CmsEcoSystem[]>([]);
  const [mediaUrls, setMediaUrls] = useState<Map<number, string>>(new Map());
  const dragFrom = useRef<number | null>(null);
  const [dragOver, setDragOver] = useState<number | null>(null);

  const load = useCallback(() => {
    if (!token || !Number.isFinite(id)) return;
    setLoading(true);
    setError(null);
    Promise.all([cmsPages.get(token, id), cmsPages.blocks(token, id)])
      .then(([pageData, blockData]: [CmsPage, CmsBlock[]]) => {
        setPage(pageData);
        setBlocks(blockData);
        setDirty(false);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, id]);

  useEffect(load, [load]);

  useEffect(() => {
    if (!token) return;
    cmsPlans.list(token).then((d) => setPlans(rows<CmsPlan>(d))).catch(() => undefined);
    // A tabela comparativa também entra na pré-visualização do bloco de preços.
    cmsPlans.features(token).then((d) => setFeatures(rows<CmsPlanFeature>(d))).catch(() => undefined);
    cmsEco.list(token).then((d) => setSystems(rows<CmsEcoSystem>(d))).catch(() => undefined);
    cmsMedia
      .list(token)
      .then((d) => setMediaUrls(new Map(rows<CmsMedia>(d).map((m) => [m.id, m.url]))))
      .catch(() => undefined);
  }, [token]);

  // Avisar antes de sair com alterações por gravar.
  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  const current = blocks[selected];

  const previewBlocks = useMemo(
    () =>
      blocks
        .filter((b) => b.enabled)
        .map((b, i) => ({
          type: b.type,
          position: i,
          content: resolveMedia(localize(b.content, locale), mediaUrls) as Record<string, unknown>,
        })),
    [blocks, locale, mediaUrls],
  );

  const previewPlans = useMemo(
    () =>
      plans
        .filter((p) => p.visible)
        .map((p) => ({
          id: p.id,
          name: i18nGet(p.name, locale),
          price_label: i18nGet(p.price_label, locale),
          unit: i18nGet(p.unit, locale),
          cta_label: i18nGet(p.cta_label, locale),
          items: (p.items?.[locale] || p.items?.pt || []) as string[],
          highlighted: p.highlighted,
          position: p.position,
        })),
    [plans, locale],
  );

  const previewFeatures = useMemo(
    () =>
      features.map((feature) => ({
        label: i18nGet(feature.label, locale),
        urban: i18nGet(feature.urban, locale),
        intercity: i18nGet(feature.intercity, locale),
        institutional: i18nGet(feature.institutional, locale),
        position: feature.position,
      })),
    [features, locale],
  );

  const previewSystems = useMemo(
    () =>
      systems
        .filter((s) => s.status === "published")
        .map((s) => ({
          id: s.id,
          name: s.name,
          logo: s.logo_url,
          url: s.url,
          note: i18nGet(s.note, locale),
          position: s.position,
        })),
    [systems, locale],
  );

  const updateBlock = (index: number, patch: Partial<CmsBlock>) => {
    setBlocks((list) => list.map((b, i) => (i === index ? { ...b, ...patch } : b)));
    setDirty(true);
  };

  const move = (from: number, to: number) => {
    if (to < 0 || to >= blocks.length || from === to) return;
    setBlocks((list) => {
      const next = [...list];
      const [item] = next.splice(from, 1);
      next.splice(to, 0, item);
      return next;
    });
    setSelected(to);
    setDirty(true);
  };

  const addBlock = (type: string) => {
    setBlocks((list) => [...list, { type, position: list.length, enabled: true, content: emptyContent(type) }]);
    setSelected(blocks.length);
    setAdding(false);
    setDirty(true);
  };

  const removeBlock = (index: number) => {
    setBlocks((list) => list.filter((_, i) => i !== index));
    setSelected((s) => Math.max(0, Math.min(s, blocks.length - 2)));
    setConfirmRemove(null);
    setDirty(true);
  };

  /** Gravar limpa o HTML dos blocos de texto antes de o mandar para o servidor. */
  const cleaned = () =>
    blocks.map((block, index) => {
      if (block.type !== "richtext") return { ...block, position: index };
      const content = { ...(block.content || {}) } as Record<string, any>;
      const html = content.html;
      if (html && typeof html === "object") {
        content.html = {
          pt: sanitizeRichText(String(html.pt || "")),
          en: sanitizeRichText(String(html.en || "")),
        };
      }
      return { ...block, position: index, content };
    });

  const save = async () => {
    if (!token) return;
    setSaving(true);
    setPublishErrors([]);
    try {
      const saved: CmsBlock[] = await cmsPages.saveBlocks(token, id, cleaned());
      setBlocks(saved);
      setDirty(false);
      showToast("success", "Rascunho gravado. Ficou uma versão nova no histórico.");
      load();
    } catch (e) {
      showToast("danger", (e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const publish = async () => {
    if (!token) return;
    setSaving(true);
    setPublishErrors([]);
    try {
      if (dirty) await cmsPages.saveBlocks(token, id, cleaned());
      const updated: CmsPage = await cmsPages.publish(token, id);
      setPage(updated);
      setDirty(false);
      showToast("success", "Página publicada.");
      load();
    } catch (e) {
      const message = (e as Error).message;
      // O backend devolve a lista de razões; mostrá-las é o que evita o
      // "não publica e não diz porquê".
      setPublishErrors([message]);
      showToast("danger", message);
    } finally {
      setSaving(false);
    }
  };

  const submitReview = async () => {
    if (!token) return;
    setSaving(true);
    try {
      if (dirty) await cmsPages.saveBlocks(token, id, cleaned());
      const updated: CmsPage = await cmsPages.submitReview(token, id);
      setPage(updated);
      setDirty(false);
      showToast("success", "Enviado para revisão.");
    } catch (e) {
      showToast("danger", (e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const preview = async () => {
    if (!token || !page) return;
    try {
      const { token: previewToken } = await cmsPages.previewToken(token, id);
      const path = page.slug ? `/${page.slug}` : "/";
      window.open(`${path}?preview_token=${encodeURIComponent(previewToken)}`, "_blank", "noopener");
    } catch (e) {
      showToast("danger", (e as Error).message);
    }
  };

  if (loading) {
    return (
      <div className="bz-page">
        <Skeleton height={28} width={280} />
        <Skeleton height={420} />
      </div>
    );
  }

  if (error || !page) {
    return (
      <div className="bz-page">
        <InlineError>{error || "Página não encontrada."}</InlineError>
        <div>
          <Button icon={<ArrowLeft size={16} />} onClick={() => navigate("/app/cms/pages")} variant="ghost">
            Voltar às páginas
          </Button>
        </div>
      </div>
    );
  }

  const canPublish = can("content.publish");

  return (
    <div className="bz-page">
      <PageHeader
        actions={
          <>
            <Button icon={<Eye size={16} />} onClick={preview} variant="ghost">
              Pré-visualizar
            </Button>
            <Button icon={<Save size={16} />} loading={saving} onClick={save} variant="ghost">
              Guardar rascunho
            </Button>
            {canPublish ? (
              <Button icon={<Upload size={16} />} loading={saving} onClick={publish}>
                Publicar
              </Button>
            ) : (
              <Button icon={<Send size={16} />} loading={saving} onClick={submitReview}>
                Enviar para revisão
              </Button>
            )}
          </>
        }
        crumbs={["Conteúdo", { label: "Páginas do site", to: "/app/cms/pages" }, page.slug ? `/${page.slug}` : "/"]}
        description={`${page.template_label} · ${page.locales.map((l) => l.toUpperCase()).join(" e ")}`}
        title={i18nGet(page.title, "pt") || "(sem nome)"}
      />

      <div className="bzc-actionbar">
        <EnumPill group="cms" value={page.status} />
        <span className="bz-field-hint">
          versão {page.version_number} · {page.published_at ? "publicada" : "por publicar"}
        </span>
        {dirty ? (
          <span className="bzc-dirty">
            <i aria-hidden="true" />
            Alterações por gravar
          </span>
        ) : null}
        <span className="bz-toolbar-spacer" />
        <Segmented ariaLabel="Idioma" onChange={setLocale} options={LOCALES} value={locale} />
        <Segmented
          ariaLabel="Dispositivo"
          onChange={setDevice}
          options={[
            ["desktop", "Desktop"],
            ["mobile", "Mobile"],
          ]}
          value={device}
        />
      </div>

      {publishErrors.length ? <InlineError>{publishErrors.join(" ")}</InlineError> : null}

      <div className="bzc-editor">
        {/* Blocos */}
        <section className="bzc-col">
          <header className="bzc-colhead">
            Blocos
            <IconButton bare icon={<Plus size={16} />} label="Acrescentar bloco" onClick={() => setAdding(true)} />
          </header>
          <div className="bzc-blocks">
            {blocks.map((block, index) => (
              <div
                className={[
                  "bzc-block",
                  index === selected ? "bzc-block-active" : "",
                  block.enabled ? "" : "bzc-block-off",
                  dragOver === index ? "bzc-block-over" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                draggable
                key={`${block.type}-${index}`}
                onClick={() => setSelected(index)}
                onDragEnd={() => {
                  dragFrom.current = null;
                  setDragOver(null);
                }}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(index);
                }}
                onDragStart={() => {
                  dragFrom.current = index;
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  if (dragFrom.current !== null) move(dragFrom.current, index);
                  dragFrom.current = null;
                  setDragOver(null);
                }}
              >
                <GripVertical className="bzc-block-drag" size={15} />
                <span className="bzc-block-name">{blockDef(block.type).label}</span>
                <span className="bzc-block-type">{String(index + 1).padStart(2, "0")}</span>
              </div>
            ))}
            {blocks.length === 0 ? <span className="bz-field-hint">Sem blocos. Acrescente o primeiro.</span> : null}
          </div>
        </section>

        {/* Formulário do bloco */}
        <section className="bzc-col">
          <header className="bzc-colhead">
            {current ? blockDef(current.type).label : "Bloco"}
            {current ? (
              <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <Switch
                  ariaLabel="Bloco activo"
                  checked={current.enabled}
                  onChange={(v) => updateBlock(selected, { enabled: v })}
                />
                <IconButton
                  bare
                  icon={<Trash2 size={15} />}
                  label="Remover bloco"
                  onClick={() => setConfirmRemove(selected)}
                  tone="danger"
                />
              </span>
            ) : null}
          </header>
          <div className="bzc-colbody bzc-colbody-scroll">
            {current ? (
              <BlockForm
                block={current}
                locale={locale}
                onChange={(content) => updateBlock(selected, { content })}
                plans={plans}
                systems={systems}
              />
            ) : (
              <span className="bz-field-hint">Escolha um bloco à esquerda.</span>
            )}
          </div>
        </section>

        {/* Pré-visualização ao vivo */}
        <aside className="bzc-preview">
          <header className="bzc-preview-head">
            <span className="bz-label">Pré-visualização</span>
            <span className="bz-field-hint">{device === "desktop" ? "1280 px" : "390 px"}</span>
          </header>
          <div className="bzc-preview-stage">
            <SiteDataProvider
              value={{ locale, plans: previewPlans, features: previewFeatures, systems: previewSystems, inert: true }}
            >
              {device === "desktop" ? (
                <div
                  className="bzc-preview-scale bzs"
                  style={{ width: 1280, transform: "scale(0.36)", height: "auto" }}
                >
                  <BlockRenderer blocks={previewBlocks as never} />
                </div>
              ) : (
                <div className="bzc-preview-phone bzs">
                  <BlockRenderer blocks={previewBlocks as never} />
                </div>
              )}
            </SiteDataProvider>
          </div>
        </aside>
      </div>

      <Modal onClose={() => setAdding(false)} open={adding} size="sm" title="Acrescentar bloco">
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {BLOCK_DEFS.map((def) => (
            <button className="bzp-popover-item" key={def.type} onClick={() => addBlock(def.type)} type="button">
              <strong>{def.label}</strong>
              <small>{def.hint}</small>
            </button>
          ))}
        </div>
      </Modal>

      <ConfirmDestructive
        confirmLabel="Remover"
        message="O bloco sai da página. A alteração só fica definitiva quando gravar."
        onCancel={() => setConfirmRemove(null)}
        onConfirm={() => confirmRemove !== null && removeBlock(confirmRemove)}
        open={confirmRemove !== null}
        title="Remover bloco"
      />
    </div>
  );
}
