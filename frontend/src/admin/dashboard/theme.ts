/** Tokens de cor e formatadores dos gráficos do dashboard.
 *
 * As cores NÃO são escolhidas a olho: partem da paleta do portal
 * (--app-accent, --app-success) e foram ajustadas até passarem as verificações
 * de daltonismo/contraste (separação CVD, piso de visão normal, banda de
 * luminosidade e contraste ≥3:1 contra a superfície de cada tema).
 *
 * Ordem dos slots = ordem de empilhamento. Trocar a ordem estraga a separação
 * entre séries vizinhas — se acrescentares uma série, valida o conjunto todo.
 *
 * Uma cor por entidade, sempre a mesma: a série "bilhetes" é azul quer haja 2
 * ou 4 séries no gráfico. Nunca colorir por posição no ranking.
 */

export interface ChartTheme {
  grid: string;
  axis: string;
  surface: string;
  /** [0] bilhetes · [1] validações · [2] recargas · [3] quarta categoria */
  series: [string, string, string, string];
  /** "Outros" — cinzento de propósito, não é uma categoria com identidade. */
  other: string;
}

const LIGHT: ChartTheme = {
  grid: "#E4E4E7",
  axis: "#71717A",
  surface: "#FFFFFF",
  series: ["#1D5FA7", "#2A9D8F", "#C77700", "#B23A48"],
  other: "#8E8E96",
};

const DARK: ChartTheme = {
  grid: "#27272A",
  axis: "#A1A1AA",
  surface: "#18181B",
  series: ["#2D8CF0", "#2FA593", "#C4830F", "#C75160"],
  other: "#7C8896",
};

export function chartTheme(theme: "light" | "dark"): ChartTheme {
  return theme === "dark" ? DARK : LIGHT;
}

/** Decimal-string do backend → número. Nunca devolve NaN. */
export function num(value: string | number | null | undefined): number {
  if (value === null || value === undefined) return 0;
  const n = typeof value === "string" ? parseFloat(value) : value;
  return Number.isFinite(n) ? n : 0;
}

/** Eixos: 1.2K / 3.4M. Casas decimais em eixos são ruído. */
export function compact(value: string | number): string {
  const n = num(value);
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString("pt-MZ", { maximumFractionDigits: 0 });
}

export function shortDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("pt-MZ", { day: "2-digit", month: "short" });
}

export function shortTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleTimeString("pt-MZ", { hour: "2-digit", minute: "2-digit" });
}

/** Rótulo humano para os providers de pagamento (CharField livre no backend). */
export function providerLabel(raw: string): string {
  const key = (raw || "").trim().toUpperCase();
  const map: Record<string, string> = {
    MPESA: "M-Pesa",
    "M-PESA": "M-Pesa",
    EMOLA: "e-Mola",
    MKESH: "mKesh",
    CASH: "Numerário",
    DINHEIRO: "Numerário",
    CARD: "Cartão",
    WALLET: "Carteira",
    POS: "POS",
    MANUAL: "Manual",
    OUTRO: "Outro",
  };
  return map[key] || (raw || "Outro");
}

export const ISO_TODAY = () => new Date().toISOString().slice(0, 10);

export function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export function isoMonthStart(): string {
  const d = new Date();
  d.setDate(1);
  return d.toISOString().slice(0, 10);
}
