import { Pause, Play, QrCode, Ticket } from "lucide-react";
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
  const completion = k.trips_total ? Math.round((k.trips_completed / k.trips_total) * 100) : 0;
  return (
    <>
      <div className="admin-metric-grid">
        <MetricCard
          detail="M-Pesa, e-Mola e numerário recebidos"
          label="Entradas de dinheiro"
          value={formatCurrency(k.cash_in)}
        />
        <MetricCard
          detail="Bilhetes + validações — o dinheiro que virou viagem"
          label="Receita de transporte"
          value={formatCurrency(k.transport_revenue)}
        />
        <MetricCard
          detail={formatCurrency(k.ticket_revenue)}
          label="Bilhetes vendidos"
          value={formatCount(k.tickets_sold)}
        />
        <MetricCard
          detail={formatCurrency(k.validation_revenue)}
          label="Validações"
          value={formatCount(k.validations)}
        />
        <MetricCard
          detail="Receita de bilhetes ÷ bilhetes emitidos"
          label="Bilhete médio"
          value={formatCurrency(k.avg_ticket)}
        />
        <MetricCard
          detail="Saldo carregado — vira receita quando o passageiro viaja"
          label="Recargas"
          value={formatCurrency(k.topups_total)}
        />
        <MetricCard
          detail={`${formatCount(k.trips_completed)} concluídas · ${completion}%`}
          label="Viagens"
          value={formatCount(k.trips_total)}
        />
        <MetricCard
          detail={`${formatCount(packages.subscriptions)} subscrições no período`}
          label="Pacotes activos"
          value={formatCount(packages.active_now)}
        />
      </div>
      <p className="dash-kpi-note">
        <strong>Entradas de dinheiro</strong> são os pagamentos confirmados nos canais externos
        (M-Pesa, e-Mola, numerário), venham de recargas ou de bilhetes. <strong>Receita de
        transporte</strong> é o serviço já prestado: bilhetes + validações. Uma recarga é
        dinheiro recebido mas ainda em dívida ao passageiro — vira receita quando ele viaja,
        por isso somar as duas contaria o mesmo dinheiro duas vezes. <strong>Recargas</strong>
        mede o saldo creditado nas carteiras, que pode divergir das entradas quando há
        créditos feitos fora dos canais de pagamento.
      </p>
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Tabelas                                                             */
/* ------------------------------------------------------------------ */

const tripCols: TableColumn<TopTripRow>[] = [
  { header: "Viagem", render: (r) => <strong>#{r.trip_id}</strong> },
  { header: "Rota", render: (r) => r.route || "-" },
  { header: "Partida", render: (r) => (r.departure ? formatDateTime(r.departure) : "-") },
  { header: "Autocarro", render: (r) => r.vehicle || "-" },
  { header: "Motorista", render: (r) => r.driver || "-" },
  { header: "Passageiros", render: (r) => formatCount(r.passengers) },
  { header: "Receita", render: (r) => formatCurrency(r.revenue) },
];

const driverCols: TableColumn<TopDriverRow>[] = [
  { header: "Motorista", render: (r) => <strong>{r.name || `#${r.driver_id}`}</strong> },
  { header: "Viagens", render: (r) => formatCount(r.trips) },
  { header: "Concluídas", render: (r) => formatCount(r.completed) },
  { header: "Passageiros", render: (r) => formatCount(r.passengers) },
  { header: "Receita", render: (r) => formatCurrency(r.revenue) },
];

const agentCols: TableColumn<TopAgentRow>[] = [
  { header: "Agente", render: (r) => <strong>{r.name || `#${r.agent_id}`}</strong> },
  { header: "Vendas", render: (r) => formatCount(r.sales) },
  { header: "Receita", render: (r) => formatCurrency(r.revenue) },
];

const packageCols: TableColumn<PackagesBlock["by_package"][number]>[] = [
  { header: "Pacote", render: (r) => <strong>{r.name || "-"}</strong> },
  { header: "Subscrições", render: (r) => formatCount(r.count) },
  { header: "Receita", render: (r) => formatCurrency(r.revenue) },
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
  return <Compact columns={tripCols} empty="Sem viagens com bilhetes no intervalo." rowKey={(r) => String(r.trip_id)} rows={rows} />;
}

export function TopDriversTable({ rows }: { rows: TopDriverRow[] }) {
  return <Compact columns={driverCols} empty="Sem motoristas com viagens no intervalo." rowKey={(r) => String(r.driver_id)} rows={rows} />;
}

export function TopAgentsTable({ rows }: { rows: TopAgentRow[] }) {
  return <Compact columns={agentCols} empty="Sem vendas de agentes no intervalo." rowKey={(r) => String(r.agent_id)} rows={rows} />;
}

export function PackagesTable({ rows }: { rows: PackagesBlock["by_package"] }) {
  return <Compact columns={packageCols} empty="Sem subscrições de pacotes no intervalo." rowKey={(r) => r.name || "-"} rows={rows} />;
}

/* ------------------------------------------------------------------ */
/* Actividade recente                                                  */
/* ------------------------------------------------------------------ */

export function AutoRefreshToggle({ on, onToggle }: { on: boolean; onToggle: () => void }) {
  return (
    <button
      aria-pressed={on}
      className={`admin-chip-button${on ? " admin-chip-button-active" : ""}`}
      onClick={onToggle}
      title={on ? "Desligar actualização automática" : "Actualizar automaticamente a cada 30 segundos"}
      type="button"
    >
      {on ? (
        <span className="dash-live">
          <span className="dash-live-dot" />
          <Pause size={11} style={{ verticalAlign: "-1px" }} />
          Auto 30s
        </span>
      ) : (
        <span className="dash-live">
          <Play size={11} style={{ verticalAlign: "-1px" }} />
          Auto 30s
        </span>
      )}
    </button>
  );
}

export function RecentActivity({ items }: { items: RecentItem[] }) {
  if (!items.length) return <p className="dashboard-empty">Sem movimentos no intervalo seleccionado.</p>;
  return (
    <div className="dash-recent-list">
      {items.map((it, i) => (
        <div className="dash-recent-item" key={`${it.at}-${i}`}>
          <span className="dash-recent-icon">
            {it.kind === "validation" ? <QrCode size={13} /> : <Ticket size={13} />}
          </span>
          <div className="dash-recent-body">
            <strong>{it.label || (it.kind === "validation" ? "Validação" : "Bilhete")}</strong>
            <span>{it.kind === "validation" ? "Validação" : "Bilhete"} · {shortTime(it.at)}</span>
          </div>
          <span className="dash-recent-amount">{formatCurrency(it.amount)}</span>
        </div>
      ))}
    </div>
  );
}
