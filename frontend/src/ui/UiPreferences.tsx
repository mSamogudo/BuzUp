import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import type { Locale } from "../lib/i18n";

type Theme = "light" | "dark";

interface UiPrefs {
  locale: Locale;
  setLocale: (v: Locale) => void;
  /** O tema em vigor, ja resolvido. E este que se pinta. */
  theme: Theme;
  /** O que o utilizador escolheu; `null` significa "seguir o sistema". */
  themeChoice: Theme | null;
  setTheme: (v: Theme | null) => void;
  toggleTheme: () => void;
}

const UiContext = createContext<UiPrefs>({
  locale: "pt",
  setLocale: () => {},
  theme: "light",
  themeChoice: null,
  setTheme: () => {},
  toggleTheme: () => {},
});

const THEME_KEY = "buzup_theme";

/** O tema do sistema operativo, quando o utilizador nao escolheu nenhum. */
function temaDoSistema(): Theme {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function UiPreferencesProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => (localStorage.getItem("buzup_locale") as Locale) || "pt");
  // Guardado: "light" | "dark" | nada. Nada nao e "claro" — e "segue o
  // sistema", que e o que a maioria dos utilizadores espera sem ter de
  // escolher. So passa a valor fixo quando alguem escolhe de proposito.
  const [themeChoice, setThemeChoice] = useState<Theme | null>(() => {
    const guardado = localStorage.getItem(THEME_KEY);
    return guardado === "light" || guardado === "dark" ? guardado : null;
  });
  const [temaSistema, setTemaSistema] = useState<Theme>(temaDoSistema);
  const theme: Theme = themeChoice ?? temaSistema;

  const setLocale = useCallback((v: Locale) => {
    localStorage.setItem("buzup_locale", v);
    setLocaleState(v);
  }, []);

  const setTheme = useCallback((v: Theme | null) => {
    if (v === null) localStorage.removeItem(THEME_KEY);
    else localStorage.setItem(THEME_KEY, v);
    setThemeChoice(v);
  }, []);

  // O botao da barra fixa um tema: quem carrega nele quer aquele, e nao
  // continuar a seguir o sistema.
  const toggleTheme = useCallback(() => {
    setTheme(theme === "light" ? "dark" : "light");
  }, [setTheme, theme]);

  // So enquanto o utilizador nao escolheu: se o portatil passa a escuro ao
  // fim da tarde, o portal acompanha.
  useEffect(() => {
    const media = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!media) return;
    const ouvir = (e: MediaQueryListEvent) => setTemaSistema(e.matches ? "dark" : "light");
    media.addEventListener("change", ouvir);
    return () => media.removeEventListener("change", ouvir);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  return (
    <UiContext.Provider value={{ locale, setLocale, theme, themeChoice, setTheme, toggleTheme }}>
      {children}
    </UiContext.Provider>
  );
}

export function useUi() {
  return useContext(UiContext);
}
