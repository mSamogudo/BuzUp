import { useCallback, useEffect, useSyncExternalStore } from "react";

export type Theme = "light" | "dark";
export type Lang = "pt" | "en";

const THEME_KEY = "busup_landing_theme";
const LANG_KEY = "busup_landing_lang";

function initialTheme(): Theme | null {
  try {
    const saved = localStorage.getItem(THEME_KEY);
    return saved === "light" || saved === "dark" ? saved : null;
  } catch {
    return null; // modo privado
  }
}

function initialLang(): Lang {
  try {
    const saved = localStorage.getItem(LANG_KEY);
    if (saved === "pt" || saved === "en") return saved;
  } catch { /* modo privado */ }
  return navigator.language?.toLowerCase().startsWith("en") ? "en" : "pt";
}

/* O estado vive FORA do React, num pequeno armazém com subscritores.
 *
 * Estava em `useState` dentro do hook, e isso só funciona enquanto houver um
 * único componente a chamá-lo — foi o caso enquanto a landing era uma página
 * só. Com a moldura partilhada das páginas da TPM-TUR passaram a existir três
 * chamadas independentes (o botão de tema, a barra e a casca): carregar no
 * botão mudava o estado DELE, gravava no localStorage e mais nada acontecia na
 * página; o tema só aparecia depois de recarregar. Medido, não suposto.
 *
 * Com um armazém partilhado, quem carrega no botão avisa todos os que estão a
 * ler, e a API do hook não muda para quem já o usava. */
type Estado = { theme: Theme | null; lang: Lang };

let estado: Estado = { theme: null, lang: "pt" };
let iniciado = false;

function garantirInicio() {
  if (iniciado) return;
  iniciado = true;
  estado = { theme: initialTheme(), lang: initialLang() };
}

const ouvintes = new Set<() => void>();

function subscrever(ouvinte: () => void) {
  ouvintes.add(ouvinte);
  return () => { ouvintes.delete(ouvinte); };
}

function ler(): Estado {
  garantirInicio();
  return estado;
}

/** O instantâneo tem de ser estável: só se troca o objecto quando muda mesmo,
 *  senão o React volta a renderizar sem fim. */
function actualizar(parcial: Partial<Estado>) {
  const seguinte = { ...ler(), ...parcial };
  if (seguinte.theme === estado.theme && seguinte.lang === estado.lang) return;
  estado = seguinte;
  for (const ouvinte of ouvintes) ouvinte();
}

/** Tema e idioma do site público, guardados entre visitas e partilhados por
 *  todos os componentes que os leem.
 *  Sem escolha guardada, o tema segue a preferência do sistema e o idioma
 *  segue o do navegador. */
export function useLandingPrefs() {
  const { theme, lang } = useSyncExternalStore(subscrever, ler, ler);

  const systemDark = typeof window !== "undefined"
    && window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  const effectiveTheme: Theme = theme ?? (systemDark ? "dark" : "light");

  const toggleTheme = useCallback(() => {
    const actual = ler().theme ?? (systemDark ? "dark" : "light");
    const next: Theme = actual === "dark" ? "light" : "dark";
    try { localStorage.setItem(THEME_KEY, next); } catch { /* modo privado */ }
    actualizar({ theme: next });
  }, [systemDark]);

  const setLang = useCallback((next: Lang) => {
    try { localStorage.setItem(LANG_KEY, next); } catch { /* modo privado */ }
    actualizar({ lang: next });
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang === "en" ? "en" : "pt";
  }, [lang]);

  return { theme, effectiveTheme, toggleTheme, lang, setLang };
}
