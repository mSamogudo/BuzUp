import { useCallback, useMemo, useState } from "react";
import { Eye, RefreshCw } from "lucide-react";
import { apiFetch, apiPublic } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import { useAuth } from "../auth/AuthContext";
import { DataTable, PageFrame, SectionCard, StatusBadge, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";

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
  status: string;
  delivery_channel: string;
  valid_from: string | null;
  valid_until: string | null;
  used_at: string | null;
  pdf_url: string;
  created_at: string;
}

type CheckoutDetail = GuestCheckout & { passes?: TravelPass[] };

const STATUS_OPTIONS = [
  { value: "all", label: "Todos os estados" },
  { value: "draft", label: "Rascunho" },
  { value: "payment_pending", label: "Pagamento pendente" },
  { value: "paid", label: "Pago" },
  { value: "issued", label: "Emitido" },
  { value: "expired", label: "Expirado" },
  { value: "cancelled", label: "Cancelado" },
  { value: "refunded", label: "Reembolsado" },
];

export default function GuestCheckoutsPage() {
  const { token } = useAuth();
  const loader = useCallback(() => apiFetch("/api/admin/guest-checkouts/", token!).then((d) => d.results || d), [token]);
  const { data: rows, loading, reload } = useAsyncData<GuestCheckout[]>(loader, [token]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [viewing, setViewing] = useState<CheckoutDetail | null>(null);

  // O endpoint admin nao suporta ?status=, por isso filtramos client-side.
  const filtered = useMemo(() => {
    const all = rows || [];
    if (statusFilter === "all") return all;
    return all.filter((r) => r.status === statusFilter);
  }, [rows, statusFilter]);

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
    <PageFrame kicker="Financeiro" title="Bilhetes ocasionais"
      description="Compras de bilhetes por passageiros sem conta (guest checkout)."
      action={<button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={16} /><span>Actualizar</span></button>}>
      <SectionCard title="Compras" description="Bilhetes ocasionais pagos por telemovel.">
        <div className="admin-toolbar" style={{ marginBottom: 12 }}>
          <label className="field" style={{ maxWidth: 260 }}>
            <span>Estado</span>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
        </div>
        <DataTable columns={[
          { header: "Referencia", sortKey: "reference", render: (r: GuestCheckout) => <TablePrimaryCell title={r.reference} subtitle={r.buyer_name || "-"} /> },
          { header: "Telefone", render: (r: GuestCheckout) => r.payer_phone || "-" },
          { header: "Rota / Viagem", render: (r: GuestCheckout) => (
            <TablePrimaryCell title={`${r.route_code}${r.route_name ? ` - ${r.route_name}` : ""}`} subtitle={`${r.origin_stop || "?"} → ${r.destination_stop || "?"}${r.trip_id ? ` · Viagem #${r.trip_id}` : ""}`} />
          ) },
          { header: "Qtd.", sortKey: "quantity", render: (r: GuestCheckout) => String(r.quantity) },
          { header: "Valor", sortKey: "total_amount", render: (r: GuestCheckout) => formatCurrency(r.total_amount) },
          { header: "Estado", sortKey: "status", render: (r: GuestCheckout) => <StatusBadge value={r.status} /> },
          { header: "Data", sortKey: "created_at", render: (r: GuestCheckout) => formatDateTime(r.created_at) },
          { header: "Accoes", className: "table-actions-cell", render: (r: GuestCheckout) => (
            <div className="admin-inline-actions">
              <TableActionButton icon={<Eye size={15} />} label="Ver" onClick={() => void openDetail(r)} />
            </div>
          ) },
        ]} rows={filtered} rowKey={(r) => r.uuid} loading={loading} emptyMessage="Sem bilhetes ocasionais." />
      </SectionCard>

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing?.reference || ""} fields={viewing ? [
        { label: "Referencia", value: viewing.reference },
        { label: "Comprador", value: viewing.buyer_name || "-" },
        { label: "Telefone do pagador", value: viewing.payer_phone || "-" },
        { label: "Rota", value: `${viewing.route_code}${viewing.route_name ? ` - ${viewing.route_name}` : ""}` },
        { label: "Origem", value: viewing.origin_stop || "-" },
        { label: "Destino", value: viewing.destination_stop || "-" },
        { label: "Viagem", value: viewing.trip_id ? `#${viewing.trip_id}` : "-" },
        { label: "Quantidade", value: String(viewing.quantity) },
        { label: "Valor unitario", value: formatCurrency(viewing.unit_amount) },
        { label: "Valor total", value: formatCurrency(viewing.total_amount) },
        { label: "Estado", value: <StatusBadge value={viewing.status} /> },
        { label: "Expira em", value: viewing.expires_at ? formatDateTime(viewing.expires_at) : "-" },
        { label: "Criado em", value: formatDateTime(viewing.created_at) },
      ] : []}>
        {viewing?.passes?.length ? (
          <div className="detail-list">
            <h4>Bilhetes emitidos ({viewing.passes.length})</h4>
            {viewing.passes.map((p) => (
              <div className="detail-list-row" key={p.uuid || String(p.id)}>
                <strong>{p.route_code} · {p.origin_stop} → {p.destination_stop}</strong>
                <span>
                  {formatCurrency(p.fare_amount)} · <StatusBadge value={p.status} />
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
