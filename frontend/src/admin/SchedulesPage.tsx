import { useCallback, useEffect, useState, type FormEvent } from "react";
import { CalendarClock, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { apiFetch, apiPost, apiPatch, apiDelete } from "../lib/api";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { AdminModal, DataTable, PageFrame, SectionCard, StatusBadge, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { useConfirm } from "../ui/ConfirmDialog";

interface Schedule {
  id: number;
  uuid: string;
  route_id: number;
  route_code: string;
  route_name: string;
  vehicle_id: number | null;
  vehicle_registration: string;
  driver_id: number | null;
  driver_name: string;
  agent_id: number | null;
  agent_name: string;
  start_time: string;
  end_time: string;
  frequency_minutes: number;
  days_of_week: number[];
  status: string;
  created_at: string;
}

interface RouteOption { id: number; code: string; name: string; }
interface VehicleOption { id: number; registration: string; }
interface PersonOption { id: number; full_name: string; }

// Ordem alinhada com Python date.weekday(): 0=Segunda ... 6=Domingo.
const DAY_LABELS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

function formatDays(days: number[] | null | undefined): string {
  if (!days || days.length === 0 || days.length === 7) return "Todos os dias";
  return [...days].sort((a, b) => a - b).map((d) => DAY_LABELS[d] ?? String(d)).join(", ");
}

function formatTime(value: string | null | undefined): string {
  return value ? value.slice(0, 5) : "--:--";
}

const EMPTY_FORM = {
  route_id: "",
  vehicle_id: "",
  driver_id: "",
  agent_id: "",
  start_time: "06:00",
  end_time: "20:00",
  frequency_minutes: "30",
  days: [] as number[],
  status: "active",
};

export default function SchedulesPage({ embedded }: { embedded?: boolean }) {
  void embedded;
  const { token } = useAuth();
  const { confirm, dialog: confirmDialog } = useConfirm();

  const loader = useCallback(() => apiFetch("/api/schedules/", token!).then((d) => d.results || d), [token]);
  const { data: rows, loading, reload } = useAsyncData<Schedule[]>(loader, [token]);

  const [routes, setRoutes] = useState<RouteOption[]>([]);
  const [vehicles, setVehicles] = useState<VehicleOption[]>([]);
  const [drivers, setDrivers] = useState<PersonOption[]>([]);
  const [agents, setAgents] = useState<PersonOption[]>([]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    Promise.all([
      apiFetch("/api/routes/", token).then((d) => d.results || d).catch(() => []),
      apiFetch("/api/vehicles/", token).then((d) => d.results || d).catch(() => []),
      apiFetch("/api/drivers/", token).then((d) => d.results || d).catch(() => []),
      apiFetch("/api/agents/", token).then((d) => d.results || d).catch(() => []),
    ]).then(([r, v, dr, ag]) => {
      if (cancelled) return;
      setRoutes(r);
      setVehicles(v);
      setDrivers(dr);
      setAgents(ag);
    });
    return () => { cancelled = true; };
  }, [token]);

  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const f = (k: string, v: string) => setForm((p) => ({ ...p, [k]: v }));
  const toggleDay = (d: number) => setForm((p) => ({ ...p, days: p.days.includes(d) ? p.days.filter((x) => x !== d) : [...p.days, d] }));
  const reset = () => { setEditId(null); setModalOpen(false); setForm({ ...EMPTY_FORM }); };

  const openEdit = (r: Schedule) => {
    setEditId(r.id);
    setModalOpen(true);
    setForm({
      route_id: String(r.route_id ?? ""),
      vehicle_id: r.vehicle_id ? String(r.vehicle_id) : "",
      driver_id: r.driver_id ? String(r.driver_id) : "",
      agent_id: r.agent_id ? String(r.agent_id) : "",
      start_time: formatTime(r.start_time),
      end_time: formatTime(r.end_time),
      frequency_minutes: String(r.frequency_minutes ?? 30),
      days: Array.isArray(r.days_of_week) ? [...r.days_of_week] : [],
      status: r.status || "active",
    });
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.route_id) { showToast("danger", "Seleccione a rota."); return; }
    setBusy(true);
    try {
      const vehicle = form.vehicle_id ? Number(form.vehicle_id) : null;
      const driver = form.driver_id ? Number(form.driver_id) : null;
      const agent = form.agent_id ? Number(form.agent_id) : null;
      // Enviamos ambas as formas (route e route_id) para cobrir as duas
      // convenções de escrita do serializer no backend.
      const payload = {
        route: Number(form.route_id), route_id: Number(form.route_id),
        vehicle, vehicle_id: vehicle,
        driver, driver_id: driver,
        agent, agent_id: agent,
        start_time: form.start_time,
        end_time: form.end_time,
        frequency_minutes: Number(form.frequency_minutes) || 30,
        days_of_week: [...form.days].sort((a, b) => a - b),
        status: form.status,
      };
      if (editId) { await apiPatch(`/api/schedules/${editId}/`, token!, payload); showToast("success", "Horário actualizado."); }
      else { await apiPost("/api/schedules/", token!, payload); showToast("success", "Horário criado."); }
      reset(); reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
    finally { setBusy(false); }
  };

  const remove = async (r: Schedule) => {
    const ok = await confirm({
      title: "Eliminar horário",
      message: `Tem a certeza que pretende eliminar o horário da rota ${r.route_code} (${formatTime(r.start_time)}–${formatTime(r.end_time)})?`,
      tone: "danger",
    });
    if (!ok) return;
    try { await apiDelete(`/api/schedules/${r.id}/`, token!); showToast("success", "Horário eliminado."); reload(); }
    catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
  };

  // --- Geração de viagens -------------------------------------------------
  const [genOpen, setGenOpen] = useState(false);
  const [genBusy, setGenBusy] = useState(false);
  const [genScheduleId, setGenScheduleId] = useState<string>("all");
  const today = new Date().toLocaleDateString("pt-PT", { weekday: "long", day: "2-digit", month: "2-digit", year: "numeric" });

  const generate = async (e: FormEvent) => {
    e.preventDefault();
    const all = rows || [];
    const targets = genScheduleId === "all"
      ? all.filter((s) => s.status === "active")
      : all.filter((s) => String(s.id) === genScheduleId);
    if (targets.length === 0) { showToast("danger", "Nenhum horário activo para gerar viagens."); return; }
    setGenBusy(true);
    try {
      let total = 0;
      let failures = 0;
      for (const s of targets) {
        try {
          const res = await apiPost("/api/trips/generate/", token!, { schedule_id: s.id });
          total += Number(res?.generated ?? 0);
        } catch { failures += 1; }
      }
      if (failures > 0 && total === 0) showToast("danger", "Não foi possível gerar viagens.");
      else showToast("success", `${total} viagem(ns) criada(s) para hoje${failures ? ` (${failures} horário(s) com erro)` : ""}.`);
      setGenOpen(false);
    } finally { setGenBusy(false); }
  };

  return (
    <PageFrame kicker="Operação" title="Horários"
      action={<>
        <button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={16} /><span>Actualizar</span></button>
        <button className="icon-text-button" onClick={() => { setGenScheduleId("all"); setGenOpen(true); }} type="button"><CalendarClock size={16} /><span>Gerar viagens</span></button>
        <button className="primary-button" onClick={() => { reset(); setModalOpen(true); }} type="button"><Plus size={16} /> Novo horário</button>
      </>}>
      <SectionCard title="Horários" description="Programações recorrentes por rota, usadas para gerar as viagens do dia.">
        <DataTable columns={[
          { header: "Rota", render: (r: Schedule) => <TablePrimaryCell title={`${r.route_code} - ${r.route_name}`} subtitle={r.agent_name ? `Agente: ${r.agent_name}` : undefined} /> },
          { header: "Veículo", render: (r: Schedule) => r.vehicle_registration || "-" },
          { header: "Motorista", render: (r: Schedule) => r.driver_name || "-" },
          { header: "Janela", render: (r: Schedule) => `${formatTime(r.start_time)} – ${formatTime(r.end_time)}` },
          { header: "Frequência", render: (r: Schedule) => `${r.frequency_minutes} min` },
          { header: "Dias", render: (r: Schedule) => formatDays(r.days_of_week) },
          { header: "Estado", render: (r: Schedule) => <StatusBadge value={r.status} /> },
          { header: "Acções", className: "table-actions-cell", render: (r: Schedule) => (
            <div className="admin-inline-actions">
              <TableActionButton icon={<Pencil size={15} />} label="Editar" onClick={() => openEdit(r)} />
              <TableActionButton icon={<Trash2 size={15} />} label="Eliminar" onClick={() => remove(r)} tone="danger" />
            </div>
          )},
        ]} rows={rows || []} rowKey={(r) => r.uuid} loading={loading} emptyMessage="Sem horários registados." />
      </SectionCard>

      <AdminModal open={modalOpen} onClose={reset} title={editId ? "Editar horário" : "Novo horário"}>
        <form className="admin-form" onSubmit={submit}>
          <div className="admin-form-grid">
            <label className="field"><span>Rota</span>
              <select required value={form.route_id} onChange={(e) => f("route_id", e.target.value)}>
                <option value="">Seleccione...</option>
                {routes.map((r) => <option key={r.id} value={r.id}>{r.code} - {r.name}</option>)}
              </select>
            </label>
            <label className="field"><span>Veículo</span>
              <select value={form.vehicle_id} onChange={(e) => f("vehicle_id", e.target.value)}>
                <option value="">Sem veículo</option>
                {vehicles.map((v) => <option key={v.id} value={v.id}>{v.registration}</option>)}
              </select>
            </label>
            <label className="field"><span>Motorista (opcional)</span>
              <select value={form.driver_id} onChange={(e) => f("driver_id", e.target.value)}>
                <option value="">Sem motorista</option>
                {drivers.map((d) => <option key={d.id} value={d.id}>{d.full_name}</option>)}
              </select>
            </label>
            <label className="field"><span>Agente (opcional)</span>
              <select value={form.agent_id} onChange={(e) => f("agent_id", e.target.value)}>
                <option value="">Sem agente</option>
                {agents.map((a) => <option key={a.id} value={a.id}>{a.full_name}</option>)}
              </select>
            </label>
            <label className="field"><span>Hora de início</span><input required type="time" value={form.start_time} onChange={(e) => f("start_time", e.target.value)} /></label>
            <label className="field"><span>Hora de fim</span><input required type="time" value={form.end_time} onChange={(e) => f("end_time", e.target.value)} /></label>
            <label className="field"><span>Frequência (minutos)</span><input required type="number" min={1} step={1} value={form.frequency_minutes} onChange={(e) => f("frequency_minutes", e.target.value)} /></label>
            <label className="field"><span>Estado</span>
              <select value={form.status} onChange={(e) => f("status", e.target.value)}>
                <option value="active">Activo</option>
                <option value="inactive">Inactivo</option>
              </select>
            </label>
          </div>
          <div className="field">
            <span>Dias da semana</span>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", marginTop: "0.35rem" }}>
              {DAY_LABELS.map((label, idx) => (
                <label key={label} style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem", cursor: "pointer" }}>
                  <input type="checkbox" checked={form.days.includes(idx)} onChange={() => toggleDay(idx)} />
                  <span>{label}</span>
                </label>
              ))}
            </div>
            <small style={{ opacity: 0.7 }}>Sem dias seleccionados = todos os dias.</small>
          </div>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy} type="submit">{busy ? "A guardar..." : editId ? "Actualizar" : "Criar"}</button>
            <button className="secondary-button" onClick={reset} type="button">Cancelar</button>
          </div>
        </form>
      </AdminModal>

      <AdminModal open={genOpen} onClose={() => setGenOpen(false)} title="Gerar viagens do dia"
        description="Cria as viagens do dia de hoje a partir dos horários activos (viagens já existentes não são duplicadas).">
        <form className="admin-form" onSubmit={generate}>
          <div className="admin-form-grid">
            <label className="field"><span>Data</span><input type="text" value={today} readOnly disabled /></label>
            <label className="field"><span>Horário</span>
              <select value={genScheduleId} onChange={(e) => setGenScheduleId(e.target.value)}>
                <option value="all">Todos os horários activos</option>
                {(rows || []).map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.route_code} · {formatTime(s.start_time)}–{formatTime(s.end_time)} · {formatDays(s.days_of_week)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <small style={{ opacity: 0.7 }}>As viagens são sempre geradas para o dia actual; horários cujo dia da semana não inclui hoje não produzem viagens.</small>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={genBusy} type="submit">{genBusy ? "A gerar..." : "Gerar viagens"}</button>
            <button className="secondary-button" onClick={() => setGenOpen(false)} type="button">Cancelar</button>
          </div>
        </form>
      </AdminModal>
      {confirmDialog}
    </PageFrame>
  );
}
