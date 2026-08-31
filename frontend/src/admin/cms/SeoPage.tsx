/**
 * CMS 3.5 — SEO e partilha.
 *
 * Formulário por página e idioma, com contadores e limites (60/160/40/90),
 * pré-visualização do resultado de pesquisa e do cartão social.
 */
import { useCallback, useEffect, useState } from "react";
import { Save } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { showToast } from "../../lib/toast";
import {
  Button,
  Card,
  Field,
  InlineError,
  Input,
  PageHeader,
  Segmented,
  Select,
  Switch,
  TableSkeleton,
  Textarea,
} from "../../design/ui";
import { MediaPicker } from "./MediaPicker";
import { cmsPages, cmsSeo, i18nGet, i18nSet, rows, type CmsPage, type CmsSeo, type Locale } from "./api";
import "./cms.css";

const LIMITS = { title: 60, description: 160, slug: 40, keywords: 90 };
const SITE_HOST = "busup.updigital.co.mz";

export default function CmsSeoPage() {
  const { token } = useAuth();
  const [pages, setPages] = useState<CmsPage[]>([]);
  const [pageId, setPageId] = useState<number | null>(null);
  const [seo, setSeo] = useState<CmsSeo | null>(null);
  const [ogUrl, setOgUrl] = useState("");
  const [locale, setLocale] = useState<Locale>("pt");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [picking, setPicking] = useState(false);

  useEffect(() => {
    if (!token) return;
    cmsPages
      .list(token)
      .then((data) => {
        const list = rows<CmsPage>(data);
        setPages(list);
        setPageId((current) => current ?? list[0]?.id ?? null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  const loadSeo = useCallback(() => {
    if (!token || !pageId) return;
    cmsSeo
      .get(token, pageId)
      .then(setSeo)
      .catch((e: Error) => setError(e.message));
  }, [token, pageId]);

  useEffect(loadSeo, [loadSeo]);

  const save = async () => {
    if (!token || !pageId || !seo) return;
    setSaving(true);
    setError(null);
    try {
      const saved = await cmsSeo.save(token, pageId, {
        title: seo.title,
        description: seo.description,
        slug: seo.slug,
        keywords: seo.keywords,
        og_image: seo.og_image,
        no_index: seo.no_index,
      });
      setSeo(saved);
      showToast("success", "SEO gravado.");
    } catch (e) {
      setError((e as Error).message);
      showToast("danger", (e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const page = pages.find((p) => p.id === pageId);
  const value = (key: keyof typeof LIMITS) => i18nGet(seo?.[key], locale);
  const set = (key: keyof typeof LIMITS, next: string) =>
    setSeo((current) => (current ? { ...current, [key]: i18nSet(current[key], locale, next) } : current));

  if (loading) {
    return (
      <div className="bz-page">
        <PageHeader crumbs={["Conteúdo", "SEO e partilha"]} title="SEO e partilha" />
        <TableSkeleton cols={2} rows={5} />
      </div>
    );
  }

  return (
    <div className="bz-page">
      <PageHeader
        actions={
          <>
            <Segmented
              ariaLabel="Idioma"
              onChange={setLocale}
              options={[
                ["pt", "PT"],
                ["en", "EN"],
              ]}
              value={locale}
            />
            <Button icon={<Save size={16} />} loading={saving} onClick={save}>
              Guardar alterações
            </Button>
          </>
        }
        crumbs={["Conteúdo", "SEO e partilha"]}
        description="O que aparece no Google e nas partilhas. Os limites são os que os motores mostram sem cortar."
        title="SEO e partilha"
      />

      {error ? <InlineError>{error}</InlineError> : null}

      <div className="bz-toolbar">
        <Select
          aria-label="Página"
          onChange={(e) => setPageId(Number(e.target.value))}
          style={{ maxWidth: 380 }}
          value={String(pageId ?? "")}
        >
          {pages.map((item) => (
            <option key={item.id} value={item.id}>
              {item.slug ? `/${item.slug}` : "/"} — {i18nGet(item.title, "pt")}
            </option>
          ))}
        </Select>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(320px, 420px)", gap: 16, alignItems: "start" }}>
        <Card large>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Field count={[value("title").length, LIMITS.title]} label={`Título · ${locale.toUpperCase()}`} required>
              <Input
                invalid={value("title").length > LIMITS.title}
                onChange={(e) => set("title", e.target.value)}
                value={value("title")}
              />
            </Field>
            <Field
              count={[value("description").length, LIMITS.description]}
              label={`Descrição · ${locale.toUpperCase()}`}
              required
            >
              <Textarea
                invalid={value("description").length > LIMITS.description}
                onChange={(e) => set("description", e.target.value)}
                value={value("description")}
              />
            </Field>
            <div className="bz-formgrid">
              <Field count={[value("slug").length, LIMITS.slug]} label={`Slug · ${locale.toUpperCase()}`}>
                <Input mono onChange={(e) => set("slug", e.target.value)} value={value("slug")} />
              </Field>
              <Field count={[value("keywords").length, LIMITS.keywords]} label={`Palavras-chave · ${locale.toUpperCase()}`}>
                <Input onChange={(e) => set("keywords", e.target.value)} value={value("keywords")} />
              </Field>
            </div>
            <div className="bz-formgrid">
              <Field label="Imagem de partilha">
                <Button onClick={() => setPicking(true)} size="sm" variant="ghost">
                  {seo?.og_image ? `Ficheiro #${seo.og_image}` : "Escolher imagem"}
                </Button>
              </Field>
              <Field hint="Uma página com esta opção não entra nos motores de busca." label="Não indexar">
                <Switch
                  checked={Boolean(seo?.no_index)}
                  label={seo?.no_index ? "Fora dos motores" : "Indexada"}
                  onChange={(v) => setSeo((current) => (current ? { ...current, no_index: v } : current))}
                />
              </Field>
            </div>
          </div>
        </Card>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <span className="bz-label">Resultado de pesquisa</span>
            <div className="bzc-serp" style={{ marginTop: 8 }}>
              <span className="bzc-serp-url">
                {SITE_HOST}
                {page?.slug ? ` › ${value("slug") || page.slug}` : ""}
              </span>
              <span className="bzc-serp-title">{value("title") || "Título por preencher"}</span>
              <span className="bzc-serp-desc">{value("description") || "Descrição por preencher."}</span>
            </div>
          </div>

          <div>
            <span className="bz-label">Cartão social</span>
            <div className="bzc-ogcard" style={{ marginTop: 8 }}>
              <div className="bzc-ogcard-img">
                {ogUrl ? <img alt="" src={ogUrl} /> : <span className="bz-label">Sem imagem</span>}
              </div>
              <div className="bzc-ogcard-body">
                <span className="bz-label">{SITE_HOST}</span>
                <strong style={{ font: "700 15px/1.35 var(--font-ui)" }}>{value("title") || "—"}</strong>
                <span style={{ font: "400 13px/1.5 var(--font-ui)", color: "var(--muted)" }}>
                  {value("description") || "—"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <MediaPicker
        onClose={() => setPicking(false)}
        onPick={(asset) => {
          setSeo((current) => (current ? { ...current, og_image: asset.id } : current));
          setOgUrl(asset.url);
          setPicking(false);
        }}
        open={picking}
      />
    </div>
  );
}
