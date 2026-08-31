/**
 * Uma página do site público, desenhada a partir do CMS.
 *
 * `/`, `/precos`, `/contactos` e `/apps` são todas esta página: o que muda são
 * os blocos que o CMS devolve. É a ligação pedida pela especificação §5 — o
 * site deixa de ter conteúdo no código.
 */
import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useUi } from "../../ui/UiPreferences";
import ErrorScreen from "../errors/ErrorScreen";
import { BlockRenderer, SiteDataProvider } from "./blocks";
import { SiteFooter, SiteHeader } from "./SiteChrome";
import { useEcoSystems, usePage, usePlans, useSite } from "./usePublicSite";
import { usePageMeta } from "./usePageMeta";
import "./site.css";

function SiteSkeleton() {
  return (
    <div className="bzs-hero" style={{ paddingTop: 80, paddingBottom: 80 }}>
      <span className="bz-skel" style={{ width: 220, height: 38, borderRadius: 999 }} />
      <span className="bz-skel" style={{ width: "min(680px, 90%)", height: 58, borderRadius: 14 }} />
      <span className="bz-skel" style={{ width: "min(560px, 85%)", height: 58, borderRadius: 14 }} />
      <span className="bz-skel" style={{ width: "min(520px, 80%)", height: 20, borderRadius: 8 }} />
      <span className="bz-skel" style={{ width: 320, height: 52, borderRadius: 999 }} />
    </div>
  );
}

export default function SitePage({ slug = "" }: { slug?: string }) {
  const { locale } = useUi();
  const lang = locale === "en" ? "en" : "pt";
  const [params] = useSearchParams();
  const previewToken = params.get("preview_token");

  const site = useSite(lang);
  const { plans, features } = usePlans(lang);
  const systems = useEcoSystems(lang);
  const result = usePage(slug, lang, previewToken);

  const page = result.state === "ready" ? result.page : null;
  const meta = useMemo(
    () =>
      page
        ? {
            title: page.seo?.title || page.title,
            description: page.seo?.description || "",
            keywords: page.seo?.keywords,
            image: page.seo?.og_image,
            noIndex: page.seo?.no_index,
            path: page.path,
            locale: lang,
          }
        : null,
    [page, lang],
  );
  usePageMeta(meta);

  // O primeiro bloco entra no gradiente quando e o heroi; os outros nao.
  const blocks = page?.blocks || [];
  const top = blocks.length && blocks[0].type === "heroi" ? blocks.slice(0, 1) : [];
  const rest = top.length ? blocks.slice(1) : blocks;

  if (result.state === "missing") return <ErrorScreen code="404" />;
  if (result.state === "error") {
    return <ErrorScreen code="500" reference={`ref. 500 · ${result.message}`} />;
  }

  return (
    <SiteDataProvider value={{ locale: lang, plans, features, systems }}>
      <div className="bzs">
        {page?.preview ? (
          <div
            style={{
              position: "sticky",
              top: 0,
              zIndex: 50,
              background: "var(--tone-warn-bg)",
              color: "var(--tone-warn-fg)",
              font: "700 12.5px/1 var(--font-ui)",
              padding: "10px 16px",
              textAlign: "center",
            }}
          >
            Pré-visualização do rascunho — esta versão ainda não está publicada.
          </div>
        ) : null}

        {/* O gradiente do desenho cobre o cabecalho e o heroi; o resto da
            pagina assenta em --surface. */}
        <div className="bzs-topgrad">
          <SiteHeader site={site} />
          {result.state === "loading" ? <SiteSkeleton /> : <BlockRenderer blocks={top} />}
        </div>
        <BlockRenderer blocks={rest} />

        <SiteFooter site={site} />
      </div>
    </SiteDataProvider>
  );
}
