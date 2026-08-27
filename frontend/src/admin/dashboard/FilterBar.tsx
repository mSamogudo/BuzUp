import { SlidersHorizontal, X } from "lucide-react";
import { t, type Locale } from "../../lib/i18n";
import { useUi } from "../../ui/UiPreferences";
import type { DashFilters, Lookup } from "./types";
import { ISO_TODAY, isoDaysAgo, isoMonthStart, providerLabel } from "./theme";

/** Filtros que valem para TUDO no painel — os mesmos parâmetros são aplicados
 * a cartões, gráficos e tabelas pelo backend, por isso os números batem certo
 * entre secções. */

/** Função e não constante: um painel aberto durante a noite tem de continuar a
 * dizer "30 dias até hoje" no dia seguinte. */
export const defaultFilters = (): DashFilters => ({
  dateFrom: isoDaysAgo(29),
  dateTo: ISO_TODAY(),
  routeId: "",
  driverId: "",
  agentId: "",
  provider: "",
});

/** Só conta o que restringe os dados: o intervalo de datas está sempre
 * definido, logo não é "um filtro activo". */
export function countActive(f: DashFilters): number {
  return [f.routeId, f.driverId, f.agentId, f.provider].filter(Boolean).length;
}

export function isDefaultRange(f: DashFilters): boolean {
  return f.dateFrom === isoDaysAgo(29) && f.dateTo === ISO_TODAY();
}

type Shortcut = { key: string; label: string; from: () => string; to: () => string };

const atalhos = (lc: Locale): Shortcut[] => [
  { key: "today", label: t(lc, "today"), from: ISO_TODAY, to: ISO_TODAY },
  { key: "7d", label: t(lc, "days7"), from: () => isoDaysAgo(6), to: ISO_TODAY },
  { key: "30d", label: t(lc, "days30"), from: () => isoDaysAgo(29), to: ISO_TODAY },
  { key: "month", label: t(lc, "thisMonth"), from: isoMonthStart, to: ISO_TODAY },
];

export default function FilterBar({
  value, onChange, onClear, routes, drivers, agents, providers, loading,
}: {
  value: DashFilters;
  onChange: (next: DashFilters) => void;
  onClear: () => void;
  routes: Lookup[];
  drivers: Lookup[];
  agents: Lookup[];
  providers: string[];
  loading: boolean;
}) {
  const { locale: lc } = useUi();
  const set = (patch: Partial<DashFilters>) => onChange({ ...value, ...patch });
  const active = countActive(value);
  const activeShortcut = atalhos(lc).find((s) => s.from() === value.dateFrom && s.to() === value.dateTo);
  const days = Math.max(
    1,
    Math.round((new Date(value.dateTo).getTime() - new Date(value.dateFrom).getTime()) / 86_400_000) + 1,
  );

  return (
    <div className="dash-filters">
      <div className="dash-filters-head">
        <span className="dash-filters-title">
          <SlidersHorizontal size={14} />
          {t(lc, "filters")}
        </span>
        <span className={`dash-badge${active ? "" : " dash-badge-muted"}`}>
          {active === 0 ? "Sem filtros" : active === 1 ? "1 filtro activo" : `${active} filtros activos`}
        </span>
        <span className="dash-badge dash-badge-muted">{days} {days === 1 ? "dia" : "dias"}</span>

        <div className="dash-spacer" />

        <div className="dash-shortcuts">
          {atalhos(lc).map((s) => (
            <button
              className={`admin-chip-button${activeShortcut?.key === s.key ? " admin-chip-button-active" : ""}`}
              key={s.key}
              onClick={() => set({ dateFrom: s.from(), dateTo: s.to() })}
              type="button"
            >
              {s.label}
            </button>
          ))}
        </div>

        {(active > 0 || !isDefaultRange(value)) && (
          <button className="admin-chip-button" onClick={onClear} type="button">
            <X size={11} style={{ verticalAlign: "-1px", marginRight: 4 }} />
            {t(lc, "clear")}
          </button>
        )}
      </div>

      <div className="dash-filter-grid">
        <label className="field">
          <span>{t(lc, "from")}</span>
          <input max={value.dateTo} onChange={(e) => set({ dateFrom: e.target.value })} type="date" value={value.dateFrom} />
        </label>
        <label className="field">
          <span>{t(lc, "to")}</span>
          <input min={value.dateFrom} onChange={(e) => set({ dateTo: e.target.value })} type="date" value={value.dateTo} />
        </label>
        <label className="field">
          <span>{t(lc, "route")}</span>
          <select onChange={(e) => set({ routeId: e.target.value })} value={value.routeId}>
            <option value="">Todas ({routes.length})</option>
            {routes.map((r) => (
              <option key={r.id} value={r.id}>{r.code ? `${r.code} · ${r.name}` : r.name}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>{t(lc, "driver")}</span>
          <select onChange={(e) => set({ driverId: e.target.value })} value={value.driverId}>
            <option value="">Todos ({drivers.length})</option>
            {drivers.map((d) => (
              <option key={d.id} value={d.id}>{d.full_name || `Motorista #${d.id}`}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>{t(lc, "agent")}</span>
          <select onChange={(e) => set({ agentId: e.target.value })} value={value.agentId}>
            <option value="">Todos ({agents.length})</option>
            {agents.map((a) => (
              <option key={a.id} value={a.id}>{a.full_name || `Agente #${a.id}`}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>{t(lc, "paymentMethod")}</span>
          <select onChange={(e) => set({ provider: e.target.value })} value={value.provider}>
            <option value="">{t(lc, "all")}</option>
            {providers.map((p) => (
              <option key={p} value={p}>{providerLabel(p)}</option>
            ))}
          </select>
        </label>
      </div>

      <p className="dash-filter-note">
        {loading
          ? "A aplicar filtros…"
          : "Os filtros aplicam-se a todos os cartões, gráficos e tabelas — os totais batem certo entre secções."}
      </p>
    </div>
  );
}
