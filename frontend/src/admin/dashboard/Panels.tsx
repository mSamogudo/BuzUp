import { Pause, Play, QrCode, Ticket } from "lucide-react";
import { useUi } from "../../ui/UiPreferences";
import { t, type Locale } from "../../lib/i18n";
import { formatCount, formatCurrency, formatDateTime } from "../../lib/format";
import { DataTable, MetricCard, type TableColumn } from "../../ui/common";
import { shortTime } from "./theme";
import type {
  AnalyticsKpis, PackagesBlock, RecentItem, TopAgentRow, TopDriverRow, TopTripRow,
} from "./types";

/* ------------------------------------------------------------------ */
/* KPIs                                                                */
/* ------------------------------------------------------------------ */

/** Cada cartão diz o que mede. A distinção que mais confunde num painel de
 * transportes: recargas ≠ receita. O backend separa-as de propósito e aqui
 * mantemos essa leitura visível em vez de a esconder num tooltip. */
export function KpiStrip({ k, packages }: { k: AnalyticsKpis; packages: PackagesBlock }) {
  const { locale: lc } = useUi();
  const completion = k.trips_total ? Math.round((k.trips_completed / k.trips_total) * 100) : 0;
  return (
    <>
      <div className="admin-metric-grid">
        <MetricCard
          detail={t(lc, "cashInHint")}
          label={t(lc, "cashIn")}
          value={formatCurrency(k.cash_in)}
        />
        <MetricCard
          detail={t(lc, "transportRevenueHint")}
          label={t(lc, "transportRevenue")}
          value={formatCurrency(k.transport_revenue)}
        />
        <MetricCard
          detail={formatCurrency(k.ticket_revenue)}
          label={t(lc, "ticketsSoldLabel")}
          value={formatCount(k.tickets_sold)}
        />
        <MetricCard
          detail={formatCurrency(k.validation_revenue)}
          label={t(lc, "validations")}
          value={formatCount(k.validations)}
        />
        <MetricCard
          detail={t(lc, "averageTicketHint")}
          label={t(lc, "averageTicket")}
          value={formatCurrency(k.avg_ticket)}
        />
        <MetricCard
          detail={t(lc, "topUpsHint")}
          label={t(lc, "topUps")}
          value={formatCurrency(k.topups_total)}
        />
        <MetricCard
          detail={`${formatCount(k.trips_completed)} ${t(lc, "completedPl").toLowerCase()} · ${completion}%`}
          label={t(lc, "trips")}
          value={formatCount(k.trips_total)}
        />
        <MetricCard
          detail={`${formatCount(packages.subscriptions)} ${t(lc, "subscriptions").toLowerCase()}`}
          label={t(lc, "activePackages")}
          value={formatCount(packages.active_now)}
        />
      </div>
      <p className="dash-kpi-note">{t(lc, "kpiNote")}</p>
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Tabelas                                                             */
/* ------------------------------------------------------------------ */

const tripCols = (lc: Locale): TableColumn<TopTripRow>[] => [
  { header: t(lc, "trip"), render: (r) => <strong>#{r.trip_id}</strong> },
  { header: t(lc, "route"), render: (r) => r.route || "-" },
  { header: t(lc, "departure"), render: (r) => (r.departure ? formatDateTime(r.departure) : "-") },
  { header: t(lc, "bus"), render: (r) => r.vehicle || "-" },
  { header: t(lc, "driver"), render: (r) => r.driver || "-" },
  { header: t(lc, "passengers"), render: (r) => formatCount(r.passengers) },
  { header: t(lc, "revenue"), render: (r) => formatCurrency(r.revenue) },
];

const driverCols = (lc: Locale): TableColumn<TopDriverRow>[] => [
  { header: t(lc, "driver"), render: (r) => <strong>{r.name || `#${r.driver_id}`}</strong> },
  { header: t(lc, "trips"), render: (r) => formatCount(r.trips) },
  { header: t(lc, "completedPl"), render: (r) => formatCount(r.completed) },
  { header: t(lc, "passengers"), render: (r) => formatCount(r.passengers) },
  { header: t(lc, "revenue"), render: (r) => formatCurrency(r.revenue) },
];

const agentCols = (lc: Locale): TableColumn<TopAgentRow>[] => [
  { header: t(lc, "agent"), render: (r) => <strong>{r.name || `#${r.agent_id}`}</strong> },
  { header: t(lc, "sales"), render: (r) => formatCount(r.sales) },
  { header: t(lc, "revenue"), render: (r) => formatCurrency(r.revenue) },
];

const packageCols = (lc: Locale): TableColumn<PackagesBlock["by_package"][number]>[] => [
  { header: t(lc, "package"), render: (r) => <strong>{r.name || "-"}</strong> },
  { header: t(lc, "subscriptions"), render: (r) => formatCount(r.count) },
  { header: t(lc, "revenue"), render: (r) => formatCurrency(r.revenue) },
];

function Compact<T>({ columns, rows, rowKey, empty }: {
  columns: TableColumn<T>[]; rows: T[]; rowKey: (r: T) => string; empty: string;
}) {
  return (
    <div className="dash-compact-table">
      <DataTable
        columns={columns}
        emptyMessage={empty}
        filterable={false}
        loading={false}
        rowKey={rowKey}
        rows={rows}
      />
    </div>
  );
}

export function TopTripsTable({ rows }: { rows: TopTripRow[] }) {
  const { locale: lc } = useUi();
  return <Compact columns={tripCols(lc)} empty={t(lc, "noTripsWithTickets")} rowKey={(r) => String(r.trip_id)} rows={rows} />;
}

export function TopDriversTable({ rows }: { rows: TopDriverRow[] }) {
  const { locale: lc } = useUi();
  return <Compact columns={driverCols(lc)} empty={t(lc, "noDriversWithTrips")} rowKey={(r) => String(r.driver_id)} rows={rows} />;
}

export function TopAgentsTable({ rows }: { rows: TopAgentRow[] }) {
  const { locale: lc } = useUi();
  return <Compact columns={agentCols(lc)} empty={t(lc, "noAgentSales")} rowKey={(r) => String(r.agent_id)} rows={rows} />;
}

export function PackagesTable({ rows }: { rows: PackagesBlock["by_package"] }) {
  const { locale: lc } = useUi();
  return <Compact columns={packageCols(lc)} empty={t(lc, "noPackageSubs")} rowKey={(r) => r.name || "-"} rows={rows} />;
}

/* ------------------------------------------------------------------ */
/* Actividade recente                                                  */
/* ------------------------------------------------------------------ */

export function AutoRefreshToggle({ on, onToggle }: { on: boolean; onToggle: () => void }) {
  const { locale: lc } = useUi();
  return (
    <button
      aria-pressed={on}
      className={`admin-chip-button${on ? " admin-chip-button-active" : ""}`}
      onClick={onToggle}
      title={on ? t(lc, "autoRefreshOff") : t(lc, "autoRefreshOn")}
      type="button"
    >
      {on ? (
        <span className="dash-live">
          <span className="dash-live-dot" />
          <Pause size={11} style={{ verticalAlign: "-1px" }} />
          {t(lc, "auto30s")}
        </span>
      ) : (
        <span className="dash-live">
          <Play size={11} style={{ verticalAlign: "-1px" }} />
          {t(lc, "auto30s")}
        </span>
      )}
    </button>
  );
}

export function RecentActivity({ items }: { items: RecentItem[] }) {
  const { locale: lc } = useUi();
  if (!items.length) return <p className="dashboard-empty">{t(lc, "noMovements")}</p>;
  return (
    <div className="dash-recent-list">
      {items.map((it, i) => (
        <div className="dash-recent-item" key={`${it.at}-${i}`}>
          <span className="dash-recent-icon">
            {it.kind === "validation" ? <QrCode size={13} /> : <Ticket size={13} />}
          </span>
          <div className="dash-recent-body">
            <strong>{it.label || (it.kind === "validation" ? t(lc, "validation") : t(lc, "ticket"))}</strong>
            <span>{it.kind === "validation" ? t(lc, "validation") : t(lc, "ticket")} · {shortTime(it.at)}</span>
          </div>
          <span className="dash-recent-amount">{formatCurrency(it.amount)}</span>
        </div>
      ))}
    </div>
  );
}
