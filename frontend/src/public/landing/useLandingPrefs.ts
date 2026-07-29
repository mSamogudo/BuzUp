import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";
export type Lang = "pt" | "en";

const THEME_KEY = "busup_landing_theme";
const LANG_KEY = "busup_landing_lang";

function initialTheme(): Theme | null {
  const saved = localStorage.getItem(THEME_KEY);
  return saved === "light" || saved === "dark" ? saved : null;
}

function initialLang(): Lang {
  const saved = localStorage.getItem(LANG_KEY);
  if (saved === "pt" || saved === "en") return saved;
  return navigator.language?.toLowerCase().startsWith("en") ? "en" : "pt";
}

/** Tema e idioma do site público, guardados entre visitas.
 *  Sem escolha guardada, o tema segue a preferência do sistema (CSS) e o
 *  idioma segue o do navegador. */
export function useLandingPrefs() {
  const [theme, setThemeState] = useState<Theme | null>(() => {
    try { return initialTheme(); } catch { return null; }
  });
  const [lang, setLangState] = useState<Lang>(() => {
    try { return initialLang(); } catch { return "pt"; }
  });

  const systemDark = typeof window !== "undefined"
    && window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  const effectiveTheme: Theme = theme ?? (systemDark ? "dark" : "light");

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => {
      const next: Theme = (prev ?? (systemDark ? "dark" : "light")) === "dark" ? "light" : "dark";
      try { localStorage.setItem(THEME_KEY, next); } catch { /* modo privado */ }
      return next;
    });
  }, [systemDark]);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try { localStorage.setItem(LANG_KEY, next); } catch { /* modo privado */ }
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang === "en" ? "en" : "pt";
  }, [lang]);

  return { theme, effectiveTheme, toggleTheme, lang, setLang };
}
