import { useCallback, useMemo, useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { CalendarClock, Eye, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { apiFetch, apiPost, apiPatch, apiDelete } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import {
  AdminModal, DataTable, MetricCard, PageFrame, SectionCard, StatusBadge,
  TabBar, TableActionButton, TablePrimaryCell, useAsyncData,
} from "../ui/common";
import { useConfirm } from "../ui/ConfirmDialog";
import SchedulesPage from "./SchedulesPage";
import ScheduleTripsWizard, { type ScheduleOption } from "./ScheduleTripsWizard";

interface Trip {
  id: number; uuid: string;
  route_id: number; route_code: string; route_name: string;
  vehicle_id: number | null; vehicle_registration: string;
  driver_id: number | null; driver_name: string;
  planned_departure_at: string | null;
  status: string;
}
interface RouteOpt { id: number; code: string; name: string }
interface VehicleOpt { id: number; registration: string }
interface DriverOpt { id: number; full_name: string }

const EMPTY_TRIP = {
  route: "", vehicle: "", driver: "",
  planned_departure_at: "", planned_arrival_at: "", status: "scheduled",
};

/** Janelas de tempo para a lista de viagens. "Próximas" é o que interessa
 *  no dia-a-dia; o histórico só se procura de propósito. */
const WHEN_FILTERS = [
  { key: "upcoming", label: "Próximas" },
  { key: "today", label: "Hoje" },
  { key: "past", label: "Passadas" },
  { key: "all", label: "Todas" },
];

function dayBounds(offset = 0): [Date, Date] {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  start.setDate(start.getDate() + offset);
  const end = new Date(start);
  end.setDate(end.getDate() + 1);
  return [start, end];
}

/**
 * Operação: viagens e as programações que as geram, no mesmo sítio.
 *
 * Estavam em dois itens de menu — "Viagens" e "Horários" — e o operador tinha
 * de saber que as viagens nascem dos horários para perceber onde ir. São a
 * mesma tarefa vista de dois ângulos, por isso vivem em separadores, e a
 * programação (criar viagens a partir dos horários) é uma acção da página,
 * não uma funcionalidade escondida dentro de um dos lados.
 */
export default function OperationPage() {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const navigate = useNavigate();
  const { confirm, dialog: confirmDialog } = useConfirm();
  const [params, setParams] = useSearchParams();

  const tab = params.get("tab") === "programacoes" ? "programacoes" : "viagens";
  const setTab = (key: string) => {
    const next = new URLSearchParams(params);
    if (key === "viagens") next.delete("tab"); else next.set("tab", key);
    setParams(next, { replace: true });
  };

  const [when, setWhen] = useState("upcoming");
  // O período é decidido no servidor. Filtrar no browser só recortava a página
  // que tinha vindo — e com milhares de viagens essa página era só futuro
  // distante, o que fazia parecer que só existiam viagens agendadas.
  const PERIODO: Record<string, string> = {
    upcoming: "proximas", today: "hoje", past: "passadas", all: "todas",
  };
  const tripLoader = useCallback(
    () => apiFetch(`/api/trips/?when=${PERIODO[when] || "proximas"}`, token!).then((d) => d.results || d),
    [token, when],
  );
  const summaryLoader = useCallback(() => apiFetch("/api/trips/summary/", token!), [token]);
  const scheduleLoader = useCallback(() => apiFetch("/api/schedules/", token!).then((d) => d.results || d), [token]);
  const routeLoader = useCallback(() => apiFetch("/api/routes/", token!).then((d) => d.results || d), [token]);
  const vehicleLoader = useCallback(() => apiFetch("/api/vehicles/", token!).then((d) => d.results || d), [token]);
  const driverLoader = useCallback(() => apiFetch("/api/drivers/", token!).then((d) => d.results || d), [token]);

  const { data: trips, loading, reload } = useAsyncData<Trip[]>(tripLoader, [token, when]);
  const { data: resumo, reload: reloadResumo } = useAsyncData<Record<string, number>>(summaryLoader, [token]);
  const { data: schedules, reload: reloadSchedules } = useAsyncData<ScheduleOption[]>(scheduleLoader, [token]);
  const { data: routeOpts } = useAsyncData<RouteOpt[]>(routeLoader, [token]);
  const { data: vehicleOpts } = useAsyncData<VehicleOpt[]>(vehicleLoader, [token]);
  const { data: driverOpts } = useAsyncData<DriverOpt[]>(driverLoader, [token]);

  const [wizardOpen, setWizardOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ ...EMPTY_TRIP });
  const f = (k: string, v: string) => setForm((p) => ({ ...p, [k]: v }));
  const reset = () => { setEditId(null); setModalOpen(false); setForm({ ...EMPTY_TRIP }); };

  // Acções da aba de programações, entregues pela página embutida.
  const [scheduleActions, setScheduleActions] = useState<{ create: () => void; reload: () => void } | null>(null);
  const registerScheduleActions = useCallback(
    (a: { create: () => void; reload: () => void }) => setScheduleActions(a), []);

  const all = useMemo(() => trips || [], [trips]);

  const visible = all;

  const counts = useMemo(() => ({
    hoje: resumo?.hoje ?? 0,
    circulacao: resumo?.circulacao ?? 0,
    agendadas: resumo?.agendadas ?? 0,
    repouso: resumo?.repouso ?? 0,
  }), [resumo]);

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true);
    const payload = {
      route: Number(form.route),
      vehicle: form.vehicle ? Number(form.vehicle) : null,
      driver: form.driver ? Number(form.driver) : null,
      planned_departure_at: form.planned_departure_at || null,
      planned_arrival_at: form.planned_arrival_at || null,
      status: form.status,
    };
    try {
      if (editId) await apiPatch(`/api/trips/${editId}/`, token!, payload);
      else await apiPost("/api/trips/", token!, payload);
      showToast("success", editId ? "Viagem actualizada." : "Viagem criada.");
      reset(); reload(); reloadResumo();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
    finally { setBusy(false); }
  };

  const removeTrip = async (r: Trip) => {
    const ok = await confirm({
      title: "Eliminar viagem",
      message: `Tem a certeza que pretende eliminar a viagem ${r.route_code}?`,
      tone: "danger",
    });
    if (!ok) return;
    try { await apiDelete(`/api/trips/${r.id}/`, token!); showToast("success", "Viagem eliminada."); reload(); reloadResumo(); }
    catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
  };

  const action = tab === "viagens" ? (
    <>
      <button className="icon-text-button" onClick={reload} type="button">
        <RefreshCw size={16} /><span>{t(lc, "refresh")}</span>
      </button>
      <button className="icon-text-button" onClick={() => setWizardOpen(true)} type="button">
        <CalendarClock size={16} /><span>Programar viagens</span>
      </button>
      <button className="primary-button" onClick={() => { reset(); setModalOpen(true); }} type="button">
        <Plus size={16} /> Nova viagem
      </button>
    </>
  ) : (
    <>
      <button className="icon-text-button" onClick={() => scheduleActions?.reload()} type="button">
        <RefreshCw size={16} /><span>{t(lc, "refresh")}</span>
      </button>
      <button className="icon-text-button" onClick={() => setWizardOpen(true)} type="button">
        <CalendarClock size={16} /><span>Programar viagens</span>
      </button>
      <button className="primary-button" onClick={() => scheduleActions?.create()} type="button">
        <Plus size={16} /> Novo horário
      </button>
    </>
  );

  return (
    <PageFrame kicker={t(lc, "operation")} title="Viagens e horários" action={action}>
      <TabBar
        items={[
          { key: "viagens", label: "Viagens", count: all.length },
          { key: "programacoes", label: "Programações", count: (schedules || []).length },
        ]}
        value={tab}
        onChange={setTab}
      />

      {tab === "viagens" ? (
        <>
          <div className="admin-metric-grid">
            <MetricCard label="Hoje" value={String(counts.hoje)} />
            <MetricCard label="Em circulação" value={String(counts.circulacao)} />
            <MetricCard label="Agendadas" value={String(counts.agendadas)} />
            <MetricCard label="Em repouso" value={String(counts.repouso)} />
          </div>

          <SectionCard
            title="Viagens"
            description="Partidas concretas. Nascem das programações ou são criadas à mão."
          >
            <div className="bztw-horizons" style={{ marginBottom: 12 }}>
              {WHEN_FILTERS.map((w) => (
                <button
                  key={w.key}
                  type="button"
                  className={`bztw-chip${when === w.key ? " is-on" : ""}`}
                  onClick={() => setWhen(w.key)}
                >
                  {w.label}
                </button>
              ))}
            </div>
            <DataTable
              columns={[
                { header: t(lc, "route"), render: (r: Trip) => (
                  <TablePrimaryCell
                    title={`${r.route_code} - ${r.route_name}`}
                    subtitle={r.vehicle_registration || "-"}
                    meta={r.driver_name || "-"}
                  />
                ) },
                { header: t(lc, "departure"), render: (r: Trip) => formatDateTime(r.planned_departure_at) },
                { header: t(lc, "status"), render: (r: Trip) => <StatusBadge value={r.status} /> },
                { header: t(lc, "actions"), className: "table-actions-cell", render: (r: Trip) => (
                  <div className="admin-inline-actions">
                    <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")}
                      onClick={() => navigate(`/app/trips/${r.id}`)} />
                    <TableActionButton icon={<Pencil size={15} />} label={t(lc, "edit")}
                      onClick={() => {
                        setEditId(r.id); setModalOpen(true);
                        setForm({
                          route: String(r.route_id),
                          vehicle: r.vehicle_id ? String(r.vehicle_id) : "",
                          driver: r.driver_id ? String(r.driver_id) : "",
                          planned_departure_at: r.planned_departure_at || "",
                          planned_arrival_at: "",
                          status: r.status,
                        });
                      }} />
                    <TableActionButton icon={<Trash2 size={15} />} label={t(lc, "delete")}
                      onClick={() => removeTrip(r)} tone="danger" />
                  </div>
                ) },
              ]}
              rows={visible}
              rowKey={(r) => r.uuid}
              loading={loading}
              emptyMessage={
                when === "upcoming"
                  ? "Sem viagens futuras. Use «Programar viagens» para as criar a partir dos horários."
                  : t(lc, "noTrips")
              }
            />
          </SectionCard>
        </>
      ) : (
        <SchedulesPage
          embedded
          onChanged={() => { reloadSchedules(); reload(); reloadResumo(); }}
          registerActions={registerScheduleActions}
        />
      )}

      <ScheduleTripsWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        schedules={schedules || []}
        routes={routeOpts || []}
        vehicles={vehicleOpts || []}
        drivers={driverOpts || []}
        onGenerated={() => { reload(); reloadSchedules(); reloadResumo(); }}
      />

      <AdminModal open={modalOpen} onClose={reset} title={editId ? "Editar viagem" : "Nova viagem"}
        description="Uma partida avulsa. Para uma série regular, crie um horário e use «Programar viagens».">
        <form className="admin-form" onSubmit={submit}>
          <div className="admin-form-grid">
            <label className="field"><span>{t(lc, "route")}</span>
              <select required value={form.route} onChange={(e) => f("route", e.target.value)}>
                <option value="">{t(lc, "select")}</option>
                {(routeOpts || []).map((r) => <option key={r.id} value={r.id}>{r.code} — {r.name}</option>)}
              </select>
            </label>
            <label className="field"><span>{t(lc, "vehicles")}</span>
              <select value={form.vehicle} onChange={(e) => f("vehicle", e.target.value)}>
                <option value="">{t(lc, "select")}</option>
                {(vehicleOpts || []).map((v) => <option key={v.id} value={v.id}>{v.registration}</option>)}
              </select>
            </label>
            <label className="field"><span>{t(lc, "drivers")}</span>
              <select value={form.driver} onChange={(e) => f("driver", e.target.value)}>
                <option value="">{t(lc, "select")}</option>
                {(driverOpts || []).map((d) => <option key={d.id} value={d.id}>{d.full_name}</option>)}
              </select>
            </label>
            <label className="field"><span>{t(lc, "plannedDeparture")}</span>
              <input type="datetime-local" value={form.planned_departure_at}
                onChange={(e) => f("planned_departure_at", e.target.value)} />
            </label>
            <label className="field"><span>{t(lc, "plannedArrival")}</span>
              <input type="datetime-local" value={form.planned_arrival_at}
                onChange={(e) => f("planned_arrival_at", e.target.value)} />
            </label>
            <label className="field"><span>{t(lc, "status")}</span>
              <select value={form.status} onChange={(e) => f("status", e.target.value)}>
                <option value="scheduled">Agendada</option>
                <option value="boarding">Em Circulacao</option>
                <option value="departed">Em Viagem</option>
                <option value="paused">Em Repouso</option>
                <option value="completed">Concluida</option>
                <option value="cancelled">Cancelada</option>
              </select>
            </label>
          </div>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy} type="submit">
              {busy ? t(lc, "saving") : editId ? t(lc, "update") : t(lc, "create")}
            </button>
            <button className="secondary-button" onClick={reset} type="button">{t(lc, "cancel")}</button>
          </div>
        </form>
      </AdminModal>
      {confirmDialog}
    </PageFrame>
  );
}
