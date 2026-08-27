import { useCallback, useMemo, useState } from "react";
import { Download, Eye, RefreshCw, Upload } from "lucide-react";
import { apiFetch, apiPublic } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import { useAuth } from "../auth/AuthContext";
import { AdminModal, DataTable, PageFrame, SectionCard, StatusBadge, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { showToast } from "../lib/toast";
import { DetailDrawer } from "../ui/DetailDrawer";
import { mensagemDeErro } from "../lib/errors";
import { t, type Locale } from "../lib/i18n";
import { useUi } from "../ui/UiPreferences";

interface GuestCheckout {
  id: number;
  uuid: string;
  reference: string;
  payer_phone: string;
  buyer_name: string;
  route_code: string;
  route_name: string;
  origin_stop: string;
  destination_stop: string;
  quantity: number;
  unit_amount: string;
  total_amount: string;
  // Moeda em que o comprador viu o preco (ex.: ZAR) — a cobranca e sempre MZN.
  display_currency: string;
  display_total_amount: string | null;
  exchange_rate: string | null;
  status: string;
  trip_id: number | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

interface TravelPass {
  id: number;
  uuid: string;
  route_code: string;
  route_name: string;
  origin_stop: string;
  destination_stop: string;
  fare_amount: string;
  display_currency: string;
  display_fare_amount: string | null;
  status: string;
  delivery_channel: string;
  valid_from: string | null;
  valid_until: string | null;
  used_at: string | null;
  pdf_url: string;
  created_at: string;
}

type CheckoutDetail = GuestCheckout & { passes?: TravelPass[] };

// Depende do idioma, por isso e uma funcao e nao uma constante: uma
// constante de modulo fixaria os rotulos no idioma que estivesse activo
// quando o ficheiro foi carregado.
const estados = (lc: Locale) => [
  { value: "all", label: t(lc, "allStatuses") },
  { value: "draft", label: t(lc, "draft") },
  { value: "payment_pending", label: t(lc, "paymentPending") },
  { value: "paid", label: t(lc, "paid") },
  { value: "issued", label: t(lc, "issued") },
  { value: "expired", label: t(lc, "expired") },
  { value: "cancelled", label: t(lc, "cancelled") },
  { value: "refunded", label: t(lc, "refunded") },
];

export default function GuestCheckoutsPage() {
  const { locale: lc } = useUi();
  const { token } = useAuth();
  const loader = useCallback(() => apiFetch("/api/admin/guest-checkouts/", token!).then((d) => d.results || d), [token]);
  const { data: rows, loading, reload } = useAsyncData<GuestCheckout[]>(loader, [token]);
  const [statusFilter, setStatusFilter] = useState("all");

  // --- Carregar vendas antigas ----------------------------------------
  const [importar, setImportar] = useState(false);
  const [ficheiro, setFicheiro] = useState<File | null>(null);
  const [aCarregar, setACarregar] = useState(false);
  const [resultado, setResultado] = useState<null | {
    imported: number; duplicates: number; total_amount: string;
    errors: { row: number; detail: string }[];
  }>(null);

  const descarregarModelo = async () => {
    try {
      const res = await fetch("/api/import/sales/template/", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Não foi possível obter o modelo.");
      const url = URL.createObjectURL(await res.blob());
      const a = document.createElement("a");
      a.href = url; a.download = "modelo_vendas_historicas.xlsx"; a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      showToast("danger", mensagemDeErro(err, lc));
    }
  };

  const carregarFicheiro = async () => {
    if (!ficheiro) return;
    setACarregar(true);
    try {
      const fd = new FormData();
      fd.append("file", ficheiro);
      const res = await fetch("/api/import/sales/", {
        method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Erro ao carregar o ficheiro.");
      setResultado(data);
      if (data.imported > 0) reload();
    } catch (err) {
      showToast("danger", mensagemDeErro(err, lc));
    } finally {
      setACarregar(false);
    }
  };

  const modalImportacao = (
    <AdminModal open={importar} onClose={() => setImportar(false)}
      title={t(lc, "importPastSales")}
      description={t(lc, "importSalesHint")}>
      {resultado ? (
        <div className="admin-form">
          <div className="admin-metric-grid">
            <div className="dash-kpi"><span className="dash-kpi-label">{t(lc, "imported")}</span>
              <strong className="dash-kpi-value">{resultado.imported}</strong></div>
            <div className="dash-kpi"><span className="dash-kpi-label">{t(lc, "alreadyExisted")}</span>
              <strong className="dash-kpi-value">{resultado.duplicates}</strong></div>
            <div className="dash-kpi"><span className="dash-kpi-label">{t(lc, "total")}</span>
              <strong className="dash-kpi-value">{formatCurrency(resultado.total_amount)} MZN</strong></div>
          </div>
          {resultado.errors.length > 0 ? (
            <>
              <p className="dash-kpi-note" style={{ marginTop: 12 }}>
                <b>{resultado.errors.length} linha(s) não entraram.</b> As restantes foram
                carregadas — corrija estas no ficheiro e volte a carregá-lo; o que já entrou
                não se repete.
              </p>
              <div style={{ maxHeight: 240, overflow: "auto", marginTop: 8 }}>
                <table className="admin-table"><tbody>
                  {resultado.errors.map((e, i) => (
                    <tr key={i}><td style={{ width: 70 }}>Linha {e.row}</td><td>{e.detail}</td></tr>
                  ))}
                </tbody></table>
              </div>
            </>
          ) : (
            <p className="dash-kpi-note" style={{ marginTop: 12 }}>
              {t(lc, "importNoErrors")} <b>já usados</b> — são viagens que
              aconteceram, não servem para viajar e ninguém recebeu SMS.
            </p>
          )}
          <div className="admin-form-actions">
            <button className="primary-button" type="button"
              onClick={() => { setResultado(null); setFicheiro(null); }}>{t(lc, "importAnother")}</button>
            <button className="secondary-button" type="button"
              onClick={() => setImportar(false)}>{t(lc, "close")}</button>
          </div>
        </div>
      ) : (
        <div className="admin-form">
          <label className="field">
            <span>{t(lc, "excelFile")}</span>
            <input type="file" accept=".xlsx"
              onChange={(e) => setFicheiro(e.target.files?.[0] || null)} />
          </label>
          <p className="dash-kpi-note">
            Use o <b>{t(lc, "template")}</b> para saber que colunas preencher. A referência do vosso
            sistema antigo é a chave: carregar o mesmo ficheiro duas vezes não duplica nada.
          </p>
          <div className="admin-form-actions">
            <button className="primary-button" type="button"
              disabled={!ficheiro || aCarregar} onClick={carregarFicheiro}>
              {aCarregar ? "A carregar…" : "Carregar"}
            </button>
            <button className="secondary-button" type="button"
              onClick={() => setImportar(false)}>{t(lc, "cancel")}</button>
          </div>
        </div>
      )}
    </AdminModal>
  );
  const [currencyFilter, setCurrencyFilter] = useState("all");
  const [viewing, setViewing] = useState<CheckoutDetail | null>(null);

  // Moedas de exibicao presentes nos dados (ex.: ZAR nas rotas p/ Africa do Sul).
  const currencies = useMemo(() => {
    const set = new Set((rows || []).map((r) => r.display_currency || "MZN"));
    return Array.from(set).sort();
  }, [rows]);

  // O endpoint admin nao suporta ?status=, por isso filtramos client-side.
  const filtered = useMemo(() => {
    let all = rows || [];
    if (statusFilter !== "all") all = all.filter((r) => r.status === statusFilter);
    if (currencyFilter !== "all") all = all.filter((r) => (r.display_currency || "MZN") === currencyFilter);
    return all;
  }, [rows, statusFilter, currencyFilter]);

  const openDetail = async (row: GuestCheckout) => {
    setViewing(row);
    try {
      // A rota publica de lookup expoe os bilhetes (passes) associados.
      const pub = await apiPublic(`/api/guest-checkouts/${row.reference}/`);
      setViewing({ ...row, passes: pub?.passes || [] });
    } catch {
      setViewing(row);
    }
  };

  return (
    <PageFrame kicker={t(lc, "finance")} title={t(lc, "guestCheckouts")}
      description={t(lc, "guestPurchasesHint")}
      action={<>
        <button className="icon-text-button" onClick={descarregarModelo} type="button">
          <Download size={15} /><span>{t(lc, "template")}</span>
        </button>
        <button className="icon-text-button" type="button"
          onClick={() => { setFicheiro(null); setResultado(null); setImportar(true); }}>
          <Upload size={15} /><span>{t(lc, "importHistory")}</span>
        </button>
        <button className="icon-text-button" onClick={reload} type="button">
          <RefreshCw size={16} /><span>{t(lc, "refresh")}</span>
        </button>
      </>}>
      {modalImportacao}
      <SectionCard title={t(lc, "purchases")} description={t(lc, "guestCheckoutsHint")}>
        <div className="admin-toolbar" style={{ marginBottom: 12 }}>
          <label className="field" style={{ maxWidth: 260 }}>
            <span>{t(lc, "status")}</span>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              {estados(lc).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
          <label className="field" style={{ maxWidth: 200 }}>
            <span>{t(lc, "displayCurrency")}</span>
            <select value={currencyFilter} onChange={(e) => setCurrencyFilter(e.target.value)}>
              <option value="all">{t(lc, "allCurrencies")}</option>
              {currencies.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
        </div>
        <DataTable columns={[
          { header: t(lc, "reference"), sortKey: "reference", render: (r: GuestCheckout) => <TablePrimaryCell title={r.reference} subtitle={r.buyer_name || "-"} /> },
          { header: t(lc, "phone"), render: (r: GuestCheckout) => r.payer_phone || "-" },
          { header: t(lc, "routeTrip"), render: (r: GuestCheckout) => (
            <TablePrimaryCell title={`${r.route_code}${r.route_name ? ` - ${r.route_name}` : ""}`} subtitle={`${r.origin_stop || "?"} → ${r.destination_stop || "?"}${r.trip_id ? ` · Viagem #${r.trip_id}` : ""}`} />
          ) },
          { header: t(lc, "qty"), sortKey: "quantity", render: (r: GuestCheckout) => String(r.quantity) },
          { header: t(lc, "amount"), sortKey: "total_amount", render: (r: GuestCheckout) => (
            r.display_currency && r.display_currency !== "MZN" && r.display_total_amount
              ? <TablePrimaryCell title={formatCurrency(r.total_amount)} subtitle={`visto como ${formatCurrency(r.display_total_amount)} ${r.display_currency}`} />
              : formatCurrency(r.total_amount)
          ) },
          { header: t(lc, "status"), sortKey: "status", render: (r: GuestCheckout) => <StatusBadge value={r.status} /> },
          { header: t(lc, "date"), sortKey: "created_at", render: (r: GuestCheckout) => formatDateTime(r.created_at) },
          { header: t(lc, "actions"), className: "table-actions-cell", render: (r: GuestCheckout) => (
            <div className="admin-inline-actions">
              <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => void openDetail(r)} />
            </div>
          ) },
        ]} rows={filtered} rowKey={(r) => r.uuid} loading={loading} emptyMessage={t(lc, "noGuestCheckouts")} />
      </SectionCard>

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing?.reference || ""} fields={viewing ? [
        { label: t(lc, "reference"), value: viewing.reference },
        { label: t(lc, "buyer"), value: viewing.buyer_name || "-" },
        { label: t(lc, "payerPhone"), value: viewing.payer_phone || "-" },
        { label: t(lc, "route"), value: `${viewing.route_code}${viewing.route_name ? ` - ${viewing.route_name}` : ""}` },
        { label: t(lc, "origin"), value: viewing.origin_stop || "-" },
        { label: t(lc, "destination"), value: viewing.destination_stop || "-" },
        { label: t(lc, "trip"), value: viewing.trip_id ? `#${viewing.trip_id}` : "-" },
        { label: t(lc, "quantity"), value: String(viewing.quantity) },
        { label: t(lc, "unitAmount"), value: formatCurrency(viewing.unit_amount) },
        { label: t(lc, "totalAmount"), value: formatCurrency(viewing.total_amount) },
        ...(viewing.display_currency && viewing.display_currency !== "MZN" ? [
          { label: t(lc, "currencyChosen"), value: viewing.display_currency },
          { label: t(lc, "amountShownToBuyer"), value: viewing.display_total_amount ? `${formatCurrency(viewing.display_total_amount)} ${viewing.display_currency}` : "-" },
          { label: t(lc, "frozenRate"), value: viewing.exchange_rate ? `1 ${viewing.display_currency} = ${formatCurrency(viewing.exchange_rate)} MZN` : "-" },
        ] : []),
        { label: t(lc, "status"), value: <StatusBadge value={viewing.status} /> },
        { label: t(lc, "expiresAt"), value: viewing.expires_at ? formatDateTime(viewing.expires_at) : "-" },
        { label: t(lc, "createdAt"), value: formatDateTime(viewing.created_at) },
      ] : []}>
        {viewing?.passes?.length ? (
          <div className="detail-list">
            <h4>Bilhetes emitidos ({viewing.passes.length})</h4>
            {viewing.passes.map((p) => (
              <div className="detail-list-row" key={p.uuid || String(p.id)}>
                <strong>{p.route_code} · {p.origin_stop} → {p.destination_stop}</strong>
                <span>
                  {formatCurrency(p.fare_amount)}
                  {p.display_currency && p.display_currency !== "MZN" && p.display_fare_amount
                    ? ` (${formatCurrency(p.display_fare_amount)} ${p.display_currency})` : ""}
                  {" · "}<StatusBadge value={p.status} />
                  {p.used_at ? ` · usado ${formatDateTime(p.used_at)}` : ""}
                  {p.pdf_url ? <> · <a href={p.pdf_url} rel="noreferrer" target="_blank">PDF</a></> : null}
                </span>
              </div>
            ))}
          </div>
        ) : null}
      </DetailDrawer>
    </PageFrame>
  );
}
