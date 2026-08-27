import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, BarChart3, Clock, CreditCard, Route as RouteIcon, RefreshCw, TrendingUp,
} from "lucide-react";
import { apiFetch } from "../lib/api";
import { t } from "../lib/i18n";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { PageFrame, SectionCard, useAsyncData } from "../ui/common";
import { SkeletonCard } from "../ui/Skeleton";
import FilterBar, { countActive, defaultFilters } from "./dashboard/FilterBar";
import {
  ChartCard, HourlyChart, PaymentDonut, RevenueChart, TopRoutesChart,
} from "./dashboard/Charts";
import {
  AutoRefreshToggle, KpiStrip, PackagesTable, RecentActivity,
  TopAgentsTable, TopDriversTable, TopTripsTable,
} from "./dashboard/Panels";
import { chartTheme, shortDate } from "./dashboard/theme";
import type { Analytics, DashFilters, Lookup } from "./dashboard/types";
import "./dashboard/dashboard.css";

const AUTO_REFRESH_MS = 30_000;

/** `useAsyncData` engole o erro num toast e deixa `data` a null — não dá para
 * distinguir "sem dados" de "falhou". Embrulhamos o resultado para termos um
 * estado de erro próprio (com botão de tentar de novo) sem duplicar a lógica
 * de carregamento do portal. */
type Loaded<T> = { ok: true; value: T } | { ok: false; error: string };

function buildQuery(f: DashFilters): string {
  const qs = new URLSearchParams();
  if (f.dateFrom) qs.set("date_from", f.dateFrom);
  if (f.dateTo) qs.set("date_to", f.dateTo);
  if (f.routeId) qs.set("route_id", f.routeId);
  if (f.driverId) qs.set("driver_id", f.driverId);
  if (f.agentId) qs.set("agent_id", f.agentId);
  if (f.provider) qs.set("provider", f.provider);
  return qs.toString();
}

export default function DashboardPage() {
  const { token } = useAuth();
  const { locale: lc, theme } = useUi();
  const c = chartTheme(theme);

  const [filters, setFilters] = useState<DashFilters>(defaultFilters);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lastLoad, setLastLoad] = useState<Date | null>(null);

  const [routes, setRoutes] = useState<Lookup[]>([]);
  const [drivers, setDrivers] = useState<Lookup[]>([]);
  const [agents, setAgents] = useState<Lookup[]>([]);
  const [providers, setProviders] = useState<string[]>([]);

  // Opções dos filtros: falhas ficam silenciosas — um dropdown vazio não deve
  // derrubar o painel inteiro.
  useEffect(() => {
    if (!token) return;
    apiFetch("/api/routes/", token).then((d) => setRoutes(d.results || d)).catch(() => {});
    apiFetch("/api/drivers/", token).then((d) => setDrivers(d.results || d)).catch(() => {});
    apiFetch("/api/agents/", token).then((d) => setAgents(d.results || d)).catch(() => {});
  }, [token]);

  const query = useMemo(() => buildQuery(filters), [filters]);

  const loader = useCallback(
    (): Promise<Loaded<Analytics>> =>
      apiFetch(`/api/admin/analytics/?${query}`, token!)
        .then((d) => ({ ok: true as const, value: d as Analytics }))
        .catch((e) => ({
          ok: false as const,
          error: e instanceof Error ? e.message : "Não foi possível carregar a analítica.",
        })),
    [token, query],
  );
  const { data: result, loading, reload } = useAsyncData<Loaded<Analytics>>(loader, [token, query]);

  const data = result?.ok ? result.value : null;
  const error = result && !result.ok ? result.error : null;

  useEffect(() => { if (result) setLastLoad(new Date()); }, [result]);

  // Providers acumulam-se entre cargas: filtrar por um método não pode fazer
  // desaparecer a própria opção do dropdown.
  useEffect(() => {
    if (!data) return;
    setProviders((prev) => {
      const next = new Set(prev);
      data.payment_methods.forEach((m) => { if (m.provider) next.add(m.provider); });
      if (next.size === prev.length) return prev;
      return Array.from(next).sort();
    });
  }, [data]);

  // Auto-refresh: a referência evita recriar o intervalo a cada render (o
  // `reload` do hook é uma função nova de cada vez).
  const reloadRef = useRef(reload);
  reloadRef.current = reload;
  useEffect(() => {
    if (!autoRefresh) return;
    const id = window.setInterval(() => reloadRef.current(), AUTO_REFRESH_MS);
    return () => window.clearInterval(id);
  }, [autoRefresh]);

  const firstLoad = loading && !data && !error;
  const refreshing = loading && (Boolean(data) || Boolean(error));

  const clampedRange = data && data.filters.date_from !== filters.dateFrom;
  const isEmpty = data
    && !data.kpis.tickets_sold && !data.kpis.validations
    && !data.kpis.trips_total && !data.payment_methods.length;

  const clearFilters = () => setFilters(defaultFilters());

  return (
    <PageFrame
      action={
        <div className="admin-page-actions">
          <AutoRefreshToggle on={autoRefresh} onToggle={() => setAutoRefresh((v) => !v)} />
          <button className="icon-text-button" disabled={loading} onClick={reload} type="button">
            <RefreshCw className={refreshing ? "button-spinner" : undefined} size={16} />
            <span>{t(lc, "refresh")}</span>
          </button>
        </div>
      }
      description={
        lastLoad
          ? `Actualizado às ${lastLoad.toLocaleTimeString("pt-MZ", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}${autoRefresh ? " · auto 30s" : ""}`
          : undefined
      }
      kicker={t(lc, "overview")}
      title={t(lc, "dashboard")}
    >
      <FilterBar
        agents={agents}
        drivers={drivers}
        loading={loading}
        onChange={setFilters}
        onClear={clearFilters}
        providers={providers}
        routes={routes}
        value={filters}
      />

      {clampedRange && data ? (
        <p className="dash-notice">
          Intervalo demasiado longo — o servidor limitou-o a{" "}
          <strong>{shortDate(data.filters.date_from)} – {shortDate(data.filters.date_to)}</strong>.
          Os números abaixo referem-se a esse intervalo.
        </p>
      ) : null}

      {error ? (
        <div className="dash-error" style={{ marginTop: 16 }}>
          <strong>{t(lc, "dashboardFailed")}</strong>
          <p>{error}</p>
          <button className="primary-button" onClick={reload} type="button">
            <RefreshCw size={15} /> {t(lc, "tryAgain")}
          </button>
        </div>
      ) : null}

      {firstLoad ? (
        <div style={{ marginTop: 16 }}>
          <SkeletonCard count={8} />
          <div className="dash-grid dash-grid-2">
            <div className="skeleton skeleton-card" style={{ height: 340 }} />
            <div className="skeleton skeleton-card" style={{ height: 340 }} />
          </div>
          <div className="dash-grid dash-grid-2-even">
            <div className="skeleton skeleton-card" style={{ height: 300 }} />
            <div className="skeleton skeleton-card" style={{ height: 300 }} />
          </div>
        </div>
      ) : null}

      {data ? (
        <div style={{ marginTop: 16, opacity: refreshing ? 0.65 : 1, transition: "opacity 160ms ease" }}>
          {isEmpty ? (
            <div className="admin-empty-state" style={{ marginBottom: 16 }}>
              Sem movimento no intervalo seleccionado
              {countActive(filters) > 0 ? " com estes filtros. Tente limpar os filtros ou alargar as datas." : ". Tente alargar as datas."}
            </div>
          ) : null}

          <KpiStrip k={data.kpis} packages={data.packages} />

          <div className="dash-grid dash-grid-2">
            <ChartCard
              icon={<TrendingUp size={18} />}
              subtitle={t(lc, "revenueChartHint")}
              title={t(lc, "revenuePerDay")}
            >
              <RevenueChart c={c} data={data.revenue_series} />
            </ChartCard>

            <ChartCard
              icon={<CreditCard size={18} />}
              subtitle={t(lc, "confirmedByChannel")}
              title={t(lc, "paymentMethods")}
            >
              <PaymentDonut c={c} data={data.payment_methods} />
            </ChartCard>
          </div>

          <div className="dash-grid dash-grid-2-even">
            <ChartCard
              icon={<Clock size={18} />}
              subtitle={t(lc, "hourlyHint")}
              title={t(lc, "hourlySpread")}
            >
              <HourlyChart c={c} data={data.hourly} />
            </ChartCard>

            <ChartCard
              icon={<RouteIcon size={18} />}
              subtitle={t(lc, "revenuePerRoute")}
              title={t(lc, "topRoutes")}
            >
              <TopRoutesChart c={c} data={data.top_routes} />
            </ChartCard>
          </div>

          <div className="dash-grid dash-grid-2">
            <SectionCard description={t(lc, "topTripsHint")} title={t(lc, "topTrips")}>
              <TopTripsTable rows={data.top_trips} />
            </SectionCard>

            <SectionCard
              description={autoRefresh ? "A actualizar a cada 30 segundos." : "Últimos movimentos no intervalo."}
              title={t(lc, "recentActivity")}
            >
              <RecentActivity items={data.recent} />
            </SectionCard>
          </div>

          <div className="dash-grid dash-grid-2-even">
            <SectionCard description={t(lc, "sortedByTripRevenue")} title={t(lc, "topDrivers")}>
              <TopDriversTable rows={data.top_drivers} />
            </SectionCard>

            <SectionCard description={t(lc, "agentSalesHint")} title={t(lc, "topAgents")}>
              <TopAgentsTable rows={data.top_agents} />
            </SectionCard>
          </div>

          <div className="dash-grid">
            <SectionCard
              description={`${data.packages.subscriptions} subscrições no intervalo · ${data.packages.active_now} activas neste momento.`}
              title={t(lc, "packages")}
            >
              <PackagesTable rows={data.packages.by_package} />
            </SectionCard>
          </div>
        </div>
      ) : null}

      {!firstLoad && !data && !error ? (
        <div className="admin-empty-state" style={{ marginTop: 16 }}>
          <BarChart3 size={16} style={{ verticalAlign: "-3px", marginRight: 6 }} />
          {t(lc, "noData")}
        </div>
      ) : null}

      {refreshing ? (
        <p className="dash-kpi-note" style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Activity size={12} /> {t(lc, "refreshing")}
        </p>
      ) : null}
    </PageFrame>
  );
}
