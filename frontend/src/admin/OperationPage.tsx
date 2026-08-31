import { useCallback, useMemo, useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { CalendarClock, Eye, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { apiFetch, apiPost, apiPatch, apiDelete } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { t, type Locale } from "../lib/i18n";
import { mensagemDeErro } from "../lib/errors";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import {
  AdminModal, DataTable, MetricCard, PageFrame, SectionCard, StatusBadge,
  TabBar, TableActionButton, TablePrimaryCell, useAsyncData,
} from "../ui/common";
import { useConfirm } from "../ui/ConfirmDialog";
import SchedulesPage from "./SchedulesPage";

interface Trip {
  id: number; uuid: string;
  route_id: number; route_code: string; route_name: string;
  vehicle_id: number | null; vehicle_registration: string;
  driver_id: number | null; driver_name: string;
  planned_departure_at: string | null;
  /** "outbound" | "inbound" — vazio nas partidas criadas antes do campo. */
  direction: string;
  status: string;
}
interface RouteOpt { id: number; code: string; name: string }
interface VehicleOpt { id: number; registration: string }
interface DriverOpt { id: number; full_name: string }

const EMPTY_TRIP = {
  route: "", vehicle: "", driver: "", direction: "",
  planned_departure_at: "", planned_arrival_at: "", status: "scheduled",
};

/** Para que lado vai a partida.
 *
 *  Uma rota traz as paragens nos dois sentidos; a viagem não trazia nenhum, e
 *  por isso quem procurava Maputo→Nelspruit recebia também as partidas de
 *  Nelspruit→Maputo.
 *
 *  Deixar em branco não é "sem sentido": é deixar a ROTA decidir. Numa rota
 *  definida num só sentido o servidor preenche-o sozinho — não há escolha a
 *  fazer, e perguntar seria pôr o operador a decidir uma coisa já decidida.
 *  Numa rota com ida e volta o servidor recusa e diz que falta, porque uma
 *  partida nova não pode nascer ambígua. */
const sentidos = (lc: Locale) => [
  { key: "", label: t(lc, "autoRouteDecides") },
  { key: "outbound", label: t(lc, "outbound") },
  { key: "inbound", label: t(lc, "inbound") },
];
const dirLabel = (lc: Locale, d: string) =>
  sentidos(lc).find((x) => x.key === d)?.label ?? "";

/** Janelas de tempo para a lista de viagens. O que vem a seguir e o que interessa
 *  no dia-a-dia; o histórico só se procura de propósito. */
const janelas = (lc: Locale) => [
  { key: "upcoming", label: t(lc, "upcoming") },
  { key: "today", label: t(lc, "today") },
  { key: "past", label: t(lc, "past") },
  { key: "all", label: t(lc, "allRoutes") },
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
 * Estavam em dois itens de menu — t(lc, "trips") e "Horários" — e o operador tinha
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
  const { data: schedules, reload: reloadSchedules } = useAsyncData<{ id: number; status: string }[]>(scheduleLoader, [token]);
  const { data: routeOpts } = useAsyncData<RouteOpt[]>(routeLoader, [token]);
  const { data: vehicleOpts } = useAsyncData<VehicleOpt[]>(vehicleLoader, [token]);
  const { data: driverOpts } = useAsyncData<DriverOpt[]>(driverLoader, [token]);

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
      direction: form.direction,
      status: form.status,
    };
    try {
      if (editId) await apiPatch(`/api/trips/${editId}/`, token!, payload);
      else await apiPost("/api/trips/", token!, payload);
      showToast("success", editId ? t(lc, "okTripUpdated") : t(lc, "okTripCreated"));
      reset(); reload(); reloadResumo();
    } catch (err) { showToast("danger", mensagemDeErro(err, lc)); }
    finally { setBusy(false); }
  };

  const removeTrip = async (r: Trip) => {
    const ok = await confirm({
      title: t(lc, "deleteTrip"),
      message: t(lc, "confirmDelete", { n: r.route_code }),
      tone: "danger",
    });
    if (!ok) return;
    try { await apiDelete(`/api/trips/${r.id}/`, token!); showToast("success", t(lc, "okTripDeleted")); reload(); reloadResumo(); }
    catch (err) { showToast("danger", mensagemDeErro(err, lc)); }
  };

  const action = tab === "viagens" ? (
    <>
      <button className="icon-text-button" onClick={reload} type="button">
        <RefreshCw size={16} /><span>{t(lc, "refresh")}</span>
      </button>
      <button className="icon-text-button" onClick={() => navigate("/app/trips/schedule")} type="button">
        <CalendarClock size={16} /><span>{t(lc, "scheduleTrips")}</span>
      </button>
      <button className="primary-button" onClick={() => { reset(); setModalOpen(true); }} type="button">
        <Plus size={16} /> {t(lc, "newTrip")}
      </button>
    </>
  ) : (
    <>
      <button className="icon-text-button" onClick={() => scheduleActions?.reload()} type="button">
        <RefreshCw size={16} /><span>{t(lc, "refresh")}</span>
      </button>
      <button className="icon-text-button" onClick={() => navigate("/app/trips/schedule")} type="button">
        <CalendarClock size={16} /><span>{t(lc, "scheduleTrips")}</span>
      </button>
      <button className="primary-button" onClick={() => scheduleActions?.create()} type="button">
        <Plus size={16} /> {t(lc, "newSchedule")}
      </button>
    </>
  );

  return (
    <PageFrame kicker={t(lc, "operation")} title={t(lc, "tripsAndSchedules")} action={action}>
      <TabBar
        items={[
          { key: "viagens", label: t(lc, "trips"), count: all.length },
          { key: "programacoes", label: t(lc, "schedulesTab"), count: (schedules || []).length },
        ]}
        value={tab}
        onChange={setTab}
      />

      {tab === "viagens" ? (
        <>
          <div className="admin-metric-grid">
            <MetricCard label={t(lc, "today")} value={String(counts.hoje)} />
            <MetricCard label={t(lc, "running")} value={String(counts.circulacao)} />
            <MetricCard label={t(lc, "scheduledPl")} value={String(counts.agendadas)} />
            <MetricCard label={t(lc, "idle")} value={String(counts.repouso)} />
          </div>

          <SectionCard
            title={t(lc, "trips")}
            description={t(lc, "tripsHint")}
          >
            <div className="bztw-horizons" style={{ marginBottom: 12 }}>
              {janelas(lc).map((w) => (
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
                { header: t(lc, "direction"), render: (r: Trip) => (
                  r.direction
                    ? <span>{dirLabel(lc, r.direction)}</span>
                    : <span className="text-muted" title={t(lc, "noDirectionHint")}>—</span>
                ) },
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
                          direction: r.direction || "",
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

      <AdminModal open={modalOpen} onClose={reset} title={editId ? "Editar viagem" : t(lc, "newTrip")}
        description={t(lc, "newTripHint")}>
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
            <label className="field"><span>{t(lc, "direction")}</span>
              <select value={form.direction} onChange={(e) => f("direction", e.target.value)}>
                {sentidos(lc).map((d) => <option key={d.key} value={d.key}>{d.label}</option>)}
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
                <option value="scheduled">{t(lc, "scheduled")}</option>
                <option value="boarding">{t(lc, "running")}</option>
                <option value="departed">{t(lc, "onTheRoad")}</option>
                <option value="paused">{t(lc, "idle")}</option>
                <option value="completed">{t(lc, "completed")}</option>
                <option value="cancelled">{t(lc, "cancelledF")}</option>
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
