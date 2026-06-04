import { useCallback, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { apiFetch, apiPost, apiPatch, apiDelete } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { AdminModal, DataTable, MetricCard, PageFrame, SectionCard, StatusBadge, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { useConfirm } from "../ui/ConfirmDialog";

interface TripPurchase { reference: string; payer_phone: string; quantity: number; total_amount: string; status: string; created_at: string; }
interface TripValidation { id: number; validation_type: string; status: string; failure_reason: string; amount_debited: string; device_serial: string; created_at: string; }
interface TripPass { uuid: string; payer_phone: string; fare_amount: string; status: string; origin_stop: string; destination_stop: string; created_at: string; used_at: string | null; }
interface TripRevenueSummary { guest_checkout: { revenue: string; count: number; tickets: number }; app_passes: { revenue: string; count: number }; wallet_validations: { revenue: string; count: number }; direct_payments: { revenue: string; count: number }; validations: { approved: number; denied: number }; total_revenue: string; }
interface TripActivityEvent { event_type: string; occurred_at: string; driver_name: string; metadata: Record<string, unknown>; }
interface Trip { id: number; uuid: string; route_id: number; route_code: string; route_name: string; vehicle_id: number | null; vehicle_registration: string; driver_id: number | null; driver_name: string; planned_departure_at: string | null; planned_arrival_at?: string | null; actual_departure_at?: string | null; actual_arrival_at?: string | null; activity_started_at?: string | null; activity_paused_at?: string | null; activity_closed_at?: string | null; pause_seconds?: number; closure_summary?: TripRevenueSummary; revenue_summary?: TripRevenueSummary; activity_events?: TripActivityEvent[]; status: string; purchases?: TripPurchase[]; validations?: TripValidation[]; travel_passes?: TripPass[]; }
interface RouteOpt { id: number; code: string; name: string; }
interface VehicleOpt { id: number; registration: string; }
interface DriverOpt { id: number; full_name: string; }

export default function TripsPage() {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const navigate = useNavigate();
  const { confirm, dialog: confirmDialog } = useConfirm();
  const loader = useCallback(() => apiFetch("/api/trips/", token!).then((d) => d.results || d), [token]);
  const routeLoader = useCallback(() => apiFetch("/api/routes/", token!).then((d) => d.results || d), [token]);
  const vehicleLoader = useCallback(() => apiFetch("/api/vehicles/", token!).then((d) => d.results || d), [token]);
  const driverLoader = useCallback(() => apiFetch("/api/drivers/", token!).then((d) => d.results || d), [token]);
  const { data: rows, loading, reload } = useAsyncData<Trip[]>(loader, [token]);
  const { data: routeOpts } = useAsyncData<RouteOpt[]>(routeLoader, [token]);
  const { data: vehicleOpts } = useAsyncData<VehicleOpt[]>(vehicleLoader, [token]);
  const { data: driverOpts } = useAsyncData<DriverOpt[]>(driverLoader, [token]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ route: "", vehicle: "", driver: "", planned_departure_at: "", planned_arrival_at: "", status: "scheduled" });
  const f = (k: string, v: string) => setForm((p) => ({ ...p, [k]: v }));
  const reset = () => { setEditId(null); setModalOpen(false); setForm({ route: "", vehicle: "", driver: "", planned_departure_at: "", planned_arrival_at: "", status: "scheduled" }); };

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true);
    const payload = { route: Number(form.route), vehicle: form.vehicle ? Number(form.vehicle) : null, driver: form.driver ? Number(form.driver) : null, planned_departure_at: form.planned_departure_at || null, planned_arrival_at: form.planned_arrival_at || null, status: form.status };
    try {
      if (editId) { await apiPatch(`/api/trips/${editId}/`, token!, payload); } else { await apiPost("/api/trips/", token!, payload); }
      showToast("success", editId ? t(lc, "update") : t(lc, "create")); reset(); reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
    finally { setBusy(false); }
  };

  return (
    <PageFrame kicker={t(lc, "operation")} title={t(lc, "trips")}
      action={<>
        <button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={16} /><span>{t(lc, "refresh")}</span></button>
        <button className="primary-button" onClick={() => { reset(); setModalOpen(true); }} type="button"><Plus size={16} /> {t(lc, "newTrip")}</button>
      </>}>
      <div className="admin-metric-grid">
        <MetricCard label={t(lc, "total")} value={String((rows || []).length)} />
        <MetricCard label={t(lc, "scheduled")} value={String((rows || []).filter((r) => r.status === "scheduled").length)} />
        <MetricCard label={t(lc, "inTransit")} value={String((rows || []).filter((r) => r.status === "departed").length)} />
        <MetricCard label="Em Repouso" value={String((rows || []).filter((r) => r.status === "paused").length)} />
      </div>
      <SectionCard title={t(lc, "trips")}>
        <DataTable columns={[
          { header: t(lc, "route"), render: (r: Trip) => <TablePrimaryCell title={`${r.route_code} - ${r.route_name}`} subtitle={r.vehicle_registration || "-"} meta={r.driver_name || "-"} /> },
          { header: t(lc, "departure"), render: (r: Trip) => formatDateTime(r.planned_departure_at) },
          { header: t(lc, "status"), render: (r: Trip) => <StatusBadge value={r.status} /> },
          { header: t(lc, "actions"), className: "table-actions-cell", render: (r: Trip) => (
            <div className="admin-inline-actions">
              <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => navigate(`/app/trips/${r.id}`)} />
              <TableActionButton icon={<Pencil size={15} />} label={t(lc, "edit")} onClick={() => { setEditId(r.id); setModalOpen(true); setForm({ route: String(r.route_id), vehicle: r.vehicle_id ? String(r.vehicle_id) : "", driver: r.driver_id ? String(r.driver_id) : "", planned_departure_at: r.planned_departure_at || "", planned_arrival_at: "", status: r.status }); }} />
              <TableActionButton icon={<Trash2 size={15} />} label={t(lc, "delete")} onClick={async () => { const ok = await confirm({ title: t(lc, "delete"), message: `Tem a certeza que pretende eliminar a viagem ${r.route_code}?`, tone: "danger" }); if (!ok) return; try { await apiDelete(`/api/trips/${r.id}/`, token!); showToast("success", t(lc, "delete")); reload(); } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); } }} tone="danger" />
            </div>
          )},
        ]} rows={rows || []} rowKey={(r) => r.uuid} loading={loading} emptyMessage={t(lc, "noTrips")} />
      </SectionCard>
      <AdminModal open={modalOpen} onClose={reset} title={editId ? t(lc, "editTrip") : t(lc, "newTrip")}>
        <form className="admin-form" onSubmit={submit}>
          <div className="admin-form-grid">
            <label className="field"><span>{t(lc, "route")}</span><select required value={form.route} onChange={(e) => f("route", e.target.value)}><option value="">{t(lc, "select")}</option>{(routeOpts || []).map((r) => <option key={r.id} value={r.id}>{r.code} — {r.name}</option>)}</select></label>
            <label className="field"><span>{t(lc, "vehicles")}</span><select value={form.vehicle} onChange={(e) => f("vehicle", e.target.value)}><option value="">{t(lc, "select")}</option>{(vehicleOpts || []).map((v) => <option key={v.id} value={v.id}>{v.registration}</option>)}</select></label>
            <label className="field"><span>{t(lc, "drivers")}</span><select value={form.driver} onChange={(e) => f("driver", e.target.value)}><option value="">{t(lc, "select")}</option>{(driverOpts || []).map((d) => <option key={d.id} value={d.id}>{d.full_name}</option>)}</select></label>
            <label className="field"><span>{t(lc, "plannedDeparture")}</span><input type="datetime-local" value={form.planned_departure_at} onChange={(e) => f("planned_departure_at", e.target.value)} /></label>
            <label className="field"><span>{t(lc, "plannedArrival")}</span><input type="datetime-local" value={form.planned_arrival_at} onChange={(e) => f("planned_arrival_at", e.target.value)} /></label>
            <label className="field"><span>{t(lc, "status")}</span><select value={form.status} onChange={(e) => f("status", e.target.value)}><option value="scheduled">Agendada</option><option value="boarding">Em Circulacao</option><option value="departed">Em Viagem</option><option value="paused">Em Repouso</option><option value="completed">Concluida</option><option value="cancelled">Cancelada</option></select></label>
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
