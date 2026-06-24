import { useNavigate } from "react-router-dom";
import type { Lang } from "../../lib/seo";

/**
 * Language switch for the public marketing pages. Navigates to the
 * equivalent URL in the other language so the visible language always
 * matches the canonical/hreflang URL.
 */
export function LangToggle({ lang, ptPath, enPath }: { lang: Lang; ptPath: string; enPath: string }) {
  const navigate = useNavigate();
  return (
    <div className="langtog" role="group" aria-label="Idioma / Language">
      <button className={lang === "pt" ? "active" : ""} onClick={() => navigate(ptPath)} type="button">PT</button>
      <button className={lang === "en" ? "active" : ""} onClick={() => navigate(enPath)} type="button">EN</button>
    </div>
  );
}
