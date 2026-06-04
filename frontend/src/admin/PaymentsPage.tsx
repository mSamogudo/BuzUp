import { useCallback, useMemo, useState } from "react";
import { Eye, RefreshCw, Filter, X } from "lucide-react";
import { apiFetch } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { DataTable, MetricCard, PageFrame, SectionCard, StatusBadge, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";

interface PI {
  id: number;
  uuid: string;
  reference: string;
  idempotency_key: string;
  purpose: string;
  purpose_label: string;
  amount: string;
  currency: string;
  payer_phone: string;
  provider: string;
  provider_label: string;
  channel: string;
  status: string;
  status_label: string;
  source: string; // POS | MOBILE | PORTAL | OUTRO
  wallet_uuid: string | null;
  wallet_passenger_name: string;
  wallet_passenger_phone: string;
  guest_payer_name: string;
  created_by_username: string;
  created_by_full_name: string;
  payer_display_name: string;
  payer_display_phone: string;
  provider_reference: string;
  confirmed_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

const SOURCE_TONE: Record<string, string> = {
  MOBILE: "var(--success, #1FB04A)",
  POS: "var(--orange, #E47B11)",
  PORTAL: "var(--navy, #071E49)",
  OUTRO: "var(--muted, #6B6356)",
};

export default function PaymentsPage() {
  const { token } = useAuth();
  const { locale: lc } = useUi();

  // Filters
  const [fStatus, setFStatus] = useState<string>("");
  const [fSource, setFSource] = useState<string>("");
  const [fProvider, setFProvider] = useState<string>("");
  const [fFrom, setFFrom] = useState<string>("");
  const [fTo, setFTo] = useState<string>("");
  const [fSearch, setFSearch] = useState<string>("");

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (fStatus) params.set("status", fStatus);
    if (fSource) params.set("source", fSource);
    if (fProvider) params.set("provider", fProvider);
    if (fFrom) params.set("date_from", fFrom);
    if (fTo) params.set("date_to", fTo);
    const qs = params.toString();
    return qs ? `?${qs}` : "";
  }, [fStatus, fSource, fProvider, fFrom, fTo]);

  const loader = useCallback(() =>
    apiFetch(`/api/payments/intents/${query}`, token!).then((d) => d.results || d),
    [token, query]);
  const { data: rows, loading, reload } = useAsyncData<PI[]>(loader, [token, query]);
  const [viewing, setViewing] = useState<PI | null>(null);

  const filtered = useMemo(() => {
    if (!fSearch) return rows || [];
    const q = fSearch.toLowerCase().trim();
    return (rows || []).filter((r) =>
      r.reference.toLowerCase().includes(q) ||
      r.provider_reference.toLowerCase().includes(q) ||
      r.payer_display_name.toLowerCase().includes(q) ||
      r.payer_display_phone.toLowerCase().includes(q) ||
      r.payer_phone.toLowerCase().includes(q));
  }, [rows, fSearch]);

  const confirmed = filtered.filter((r) => r.status === "confirmed");
  const pending = filtered.filter((r) => r.status === "pending");
  const failed = filtered.filter((r) => r.status === "failed");
  const totalConfirmed = confirmed.reduce((s, r) => s + parseFloat(r.amount || "0"), 0);

  const clearFilters = () => {
    setFStatus("");
    setFSource("");
    setFProvider("");
    setFFrom("");
    setFTo("");
    setFSearch("");
  };
  const anyFilter = Boolean(fStatus || fSource || fProvider || fFrom || fTo || fSearch);

  return (
    <PageFrame
      kicker={t(lc, "financial")}
      title={t(lc, "payments")}
      action={<button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={15} /><span>{t(lc, "refresh")}</span></button>}>

      <div className="admin-metric-grid">
        <MetricCard label={t(lc, "total")} value={String(filtered.length)} />
        <MetricCard label={t(lc, "confirmed")} value={String(confirmed.length)} detail={formatCurrency(totalConfirmed)} />
        <MetricCard label={t(lc, "pending")} value={String(pending.length)} />
        <MetricCard label="Falhados" value={String(failed.length)} />
      </div>

      <SectionCard title={t(lc, "payments")}>
        {/* Filter bar */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12, alignItems: "center" }}>
          <Filter size={14} style={{ opacity: 0.6 }} />
          <input
            type="text"
            placeholder="Buscar ref, telefone, nome..."
            value={fSearch}
            onChange={(e) => setFSearch(e.target.value)}
            style={{ minWidth: 220, padding: "6px 10px", fontSize: 13, borderRadius: 6, border: "1px solid var(--border, #E7E1D4)" }}
          />
          <select value={fSource} onChange={(e) => setFSource(e.target.value)}
            style={{ padding: "6px 10px", fontSize: 13, borderRadius: 6, border: "1px solid var(--border, #E7E1D4)" }}>
            <option value="">Origem · todas</option>
            <option value="MOBILE">App passageiro</option>
            <option value="POS">POS agente</option>
            <option value="PORTAL">Portal/convidado</option>
          </select>
          <select value={fProvider} onChange={(e) => setFProvider(e.target.value)}
            style={{ padding: "6px 10px", fontSize: 13, borderRadius: 6, border: "1px solid var(--border, #E7E1D4)" }}>
            <option value="">Canal · todos</option>
            <option value="mpesa">M-Pesa</option>
            <option value="emola">E-Mola</option>
            <option value="mock">Teste/Mock</option>
            <option value="card">Cartao</option>
            <option value="cash">Numerario</option>
          </select>
          <select value={fStatus} onChange={(e) => setFStatus(e.target.value)}
            style={{ padding: "6px 10px", fontSize: 13, borderRadius: 6, border: "1px solid var(--border, #E7E1D4)" }}>
            <option value="">Estado · todos</option>
            <option value="confirmed">Confirmado</option>
            <option value="pending">Pendente</option>
            <option value="failed">Falhado</option>
            <option value="expired">Expirado</option>
            <option value="reversed">Revertido</option>
          </select>
          <input type="date" value={fFrom} onChange={(e) => setFFrom(e.target.value)}
            style={{ padding: "6px 10px", fontSize: 13, borderRadius: 6, border: "1px solid var(--border, #E7E1D4)" }} />
          <span style={{ opacity: 0.5 }}>→</span>
          <input type="date" value={fTo} onChange={(e) => setFTo(e.target.value)}
            style={{ padding: "6px 10px", fontSize: 13, borderRadius: 6, border: "1px solid var(--border, #E7E1D4)" }} />
          {anyFilter && (
            <button type="button" onClick={clearFilters}
              style={{ display: "inline-flex", gap: 4, alignItems: "center", padding: "6px 10px", fontSize: 12, borderRadius: 6, border: "1px solid var(--border, #E7E1D4)", background: "transparent", cursor: "pointer" }}>
              <X size={12} /> Limpar
            </button>
          )}
        </div>

        <DataTable
          columns={[
            {
              header: "Origem", sortKey: "source", render: (r: PI) => (
                <span style={{
                  display: "inline-block", padding: "2px 8px", borderRadius: 12,
                  fontSize: 10.5, fontWeight: 900, letterSpacing: 0.6,
                  color: SOURCE_TONE[r.source] || "#666",
                  background: `${SOURCE_TONE[r.source] || "#666"}1F`,
                }}>{r.source}</span>
              ),
            },
            {
              header: t(lc, "reference"), sortKey: "reference",
              render: (r: PI) => <TablePrimaryCell title={r.reference} subtitle={r.purpose_label || r.purpose.replace(/_/g, " ")} />,
            },
            {
              header: "Pagador", render: (r: PI) => (
                <div style={{ lineHeight: 1.25 }}>
                  <div style={{ fontWeight: 700, fontSize: 12.5 }}>{r.payer_display_name || "-"}</div>
                  <div style={{ fontSize: 11, opacity: 0.7 }}>{r.payer_display_phone || r.payer_phone || ""}</div>
                </div>
              ),
            },
            {
              header: "Quem registou", render: (r: PI) => (
                <div style={{ lineHeight: 1.25, fontSize: 12 }}>
                  {r.created_by_full_name || r.created_by_username || (r.source === "MOBILE" ? "(self-service)" : "-")}
                </div>
              ),
            },
            {
              header: "Canal", sortKey: "provider", render: (r: PI) => (
                <span style={{ fontSize: 12, fontWeight: 700 }}>{r.provider_label || r.provider || "-"}</span>
              ),
            },
            {
              header: t(lc, "amount"), sortKey: "amount",
              render: (r: PI) => <span style={{ fontWeight: 800 }}>{formatCurrency(r.amount, r.currency)}</span>,
            },
            { header: t(lc, "status"), sortKey: "status", render: (r: PI) => <StatusBadge value={r.status} /> },
            {
              header: "Data", sortKey: "created_at",
              render: (r: PI) => <span style={{ fontSize: 12 }}>{formatDateTime(r.confirmed_at || r.created_at)}</span>,
            },
            {
              header: t(lc, "actions"), className: "table-actions-cell", render: (r: PI) => (
                <div className="admin-inline-actions">
                  <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => setViewing(r)} />
                </div>
              ),
            },
          ]}
          rows={filtered}
          rowKey={(r) => r.uuid}
          loading={loading}
          emptyMessage={anyFilter ? "Sem pagamentos para os filtros seleccionados." : t(lc, "noPayments")}
        />
      </SectionCard>

      <DetailDrawer
        open={!!viewing}
        onClose={() => setViewing(null)}
        title={viewing?.reference || ""}
        fields={viewing ? [
          { label: "Origem", value: viewing.source },
          { label: "Finalidade", value: viewing.purpose_label || viewing.purpose.replace(/_/g, " ") },
          { label: t(lc, "reference"), value: viewing.reference },
          { label: t(lc, "amount"), value: formatCurrency(viewing.amount, viewing.currency) },
          { label: "Pagador (nome)", value: viewing.payer_display_name || "-" },
          { label: "Pagador (telefone)", value: viewing.payer_display_phone || viewing.payer_phone || "-" },
          { label: "Conta passageiro", value: viewing.wallet_passenger_name || "-" },
          { label: "Convidado (guest)", value: viewing.guest_payer_name || "-" },
          { label: "Quem registou", value: viewing.created_by_full_name || viewing.created_by_username || "-" },
          { label: t(lc, "provider"), value: viewing.provider_label || viewing.provider || "-" },
          { label: "Canal (campo bruto)", value: viewing.channel || "-" },
          { label: "Ref. Provedor", value: viewing.provider_reference || "-" },
          { label: t(lc, "status"), value: <StatusBadge value={viewing.status} /> },
          { label: t(lc, "confirmed"), value: formatDateTime(viewing.confirmed_at) },
          { label: t(lc, "created"), value: formatDateTime(viewing.created_at) },
          { label: "Idempotency", value: viewing.idempotency_key },
        ] : []}
      />
    </PageFrame>
  );
}
