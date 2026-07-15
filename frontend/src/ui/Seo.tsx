import { Helmet } from "react-helmet-async";
import { abs, OG_IMAGE, OG_IMAGE_ALT, OG_IMAGE_H, OG_IMAGE_W, type Lang, type PageSeo } from "../lib/seo";

interface SeoProps {
  page: PageSeo;
  lang: Lang;
  /** Optional JSON-LD blocks for this page. */
  jsonLd?: object[];
  /** Override social preview image (absolute or root-relative). */
  image?: string;
}

/**
 * Per-route <head> management for the public marketing pages.
 * Sets title, description, canonical, hreflang alternates, Open Graph
 * and Twitter cards, plus any structured-data blocks.
 */
export function Seo({ page, lang, jsonLd, image }: SeoProps) {
  const title = page.title[lang];
  const description = page.description[lang];
  const path = lang === "en" ? page.enPath : page.ptPath;
  const canonical = abs(path);
  const ptUrl = abs(page.ptPath);
  const enUrl = abs(page.enPath);
  const usingDefaultImage = !image;
  const ogImage = image ? (image.startsWith("http") ? image : abs(image)) : OG_IMAGE;
  const ogLocale = lang === "en" ? "en" : "pt_MZ";

  return (
    <Helmet htmlAttributes={{ lang: lang === "en" ? "en" : "pt-MZ" }}>
      <title>{title}</title>
      <meta name="description" content={description} />
      <link rel="canonical" href={canonical} />

      {/* hreflang alternates */}
      <link rel="alternate" hrefLang="pt-MZ" href={ptUrl} />
      <link rel="alternate" hrefLang="en" href={enUrl} />
      <link rel="alternate" hrefLang="x-default" href={ptUrl} />

      {/* Open Graph */}
      <meta property="og:type" content="website" />
      <meta property="og:site_name" content="BusUp" />
      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:url" content={canonical} />
      <meta property="og:image" content={ogImage} />
      {usingDefaultImage && <meta property="og:image:width" content={String(OG_IMAGE_W)} />}
      {usingDefaultImage && <meta property="og:image:height" content={String(OG_IMAGE_H)} />}
      {usingDefaultImage && <meta property="og:image:alt" content={OG_IMAGE_ALT} />}
      <meta property="og:locale" content={ogLocale} />

      {/* Twitter */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={ogImage} />
      {usingDefaultImage && <meta name="twitter:image:alt" content={OG_IMAGE_ALT} />}

      {jsonLd?.map((block, i) => (
        <script key={i} type="application/ld+json">
          {JSON.stringify(block)}
        </script>
      ))}
    </Helmet>
  );
}
