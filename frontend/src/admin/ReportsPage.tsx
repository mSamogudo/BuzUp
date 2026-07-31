import { useCallback, useEffect, useMemo, useState } from "react";
import { Download, FileSpreadsheet, FileText, RefreshCw, Search, Sliders } from "lucide-react";
import { apiDownload, apiFetch } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { DataTable, MetricCard, PageFrame, SectionCard, StatusBadge, TabBar, TablePrimaryCell, useAsyncData, type TableColumn } from "../ui/common";
import { SkeletonCard } from "../ui/Skeleton";

interface RevenueData {
  validations: { total_count: number; total_revenue: string; by_route: { route__code: string; route__name: string; count: number; total: string }[] };
  topups: { count: number; total: string };
}
interface ReconData {
  payments: { confirmed: { count: number; total: string }; pending: { count: number; total: string }; failed: { count: number; total: string } };
  wallet_transactions: { topups: { count: number; total: string }; fare_debits: { count: number; total: string } };
  guest_checkouts: { passes_issued: number; passes_used: number; passes_active: number };
  circulation: { total_balance: string; negative_wallets: number };
}

interface OpTripSummary {
  guest_checkout: { count: number; tickets: number; revenue: string };
  app_passes: { count: number; revenue: string };
  wallet_validations: { count: number; revenue: string };
  direct_payments: { count: number; revenue: string };
  validations: { approved: number; denied: number };
  total_revenue: string;
}
interface OpTripRow {
  trip_id: number; route_id: number; route_code: string; route_name: string;
  vehicle_id: number | null; vehicle_registration: string;
  driver_id: number | null; driver_name: string; status: string;
  opened_at: string | null; closed_at: string | null; pause_seconds: number;
  summary: OpTripSummary;
}
interface OperationalData {
  period: { from: string; to: string };
  totals: {
    guest_checkout_revenue: string; app_pass_revenue: string;
    wallet_validation_revenue: string; direct_payment_revenue: string;
    total_revenue: string; validations_approved: number; validations_denied: number;
  };
  by_vehicle: { vehicle_id: number | null; vehicle_registration: string; trips: number; total_revenue: string }[];
  by_route: { route_id: number; route_code: string; route_name: string; trips: number; total_revenue: string }[];
  trips: OpTripRow[];
}
interface ValidationsData {
  period: { from: string; to: string };
  by_status: { status: string; count: number }[];
  by_type: { validation_type: string; count: number }[];
  by_failure_reason: { failure_reason: string; count: number }[];
  by_device: { device__serial_number: string; device__device_type: string; count: number; approved: number; revenue: string | null }[];
}

interface ReportSpec { key: string; title: string; columns: { key: string; label: string }[]; }
interface ReportResult {
  kind: string; title: string; period_from: string; period_to: string;
  totals: Record<string, string | number>;
  columns: { key: string; label: string }[];
  rows: Record<string, unknown>[];
  row_count: number; truncated: boolean;
  /** A consulta bateu no tecto: ha movimentos que nem sequer foram lidos. */
  row_limit_reached?: boolean; row_limit?: number;
}
interface Lookup { id: number; full_name?: string; name?: string; code?: string; phone_number?: string; }

function todayISO() { return new Date().toISOString().slice(0, 10); }
function daysAgoISO(d: number) { const dt = new Date(); dt.setDate(dt.getDate() - d); return dt.toISOString().slice(0, 10); }

export default function ReportsPage({ embedded }: { embedded?: boolean }) {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const revLoader = useCallback(() => apiFetch("/api/admin/reports/revenue/", token!), [token]);
  const reconLoader = useCallback(() => apiFetch("/api/admin/reconciliation/payments/", token!), [token]);
  const { data: rev, loading: loadingR, reload: reloadR } = useAsyncData<RevenueData>(revLoader, [token]);
  const { data: recon, loading: loadingC, reload: reloadC } = useAsyncData<ReconData>(reconLoader, [token]);
  const [tab, setTab] = useState<"builder" | "revenue" | "recon" | "operational" | "validations">("builder");

  // -------- Receita operacional (/api/admin/reports/operational-revenue/) --------
  const [opFrom, setOpFrom] = useState(todayISO());
  const [opTo, setOpTo] = useState(todayISO());
  const [opRouteId, setOpRouteId] = useState("");
  const opLoader = useCallback(() => {
    const qs = new URLSearchParams();
    if (opFrom) qs.set("date_from", opFrom);
    if (opTo) qs.set("date_to", opTo);
    if (opRouteId) qs.set("route_id", opRouteId);
    return apiFetch(`/api/admin/reports/operational-revenue/?${qs.toString()}`, token!);
  }, [token, opFrom, opTo, opRouteId]);
  const { data: op, loading: loadingOp, reload: reloadOp } = useAsyncData<OperationalData>(opLoader, [token]);

  // -------- Validacoes (/api/admin/reports/validations/) --------
  const [valFrom, setValFrom] = useState(todayISO());
  const [valTo, setValTo] = useState(todayISO());
  const [valRouteId, setValRouteId] = useState("");
  const valLoader = useCallback(() => {
    const qs = new URLSearchParams();
    if (valFrom) qs.set("date_from", valFrom);
    if (valTo) qs.set("date_to", valTo);
    if (valRouteId) qs.set("route_id", valRouteId);
    return apiFetch(`/api/admin/reports/validations/?${qs.toString()}`, token!);
  }, [token, valFrom, valTo, valRouteId]);
  const { data: val, loading: loadingV, reload: reloadV } = useAsyncData<ValidationsData>(valLoader, [token]);

  const reload = () => { reloadR(); reloadC(); reloadOp(); reloadV(); };

  // -------- Report builder state --------
  const [specs, setSpecs] = useState<ReportSpec[]>([]);
  const [kind, setKind] = useState<string>("sales");
  const [dateFrom, setDateFrom] = useState(daysAgoISO(7));
  const [dateTo, setDateTo] = useState(todayISO());
  const [status, setStatus] = useState<string>("");
  const [agentId, setAgentId] = useState<string>("");
  const [routeId, setRouteId] = useState<string>("");
  const [passengerId, setPassengerId] = useState<string>("");
  const [source, setSource] = useState<string>("");
  const [extraKind, setExtraKind] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ReportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [specsLoading, setSpecsLoading] = useState(true);

  // -------- Lookup state (dropdown options) --------
  const [routes, setRoutes] = useState<Lookup[]>([]);
  const [agents, setAgents] = useState<Lookup[]>([]);
  const [passengers, setPassengers] = useState<Lookup[]>([]);
  const [agentSearch, setAgentSearch] = useState("");
  const [passengerSearch, setPassengerSearch] = useState("");

  useEffect(() => {
    if (!token) return;
    setSpecsLoading(true);
    apiFetch("/api/admin/reports/builder/", token).then((d) => {
      setSpecs((d.reports || []) as ReportSpec[]);
      setSpecsLoading(false);
    }).catch((e) => {
      setError(e instanceof Error ? e.message : "Erro a carregar tipos de relatorio.");
      setSpecsLoading(false);
    });
    // Lazy-fetch lookups in parallel; failures are silent (filters stay empty).
    apiFetch("/api/routes/", token).then((d) => setRoutes(d.results || d)).catch(() => {});
    apiFetch("/api/agents/", token).then((d) => setAgents(d.results || d)).catch(() => {});
    apiFetch("/api/passengers/", token).then((d) => setPassengers(d.results || d)).catch(() => {});
  }, [token]);

  const filteredAgents = useMemo(() => {
    const q = agentSearch.trim().toLowerCase();
    if (!q) return agents.slice(0, 100);
    return agents.filter((a) =>
      (a.full_name || "").toLowerCase().includes(q) ||
      (a.phone_number || "").toLowerCase().includes(q) ||
      String(a.id).includes(q)).slice(0, 100);
  }, [agents, agentSearch]);

  const filteredPassengers = useMemo(() => {
    const q = passengerSearch.trim().toLowerCase();
    if (!q) return passengers.slice(0, 100);
    return passengers.filter((p) =>
      (p.full_name || "").toLowerCase().includes(q) ||
      (p.phone_number || "").toLowerCase().includes(q) ||
      String(p.id).includes(q)).slice(0, 100);
  }, [passengers, passengerSearch]);

  const currentSpec = useMemo(() => specs.find((s) => s.key === kind), [specs, kind]);

  const buildQS = () => {
    const qs = new URLSearchParams();
    if (dateFrom) qs.set("date_from", dateFrom);
    if (dateTo) qs.set("date_to", dateTo);
    if (status) qs.set("status", status);
    if (agentId) qs.set("agent_user_id", agentId);
    if (routeId) qs.set("route_id", routeId);
    if (passengerId) qs.set("passenger_id", passengerId);
    if (source) qs.set("source", source);
    if (extraKind) qs.set("kind", extraKind);
    return qs.toString();
  };

  const clearFilters = () => {
    setStatus("");
    setAgentId("");
    setRouteId("");
    setPassengerId("");
    setSource("");
    setExtraKind("");
    setAgentSearch("");
    setPassengerSearch("");
  };

  const runReport = async () => {
    setRunning(true);
    setError(null);
    try {
      const r = await apiFetch(`/api/admin/reports/builder/${kind}/?${buildQS()}`, token!);
      setResult(r as ReportResult);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro a gerar relatorio.");
    } finally { setRunning(false); }
  };

  // Descarga com o token no cabecalho, nao no URL: o URL fica gravado no log
  // do nginx e no historico do browser, e o que la ficava era o token de
  // acesso completo.
  const exportReport = async (format: "pdf" | "xlsx") => {
    const qs = new URLSearchParams(buildQS());
    qs.set("output", format);
    try {
      await apiDownload(
        `/api/admin/reports/builder/${kind}/?${qs.toString()}`,
        token!,
        `relatorio-${kind}.${format}`,
      );
    } catch (e) {
      showToast("danger", e instanceof Error ? e.message : "Erro ao exportar.");
    }
  };

  const formatCell = (key: string, value: unknown): string => {
    if (value === null || value === undefined) return "-";
    if (key.endsWith("amount") || key.endsWith("debited") || key === "total") {
      return `${formatCurrency(String(value))} MZN`;
    }
    if (key === "created_at" && typeof value === "string") {
      return value.replace("T", " ").substring(0, 16);
    }
    return String(value);
  };

  const builderColumns: TableColumn<Record<string, unknown>>[] = useMemo(() => {
    const cols = result?.columns ?? currentSpec?.columns ?? [];
    return cols.map((c) => ({
      header: c.label,
      render: (row) => {
        const v = row[c.key];
        if (c.key === "status") {
          return <StatusBadge value={String(v ?? "")} />;
        }
        return formatCell(c.key, v);
      },
    }));
  }, [result, currentSpec]);

  return (
    <PageFrame kicker={t(lc, "financial")} title={t(lc, "reports")}
      action={
        <div className="admin-page-actions">
          <button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={16} /><span>{t(lc, "refresh")}</span></button>
          <a className="icon-text-button" href="/api/admin/exports/validations/" target="_blank" rel="noreferrer"><Download size={16} /><span>{t(lc, "exportValidationsCsv")}</span></a>
          <a className="icon-text-button" href="/api/admin/exports/transactions/" target="_blank" rel="noreferrer"><Download size={16} /><span>{t(lc, "exportTransactionsCsv")}</span></a>
        </div>
      }>
      <TabBar items={[
        { key: "builder", label: "Gerador de relatorios" },
        { key: "revenue", label: t(lc, "revenueToday") },
        { key: "operational", label: "Receita operacional" },
        { key: "validations", label: "Validacoes" },
        { key: "recon", label: t(lc, "reconciliation") },
      ]} value={tab} onChange={(k) => setTab(k as "builder" | "revenue" | "recon" | "operational" | "validations")} />

      {tab === "builder" && (
        <SectionCard
          title="Gerador de relatorios premium"
          description="Escolha o tipo de relatorio, defina filtros, visualize a pre-visualizacao e descarregue em PDF ou Excel com a identidade da plataforma."
        >
          {error && (
            <div style={{
              padding: "10px 14px", marginBottom: 14,
              background: "rgba(239,68,68,0.10)", border: "1px solid rgba(239,68,68,0.30)",
              borderRadius: 8, color: "#b91c1c", fontSize: 13,
            }}>{error}</div>
          )}
          {specsLoading && (
            <div className="admin-empty-state">A carregar tipos de relatorio...</div>
          )}
          {!specsLoading && specs.length === 0 && (
            <div className="admin-empty-state">
              Nao foi possivel carregar os tipos de relatorio. Verifique permissoes (reports.read) ou recarregue a pagina.
            </div>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 10 }}>
            <label className="field">
              <span>Tipo de relatorio</span>
              <select value={kind} onChange={(e) => { setKind(e.target.value); setResult(null); }}>
                {specs.length === 0 && <option value="">(nenhum disponivel)</option>}
                {specs.map((s) => <option key={s.key} value={s.key}>{s.title}</option>)}
              </select>
            </label>
            <label className="field"><span>De</span>
              <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} /></label>
            <label className="field"><span>Ate</span>
              <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} /></label>
            <label className="field"><span>Estado</span>
              <select value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="">Todos</option>
                <option value="confirmed">Confirmado</option>
                <option value="pending">Pendente</option>
                <option value="failed">Falhado</option>
                <option value="expired">Expirado</option>
                <option value="reversed">Revertido</option>
                <option value="approved">Aprovado</option>
                <option value="denied">Negado</option>
                <option value="active">Activo</option>
                <option value="used">Usado</option>
              </select>
            </label>
            <label className="field"><span>Origem</span>
              <select value={source} onChange={(e) => setSource(e.target.value)}>
                <option value="">Todas</option>
                <option value="MOBILE">App passageiro</option>
                <option value="POS">POS agente</option>
                <option value="PORTAL">Portal/convidado</option>
              </select>
            </label>
            <label className="field"><span>Rota</span>
              <select value={routeId} onChange={(e) => setRouteId(e.target.value)}>
                <option value="">Todas as rotas ({routes.length})</option>
                {routes.map((r) => (
                  <option key={r.id} value={r.id}>{r.code ? `${r.code} · ${r.name}` : r.name}</option>
                ))}
              </select>
            </label>
            <label className="field" style={{ position: "relative" }}>
              <span>Agente</span>
              <input
                type="text"
                value={agentId
                  ? (agents.find((a) => String(a.id) === agentId)?.full_name || `#${agentId}`)
                  : agentSearch}
                placeholder={`Buscar entre ${agents.length} agentes...`}
                onChange={(e) => {
                  setAgentSearch(e.target.value);
                  if (agentId) setAgentId("");
                }}
              />
              {agentSearch && !agentId && filteredAgents.length > 0 && (
                <div style={{
                  position: "absolute", top: "100%", left: 0, right: 0, zIndex: 10,
                  background: "var(--app-surface, #fff)", border: "1px solid var(--app-border, #ddd)",
                  borderRadius: 6, maxHeight: 200, overflowY: "auto",
                  boxShadow: "0 8px 24px rgba(0,0,0,0.08)",
                }}>
                  {filteredAgents.map((a) => (
                    <div key={a.id}
                      onClick={() => { setAgentId(String(a.id)); setAgentSearch(""); }}
                      style={{ padding: "8px 12px", cursor: "pointer", fontSize: 13, borderBottom: "1px solid var(--app-border, #eee)" }}>
                      <strong>{a.full_name || `Agente #${a.id}`}</strong>
                      {a.phone_number && <span style={{ marginLeft: 8, color: "#888", fontSize: 11 }}>{a.phone_number}</span>}
                    </div>
                  ))}
                </div>
              )}
              {agentId && (
                <button type="button" onClick={() => { setAgentId(""); setAgentSearch(""); }}
                  style={{ position: "absolute", right: 6, top: 28, background: "none", border: "none", cursor: "pointer", color: "#999", fontSize: 16 }}>×</button>
              )}
            </label>
            <label className="field" style={{ position: "relative" }}>
              <span>Passageiro</span>
              <input
                type="text"
                value={passengerId
                  ? (passengers.find((p) => String(p.id) === passengerId)?.full_name || `#${passengerId}`)
                  : passengerSearch}
                placeholder={`Buscar entre ${passengers.length} passageiros...`}
                onChange={(e) => {
                  setPassengerSearch(e.target.value);
                  if (passengerId) setPassengerId("");
                }}
              />
              {passengerSearch && !passengerId && filteredPassengers.length > 0 && (
                <div style={{
                  position: "absolute", top: "100%", left: 0, right: 0, zIndex: 10,
                  background: "var(--app-surface, #fff)", border: "1px solid var(--app-border, #ddd)",
                  borderRadius: 6, maxHeight: 200, overflowY: "auto",
                  boxShadow: "0 8px 24px rgba(0,0,0,0.08)",
                }}>
                  {filteredPassengers.map((p) => (
                    <div key={p.id}
                      onClick={() => { setPassengerId(String(p.id)); setPassengerSearch(""); }}
                      style={{ padding: "8px 12px", cursor: "pointer", fontSize: 13, borderBottom: "1px solid var(--app-border, #eee)" }}>
                      <strong>{p.full_name || `Passageiro #${p.id}`}</strong>
                      {p.phone_number && <span style={{ marginLeft: 8, color: "#888", fontSize: 11 }}>{p.phone_number}</span>}
                    </div>
                  ))}
                </div>
              )}
              {passengerId && (
                <button type="button" onClick={() => { setPassengerId(""); setPassengerSearch(""); }}
                  style={{ position: "absolute", right: 6, top: 28, background: "none", border: "none", cursor: "pointer", color: "#999", fontSize: 16 }}>×</button>
              )}
            </label>
            {kind === "topups" && (
              <label className="field"><span>Sub-tipo</span>
                <select value={extraKind} onChange={(e) => setExtraKind(e.target.value)}>
                  <option value="">Todos</option>
                  <option value="wallet">Recarga de carteira</option>
                  <option value="package">Pacote</option>
                  <option value="card_issuance">Emissao de cartao</option>
                  <option value="card_recovery">Recuperacao de cartao</option>
                </select>
              </label>
            )}
          </div>
          <div style={{ marginBottom: 14, display: "flex", justifyContent: "flex-end" }}>
            {(status || source || agentId || routeId || passengerId || extraKind) && (
              <button type="button" onClick={clearFilters}
                style={{ fontSize: 12, color: "var(--app-accent)", background: "none", border: "none", cursor: "pointer" }}>
                Limpar filtros
              </button>
            )}
          </div>

          <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
            <button className="primary-button" type="button" onClick={runReport} disabled={running}>
              <Search size={15} /> {running ? "A gerar..." : "Gerar pre-visualizacao"}
            </button>
            <button className="icon-text-button" type="button" onClick={() => void exportReport("pdf")}><FileText size={15} /><span>PDF</span></button>
            <button className="icon-text-button" type="button" onClick={() => void exportReport("xlsx")}><FileSpreadsheet size={15} /><span>Excel</span></button>
          </div>

          {result && (
            <>
              <div className="admin-metric-grid" style={{ marginBottom: 14 }}>
                {Object.entries(result.totals).map(([k, v]) => (
                  <MetricCard
                    key={k}
                    label={k.replace(/_/g, " ").toUpperCase()}
                    value={String(v).match(/^[0-9.]+$/) && k.includes("amount") ? `${formatCurrency(String(v))} MZN` : String(v)}
                  />
                ))}
              </div>
              <DataTable
                columns={builderColumns}
                rows={result.rows}
                rowKey={(r) => String((r as Record<string, unknown>).reference || (r as Record<string, unknown>).created_at || Math.random())}
                loading={false}
                emptyMessage="Sem registos no periodo / filtros indicados."
              />
              {result.row_limit_reached ? (
                // Nao e o mesmo que mostrar so 500 na tabela: aqui a propria
                // consulta parou no tecto, e o PDF/Excel sai igualmente
                // incompleto. Dizer "use PDF para obter tudo" seria mentira.
                <p style={{ fontSize: 12, color: "#B4432B", marginTop: 6, fontWeight: 600 }}>
                  <Sliders size={11} /> Ha mais movimentos do que as {result.row_limit ?? 5000} linhas que o relatorio consegue trazer.
                  O PDF e o Excel saem igualmente incompletos — reduza o intervalo de datas ou filtre por rota/agente.
                </p>
              ) : result.truncated ? (
                <p style={{ fontSize: 12, color: "#6B6356", marginTop: 6 }}>
                  <Sliders size={11} /> Apenas as primeiras 500 linhas sao mostradas aqui. O PDF e o Excel trazem o periodo completo.
                </p>
              ) : null}
            </>
          )}
        </SectionCard>
      )}

      {tab === "revenue" && (
        <SectionCard title={t(lc, "revenueToday")}>
          {loadingR ? <SkeletonCard count={3} /> : !rev ? <div className="admin-empty-state">{t(lc, "noData")}</div> : (
            <>
              <div className="admin-metric-grid">
                <MetricCard label={t(lc, "validationsCount")} value={String(rev.validations.total_count)} />
                <MetricCard label={t(lc, "total")} value={formatCurrency(rev.validations.total_revenue)} />
                <MetricCard label={t(lc, "topups")} value={String(rev.topups.count)} detail={formatCurrency(rev.topups.total)} />
              </div>
              {rev.validations.by_route.length > 0 && (
                <>
                  <h4 style={{ margin: "16px 0 8px", fontSize: 13, fontWeight: 600, opacity: 0.7, textTransform: "uppercase" }}>{t(lc, "revenueByRoute")}</h4>
                  <DataTable columns={[
                    { header: t(lc, "route"), render: (r: { route__code: string; route__name: string }) => `${r.route__code} ${r.route__name}` },
                    { header: t(lc, "validationsCount"), render: (r: { count: number }) => String(r.count) },
                    { header: t(lc, "total"), render: (r: { total: string }) => formatCurrency(r.total) },
                  ]} rows={rev.validations.by_route} rowKey={(r) => r.route__code} loading={false} emptyMessage="" filterable={false} />
                </>
              )}
            </>
          )}
        </SectionCard>
      )}

      {tab === "operational" && (
        <SectionCard title="Receita operacional" description="Receita por viagem, rota e autocarro no periodo escolhido (bilhetes de convidado, passes da app, carteira e pagamentos directos).">
          <div className="admin-form-grid" style={{ marginBottom: 12 }}>
            <label className="field"><span>De</span><input type="date" value={opFrom} onChange={(e) => setOpFrom(e.target.value)} /></label>
            <label className="field"><span>Ate</span><input type="date" value={opTo} onChange={(e) => setOpTo(e.target.value)} /></label>
            <label className="field"><span>Rota</span>
              <select value={opRouteId} onChange={(e) => setOpRouteId(e.target.value)}>
                <option value="">Todas as rotas</option>
                {routes.map((r) => <option key={r.id} value={r.id}>{r.code ? `${r.code} · ${r.name}` : r.name}</option>)}
              </select>
            </label>
            <div className="admin-form-actions" style={{ alignItems: "flex-end" }}>
              <button className="primary-button" type="button" onClick={reloadOp}>Aplicar</button>
            </div>
          </div>
          {loadingOp ? <SkeletonCard count={4} /> : !op ? <div className="admin-empty-state">{t(lc, "noData")}</div> : (
            <>
              <div className="admin-metric-grid" style={{ marginBottom: 14 }}>
                <MetricCard label="Receita total" value={formatCurrency(op.totals.total_revenue)} />
                <MetricCard label="Bilhetes convidado" value={formatCurrency(op.totals.guest_checkout_revenue)} />
                <MetricCard label="Passes da app" value={formatCurrency(op.totals.app_pass_revenue)} />
                <MetricCard label="Carteira (validacoes)" value={formatCurrency(op.totals.wallet_validation_revenue)} />
                <MetricCard label="Pagamentos directos" value={formatCurrency(op.totals.direct_payment_revenue)} />
                <MetricCard label="Validacoes" value={String(op.totals.validations_approved)} detail={`${op.totals.validations_denied} negadas`} />
              </div>
              {op.by_route.length > 0 && (
                <>
                  <h4 style={{ margin: "16px 0 8px", fontSize: 13, fontWeight: 600, opacity: 0.7, textTransform: "uppercase" }}>Por rota</h4>
                  <DataTable columns={[
                    { header: "Rota", render: (r: OperationalData["by_route"][number]) => `${r.route_code} ${r.route_name}` },
                    { header: "Viagens", render: (r: OperationalData["by_route"][number]) => String(r.trips) },
                    { header: t(lc, "total"), render: (r: OperationalData["by_route"][number]) => formatCurrency(r.total_revenue) },
                  ]} rows={op.by_route} rowKey={(r) => String(r.route_id)} loading={false} emptyMessage="" filterable={false} />
                </>
              )}
              {op.by_vehicle.length > 0 && (
                <>
                  <h4 style={{ margin: "16px 0 8px", fontSize: 13, fontWeight: 600, opacity: 0.7, textTransform: "uppercase" }}>Por autocarro</h4>
                  <DataTable columns={[
                    { header: "Autocarro", render: (r: OperationalData["by_vehicle"][number]) => r.vehicle_registration || "Sem autocarro" },
                    { header: "Viagens", render: (r: OperationalData["by_vehicle"][number]) => String(r.trips) },
                    { header: t(lc, "total"), render: (r: OperationalData["by_vehicle"][number]) => formatCurrency(r.total_revenue) },
                  ]} rows={op.by_vehicle} rowKey={(r) => String(r.vehicle_id ?? 0)} loading={false} emptyMessage="" filterable={false} />
                </>
              )}
              <h4 style={{ margin: "16px 0 8px", fontSize: 13, fontWeight: 600, opacity: 0.7, textTransform: "uppercase" }}>Viagens</h4>
              <DataTable columns={[
                { header: "Viagem", render: (r: OpTripRow) => <TablePrimaryCell title={`#${r.trip_id}`} subtitle={`${r.route_code} ${r.route_name}`} /> },
                { header: "Autocarro", render: (r: OpTripRow) => r.vehicle_registration || "-" },
                { header: "Motorista", render: (r: OpTripRow) => r.driver_name || "-" },
                { header: t(lc, "status"), render: (r: OpTripRow) => <StatusBadge value={r.status} /> },
                { header: "Abertura", render: (r: OpTripRow) => r.opened_at ? formatDateTime(r.opened_at) : "-" },
                { header: "Fecho", render: (r: OpTripRow) => r.closed_at ? formatDateTime(r.closed_at) : "-" },
                { header: "Validacoes (A/N)", render: (r: OpTripRow) => `${r.summary.validations.approved} / ${r.summary.validations.denied}` },
                { header: t(lc, "total"), render: (r: OpTripRow) => formatCurrency(r.summary.total_revenue) },
              ]} rows={op.trips} rowKey={(r) => String(r.trip_id)} loading={false} emptyMessage="Sem viagens no periodo indicado." />
            </>
          )}
        </SectionCard>
      )}

      {tab === "validations" && (
        <SectionCard title="Relatorio de validacoes" description="Validacoes no periodo escolhido, por estado, tipo, motivo de recusa e terminal.">
          <div className="admin-form-grid" style={{ marginBottom: 12 }}>
            <label className="field"><span>De</span><input type="date" value={valFrom} onChange={(e) => setValFrom(e.target.value)} /></label>
            <label className="field"><span>Ate</span><input type="date" value={valTo} onChange={(e) => setValTo(e.target.value)} /></label>
            <label className="field"><span>Rota</span>
              <select value={valRouteId} onChange={(e) => setValRouteId(e.target.value)}>
                <option value="">Todas as rotas</option>
                {routes.map((r) => <option key={r.id} value={r.id}>{r.code ? `${r.code} · ${r.name}` : r.name}</option>)}
              </select>
            </label>
            <div className="admin-form-actions" style={{ alignItems: "flex-end" }}>
              <button className="primary-button" type="button" onClick={reloadV}>Aplicar</button>
            </div>
          </div>
          {loadingV ? <SkeletonCard count={4} /> : !val ? <div className="admin-empty-state">{t(lc, "noData")}</div> : (
            <>
              <div className="admin-metric-grid" style={{ marginBottom: 14 }}>
                <MetricCard label="Total de validacoes" value={String(val.by_status.reduce((s, r) => s + r.count, 0))} />
                {val.by_status.map((s) => (
                  <MetricCard key={s.status} label={s.status.toUpperCase()} value={String(s.count)} />
                ))}
              </div>
              {val.by_type.length > 0 && (
                <>
                  <h4 style={{ margin: "16px 0 8px", fontSize: 13, fontWeight: 600, opacity: 0.7, textTransform: "uppercase" }}>Por tipo</h4>
                  <DataTable columns={[
                    { header: "Tipo", render: (r: ValidationsData["by_type"][number]) => <StatusBadge value={r.validation_type} /> },
                    { header: "Quantidade", render: (r: ValidationsData["by_type"][number]) => String(r.count) },
                  ]} rows={val.by_type} rowKey={(r) => r.validation_type} loading={false} emptyMessage="" filterable={false} />
                </>
              )}
              {val.by_failure_reason.length > 0 && (
                <>
                  <h4 style={{ margin: "16px 0 8px", fontSize: 13, fontWeight: 600, opacity: 0.7, textTransform: "uppercase" }}>Motivos de recusa</h4>
                  <DataTable columns={[
                    { header: "Motivo", render: (r: ValidationsData["by_failure_reason"][number]) => r.failure_reason || "-" },
                    { header: "Quantidade", render: (r: ValidationsData["by_failure_reason"][number]) => String(r.count) },
                  ]} rows={val.by_failure_reason} rowKey={(r) => r.failure_reason || "-"} loading={false} emptyMessage="" filterable={false} />
                </>
              )}
              <h4 style={{ margin: "16px 0 8px", fontSize: 13, fontWeight: 600, opacity: 0.7, textTransform: "uppercase" }}>Por terminal</h4>
              <DataTable columns={[
                { header: "Terminal", render: (r: ValidationsData["by_device"][number]) => <TablePrimaryCell title={r.device__serial_number} subtitle={r.device__device_type} /> },
                { header: "Validacoes", render: (r: ValidationsData["by_device"][number]) => String(r.count) },
                { header: "Aprovadas", render: (r: ValidationsData["by_device"][number]) => String(r.approved) },
                { header: "Receita", render: (r: ValidationsData["by_device"][number]) => formatCurrency(r.revenue ?? "0") },
              ]} rows={val.by_device} rowKey={(r) => r.device__serial_number} loading={false} emptyMessage="Sem validacoes com terminal no periodo." />
            </>
          )}
        </SectionCard>
      )}

      {tab === "recon" && (
        <SectionCard title={t(lc, "reconciliation")}>
          {loadingC ? <SkeletonCard count={6} /> : !recon ? <div className="admin-empty-state">{t(lc, "noData")}</div> : (
            <div className="admin-metric-grid">
              <MetricCard label={t(lc, "confirmedPayments")} value={String(recon.payments.confirmed.count)} detail={formatCurrency(recon.payments.confirmed.total)} />
              <MetricCard label={t(lc, "pendingPaymentsShort")} value={String(recon.payments.pending.count)} detail={formatCurrency(recon.payments.pending.total)} />
              <MetricCard label={t(lc, "failedPayments")} value={String(recon.payments.failed.count)} detail={formatCurrency(recon.payments.failed.total)} />
              <MetricCard label={t(lc, "ledgerTopups")} value={String(recon.wallet_transactions.topups.count)} detail={formatCurrency(recon.wallet_transactions.topups.total)} />
              <MetricCard label={t(lc, "fareDebits")} value={String(recon.wallet_transactions.fare_debits.count)} detail={formatCurrency(recon.wallet_transactions.fare_debits.total)} />
              <MetricCard label={t(lc, "circulationBalance")} value={formatCurrency(recon.circulation.total_balance)} detail={`${recon.circulation.negative_wallets} ${t(lc, "negativeWallets")}`} />
              <MetricCard label={t(lc, "passesIssued")} value={String(recon.guest_checkouts.passes_issued)} />
              <MetricCard label={t(lc, "passesUsed")} value={String(recon.guest_checkouts.passes_used)} />
              <MetricCard label={t(lc, "passesActive")} value={String(recon.guest_checkouts.passes_active)} />
            </div>
          )}
        </SectionCard>
      )}
    </PageFrame>
  );
}
