import { useCallback, useState } from "react";
import { Coins, Eye, FileSpreadsheet, FileText, RefreshCw, Search, X } from "lucide-react";
import { apiDownload, apiFetch } from "../lib/api";
import { showToast } from "../lib/toast";
import { formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { mensagemDeErro } from "../lib/errors";
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
    if (agentFilter) qs.set("q", agentFilter);
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

  // O token vai no cabecalho, nao no URL: um URL fica gravado no log do nginx
  // e no historico do browser, e ali ia o token de acesso completo.
  const exportReport = async (kind: "pdf" | "xlsx", scope: "session" | "summary", id?: number) => {
    let path: string;
    let name: string;
    if (scope === "session" && id) {
      path = `/api/agent/admin/day-closes/${id}/export.${kind}`;
      name = `fecho-${id}.${kind}`;
    } else {
      const qs = new URLSearchParams();
      if (dateFrom) qs.set("date_from", dateFrom);
      if (dateTo) qs.set("date_to", dateTo);
      path = `/api/agent/admin/revenue/export.${kind}?${qs.toString()}`;
      name = `receita-agentes.${kind}`;
    }
    try {
      await apiDownload(path, token!, name);
    } catch (e) {
      showToast("danger", mensagemDeErro(e, lc));
    }
  };

  const sessionColumns: TableColumn<DayCloseRow>[] = [
    {
      header: t(lc, "agent"),
      render: (r) => (
        <TablePrimaryCell
          title={r.agent_name || `Agente #${r.agent_id ?? "-"}`}
          subtitle={r.agent_phone || ""}
        />
      ),
    },
    { header: t(lc, "date"), render: (r) => r.date },
    { header: t(lc, "closedOn"), render: (r) => formatDateTime(r.closed_at) },
    { header: t(lc, "revenue"), render: (r) => `${fmt(r.total_revenue)} MZN` },
    { header: t(lc, "sales"), render: (r) => `${fmt(r.sales_total)} MZN` },
    { header: t(lc, "topUps"), render: (r) => `${fmt(r.topups_total)} MZN` },
    { header: t(lc, "validations"), render: (r) => `${fmt(r.validations_revenue)} MZN` },
    { header: t(lc, "tickets"), render: (r) => String(r.tickets_count) },
    {
      header: t(lc, "status"),
      render: (r) => (
        <span style={{ display: "inline-flex", gap: 4 }}>
          <StatusBadge value={r.confirmed_count > 0 ? "confirmed" : "neutral"} />
          {r.pending_count > 0 && <small>{r.pending_count} pend</small>}
          {r.failed_count > 0 && <small>{r.failed_count} fail</small>}
        </span>
      ),
    },
    {
      header: t(lc, "actions"),
      render: (r) => (
        <span style={{ display: "inline-flex", gap: 6 }}>
          <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => openDetail(r)} />
          <button className="admin-inline-button admin-inline-button-icon" type="button" onClick={() => void exportReport("pdf", "session", r.id)} title={t(lc, "exportPdf")}>
            <FileText size={15} />
          </button>
          <button className="admin-inline-button admin-inline-button-icon" type="button" onClick={() => void exportReport("xlsx", "session", r.id)} title={t(lc, "exportExcel")}>
            <FileSpreadsheet size={15} />
          </button>
        </span>
      ),
    },
  ];

  const agentColumns: TableColumn<AgentSummary>[] = [
    {
      header: t(lc, "agent"),
      render: (r) => (
        <TablePrimaryCell
          title={r.agent_name || `Agente #${r.agent_id ?? r.agent_user_id}`}
          subtitle={r.agent_phone || ""}
        />
      ),
    },
    { header: t(lc, "revenue"), render: (r) => `${fmt(r.total_revenue)} MZN` },
    { header: t(lc, "sales"), render: (r) => `${fmt(r.sales_total)} MZN` },
    { header: t(lc, "topUps"), render: (r) => `${fmt(r.topups_total)} MZN` },
    { header: t(lc, "validations"), render: (r) => `${fmt(r.validations_revenue)} MZN` },
    { header: t(lc, "tickets"), render: (r) => String(r.tickets) },
    { header: t(lc, "closures"), render: (r) => String(r.closes) },
  ];

  return (
    <PageFrame
      kicker={t(lc, "financial")}
      title={t(lc, "agentRevenue")}
      description={t(lc, "agentRevenueHint")}
      action={
        <>
          <button className="icon-text-button" onClick={reloadBoth} type="button">
            <RefreshCw size={15} /><span>{t(lc, "refresh")}</span>
          </button>
          <button className="icon-text-button" type="button" onClick={() => void exportReport("pdf", "summary")}>
            <FileText size={15} /><span>{t(lc, "summaryPdf")}</span>
          </button>
          <button className="icon-text-button" type="button" onClick={() => void exportReport("xlsx", "summary")}>
            <FileSpreadsheet size={15} /><span>{t(lc, "summaryExcel")}</span>
          </button>
        </>
      }
    >
      <SectionCard title={t(lc, "filters")} description={t(lc, "filtersHint")}>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "end" }}>
          <label className="field">
            <span>{t(lc, "from")}</span>
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </label>
          <label className="field">
            <span>{t(lc, "to")}</span>
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </label>
          <label className="field">
            <span>{t(lc, "search")}</span>
            {/* Era "ID do agente". Ninguem sabe de cor o id do motorista — a
                operacao fala destes fechos por nome e por rota. */}
            <input type="text" value={agentFilter} style={{ minWidth: 220 }}
              onChange={(e) => setAgentFilter(e.target.value)}
              placeholder={t(lc, "searchAgentHint")} />
          </label>
          <div style={{ display: "flex", gap: 8, paddingBottom: 6 }}>
            <button className="icon-text-button" onClick={reloadBoth} type="button">
              <Search size={15} /><span>{t(lc, "apply")}</span>
            </button>
            {agentFilter && (
              <button className="icon-text-button" onClick={() => setAgentFilter("")} type="button">
                <X size={15} /><span>{t(lc, "clear")}</span>
              </button>
            )}
          </div>
        </div>
      </SectionCard>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 12 }}>
        <MetricCard label={t(lc, "totalRevenue")} value={`${fmt(String(totals.total_revenue ?? "0"))} MZN`} />
        <MetricCard label={t(lc, "sales")} value={`${fmt(String(totals.sales_total ?? "0"))} MZN`} />
        <MetricCard label={t(lc, "topUps")} value={`${fmt(String(totals.topups_total ?? "0"))} MZN`} />
        <MetricCard label={t(lc, "validations")} value={`${fmt(String(totals.validations_revenue ?? "0"))} MZN`} />
        <MetricCard label={t(lc, "tickets")} value={String(totals.tickets ?? 0)} />
        <MetricCard label={t(lc, "activeAgents")} value={String(totals.agents_count ?? 0)} />
      </div>

      <TabBar
        items={[
          { key: "sessions", label: t(lc, "closuresToday"), count: sessionsList.length },
          { key: "agents", label: t(lc, "agentSummary"), count: agentsList.length },
        ]}
        value={tab}
        onChange={(k) => setTab(k as "sessions" | "agents")}
      />

      {tab === "sessions" && (
        <SectionCard title={t(lc, "closuresToday")} description={t(lc, "sessionsHint")}>
          <DataTable<DayCloseRow>
            columns={sessionColumns}
            rows={sessionsList}
            rowKey={(r) => String(r.id)}
            loading={loadingSessions}
            emptyMessage={t(lc, "noClosures")}
          />
        </SectionCard>
      )}

      {tab === "agents" && (
        <SectionCard title={t(lc, "agentSummaryHint")} description={`Periodo: ${revenue?.date_from || dateFrom} a ${revenue?.date_to || dateTo}`}>
          <DataTable<AgentSummary>
            columns={agentColumns}
            rows={agentsList}
            rowKey={(r) => String(r.agent_user_id)}
            loading={loadingRevenue}
            emptyMessage={t(lc, "noActivityPeriod")}
          />
        </SectionCard>
      )}

      <AdminModal
        open={detail !== null}
        onClose={() => setDetail(null)}
        title={detail ? `Sessao ${detail.date} - ${detail.agent_name || t(lc, "agent")}` : ""}
        description={detail ? `Fechada em ${formatDateTime(detail.closed_at)} | Receita: ${fmt(detail.total_revenue)} MZN` : ""}
      >
        {loadingDetail || !detail ? (
          <div className="admin-empty-state">{t(lc, "loading")}</div>
        ) : (
          <div style={{ display: "grid", gap: 16 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
              <MetricCard label={t(lc, "sales")} value={`${fmt(detail.sales_total)} MZN`} />
              <MetricCard label={t(lc, "topUps")} value={`${fmt(detail.topups_total)} MZN`} />
              <MetricCard label={t(lc, "validations")} value={`${fmt(detail.validations_revenue)} MZN`} />
              <MetricCard label={t(lc, "tickets")} value={String(detail.tickets_count)} />
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <button className="icon-text-button" type="button" onClick={() => void exportReport("pdf", "session", detail.id)}>
                <FileText size={15} /><span>{t(lc, "sessionPdf")}</span>
              </button>
              <button className="icon-text-button" type="button" onClick={() => void exportReport("xlsx", "session", detail.id)}>
                <FileSpreadsheet size={15} /><span>{t(lc, "sessionExcel")}</span>
              </button>
            </div>

            <SectionCard title={`Vendas (${(detail.payload.sales || []).length})`}>
              <DataTable<Record<string, unknown>>
                rows={detail.payload.sales || []}
                rowKey={(r) => String(r.reference || r.sale_reference || JSON.stringify(r))}
                loading={false}
                emptyMessage={t(lc, "noSales")}
                columns={[
                  { header: t(lc, "reference"), render: (r) => String(r.sale_reference || r.reference || "") },
                  { header: t(lc, "phone"), render: (r) => String(r.payer_phone_masked || "") },
                  { header: t(lc, "qty"), render: (r) => String(r.quantity ?? "-") },
                  { header: t(lc, "amount"), render: (r) => `${fmt(String(r.amount ?? "0"))} MZN` },
                  { header: t(lc, "status"), render: (r) => <StatusBadge value={String(r.status || "")} /> },
                ]}
              />
            </SectionCard>

            <SectionCard title={`Recargas (${(detail.payload.topups || []).length})`}>
              <DataTable<Record<string, unknown>>
                rows={detail.payload.topups || []}
                rowKey={(r) => String(r.reference || JSON.stringify(r))}
                loading={false}
                emptyMessage={t(lc, "noTopUps")}
                columns={[
                  { header: t(lc, "reference"), render: (r) => String(r.reference || "") },
                  { header: t(lc, "phone"), render: (r) => String(r.payer_phone_masked || "") },
                  { header: t(lc, "amount"), render: (r) => `${fmt(String(r.amount ?? "0"))} MZN` },
                  { header: t(lc, "status"), render: (r) => <StatusBadge value={String(r.status || "")} /> },
                ]}
              />
            </SectionCard>

            <SectionCard title={`Validacoes (${(detail.payload.validations || []).length})`}>
              <DataTable<Record<string, unknown>>
                rows={detail.payload.validations || []}
                rowKey={(r) => String(r.id || JSON.stringify(r))}
                loading={false}
                emptyMessage={t(lc, "noValidations")}
                columns={[
                  { header: t(lc, "type"), render: (r) => String(r.validation_type || "") },
                  { header: t(lc, "route"), render: (r) => String(r.route || "") },
                  { header: t(lc, "debit"), render: (r) => `${fmt(String(r.amount_debited ?? "0"))} MZN` },
                  { header: t(lc, "device"), render: (r) => String(r.device_serial || "") },
                  { header: t(lc, "status"), render: (r) => <StatusBadge value={String(r.status || "")} /> },
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
