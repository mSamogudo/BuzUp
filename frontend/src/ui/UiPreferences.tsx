import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import type { Locale } from "../lib/i18n";

type Theme = "light" | "dark";

interface UiPrefs {
  locale: Locale;
  setLocale: (v: Locale) => void;
  theme: Theme;
  toggleTheme: () => void;
}

const UiContext = createContext<UiPrefs>({
  locale: "pt",
  setLocale: () => {},
  theme: "light",
  toggleTheme: () => {},
});

export function UiPreferencesProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => (localStorage.getItem("buzup_locale") as Locale) || "pt");
  const [theme, setThemeState] = useState<Theme>(() => (localStorage.getItem("buzup_theme") as Theme) || "light");

  const setLocale = useCallback((v: Locale) => {
    localStorage.setItem("buzup_locale", v);
    setLocaleState(v);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((c) => {
      const next = c === "light" ? "dark" : "light";
      localStorage.setItem("buzup_theme", next);
      return next;
    });
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  return (
    <UiContext.Provider value={{ locale, setLocale, theme, toggleTheme }}>
      {children}
    </UiContext.Provider>
  );
}

export function useUi() {
  return useContext(UiContext);
}
