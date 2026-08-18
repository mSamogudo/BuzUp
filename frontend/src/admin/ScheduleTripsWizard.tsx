import { useCallback, useEffect, useState, type FormEvent } from "react";
import { CalendarRange, CheckCircle2, Loader2, Sparkles, TriangleAlert } from "lucide-react";
import { apiPost } from "../lib/api";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { AdminModal } from "../ui/common";
import TripCalendar from "./TripCalendar";

export interface RouteOption { id: number; code: string; name: string; }
export interface VehicleOption { id: number; registration: string; }
export interface PersonOption { id: number; full_name: string; }

interface CalendarPreview {
  would_generate: number;
  already_scheduled: number;
  by_day: { date: string; count: number; existing: number }[];
}

export interface ScheduleOption {
  id: number;
  route_code: string;
  route_name: string;
  start_time: string;
  end_time: string;
  days_of_week: number[];
  status: string;
}

interface PreviewDay { date: string; count: number }
interface PreviewSchedule { schedule_id: number; route_code: string; route_name: string; count: number }
interface PreviewResult {
  would_generate: number;
  days: number;
  date_from: string;
  date_to: string;
  schedules_considered: number;
  by_day: PreviewDay[];
  by_schedule: PreviewSchedule[];
}

const DAY_LABELS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

function todayISO(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function humanDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("pt-PT", {
    weekday: "short", day: "2-digit", month: "short",
  });
}

/** Atalhos de horizonte: o operador raramente quer "13 dias". */
const HORIZONS = [
  { days: 1, label: "Hoje" },
  { days: 7, label: "7 dias" },
  { days: 14, label: "14 dias" },
  { days: 30, label: "30 dias" },
];

/**
 * Assistente de programação de viagens.
 *
 * A geração era um botão que criava viagens do dia e dizia um número no fim —
 * o operador só sabia o que ia acontecer depois de acontecer. Aqui escolhe-se
 * o horário e o horizonte, vê-se **quantas viagens nascem em cada dia** e só
 * depois se confirma. O número mostrado vem do próprio servidor em modo de
 * pré-visualização, com as mesmas regras da geração real.
 */
export default function ScheduleTripsWizard({
  open, onClose, schedules, onGenerated, routes = [], vehicles = [], drivers = [],
}: {
  open: boolean;
  onClose: () => void;
  schedules: ScheduleOption[];
  onGenerated: () => void;
  routes?: RouteOption[];
  vehicles?: VehicleOption[];
  drivers?: PersonOption[];
}) {
  const { token } = useAuth();
  // Por omissão o calendário: é o único caminho que funciona sem haver
  // horários criados, e é como se programa uma carreira que sai uma vez por
  // dia. O horário recorrente continua ali para as carreiras urbanas.
  const [mode, setMode] = useState<"calendario" | "horario">("calendario");
  const [calRoute, setCalRoute] = useState("");
  const [calVehicle, setCalVehicle] = useState("");
  const [calDriver, setCalDriver] = useState("");
  const [calTimes, setCalTimes] = useState<string[]>(["05:00"]);
  const [calDates, setCalDates] = useState<string[]>([]);
  const [calDuration, setCalDuration] = useState("");
  const [calPreview, setCalPreview] = useState<CalendarPreview | null>(null);
  const [scheduleId, setScheduleId] = useState<string>("all");
  const [dateFrom, setDateFrom] = useState<string>(todayISO());
  const [days, setDays] = useState<number>(7);
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const activeCount = schedules.filter((s) => s.status === "active").length;

  const loadPreview = useCallback(async () => {
    if (!token || !open) return;
    setLoading(true);
    setError("");
    try {
      const body: Record<string, unknown> = { days, date_from: dateFrom, preview: true };
      if (scheduleId !== "all") body.schedule_id = Number(scheduleId);
      const res = await apiPost("/api/trips/generate/", token, body);
      setPreview(res as PreviewResult);
    } catch (err) {
      setPreview(null);
      setError(err instanceof Error ? err.message : "Não foi possível pré-visualizar.");
    } finally {
      setLoading(false);
    }
  }, [token, open, days, dateFrom, scheduleId]);

  // A pré-visualização acompanha as escolhas: mudar o horizonte actualiza o
  // número sem obrigar a carregar em nada.
  useEffect(() => {
    if (!open) return;
    const id = window.setTimeout(() => { void loadPreview(); }, 220);
    return () => window.clearTimeout(id);
  }, [open, loadPreview]);

  useEffect(() => {
    if (!open) return;
    setScheduleId("all"); setDays(7); setDateFrom(todayISO()); setPreview(null);
    setMode(schedules.some((s) => s.status === "active") ? "calendario" : "calendario");
    setCalRoute(routes.length === 1 ? String(routes[0].id) : "");
    setCalVehicle(""); setCalDriver(""); setCalTimes(["05:00"]);
    setCalDates([]); setCalDuration(""); setCalPreview(null); setError("");
    // Só quando o modal abre: reabrir limpo é o comportamento esperado, mas
    // seguir `routes`/`schedules` faria o formulário saltar a meio da escolha.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // --- Modo calendário ------------------------------------------------
  const calBody = useCallback((preview: boolean) => ({
    route_id: Number(calRoute),
    vehicle_id: calVehicle ? Number(calVehicle) : null,
    driver_id: calDriver ? Number(calDriver) : null,
    dates: calDates,
    times: calTimes.filter(Boolean),
    duration_minutes: calDuration ? Number(calDuration) : null,
    preview,
  }), [calRoute, calVehicle, calDriver, calDates, calTimes, calDuration]);

  const calReady = calRoute !== "" && calDates.length > 0 && calTimes.filter(Boolean).length > 0;

  useEffect(() => {
    if (!open || mode !== "calendario" || !calReady || !token) { setCalPreview(null); return; }
    let cancelado = false;
    const id = window.setTimeout(() => {
      setLoading(true);
      apiPost("/api/trips/schedule-days/", token, calBody(true))
        .then((r) => { if (!cancelado) { setCalPreview(r as CalendarPreview); setError(""); } })
        .catch((e) => { if (!cancelado) { setCalPreview(null); setError(e instanceof Error ? e.message : "Erro"); } })
        .finally(() => { if (!cancelado) setLoading(false); });
    }, 220);
    return () => { cancelado = true; window.clearTimeout(id); };
  }, [open, mode, calReady, calBody, token]);

  const criarPorCalendario = async () => {
    setBusy(true);
    try {
      const res = await apiPost("/api/trips/schedule-days/", token!, calBody(false));
      const n = Number(res?.created ?? 0);
      showToast("success", n > 0
        ? `${n} partida(s) programada(s).`
        : "Nada a criar: estas partidas já existem.");
      onGenerated();
      onClose();
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro ao programar partidas.");
    } finally {
      setBusy(false);
    }
  };

  /** Dias que já têm partida programada — o calendário marca-os com um ponto. */
  const jaProgramados = new Set(
    (calPreview?.by_day || []).filter((d) => d.existing > 0).map((d) => d.date),
  );

  const confirm = async (e: FormEvent) => {
    e.preventDefault();
    if (!preview || preview.would_generate === 0) return;
    setBusy(true);
    try {
      const body: Record<string, unknown> = { days, date_from: dateFrom };
      if (scheduleId !== "all") body.schedule_id = Number(scheduleId);
      const res = await apiPost("/api/trips/generate/", token!, body);
      const n = Number(res?.generated ?? 0);
      showToast("success", `${n} viagem(ns) programada(s).`);
      onGenerated();
      onClose();
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro ao programar viagens.");
    } finally {
      setBusy(false);
    }
  };

  const maxDay = preview ? Math.max(1, ...preview.by_day.map((d) => d.count)) : 1;
  const nothing = preview !== null && preview.would_generate === 0;

  return (
    <AdminModal
      open={open}
      onClose={onClose}
      title="Programar viagens"
      description="Marque os dias no calendário, ou gere a partir de um horário recorrente. Vê quantas partidas nascem antes de confirmar."
    >
      <div className="bztw-modes" role="tablist" aria-label="Modo de programação">
        <button type="button" role="tab" aria-selected={mode === "calendario"}
          className={`bztw-mode${mode === "calendario" ? " is-on" : ""}`}
          onClick={() => { setMode("calendario"); setError(""); }}>
          Calendário
        </button>
        <button type="button" role="tab" aria-selected={mode === "horario"}
          className={`bztw-mode${mode === "horario" ? " is-on" : ""}`}
          onClick={() => { setMode("horario"); setError(""); }}>
          Horário recorrente {activeCount > 0 ? `(${activeCount})` : ""}
        </button>
      </div>

      {mode === "calendario" ? (
        <form className="admin-form" onSubmit={(e) => { e.preventDefault(); void criarPorCalendario(); }}>
          <div className="admin-form-grid">
            <label className="field">
              <span>Rota</span>
              <select required value={calRoute} onChange={(e) => setCalRoute(e.target.value)}>
                <option value="">Escolher…</option>
                {routes.map((r) => <option key={r.id} value={r.id}>{r.code} — {r.name}</option>)}
              </select>
            </label>
            <label className="field">
              <span>Autocarro</span>
              <select value={calVehicle} onChange={(e) => setCalVehicle(e.target.value)}>
                <option value="">Sem autocarro atribuído</option>
                {vehicles.map((v) => <option key={v.id} value={v.id}>{v.registration}</option>)}
              </select>
            </label>
            <label className="field">
              <span>Motorista</span>
              <select value={calDriver} onChange={(e) => setCalDriver(e.target.value)}>
                <option value="">Sem motorista atribuído</option>
                {drivers.map((d) => <option key={d.id} value={d.id}>{d.full_name}</option>)}
              </select>
            </label>
            <label className="field">
              <span>Duração da viagem (min)</span>
              <input type="number" min={1} max={2880} placeholder="ex.: 270"
                value={calDuration} onChange={(e) => setCalDuration(e.target.value)} />
            </label>
          </div>

          <div className="field">
            <span>Hora(s) de partida</span>
            <div className="bztw-times">
              {calTimes.map((t, i) => (
                <div className="bztw-time" key={i}>
                  <input type="time" value={t} required
                    onChange={(e) => setCalTimes(calTimes.map((x, j) => (j === i ? e.target.value : x)))} />
                  {calTimes.length > 1 ? (
                    <button type="button" className="bztw-time-x" aria-label="Remover hora"
                      onClick={() => setCalTimes(calTimes.filter((_, j) => j !== i))}>×</button>
                  ) : null}
                </div>
              ))}
              {calTimes.length < 6 ? (
                <button type="button" className="bztw-chip"
                  onClick={() => setCalTimes([...calTimes, "15:00"])}>
                  + hora
                </button>
              ) : null}
            </div>
            <small style={{ opacity: 0.7 }}>
              Cada hora cria uma partida em cada dia marcado — é assim que se programa a ida e a volta.
            </small>
          </div>

          <div className="field">
            <span>Dias</span>
            <TripCalendar selected={calDates} onChange={setCalDates}
              alreadyScheduled={jaProgramados} />
          </div>

          <div className="bztw-preview">
            {!calReady ? (
              <div className="bztw-preview-empty">
                Escolha a rota, a hora e os dias.
              </div>
            ) : loading ? (
              <div className="bztw-preview-empty"><Loader2 className="bztw-spin" size={16} /> A calcular…</div>
            ) : error ? (
              <div className="bztw-preview-empty bztw-error"><TriangleAlert size={16} /> {error}</div>
            ) : calPreview ? (
              <div className="bztw-headline">
                <div className={`bztw-count${calPreview.would_generate === 0 ? " is-zero" : ""}`}>
                  {calPreview.would_generate === 0 ? <TriangleAlert size={20} /> : <Sparkles size={20} />}
                  <strong>{calPreview.would_generate}</strong>
                  <span>partida(s) a criar</span>
                </div>
                {calPreview.already_scheduled > 0 ? (
                  <div className="bztw-range">
                    <CalendarRange size={14} />
                    {calPreview.already_scheduled} já programada(s)
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>

          <div className="admin-form-actions">
            <button className="primary-button" type="submit"
              disabled={busy || loading || !calReady || (calPreview?.would_generate ?? 0) === 0}>
              {busy ? "A programar…" : (
                <><CheckCircle2 size={16} />
                  {calPreview && calPreview.would_generate > 0
                    ? ` Criar ${calPreview.would_generate} partidas` : " Criar partidas"}</>
              )}
            </button>
            <button className="secondary-button" onClick={onClose} type="button">Cancelar</button>
          </div>
          <small style={{ opacity: 0.7 }}>
            Partidas que já existam não são duplicadas — pode marcar as vezes que quiser.
          </small>
        </form>
      ) : activeCount === 0 ? (
        <div className="bztw-preview">
          <div className="bztw-preview-empty">
            Ainda não há horários recorrentes. Crie um no separador «Programações»,
            ou use o calendário — é mais directo para uma carreira que sai uma vez por dia.
          </div>
        </div>
      ) : (
      <form className="admin-form" onSubmit={confirm}>
        <div className="admin-form-grid">
          <label className="field">
            <span>Horário</span>
            <select value={scheduleId} onChange={(e) => setScheduleId(e.target.value)}>
              <option value="all">Todos os horários activos ({activeCount})</option>
              {schedules.map((s) => (
                <option key={s.id} value={s.id} disabled={s.status !== "active"}>
                  {s.route_code} · {s.start_time?.slice(0, 5)}–{s.end_time?.slice(0, 5)}
                  {s.status !== "active" ? " (inactivo)" : ""}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>A partir de</span>
            <input type="date" value={dateFrom} min={todayISO()}
              onChange={(e) => setDateFrom(e.target.value || todayISO())} />
          </label>
        </div>

        <div className="field">
          <span>Horizonte</span>
          <div className="bztw-horizons">
            {HORIZONS.map((h) => (
              <button
                key={h.days}
                type="button"
                className={`bztw-chip${days === h.days ? " is-on" : ""}`}
                onClick={() => setDays(h.days)}
              >
                {h.label}
              </button>
            ))}
            <input
              className="bztw-days"
              type="number" min={1} max={30} value={days}
              onChange={(e) => setDays(Math.min(30, Math.max(1, Number(e.target.value) || 1)))}
              aria-label="Número de dias"
            />
            <span className="bztw-days-unit">dias</span>
          </div>
        </div>

        {/* --- Pré-visualização --------------------------------------- */}
        <div className="bztw-preview">
          {loading ? (
            <div className="bztw-preview-empty">
              <Loader2 className="bztw-spin" size={16} /> A calcular…
            </div>
          ) : error ? (
            <div className="bztw-preview-empty bztw-error">
              <TriangleAlert size={16} /> {error}
            </div>
          ) : preview ? (
            <>
              <div className="bztw-headline">
                <div className={`bztw-count${nothing ? " is-zero" : ""}`}>
                  {nothing ? <TriangleAlert size={20} /> : <Sparkles size={20} />}
                  <strong>{preview.would_generate}</strong>
                  <span>viagem(ns) a criar</span>
                </div>
                <div className="bztw-range">
                  <CalendarRange size={14} />
                  {humanDate(preview.date_from)}
                  {preview.days > 1 ? ` → ${humanDate(preview.date_to)}` : ""}
                </div>
              </div>

              {nothing ? (
                <p className="bztw-note">
                  Nada a criar neste intervalo. Ou as viagens já existem, ou os dias
                  da semana do horário não caem aqui, ou não há horários activos.
                </p>
              ) : (
                <>
                  <div className="bztw-bars" role="img"
                    aria-label={`Distribuição de ${preview.would_generate} viagens por dia`}>
                    {preview.by_day.map((d) => (
                      <div className="bztw-bar-col" key={d.date} title={`${humanDate(d.date)}: ${d.count}`}>
                        <div className="bztw-bar-track">
                          <div
                            className={`bztw-bar${d.count === 0 ? " is-empty" : ""}`}
                            style={{ height: `${d.count === 0 ? 3 : Math.max(8, (d.count / maxDay) * 100)}%` }}
                          />
                        </div>
                        <span className="bztw-bar-n">{d.count}</span>
                        <span className="bztw-bar-d">
                          {DAY_LABELS[(new Date(`${d.date}T00:00:00`).getDay() + 6) % 7]}
                        </span>
                      </div>
                    ))}
                  </div>

                  {preview.by_schedule.length > 1 ? (
                    <ul className="bztw-schedules">
                      {preview.by_schedule.slice(0, 6).map((s) => (
                        <li key={s.schedule_id}>
                          <span>{s.route_code} — {s.route_name}</span>
                          <strong>{s.count}</strong>
                        </li>
                      ))}
                      {preview.by_schedule.length > 6 ? (
                        <li className="bztw-more">
                          <span>+ {preview.by_schedule.length - 6} horário(s)</span>
                        </li>
                      ) : null}
                    </ul>
                  ) : null}
                </>
              )}
            </>
          ) : null}
        </div>

        <div className="admin-form-actions">
          <button className="primary-button" type="submit"
            disabled={busy || loading || !preview || nothing}>
            {busy ? "A programar…" : (
              <>
                <CheckCircle2 size={16} />
                {preview && !nothing ? ` Criar ${preview.would_generate} viagens` : " Criar viagens"}
              </>
            )}
          </button>
          <button className="secondary-button" onClick={onClose} type="button">Cancelar</button>
        </div>
        <small style={{ opacity: 0.7 }}>
          Viagens que já existam não são duplicadas — pode correr isto as vezes que quiser.
        </small>
      </form>
      )}
    </AdminModal>
  );
}
