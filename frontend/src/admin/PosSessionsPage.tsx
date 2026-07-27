import { useCallback } from "react";
import { RefreshCw } from "lucide-react";
import { apiFetch } from "../lib/api";
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
  const { token } = useAuth();
  const loader = useCallback(() => apiFetch("/api/pos/sessions/", token!).then((d) => d.results || d), [token]);
  const { data: rows, loading, reload } = useAsyncData<PosSession[]>(loader, [token]);

  return (
    <PageFrame kicker="Operação" title="Sessões POS"
      description="Sessões de venda abertas pelos agentes nos terminais POS."
      action={<button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={16} /><span>Actualizar</span></button>}>
      <SectionCard title="Sessões" description="Histórico de sessões por agente e terminal.">
        <DataTable columns={[
          { header: "Agente", render: (r: PosSession) => r.agent
            ? <TablePrimaryCell title={r.agent.name || r.agent.username} subtitle={r.agent.username} />
            : "-" },
          { header: "Terminal", render: (r: PosSession) => r.device?.serial_number || "-" },
          { header: "Rota alocada", render: (r: PosSession) => r.allocated_route?.code || "-" },
          { header: "Aberta em", sortKey: "opened_at", render: (r: PosSession) => formatDateTime(r.opened_at) },
          { header: "Fechada em", sortKey: "closed_at", render: (r: PosSession) => r.closed_at ? formatDateTime(r.closed_at) : "-" },
          { header: "Estado", sortKey: "status", render: (r: PosSession) => <StatusBadge value={r.status} /> },
        ]} rows={rows || []} rowKey={(r) => String(r.id)} loading={loading} emptyMessage="Sem sessões POS." />
      </SectionCard>
    </PageFrame>
  );
}
