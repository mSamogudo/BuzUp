import { useCallback, useState } from "react";
import { Eye, Lock, QrCode, RefreshCw } from "lucide-react";
import { apiFetch, apiPost } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { AdminModal, DataTable, MetricCard, PageFrame, SegmentedControl, StatusBadge, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";

interface CardRecord { id: number; uuid: string; card_type: string; card_uid: string; card_number: string; card_technology: string; status: string; passenger_name: string; passenger_phone: string; balance: string | null; activated_at: string | null; created_at: string; }

export default function DigitalCardsPage() {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const loader = useCallback(() => apiFetch("/api/cards/?type=digital", token!).then((d) => d.results || d), [token]);
  const { data: cards, loading, reload } = useAsyncData<CardRecord[]>(loader, [token]);
  const [filter, setFilter] = useState<"active" | "inactive">("active");
  const [viewing, setViewing] = useState<CardRecord | null>(null);
  const [qrCard, setQrCard] = useState<CardRecord | null>(null);

  const all = cards || [];
  const filtered = filter === "active" ? all.filter((c) => c.status === "active") : all.filter((c) => c.status !== "active");

  const block = async (uid: string) => {
    if (!confirm(`${t(lc, "block")}?`)) return;
    try { await apiPost("/api/card-actions/block/", token!, { card_uid: uid }); showToast("success", t(lc, "block")); reload(); }
    catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
  };

  return (
    <PageFrame kicker={t(lc, "management")} title={t(lc, "digitalCards")}
      action={<button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={15} /><span>{t(lc, "refresh")}</span></button>}>
      <div className="admin-metric-grid">
        <MetricCard label={t(lc, "total")} value={String(all.length)} />
        <MetricCard label={t(lc, "active")} value={String(all.filter((c) => c.status === "active").length)} />
      </div>

      <SegmentedControl items={[
        { key: "active", label: `${t(lc, "active")} (${all.filter((c) => c.status === "active").length})` },
        { key: "inactive", label: `${t(lc, "inactive")} (${all.filter((c) => c.status !== "active").length})` },
      ]} value={filter} onChange={(k) => setFilter(k as "active" | "inactive")} />

      <DataTable columns={[
        { header: t(lc, "cardNumber"), sortKey: "card_number", render: (r: CardRecord) => <TablePrimaryCell title={r.card_number} subtitle={r.passenger_name || "-"} /> },
        { header: t(lc, "status"), render: (r: CardRecord) => <StatusBadge value={r.status} /> },
        { header: t(lc, "actions"), className: "table-actions-cell", render: (r: CardRecord) => (
          <div className="admin-inline-actions">
            <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => setViewing(r)} />
            <TableActionButton icon={<QrCode size={15} />} label="QR" onClick={() => setQrCard(r)} />
            {r.status === "active" && <TableActionButton icon={<Lock size={15} />} label={t(lc, "block")} onClick={() => block(r.card_uid)} tone="danger" />}
          </div>
        )},
      ]} rows={filtered} rowKey={(r) => r.uuid} loading={loading} emptyMessage={t(lc, "noCards")} />

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing?.card_number || ""} fields={viewing ? [
        { label: t(lc, "cardNumber"), value: viewing.card_number },
        { label: t(lc, "type"), value: "Digital (QR Code)" },
        { label: t(lc, "status"), value: <StatusBadge value={viewing.status} /> },
        { label: t(lc, "passenger"), value: viewing.passenger_name || "-" },
        { label: t(lc, "phone"), value: viewing.passenger_phone || "-" },
        { label: t(lc, "balance"), value: viewing.balance !== null ? formatCurrency(viewing.balance) : "-" },
        { label: t(lc, "activated"), value: formatDateTime(viewing.activated_at) },
      ] : []} />

      <AdminModal
        open={!!qrCard}
        onClose={() => setQrCard(null)}
        title={qrCard ? `QR Code - ${qrCard.card_number}` : ""}
        description={qrCard ? `${qrCard.passenger_name || "Sem passageiro"} ${qrCard.passenger_phone ? `· ${qrCard.passenger_phone}` : ""}` : ""}
      >
        {qrCard && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16, padding: "8px 0" }}>
            <img
              src={`/api/cards/${qrCard.id}/qr.png?token=${encodeURIComponent(token || "")}`}
              alt="QR"
              style={{ width: 280, height: 280, background: "#fff", borderRadius: 12, padding: 8, border: "1px solid #E7E1D4" }}
            />
            <p style={{ color: "#6B6356", fontSize: 12, textAlign: "center", margin: 0 }}>
              Mostre este QR ao agente para cobranca de bilhetes ou recarga.<br />
              Cartao: <strong>{qrCard.card_number}</strong>
            </p>
            <a
              className="icon-text-button"
              href={`/api/cards/${qrCard.id}/qr.png?token=${encodeURIComponent(token || "")}`}
              download={`buzup-qr-${qrCard.card_number}.png`}
            >
              <QrCode size={15} /><span>Descarregar PNG</span>
            </a>
          </div>
        )}
      </AdminModal>
    </PageFrame>
  );
}
