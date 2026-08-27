import { useCallback, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, MapPin, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { apiFetch, apiPost, apiPatch, apiDelete } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { t, type Locale } from "../lib/i18n";
import { mensagemDeErro } from "../lib/errors";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { AdminModal, DataTable, MetricCard, PageFrame, SectionCard, StatusBadge, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";
import { useConfirm } from "../ui/ConfirmDialog";

type RouteDirection = "outbound" | "inbound";

interface RouteRecord { id: number; uuid: string; code: string; name: string; description: string; status: string; service_type: string; stop_count: number; created_at: string; }
const tiposDeServico = (lc: Locale): Record<string, string> => ({
  urban: t(lc, "urbanIntercity"),
  interprovincial: t(lc, "interprovincial"),
  international: t(lc, "international"),
});

interface RouteStopRecord { id?: number; uuid?: string; stop_id: number; stop_code?: string; stop_name: string; sequence: number; distance_from_start_km: string; direction: RouteDirection; }

const DIRECTIONS: RouteDirection[] = ["outbound", "inbound"];

export default function RoutesPage({ embedded }: { embedded?: boolean }) {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const navigate = useNavigate();
  const { confirm, dialog: confirmDialog } = useConfirm();
  const loader = useCallback(() => apiFetch("/api/routes/", token!).then((d) => d.results || d), [token]);
  const { data: rows, loading, reload } = useAsyncData<RouteRecord[]>(loader, [token]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [viewing, setViewing] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", status: "active", service_type: "urban" });
  const f = (k: string, v: string) => setForm((p) => ({ ...p, [k]: v }));
  const reset = () => { setEditId(null); setModalOpen(false); setForm({ name: "", description: "", status: "active", service_type: "urban" }); };

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true);
    try {
      if (editId) { await apiPatch(`/api/routes/${editId}/`, token!, form); showToast("success", t(lc, "okRouteUpdated")); }
      else { await apiPost("/api/routes/", token!, form); showToast("success", t(lc, "okRouteCreated")); }
      reset(); reload();
    } catch (err) { showToast("danger", mensagemDeErro(err, lc)); }
    finally { setBusy(false); }
  };

  const remove = async (r: RouteRecord) => {
    const ok = await confirm({ title: t(lc, "delete"), message: t(lc, "confirmDelete", { n: r.code }), tone: "danger" });
    if (!ok) return;
    try { await apiDelete(`/api/routes/${r.id}/`, token!); showToast("success", t(lc, "okRouteDeleted")); reload(); }
    catch (err) { showToast("danger", mensagemDeErro(err, lc)); }
  };

  const openDetail = async (route: RouteRecord) => {
    setViewing(route);
    try {
      const detail = await apiFetch(`/api/routes/${route.id}/`, token!);
      setViewing(detail);
    } catch {
      setViewing(route);
    }
  };

  return (
    <PageFrame kicker={t(lc, "operation")} title={t(lc, "routes")}
      action={<>
        <button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={16} /><span>{t(lc, "refresh")}</span></button>
        <button className="primary-button" onClick={() => { reset(); setModalOpen(true); }} type="button"><Plus size={16} /> {t(lc, "newRoute")}</button>
      </>}>
      <div className="admin-metric-grid">
        <MetricCard label={t(lc, "total")} value={String((rows || []).length)} />
        <MetricCard label={t(lc, "active")} value={String((rows || []).filter((r) => r.status === "active").length)} />
      </div>
      <SectionCard title={t(lc, "routes")}>
        <DataTable columns={[
          { header: t(lc, "route"), render: (r: RouteRecord) => <TablePrimaryCell title={r.code} subtitle={r.name} /> },
          { header: t(lc, "type"), render: (r: RouteRecord) => tiposDeServico(lc)[r.service_type] || t(lc, "urbanIntercity") },
          { header: t(lc, "routeStops"), render: (r: RouteRecord) => String(r.stop_count || 0) },
          { header: t(lc, "status"), render: (r: RouteRecord) => <StatusBadge value={r.status} /> },
          { header: t(lc, "created"), render: (r: RouteRecord) => formatDateTime(r.created_at) },
          { header: t(lc, "actions"), className: "table-actions-cell", render: (r: RouteRecord) => (
            <div className="admin-inline-actions">
              <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => void openDetail(r)} />
              <TableActionButton icon={<MapPin size={15} />} label={t(lc, "manageStops")} onClick={() => navigate(`/app/routes/${r.id}/stops`)} />
              <TableActionButton icon={<Pencil size={15} />} label={t(lc, "edit")} onClick={() => { setEditId(r.id); setModalOpen(true); setForm({ name: r.name, description: r.description, status: r.status, service_type: r.service_type || "urban" }); }} />
              <TableActionButton icon={<Trash2 size={15} />} label={t(lc, "delete")} onClick={() => remove(r)} tone="danger" />
            </div>
          )},
        ]} rows={rows || []} rowKey={(r) => r.uuid} loading={loading} emptyMessage={t(lc, "noRoutes")} />
      </SectionCard>

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing?.code || viewing?.name || ""} fields={viewing ? [
        { label: t(lc, "code"), value: viewing.code },
        { label: t(lc, "name"), value: viewing.name },
        { label: t(lc, "routeStops"), value: String(viewing.stop_count || (viewing.stops || []).length) },
        { label: t(lc, "description"), value: viewing.description || "-" },
        { label: t(lc, "status"), value: viewing.status },
        { label: t(lc, "created"), value: viewing.created_at },
      ] : []}>
        {viewing?.stops?.length ? (
          <div className="route-detail-stops">
            {DIRECTIONS.map((direction) => {
              const items = (viewing.stops as RouteStopRecord[])
                .filter((s) => s.direction === direction)
                .sort((a, b) => a.sequence - b.sequence);
              if (items.length === 0) return null;
              return (
                <div className="route-detail-direction" key={direction}>
                  <h4 className="route-detail-direction-title">
                    {direction === "outbound" ? t(lc, "outbound") : t(lc, "inbound")}
                    <span className="route-detail-direction-count">{items.length}</span>
                  </h4>
                  <ol className="route-detail-stop-list">
                    {items.map((item) => (
                      <li className="route-detail-stop-item" key={`${item.direction}-${item.sequence}-${item.stop_id}`}>
                        <div className="route-detail-stop-seq">{item.sequence}</div>
                        <div className="route-detail-stop-main">
                          <strong>{item.stop_name}</strong>
                          <span>{item.stop_code || "-"} · {item.distance_from_start_km || "0"} km</span>
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
              );
            })}
          </div>
        ) : null}
      </DetailDrawer>

      <AdminModal open={modalOpen} onClose={reset} title={editId ? t(lc, "editRoute") : t(lc, "newRoute")}>
        <form className="admin-form" onSubmit={submit}>
          <div className="admin-form-grid">
            <label className="field"><span>{t(lc, "name")}</span><input required value={form.name} onChange={(e) => f("name", e.target.value)} /></label>
            <label className="field"><span>{t(lc, "status")}</span><select value={form.status} onChange={(e) => f("status", e.target.value)}><option value="active">{t(lc, "active")}</option><option value="inactive">{t(lc, "inactive")}</option><option value="suspended">{t(lc, "suspended")}</option></select></label>
            <label className="field"><span>{t(lc, "serviceType")}</span><select value={form.service_type} onChange={(e) => f("service_type", e.target.value)}><option value="urban">{t(lc, "urbanIntercity")}</option><option value="interprovincial">{t(lc, "interprovincial")}</option><option value="international">{t(lc, "international")}</option></select></label>
            <label className="field admin-field-span-full"><span>{t(lc, "description")}</span><textarea value={form.description} onChange={(e) => f("description", e.target.value)} /></label>
          </div>
          <p className="dash-kpi-note" style={{ marginTop: 4 }}>
            O tipo de serviço decide se o passageiro escolhe lugar: nas carreiras urbanas ninguém escolhe, nas interprovinciais e internacionais a planta do autocarro é mostrada na compra. Escolher mal faz o passo desaparecer ou aparecer onde não devia.
          </p>
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
