import { useCallback, useState } from "react";
import { Eye, RefreshCw } from "lucide-react";
import { apiFetch } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { DataTable, MetricCard, PageFrame, SectionCard, StatusBadge, TablePrimaryCell, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";

interface VE { id: number; uuid: string; validation_type: string; status: string; failure_reason: string; amount_debited: string; route_code: string; device_serial: string; created_at: string; }

export default function ValidationsPage({ embedded }: { embedded?: boolean }) {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const loader = useCallback(() => apiFetch("/api/admin/validations/", token!).then((d) => d.results || d), [token]);
  const { data: rows, loading, reload } = useAsyncData<VE[]>(loader, [token]);
  const approved = (rows || []).filter((r) => r.status === "approved");
  const [viewing, setViewing] = useState<any>(null);
  const denied = (rows || []).filter((r) => r.status === "denied");

  return (
    <PageFrame kicker={t(lc, "operation")} title={t(lc, "validations")}
      action={<button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={16} /><span>{t(lc, "refresh")}</span></button>}>
      <div className="admin-metric-grid">
        <MetricCard label={t(lc, "total")} value={String((rows || []).length)} />
        <MetricCard label={t(lc, "approved")} value={String(approved.length)} detail={formatCurrency(approved.reduce((s, r) => s + parseFloat(r.amount_debited || "0"), 0))} />
        <MetricCard label={t(lc, "blocked")} value={String(denied.length)} />
      </div>
      <SectionCard title={t(lc, "validations")}>
        <DataTable columns={[
          { header: t(lc, "type"), render: (r: VE) => <TablePrimaryCell title={r.validation_type.replace(/_/g, " ")} subtitle={r.route_code || "-"} meta={r.device_serial || "-"} /> },
          { header: t(lc, "amount"), render: (r: VE) => formatCurrency(r.amount_debited) },
          { header: t(lc, "status"), render: (r: VE) => <StatusBadge value={r.status} /> },
          { header: t(lc, "failure"), render: (r: VE) => r.failure_reason ? r.failure_reason.replace(/_/g, " ") : "-" },
          { header: t(lc, "date"), render: (r: VE) => formatDateTime(r.created_at) },
        ]} rows={rows || []} rowKey={(r) => r.uuid} loading={loading} emptyMessage={t(lc, "noValidations")} />
      </SectionCard>

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing?.name || viewing?.serial_number || viewing?.version_name || viewing?.code || ""} fields={viewing ? [
        { label: "Tipo", value: viewing.validation_type },
        { label: "Rota", value: viewing.route_code || "-" },
        { label: "Terminal", value: viewing.device_serial || "-" },
        { label: "Valor", value: viewing.amount_debited },
        { label: "Estado", value: viewing.status },
        { label: "Falha", value: viewing.failure_reason || "-" },
        { label: "Data", value: viewing.created_at },
      ] : []} />

    </PageFrame>
  );
}
