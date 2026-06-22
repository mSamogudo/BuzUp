import { useCallback, useState } from "react";
import { Eye, RefreshCw } from "lucide-react";
import { apiFetch } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { DataTable, PageFrame, SectionCard, StatusBadge, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";

interface AuditEntry {
  id: number; actor: number | null; actor_name: string; action: string;
  entity_type: string; entity_id: string; before: Record<string, unknown>;
  after: Record<string, unknown>; ip_address: string | null; device: string; created_at: string;
}

const ACTIONS = ["", "create", "update", "delete", "restore", "login", "login_failed"];

export default function AuditPage({ embedded }: { embedded?: boolean }) {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const [action, setAction] = useState("");
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [viewing, setViewing] = useState<AuditEntry | null>(null);

  const loader = useCallback(() => {
    const p = new URLSearchParams();
    if (action) p.set("action", action);
    if (search) p.set("search", search);
    if (dateFrom) p.set("date_from", dateFrom);
    if (dateTo) p.set("date_to", dateTo);
    const qs = p.toString();
    return apiFetch(`/api/audit-logs/${qs ? `?${qs}` : ""}`, token!).then((d) => d.results || d);
  }, [token, action, search, dateFrom, dateTo]);
  const { data: rows, loading, reload } = useAsyncData<AuditEntry[]>(loader, [token]);

  return (
    <PageFrame kicker={t(lc, "security")} title={t(lc, "audit")}
      action={<button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={16} /><span>{t(lc, "refresh")}</span></button>}>
      <SectionCard title={t(lc, "audit")}>
        <div className="admin-form-grid" style={{ marginBottom: 12 }}>
          <label className="field"><span>{t(lc, "action")}</span>
            <select value={action} onChange={(e) => setAction(e.target.value)}>
              {ACTIONS.map((a) => <option key={a} value={a}>{a ? t(lc, `audit_${a}` as never) : t(lc, "all")}</option>)}
            </select>
          </label>
          <label className="field"><span>{t(lc, "search")}</span><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t(lc, "auditSearchHint")} /></label>
          <label className="field"><span>{t(lc, "from")}</span><input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} /></label>
          <label className="field"><span>{t(lc, "to")}</span><input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} /></label>
          <div className="admin-form-actions" style={{ alignItems: "flex-end" }}>
            <button className="primary-button" type="button" onClick={reload}>{t(lc, "filter")}</button>
          </div>
        </div>
        <DataTable columns={[
          { header: t(lc, "date"), render: (r: AuditEntry) => formatDateTime(r.created_at) },
          { header: t(lc, "action"), render: (r: AuditEntry) => <StatusBadge value={r.action} /> },
          { header: t(lc, "entity"), render: (r: AuditEntry) => <TablePrimaryCell title={r.entity_type} subtitle={r.entity_id ? `#${r.entity_id}` : "-"} /> },
          { header: t(lc, "actor"), render: (r: AuditEntry) => r.actor_name || t(lc, "system") },
          { header: "IP", render: (r: AuditEntry) => r.ip_address || "-" },
          { header: t(lc, "actions"), className: "table-actions-cell", render: (r: AuditEntry) => (
            <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => setViewing(r)} />
          )},
        ]} rows={rows || []} rowKey={(r) => String(r.id)} loading={loading} emptyMessage={t(lc, "noAudit")} />
      </SectionCard>

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing ? `${viewing.action} · ${viewing.entity_type}` : ""} fields={viewing ? [
        { label: t(lc, "date"), value: formatDateTime(viewing.created_at) },
        { label: t(lc, "action"), value: <StatusBadge value={viewing.action} /> },
        { label: t(lc, "entity"), value: `${viewing.entity_type} ${viewing.entity_id ? `#${viewing.entity_id}` : ""}` },
        { label: t(lc, "actor"), value: viewing.actor_name || t(lc, "system") },
        { label: "IP", value: viewing.ip_address || "-" },
        { label: t(lc, "device"), value: viewing.device || "-" },
      ] : []}>
        {viewing && (
          <>
            {viewing.before && Object.keys(viewing.before).length > 0 && (
              <div style={{ marginTop: 16, padding: "12px 0", borderTop: "1px solid var(--app-border)" }}>
                <h4 style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--app-text-muted)", marginBottom: 8 }}>{t(lc, "before")}</h4>
                <pre style={{ fontSize: 11, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{JSON.stringify(viewing.before, null, 2)}</pre>
              </div>
            )}
            {viewing.after && Object.keys(viewing.after).length > 0 && (
              <div style={{ marginTop: 16, padding: "12px 0", borderTop: "1px solid var(--app-border)" }}>
                <h4 style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--app-text-muted)", marginBottom: 8 }}>{t(lc, "after")}</h4>
                <pre style={{ fontSize: 11, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{JSON.stringify(viewing.after, null, 2)}</pre>
              </div>
            )}
          </>
        )}
      </DetailDrawer>
    </PageFrame>
  );
}
