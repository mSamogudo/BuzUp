import { useCallback, useState, type FormEvent } from "react";
import { Eye, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { apiFetch, apiPost, apiPatch, apiDelete } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { AdminModal, DataTable, PageFrame, SectionCard, StatusBadge, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";
import { useConfirm } from "../ui/ConfirmDialog";

interface StopRouteLink { route_id: number; route_code: string; route_name: string; sequence: number; distance_from_start_km: string; direction: "outbound" | "inbound"; }
interface Stop { id: number; uuid: string; code: string; name: string; latitude: string | null; longitude: string | null; status: string; route_count: number; route_links?: StopRouteLink[]; created_at: string; }

export default function StopsPage({ embedded }: { embedded?: boolean }) {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const { confirm, dialog: confirmDialog } = useConfirm();
  const loader = useCallback(() => apiFetch("/api/stops/", token!).then((d) => d.results || d), [token]);
  const { data: rows, loading, reload } = useAsyncData<Stop[]>(loader, [token]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [viewing, setViewing] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ name: "", latitude: "", longitude: "", status: "active" });
  const f = (k: string, v: string) => setForm((p) => ({ ...p, [k]: v }));
  const reset = () => { setEditId(null); setModalOpen(false); setForm({ name: "", latitude: "", longitude: "", status: "active" }); };

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true);
    try {
      const payload = { ...form, latitude: form.latitude || null, longitude: form.longitude || null };
      if (editId) { await apiPatch(`/api/stops/${editId}/`, token!, payload); showToast("success", t(lc, "update")); }
      else { await apiPost("/api/stops/", token!, payload); showToast("success", t(lc, "create")); }
      reset(); reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
    finally { setBusy(false); }
  };

  const remove = async (r: Stop) => {
    const ok = await confirm({ title: t(lc, "delete"), message: `Tem a certeza que pretende eliminar a paragem ${r.name}?`, tone: "danger" });
    if (!ok) return;
    try { await apiDelete(`/api/stops/${r.id}/`, token!); reload(); } catch {}
  };

  const openDetail = async (stop: Stop) => {
    setViewing(stop);
    try {
      const detail = await apiFetch(`/api/stops/${stop.id}/`, token!);
      setViewing(detail);
    } catch {
      setViewing(stop);
    }
  };

  return (
    <PageFrame kicker={t(lc, "operation")} title={t(lc, "stops")}
      action={<>
        <button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={16} /><span>{t(lc, "refresh")}</span></button>
        <button className="primary-button" onClick={() => { reset(); setModalOpen(true); }} type="button"><Plus size={16} /> {t(lc, "newStop")}</button>
      </>}>
      <SectionCard title={t(lc, "stops")}>
        <DataTable columns={[
          { header: t(lc, "name"), render: (r: Stop) => <TablePrimaryCell title={r.name} subtitle={r.code} /> },
          { header: t(lc, "routes"), render: (r: Stop) => String(r.route_count || 0) },
          { header: t(lc, "coordinates"), render: (r: Stop) => r.latitude && r.longitude ? `${r.latitude}, ${r.longitude}` : "-" },
          { header: t(lc, "status"), render: (r: Stop) => <StatusBadge value={r.status} /> },
          { header: t(lc, "actions"), className: "table-actions-cell", render: (r: Stop) => (
            <div className="admin-inline-actions">
              <TableActionButton icon={<Eye size={15} />} label="Ver" onClick={() => void openDetail(r)} />
              <TableActionButton icon={<Pencil size={15} />} label={t(lc, "edit")} onClick={() => { setEditId(r.id); setModalOpen(true); setForm({ name: r.name, latitude: r.latitude || "", longitude: r.longitude || "", status: r.status }); }} />
              <TableActionButton icon={<Trash2 size={15} />} label={t(lc, "delete")} onClick={() => remove(r)} tone="danger" />
            </div>
          )},
        ]} rows={rows || []} rowKey={(r) => r.uuid} loading={loading} emptyMessage={t(lc, "noStops")} />
      </SectionCard>

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing?.name || viewing?.serial_number || viewing?.version_name || viewing?.code || ""} fields={viewing ? [
        { label: "Codigo", value: viewing.code },
        { label: "Nome", value: viewing.name },
        { label: t(lc, "routes"), value: String(viewing.route_count || 0) },
        { label: "Latitude", value: viewing.latitude || "-" },
        { label: "Longitude", value: viewing.longitude || "-" },
        { label: "Estado", value: viewing.status },
      ] : []}>
        {viewing?.route_links?.length ? (
          <div className="detail-list">
            <h4>{t(lc, "routes")}</h4>
            {viewing.route_links.map((item: StopRouteLink) => (
              <div className="detail-list-row" key={`${item.route_id}-${item.direction}-${item.sequence}`}>
                <strong>{item.route_code} - {item.route_name}</strong>
                <span>{item.direction === "outbound" ? t(lc, "outbound") : t(lc, "inbound")} · #{item.sequence} · {item.distance_from_start_km || "0"} km</span>
              </div>
            ))}
          </div>
        ) : null}
      </DetailDrawer>

      <AdminModal open={modalOpen} onClose={reset} title={editId ? t(lc, "editStop") : t(lc, "newStop")}>
        <form className="admin-form" onSubmit={submit}>
          <div className="admin-form-grid">
            <label className="field"><span>{t(lc, "name")}</span><input required value={form.name} onChange={(e) => f("name", e.target.value)} /></label>
            <label className="field"><span>{t(lc, "latitude")}</span><input type="number" step="any" value={form.latitude} onChange={(e) => f("latitude", e.target.value)} /></label>
            <label className="field"><span>{t(lc, "longitude")}</span><input type="number" step="any" value={form.longitude} onChange={(e) => f("longitude", e.target.value)} /></label>
            <label className="field"><span>{t(lc, "status")}</span><select value={form.status} onChange={(e) => f("status", e.target.value)}><option value="active">{t(lc, "active")}</option><option value="inactive">{t(lc, "inactive")}</option></select></label>
          </div>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy} type="submit">{busy ? t(lc, "saving") : editId ? t(lc, "update") : t(lc, "create")}</button>
            <button className="secondary-button" onClick={reset} type="button">{t(lc, "cancel")}</button>
          </div>
        </form>
      </AdminModal>
      {confirmDialog}
    </PageFrame>
  );
}
