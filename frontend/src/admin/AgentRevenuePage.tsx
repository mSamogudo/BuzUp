import { useCallback, useState } from "react";
import { Coins, Eye, FileSpreadsheet, FileText, RefreshCw, Search, X } from "lucide-react";
import { apiFetch } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import {
  AdminModal,
  DataTable,
  MetricCard,
  PageFrame,
  SectionCard,
  StatusBadge,
  TabBar,
  TableActionButton,
  TablePrimaryCell,
  useAsyncData,
  type TableColumn,
} from "../ui/common";

interface DayCloseRow {
  id: number;
  uuid: string;
  agent_id: number | null;
  agent_name: string;
  agent_phone: string;
  date: string;
  closed_at: string;
  total_revenue: string;
  sales_total: string;
  topups_total: string;
  validations_revenue: string;
  tickets_count: number;
  validations_count: number;
  confirmed_count: number;
  pending_count: number;
  failed_count: number;
  sessions_closed: number;
}

interface AgentSummary {
  agent_id: number | null;
  agent_user_id: number;
  agent_name: string;
  agent_phone: string;
  total_revenue: string;
  sales_total: string;
  topups_total: string;
  validations_revenue: string;
  tickets: number;
  validations: number;
  closes: number;
}

interface DayCloseDetail extends DayCloseRow {
  payload: {
    sales?: Array<Record<string, unknown>>;
    topups?: Array<Record<string, unknown>>;
    validations?: Array<Record<string, unknown>>;
    totals?: Record<string, unknown>;
  };
}

interface RevenueResponse {
  totals: Record<string, unknown>;
  agents: AgentSummary[];
  date_from: string;
  date_to: string;
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}
function daysAgoISO(d: number) {
  const dt = new Date();
  dt.setDate(dt.getDate() - d);
  return dt.toISOString().slice(0, 10);
}
function fmt(v: string | number | undefined) {
  const n = Number(v ?? 0);
  return n.toLocaleString("pt-PT", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function AgentRevenuePage() {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const [tab, setTab] = useState<"sessions" | "agents">("sessions");
  const [dateFrom, setDateFrom] = useState(daysAgoISO(30));
  const [dateTo, setDateTo] = useState(todayISO());
  const [agentFilter, setAgentFilter] = useState<string>("");
  const [detail, setDetail] = useState<DayCloseDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const sessionsLoader = useCallback(async () => {
    const qs = new URLSearchParams();
    if (dateFrom) qs.set("date_from", dateFrom);
    if (dateTo) qs.set("date_to", dateTo);
    if (agentFilter) qs.set("agent_id", agentFilter);
    const r = await apiFetch(`/api/agent/admin/day-closes/?${qs.toString()}`, token!);
    return (r?.results || []) as DayCloseRow[];
  }, [token, dateFrom, dateTo, agentFilter]);

  const revenueLoader = useCallback(async () => {
    const qs = new URLSearchParams();
    if (dateFrom) qs.set("date_from", dateFrom);
    if (dateTo) qs.set("date_to", dateTo);
    const r = await apiFetch(`/api/agent/admin/revenue/?${qs.toString()}`, token!);
    return r as RevenueResponse;
  }, [token, dateFrom, dateTo]);

  const { data: sessions, loading: loadingSessions, reload: reloadSessions } = useAsyncData<DayCloseRow[]>(sessionsLoader, [token, dateFrom, dateTo, agentFilter]);
  const { data: revenue, loading: loadingRevenue, reload: reloadRevenue } = useAsyncData<RevenueResponse>(revenueLoader, [token, dateFrom, dateTo]);

  const reloadBoth = () => { reloadSessions(); reloadRevenue(); };

  const totals = revenue?.totals || {};
  const agentsList = revenue?.agents || [];
  const sessionsList = sessions || [];

  const openDetail = async (row: DayCloseRow) => {
    setLoadingDetail(true);
    try {
      const r = await apiFetch(`/api/agent/admin/day-closes/${row.id}/`, token!);
      setDetail(r as DayCloseDetail);
    } finally {
      setLoadingDetail(false);
    }
  };

  const exportUrl = (kind: "pdf" | "xlsx", scope: "session" | "summary", id?: number) => {
    if (scope === "session" && id) return `/api/agent/admin/day-closes/${id}/export.${kind}?token=${encodeURIComponent(token || "")}`;
    const qs = new URLSearchParams();
    if (dateFrom) qs.set("date_from", dateFrom);
    if (dateTo) qs.set("date_to", dateTo);
    qs.set("token", token || "");
    return `/api/agent/admin/revenue/export.${kind}?${qs.toString()}`;
  };

  const sessionColumns: TableColumn<DayCloseRow>[] = [
    {
      header: "Agente",
      render: (r) => (
        <TablePrimaryCell
          title={r.agent_name || `Agente #${r.agent_id ?? "-"}`}
          subtitle={r.agent_phone || ""}
        />
      ),
    },
    { header: "Data", render: (r) => r.date },
    { header: "Fechado em", render: (r) => formatDateTime(r.closed_at) },
    { header: "Receita", render: (r) => `${fmt(r.total_revenue)} MZN` },
    { header: "Vendas", render: (r) => `${fmt(r.sales_total)} MZN` },
    { header: "Recargas", render: (r) => `${fmt(r.topups_total)} MZN` },
    { header: "Validacoes", render: (r) => `${fmt(r.validations_revenue)} MZN` },
    { header: "Bilhetes", render: (r) => String(r.tickets_count) },
    {
      header: "Estado",
      render: (r) => (
        <span style={{ display: "inline-flex", gap: 4 }}>
          <StatusBadge value={r.confirmed_count > 0 ? "confirmed" : "neutral"} />
          {r.pending_count > 0 && <small>{r.pending_count} pend</small>}
          {r.failed_count > 0 && <small>{r.failed_count} fail</small>}
        </span>
      ),
    },
    {
      header: "Acoes",
      render: (r) => (
        <span style={{ display: "inline-flex", gap: 6 }}>
          <TableActionButton icon={<Eye size={15} />} label="Ver" onClick={() => openDetail(r)} />
          <a className="admin-inline-button admin-inline-button-icon" href={exportUrl("pdf", "session", r.id)} target="_blank" rel="noreferrer" title="Exportar PDF">
            <FileText size={15} />
          </a>
          <a className="admin-inline-button admin-inline-button-icon" href={exportUrl("xlsx", "session", r.id)} target="_blank" rel="noreferrer" title="Exportar Excel">
            <FileSpreadsheet size={15} />
          </a>
        </span>
      ),
    },
  ];

  const agentColumns: TableColumn<AgentSummary>[] = [
    {
      header: "Agente",
      render: (r) => (
        <TablePrimaryCell
          title={r.agent_name || `Agente #${r.agent_id ?? r.agent_user_id}`}
          subtitle={r.agent_phone || ""}
        />
      ),
    },
    { header: "Receita", render: (r) => `${fmt(r.total_revenue)} MZN` },
    { header: "Vendas", render: (r) => `${fmt(r.sales_total)} MZN` },
    { header: "Recargas", render: (r) => `${fmt(r.topups_total)} MZN` },
    { header: "Validacoes", render: (r) => `${fmt(r.validations_revenue)} MZN` },
    { header: "Bilhetes", render: (r) => String(r.tickets) },
    { header: "Fechos", render: (r) => String(r.closes) },
  ];

  return (
    <PageFrame
      kicker={t(lc, "financial")}
      title={t(lc, "agentRevenue")}
      description="Acompanhe a receita por agente, exporte PDF/Excel e veja o detalhe de cada fecho de caixa."
      action={
        <>
          <button className="icon-text-button" onClick={reloadBoth} type="button">
            <RefreshCw size={15} /><span>Actualizar</span>
          </button>
          <a className="icon-text-button" href={exportUrl("pdf", "summary")} target="_blank" rel="noreferrer">
            <FileText size={15} /><span>PDF Resumo</span>
          </a>
          <a className="icon-text-button" href={exportUrl("xlsx", "summary")} target="_blank" rel="noreferrer">
            <FileSpreadsheet size={15} /><span>Excel Resumo</span>
          </a>
        </>
      }
    >
      <SectionCard title="Filtros" description="Defina o intervalo e (opcional) o agente.">
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "end" }}>
          <label className="field">
            <span>De</span>
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </label>
          <label className="field">
            <span>Ate</span>
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </label>
          <label className="field">
            <span>ID do agente (opcional)</span>
            <input type="text" value={agentFilter} onChange={(e) => setAgentFilter(e.target.value)} placeholder="Ex.: 12" />
          </label>
          <div style={{ display: "flex", gap: 8, paddingBottom: 6 }}>
            <button className="icon-text-button" onClick={reloadBoth} type="button">
              <Search size={15} /><span>Aplicar</span>
            </button>
            {agentFilter && (
              <button className="icon-text-button" onClick={() => setAgentFilter("")} type="button">
                <X size={15} /><span>Limpar</span>
              </button>
            )}
          </div>
        </div>
      </SectionCard>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 12 }}>
        <MetricCard label="Receita total" value={`${fmt(String(totals.total_revenue ?? "0"))} MZN`} />
        <MetricCard label="Vendas" value={`${fmt(String(totals.sales_total ?? "0"))} MZN`} />
        <MetricCard label="Recargas" value={`${fmt(String(totals.topups_total ?? "0"))} MZN`} />
        <MetricCard label="Validacoes" value={`${fmt(String(totals.validations_revenue ?? "0"))} MZN`} />
        <MetricCard label="Bilhetes" value={String(totals.tickets ?? 0)} />
        <MetricCard label="Agentes activos" value={String(totals.agents_count ?? 0)} />
      </div>

      <TabBar
        items={[
          { key: "sessions", label: "Fechos do dia", count: sessionsList.length },
          { key: "agents", label: "Resumo por agente", count: agentsList.length },
        ]}
        value={tab}
        onChange={(k) => setTab(k as "sessions" | "agents")}
      />

      {tab === "sessions" && (
        <SectionCard title="Fechos do dia" description="Cada linha representa uma sessao fechada por um agente.">
          <DataTable<DayCloseRow>
            columns={sessionColumns}
            rows={sessionsList}
            rowKey={(r) => String(r.id)}
            loading={loadingSessions}
            emptyMessage="Sem fechos no intervalo seleccionado."
          />
        </SectionCard>
      )}

      {tab === "agents" && (
        <SectionCard title="Resumo agregado por agente" description={`Periodo: ${revenue?.date_from || dateFrom} a ${revenue?.date_to || dateTo}`}>
          <DataTable<AgentSummary>
            columns={agentColumns}
            rows={agentsList}
            rowKey={(r) => String(r.agent_user_id)}
            loading={loadingRevenue}
            emptyMessage="Sem actividade no periodo."
          />
        </SectionCard>
      )}

      <AdminModal
        open={detail !== null}
        onClose={() => setDetail(null)}
        title={detail ? `Sessao ${detail.date} - ${detail.agent_name || "Agente"}` : ""}
        description={detail ? `Fechada em ${formatDateTime(detail.closed_at)} | Receita: ${fmt(detail.total_revenue)} MZN` : ""}
      >
        {loadingDetail || !detail ? (
          <div className="admin-empty-state">A carregar...</div>
        ) : (
          <div style={{ display: "grid", gap: 16 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
              <MetricCard label="Vendas" value={`${fmt(detail.sales_total)} MZN`} />
              <MetricCard label="Recargas" value={`${fmt(detail.topups_total)} MZN`} />
              <MetricCard label="Validacoes" value={`${fmt(detail.validations_revenue)} MZN`} />
              <MetricCard label="Bilhetes" value={String(detail.tickets_count)} />
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <a className="icon-text-button" href={exportUrl("pdf", "session", detail.id)} target="_blank" rel="noreferrer">
                <FileText size={15} /><span>PDF da sessao</span>
              </a>
              <a className="icon-text-button" href={exportUrl("xlsx", "session", detail.id)} target="_blank" rel="noreferrer">
                <FileSpreadsheet size={15} /><span>Excel da sessao</span>
              </a>
            </div>

            <SectionCard title={`Vendas (${(detail.payload.sales || []).length})`}>
              <DataTable<Record<string, unknown>>
                rows={detail.payload.sales || []}
                rowKey={(r) => String(r.reference || r.sale_reference || JSON.stringify(r))}
                loading={false}
                emptyMessage="Sem vendas."
                columns={[
                  { header: "Referencia", render: (r) => String(r.sale_reference || r.reference || "") },
                  { header: "Telefone", render: (r) => String(r.payer_phone_masked || "") },
                  { header: "Qtd", render: (r) => String(r.quantity ?? "-") },
                  { header: "Valor", render: (r) => `${fmt(String(r.amount ?? "0"))} MZN` },
                  { header: "Estado", render: (r) => <StatusBadge value={String(r.status || "")} /> },
                ]}
              />
            </SectionCard>

            <SectionCard title={`Recargas (${(detail.payload.topups || []).length})`}>
              <DataTable<Record<string, unknown>>
                rows={detail.payload.topups || []}
                rowKey={(r) => String(r.reference || JSON.stringify(r))}
                loading={false}
                emptyMessage="Sem recargas."
                columns={[
                  { header: "Referencia", render: (r) => String(r.reference || "") },
                  { header: "Telefone", render: (r) => String(r.payer_phone_masked || "") },
                  { header: "Valor", render: (r) => `${fmt(String(r.amount ?? "0"))} MZN` },
                  { header: "Estado", render: (r) => <StatusBadge value={String(r.status || "")} /> },
                ]}
              />
            </SectionCard>

            <SectionCard title={`Validacoes (${(detail.payload.validations || []).length})`}>
              <DataTable<Record<string, unknown>>
                rows={detail.payload.validations || []}
                rowKey={(r) => String(r.id || JSON.stringify(r))}
                loading={false}
                emptyMessage="Sem validacoes."
                columns={[
                  { header: "Tipo", render: (r) => String(r.validation_type || "") },
                  { header: "Rota", render: (r) => String(r.route || "") },
                  { header: "Debito", render: (r) => `${fmt(String(r.amount_debited ?? "0"))} MZN` },
                  { header: "Dispositivo", render: (r) => String(r.device_serial || "") },
                  { header: "Estado", render: (r) => <StatusBadge value={String(r.status || "")} /> },
                ]}
              />
            </SectionCard>
          </div>
        )}
      </AdminModal>

      <Coins style={{ display: "none" }} />
    </PageFrame>
  );
}
