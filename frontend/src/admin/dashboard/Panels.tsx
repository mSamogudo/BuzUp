import { Pause, Play, QrCode, Ticket } from "lucide-react";
import type { ReactNode } from "react";
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

/** Um numero por pergunta, e as perguntas agrupadas.
 *
 * Antes eram oito cartoes numa grelha lisa, quatro deles com dinheiro. Sem
 * hierarquia, «Entradas de dinheiro» e «Receita de transporte» leem-se como
 * duas respostas rivais a mesma pergunta. Nao sao: tem bases diferentes que se
 * CRUZAM em parte.
 *
 *   entradas = pagamentos externos confirmados (M-Pesa, e-Mola, numerario),
 *              venham de recarga ou de bilhete
 *   receita  = bilhetes + validacoes
 *
 * Um bilhete pago por M-Pesa esta nas duas. Uma validacao so esta na receita —
 * esse dinheiro entrou antes, na recarga. Uma recarga so esta nas entradas.
 * Nenhuma contem a outra, e somar as duas conta o mesmo dinheiro duas vezes.
 *
 * Isto ja estava escrito, numa nota de sessenta palavras debaixo dos oito
 * cartoes. Nao chegou: o cliente voltou a confundir-se, que e a prova. Uma
 * explicacao que so funciona se for lida nao e uma explicacao — a separacao
 * tem de estar no layout. Dai os grupos: cada numero fica debaixo da pergunta
 * a que responde, e a soma vem DEPOIS das suas parcelas, como numa factura. */
/** Quanto vale o que embarcou, e quanto disso foi cobrado a bordo.
 *
 * Sao numeros de natureza diferente e por isso nao se somam: o primeiro sao
 * bilhetes ja pagos na compra a passar pelo validador, o segundo e saldo a
 * sair na hora. Quem nao usa saldo — que e o caso de hoje — so ve o primeiro. */
function detalheDasValidacoes(lc: Locale, k: AnalyticsKpis): string {
  const partes: string[] = [];
  if (Number(k.validations_nominal) > 0) {
    partes.push(`${formatCurrency(k.validations_nominal)} ${t(lc, "boardedTickets")}`);
  }
  if (Number(k.validation_revenue) > 0) {
    partes.push(`${formatCurrency(k.validation_revenue)} ${t(lc, "chargedOnBoard")}`);
  }
  return partes.join(" · ") || t(lc, "noFareCollected");
}

/** A conta que forma a receita — mas so quando ha duas parcelas.
 *
 * Escrever «X em bilhetes + 0,00 cobrados a bordo» numa operacao que nao usa
 * saldo e ruido: convida a procurar um numero que nunca vai existir. */
function detalheDaReceita(lc: Locale, k: AnalyticsKpis): string {
  if (Number(k.validation_revenue) > 0) {
    return `${formatCurrency(k.ticket_revenue)} ${t(lc, "inTickets")} + `
      + `${formatCurrency(k.validation_revenue)} ${t(lc, "chargedOnBoard")}`;
  }
  return `${formatCurrency(k.ticket_revenue)} ${t(lc, "inTicketsOnly")}`;
}

function KpiGroup({ title, hint, children }: { title: string; hint: string; children: ReactNode }) {
  return (
    <section className="dash-kpi-group">
      <header className="dash-kpi-group-head">
        <h3>{title}</h3>
        <span>{hint}</span>
      </header>
      <div className="admin-metric-grid">{children}</div>
    </section>
  );
}

export function KpiStrip({ k, packages }: { k: AnalyticsKpis; packages: PackagesBlock }) {
  const { locale: lc } = useUi();
  const completion = k.trips_total ? Math.round((k.trips_completed / k.trips_total) * 100) : 0;
  return (
    <>
      {/* Caixa: o que reconcilia com o extracto do M-Pesa, do e-Mola e do cofre. */}
      <KpiGroup hint={t(lc, "kpiGroupCashHint")} title={t(lc, "kpiGroupCash")}>
        <MetricCard
          detail={t(lc, "cashInHint")}
          label={t(lc, "cashIn")}
          value={formatCurrency(k.cash_in)}
        />
        <MetricCard
          detail={t(lc, "topUpsHint")}
          label={t(lc, "topUps")}
          value={formatCurrency(k.topups_total)}
        />
      </KpiGroup>

      {/* Servico: o que a operacao entregou. Nao e dinheiro novo. */}
      <KpiGroup hint={t(lc, "kpiGroupServiceHint")} title={t(lc, "kpiGroupService")}>
        <MetricCard
          detail={formatCurrency(k.ticket_revenue)}
          label={t(lc, "ticketsSoldLabel")}
          value={formatCount(k.tickets_sold)}
        />
        {/* Validacoes sao EMBARQUES, nao vendas. Mostrar aqui o
            `validation_revenue` fazia o cartao parecer uma segunda receita —
            e para quem nao usa saldo, como a TPM-TUR, mostraria 0,00 ao lado
            de sete embarques reais. O que importa e o valor que embarcou. */}
        <MetricCard
          detail={detalheDasValidacoes(lc, k)}
          label={t(lc, "validations")}
          value={formatCount(k.validations)}
        />
        {/* A conta VISIVEL, e a seguir as parcelas que a formam. O cliente
            comparou este numero com o total do relatorio de vendas e encontrou
            10 900,00 MZN de diferenca — eram as validacoes, somadas aqui e
            ausentes de la. Ver as duas parcelas deixa fazer a conta de cabeca. */}
        <MetricCard
          detail={detalheDaReceita(lc, k)}
          label={t(lc, "transportRevenue")}
          value={formatCurrency(k.transport_revenue)}
        />
        <MetricCard
          detail={t(lc, "averageTicketHint")}
          label={t(lc, "averageTicket")}
          value={formatCurrency(k.avg_ticket)}
        />
      </KpiGroup>

      <KpiGroup hint={t(lc, "kpiGroupOpsHint")} title={t(lc, "kpiGroupOps")}>
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
      </KpiGroup>

      {/* O unico aviso que sobra: o erro que se pode mesmo cometer. */}
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
