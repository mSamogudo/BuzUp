import { useCallback, useState } from "react";
import { useUi } from "../ui/UiPreferences";
import { CORES_DE_MARCA, RAIOS, type ThemePreset } from "./tipos";

/** Todas as variaveis que um preset pode ter posto no <html>.
 *  Repor o tema e remove-las todas: sem estilo inline, o que manda outra vez
 *  e o `themes/tpm-tur.css`, que e de onde a aplicacao arranca. */
const VARIAVEIS = [
  "background", "foreground", "card", "card-foreground", "popover", "popover-foreground",
  "primary", "primary-foreground", "secondary", "secondary-foreground",
  "muted", "muted-foreground", "accent", "accent-foreground",
  "warning", "warning-foreground", "success", "success-foreground",
  "destructive", "destructive-foreground", "border", "input", "ring", "radius",
  "chart-1", "chart-2", "chart-3", "chart-4", "chart-5",
  "sidebar", "sidebar-foreground", "sidebar-primary",
  "sidebar-primary-foreground", "sidebar-accent", "sidebar-accent-foreground",
  "sidebar-border", "sidebar-ring",
  "font-sans", "font-display",
];

/* O preset escolhido guarda-se com os estilos ja resolvidos (light + dark),
 * e nao so o nome: assim o arranque reaplica o tema sem carregar os ~140KB
 * de presets, que so entram quando o painel abre. raio e cores de marca
 * guardam-se a parte porque se aplicam POR CIMA de qualquer preset. */
const CHAVE_APLICADO = "buzup_tema_aplicado";
const CHAVE_RAIO = "buzup_tema_raio";
const CHAVE_CORES = "buzup_tema_cores";

interface TemaAplicado {
  preset: string;
  light: Record<string, string>;
  dark: Record<string, string>;
}

function lerJSON<T>(chave: string): T | null {
  try {
    const crua = localStorage.getItem(chave);
    return crua ? (JSON.parse(crua) as T) : null;
  } catch {
    return null; // JSON estragado por edicao manual: ignora-se, nunca se rebenta o arranque
  }
}

/** Muitos presets do template so trazem o nucleo de cores e nao tocam na
 *  barra lateral. No template isso significa "fica a barra base" — aqui dava
 *  um tema verde-lima com barra navy, e o objectivo destes presets e
 *  precisamente mostrar como o produto fica noutro operador.
 *
 *  Quando faltam, derivam-se do proprio preset, pelo mapa que o shadcn usa
 *  por omissao. Um valor que o preset traga nunca e substituido. */
function comBarraLateral(estilos: Record<string, string>): Record<string, string> {
  const derivar: Record<string, string> = {
    sidebar: "card",
    "sidebar-foreground": "card-foreground",
    "sidebar-primary": "primary",
    "sidebar-primary-foreground": "primary-foreground",
    "sidebar-accent": "accent",
    "sidebar-accent-foreground": "accent-foreground",
    "sidebar-border": "border",
    "sidebar-ring": "ring",
  };
  const saida = { ...estilos };
  for (const [alvo, origem] of Object.entries(derivar)) {
    if (!saida[alvo] && estilos[origem]) saida[alvo] = estilos[origem];
  }
  return saida;
}

function limparInline() {
  const raiz = document.documentElement;
  for (const v of VARIAVEIS) raiz.style.removeProperty(`--${v}`);
  // Varrer tambem o que um tema importado possa ter deixado para tras.
  for (let i = raiz.style.length - 1; i >= 0; i--) {
    const prop = raiz.style[i];
    if (prop.startsWith("--")) raiz.style.removeProperty(prop);
  }
}

export function useGestorDeTema() {
  // O claro/escuro continua a ser do UiPreferences. Trazer o ThemeProvider do
  // template daria dois donos do mesmo <html> e duas chaves de localStorage a
  // discordar uma da outra.
  const { theme } = useUi();
  const escuro = theme === "dark";

  const [presetActual, setPresetActual] = useState<string>(
    () => lerJSON<TemaAplicado>(CHAVE_APLICADO)?.preset || "tpm-tur",
  );
  const [raioActual, setRaioActual] = useState<string>(
    () => localStorage.getItem(CHAVE_RAIO) || "0.5rem",
  );
  const [coresDeMarca, setCoresDeMarca] = useState<Record<string, string>>(
    () => lerJSON<Record<string, string>>(CHAVE_CORES) ?? {},
  );

  /** Aplica um conjunto de estilos e depois as escolhas manuais (raio e
   *  cores): a intencao do utilizador ganha sempre ao que o preset traz. */
  const aplicarEstilos = useCallback(
    (estilos: Record<string, string>, raio?: string, cores?: Record<string, string>) => {
      const raiz = document.documentElement;
      const completos = comBarraLateral(estilos);
      for (const [chave, valor] of Object.entries(completos)) {
        raiz.style.setProperty(`--${chave}`, valor);
      }
      const raioFinal = raio ?? localStorage.getItem(CHAVE_RAIO);
      if (raioFinal) raiz.style.setProperty("--radius", raioFinal);
      const coresFinais = cores ?? lerJSON<Record<string, string>>(CHAVE_CORES) ?? {};
      for (const [cssVar, valor] of Object.entries(coresFinais)) {
        raiz.style.setProperty(cssVar, valor);
      }
    },
    [],
  );

  const repor = useCallback(() => {
    limparInline();
    localStorage.removeItem(CHAVE_APLICADO);
    localStorage.removeItem(CHAVE_RAIO);
    localStorage.removeItem(CHAVE_CORES);
    localStorage.removeItem("buzup_tema_preset"); // chave da primeira versao
    setPresetActual("tpm-tur");
    setRaioActual("0.5rem");
    setCoresDeMarca({});
  }, []);

  /** As cores a mostrar nos pickers: as do preset, com os ajustes manuais
   *  guardados por cima. Trocar de preset limpa os ajustes — mexeram-se em
   *  cima daquele preset, nao fariam sentido noutro. */
  const lerCoresDeMarca = useCallback((estilos: Record<string, string>) => {
    const novas: Record<string, string> = {};
    for (const { cssVar } of CORES_DE_MARCA) {
      const nome = cssVar.replace("--", "");
      if (estilos[nome]) novas[cssVar] = estilos[nome];
    }
    setCoresDeMarca({ ...novas, ...(lerJSON<Record<string, string>>(CHAVE_CORES) ?? {}) });
  }, []);

  const aplicarPreset = useCallback(
    (valor: string, preset: ThemePreset) => {
      limparInline();
      localStorage.removeItem(CHAVE_CORES);
      setPresetActual(valor);

      // O TPM-TUR e o estado de repouso: ja esta no CSS, nao precisa de estilo
      // inline. Aplica-lo como os outros funcionaria, mas deixava o <html>
      // cheio de variaveis iguais as que ja la estavam.
      if (valor === "tpm-tur") {
        localStorage.removeItem(CHAVE_APLICADO);
        const raio = localStorage.getItem(CHAVE_RAIO);
        if (raio) document.documentElement.style.setProperty("--radius", raio);
        setCoresDeMarca({});
        return;
      }

      localStorage.setItem(
        CHAVE_APLICADO,
        JSON.stringify({ preset: valor, light: preset.styles.light, dark: preset.styles.dark }),
      );
      aplicarEstilos(escuro ? preset.styles.dark : preset.styles.light);
      lerCoresDeMarca(escuro ? preset.styles.dark : preset.styles.light);
    },
    [escuro, aplicarEstilos, lerCoresDeMarca],
  );

  const aplicarImportado = useCallback(
    (dados: { light: Record<string, string>; dark: Record<string, string> }) => {
      limparInline();
      localStorage.removeItem(CHAVE_CORES);
      setPresetActual("importado");
      localStorage.setItem(
        CHAVE_APLICADO,
        JSON.stringify({ preset: "importado", light: dados.light, dark: dados.dark }),
      );
      aplicarEstilos(escuro ? dados.dark : dados.light);
      lerCoresDeMarca(escuro ? dados.dark : dados.light);
    },
    [escuro, aplicarEstilos, lerCoresDeMarca],
  );

  /** O que sobrevive ao reload: corre no arranque e em cada troca
   *  claro/escuro, mesmo com o painel fechado. Sem ele, o preset guardado
   *  so voltava quando alguem abrisse o painel. */
  const restaurarGuardado = useCallback(() => {
    const guardado = lerJSON<TemaAplicado>(CHAVE_APLICADO);
    if (!guardado || guardado.preset === "tpm-tur") return;
    limparInline();
    aplicarEstilos(escuro ? guardado.dark : guardado.light);
    lerCoresDeMarca(escuro ? guardado.dark : guardado.light);
  }, [escuro, aplicarEstilos, lerCoresDeMarca]);

  const aplicarRaio = useCallback((raio: string) => {
    document.documentElement.style.setProperty("--radius", raio);
    localStorage.setItem(CHAVE_RAIO, raio);
    setRaioActual(raio);
  }, []);

  const mudarCor = useCallback((cssVar: string, valor: string) => {
    document.documentElement.style.setProperty(cssVar, valor);
    setCoresDeMarca((anteriores) => {
      const novas = { ...anteriores, [cssVar]: valor };
      localStorage.setItem(CHAVE_CORES, JSON.stringify(novas));
      return novas;
    });
  }, []);

  return {
    escuro,
    presetActual,
    raioActual: RAIOS.some((r) => r.valor === raioActual) ? raioActual : "0.5rem",
    coresDeMarca,
    repor,
    aplicarPreset,
    aplicarImportado,
    restaurarGuardado,
    aplicarRaio,
    mudarCor,
  };
}
