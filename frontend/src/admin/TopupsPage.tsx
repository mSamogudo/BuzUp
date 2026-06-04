import { useCallback, useState } from "react";
import { Eye, RefreshCw } from "lucide-react";
import { apiFetch } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { DataTable, MetricCard, PageFrame, SectionCard, StatusBadge, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";

interface TopupIntent {
  id: number;
  uuid: string;
  reference: string;
  idempotency_key: string;
  purpose: string;
  amount: string;
  currency: string;
  payer_phone: string;
  provider: string;
  channel: string;
  status: string;
  wallet_uuid: string | null;
  wallet_passenger_name: string;
  wallet_passenger_phone: string;
  provider_reference: string;
  confirmed_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export default function TopupsPage() {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const loader = useCallback(() => (
    apiFetch("/api/payments/intents/?purpose=mobile_wallet_topup,pos_card_topup", token!).then((d) => d.results || d)
  ), [token]);
  const { data: rows, loading, reload } = useAsyncData<TopupIntent[]>(loader, [token]);
  const [viewing, setViewing] = useState<TopupIntent | null>(null);
  const confirmed = (rows || []).filter((r) => r.status === "confirmed");
  const pending = (rows || []).filter((r) => r.status === "pending");
  const failed = (rows || []).filter((r) => r.status === "failed");
  const confirmedTotal = confirmed.reduce((sum, row) => sum + parseFloat(row.amount || "0"), 0);

  return (
    <PageFrame
      kicker={t(lc, "financial")}
      title={t(lc, "topups")}
      action={<button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={15} /><span>{t(lc, "refresh")}</span></button>}
    >
      <div className="admin-metric-grid">
        <MetricCard label={t(lc, "topups")} value={String((rows || []).length)} />
        <MetricCard label={t(lc, "confirmed")} value={String(confirmed.length)} detail={formatCurrency(confirmedTotal)} />
        <MetricCard label={t(lc, "pending")} value={String(pending.length)} />
        <MetricCard label={t(lc, "failure")} value={String(failed.length)} />
      </div>

      <SectionCard title={t(lc, "topups")}>
        <DataTable columns={[
          { header: t(lc, "reference"), sortKey: "reference", render: (r: TopupIntent) => <TablePrimaryCell title={r.reference} subtitle={r.purpose.replace(/_/g, " ")} /> },
          { header: t(lc, "passenger"), render: (r: TopupIntent) => <TablePrimaryCell title={r.wallet_passenger_name || "-"} subtitle={r.wallet_passenger_phone || r.payer_phone} /> },
          { header: t(lc, "amount"), sortKey: "amount", render: (r: TopupIntent) => formatCurrency(r.amount, r.currency) },
          { header: t(lc, "provider"), sortKey: "provider", render: (r: TopupIntent) => r.provider || "-" },
          { header: t(lc, "status"), sortKey: "status", render: (r: TopupIntent) => <StatusBadge value={r.status} /> },
          { header: t(lc, "created"), sortKey: "created_at", render: (r: TopupIntent) => formatDateTime(r.created_at) },
          { header: t(lc, "actions"), className: "table-actions-cell", render: (r: TopupIntent) => (
            <div className="admin-inline-actions">
              <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => setViewing(r)} />
            </div>
          )},
        ]} rows={rows || []} rowKey={(r) => r.uuid} loading={loading} emptyMessage={t(lc, "noTopups")} />
      </SectionCard>

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing?.reference || ""} fields={viewing ? [
        { label: t(lc, "reference"), value: viewing.reference },
        { label: "Tipo", value: viewing.purpose.replace(/_/g, " ") },
        { label: t(lc, "amount"), value: formatCurrency(viewing.amount, viewing.currency) },
        { label: t(lc, "passenger"), value: viewing.wallet_passenger_name || "-" },
        { label: t(lc, "phone"), value: viewing.wallet_passenger_phone || viewing.payer_phone },
        { label: t(lc, "provider"), value: viewing.provider || "-" },
        { label: "Ref. Provedor", value: viewing.provider_reference || "-" },
        { label: t(lc, "status"), value: <StatusBadge value={viewing.status} /> },
        { label: t(lc, "confirmed"), value: formatDateTime(viewing.confirmed_at) },
        { label: t(lc, "created"), value: formatDateTime(viewing.created_at) },
        { label: "Idempotency", value: viewing.idempotency_key },
      ] : []} />
    </PageFrame>
  );
}
