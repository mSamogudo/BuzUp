import { useCallback } from "react";
import { RefreshCw } from "lucide-react";
import { apiFetch } from "../lib/api";
import { t } from "../lib/i18n";
import { useUi } from "../ui/UiPreferences";
import { formatDateTime } from "../lib/format";
import { useAuth } from "../auth/AuthContext";
import { DataTable, PageFrame, SectionCard, StatusBadge, TablePrimaryCell, useAsyncData } from "../ui/common";

interface PosSessionAgent { id: number; username: string; name: string; }
interface PosSessionDevice { id: number; serial_number: string; }
interface PosSessionRoute { id: number; code: string; }

interface PosSession {
  id: number;
  agent: PosSessionAgent | null;
  device: PosSessionDevice | null;
  allocated_route: PosSessionRoute | null;
  status: string;
  opened_at: string;
  closed_at: string | null;
}

export default function PosSessionsPage() {
  const { locale: lc } = useUi();
  const { token } = useAuth();
  const loader = useCallback(() => apiFetch("/api/pos/sessions/", token!).then((d) => d.results || d), [token]);
  const { data: rows, loading, reload } = useAsyncData<PosSession[]>(loader, [token]);

  return (
    <PageFrame kicker={t(lc, "operations")} title={t(lc, "posSessions")}
      description={t(lc, "posSessionsHint")}
      action={<button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={16} /><span>{t(lc, "refresh")}</span></button>}>
      <SectionCard title={t(lc, "sessions")} description={t(lc, "posSessionsHistory")}>
        <DataTable columns={[
          { header: t(lc, "agent"), render: (r: PosSession) => r.agent
            ? <TablePrimaryCell title={r.agent.name || r.agent.username} subtitle={r.agent.username} />
            : "-" },
          { header: t(lc, "terminal"), render: (r: PosSession) => r.device?.serial_number || "-" },
          { header: t(lc, "assignedRoute"), render: (r: PosSession) => r.allocated_route?.code || "-" },
          { header: t(lc, "openedAtF"), sortKey: "opened_at", render: (r: PosSession) => formatDateTime(r.opened_at) },
          { header: t(lc, "closedAtF"), sortKey: "closed_at", render: (r: PosSession) => r.closed_at ? formatDateTime(r.closed_at) : "-" },
          { header: t(lc, "status"), sortKey: "status", render: (r: PosSession) => <StatusBadge value={r.status} /> },
        ]} rows={rows || []} rowKey={(r) => String(r.id)} loading={loading} emptyMessage={t(lc, "noPosSessions")} />
      </SectionCard>
    </PageFrame>
  );
}
