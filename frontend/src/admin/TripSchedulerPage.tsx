import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft, Bus, CalendarClock, CalendarDays, CheckCircle2, Clock, Loader2,
  Plus, Repeat, Route as RouteIcon, Sparkles, TriangleAlert, UserRound, X,
} from "lucide-react";
import { apiFetch, apiPost } from "../lib/api";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { PageFrame, useAsyncData } from "../ui/common";
import TripCalendar from "./TripCalendar";

interface RouteOpt { id: number; code: string; name: string; service_type?: string }
interface VehicleOpt { id: number; registration: string; seated_capacity?: number }
interface PersonOpt { id: number; full_name: string }
interface ScheduleOpt {
  id: number; route_code: string; route_name: string;
  start_time: string; end_time: string; days_of_week: number[]; status: string;
}

interface CalendarPreview {
  would_generate: number;
  already_scheduled: number;
  by_day: { date: string; count: number; existing: number }[];
}
interface SchedulePreview {
  would_generate: number; days: number; date_from: string; date_to: string;
  by_day: { date: string; count: number }[];
  by_schedule: { schedule_id: number; route_code: string; route_name: string; count: number }[];
}

const HORIZONS = [1, 7, 14, 30];

function todayISO(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function diaCurto(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("pt-PT", { day: "2-digit", month: "short" });
}

/**
 * Programar partidas.
 *
 * Era um modal onde tudo se empilhava: os selectores, as horas, o calendário e
 * a pré-visualização, uns por baixo dos outros. Programar um mês obrigava a
 * rolar três vezes e a perder de vista o que já se tinha escolhido.
 *
 * Aqui a tarefa está dividida no eixo em que ela realmente se divide: **o quê**
 * à esquerda (a partida a criar — rota, autocarro, motorista, horas) e **quando**
 * à direita (o calendário). Nada muda de sítio enquanto se trabalha, e o rodapé
 * diz sempre quantas partidas nascem e quanto isso é.
 */
export default function TripSchedulerPage() {
  const { token } = useAuth();
  const navigate = useNavigate();

  const [modo, setModo] = useState<"calendario" | "horario">("calendario");

  const routeLoader = useCallback(() => apiFetch("/api/routes/", token!).then((d) => d.results || d), [token]);
  const vehicleLoader = useCallback(() => apiFetch("/api/vehicles/", token!).then((d) => d.results || d), [token]);
  const driverLoader = useCallback(() => apiFetch("/api/drivers/", token!).then((d) => d.results || d), [token]);
  const scheduleLoader = useCallback(() => apiFetch("/api/schedules/", token!).then((d) => d.results || d), [token]);

  const { data: routes } = useAsyncData<RouteOpt[]>(routeLoader, [token]);
  const { data: vehicles } = useAsyncData<VehicleOpt[]>(vehicleLoader, [token]);
  const { data: drivers } = useAsyncData<PersonOpt[]>(driverLoader, [token]);
  const { data: schedules } = useAsyncData<ScheduleOpt[]>(scheduleLoader, [token]);

  // --- Modo calendário -------------------------------------------------
  const [rota, setRota] = useState("");
  const [viatura, setViatura] = useState("");
  const [motorista, setMotorista] = useState("");
  // Para que lado vai a partida. A rota tem as paragens nos dois sentidos; a
  // viagem não tinha nenhum, e quem procurava a ida recebia também a volta.
  const [sentido, setSentido] = useState<"outbound" | "inbound">("outbound");
  const [horas, setHoras] = useState<string[]>(["05:00"]);
  const [duracao, setDuracao] = useState("");
  const [dias, setDias] = useState<string[]>([]);
  const [previa, setPrevia] = useState<CalendarPreview | null>(null);

  // --- Modo horário recorrente -----------------------------------------
  const [horarioId, setHorarioId] = useState("all");
  const [desde, setDesde] = useState(todayISO());
  const [horizonte, setHorizonte] = useState(7);
  const [previaH, setPreviaH] = useState<SchedulePreview | null>(null);

  const [aCalcular, setACalcular] = useState(false);
  const [aCriar, setACriar] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (routes && routes.length === 1 && !rota) setRota(String(routes[0].id));
  }, [routes, rota]);

  const horasValidas = useMemo(() => horas.filter(Boolean), [horas]);
  const pronto = rota !== "" && dias.length > 0 && horasValidas.length > 0;

  const corpo = useCallback((preview: boolean) => ({
    route_id: Number(rota),
    vehicle_id: viatura ? Number(viatura) : null,
    driver_id: motorista ? Number(motorista) : null,
    dates: dias,
    times: horasValidas,
    duration_minutes: duracao ? Number(duracao) : null,
    direction: sentido,
    preview,
  }), [rota, viatura, motorista, dias, horasValidas, duracao, sentido]);

  useEffect(() => {
    if (modo !== "calendario" || !pronto || !token) { setPrevia(null); return; }
    let cancelado = false;
    const id = window.setTimeout(() => {
      setACalcular(true);
      apiPost("/api/trips/schedule-days/", token, corpo(true))
        .then((r) => { if (!cancelado) { setPrevia(r as CalendarPreview); setErro(""); } })
        .catch((e) => { if (!cancelado) { setPrevia(null); setErro(e instanceof Error ? e.message : "Erro"); } })
        .finally(() => { if (!cancelado) setACalcular(false); });
    }, 220);
    return () => { cancelado = true; window.clearTimeout(id); };
  }, [modo, pronto, corpo, token]);

  useEffect(() => {
    if (modo !== "horario" || !token) return;
    let cancelado = false;
    const id = window.setTimeout(() => {
      setACalcular(true);
      const body: Record<string, unknown> = { days: horizonte, date_from: desde, preview: true };
      if (horarioId !== "all") body.schedule_id = Number(horarioId);
      apiPost("/api/trips/generate/", token, body)
        .then((r) => { if (!cancelado) { setPreviaH(r as SchedulePreview); setErro(""); } })
        .catch((e) => { if (!cancelado) { setPreviaH(null); setErro(e instanceof Error ? e.message : "Erro"); } })
        .finally(() => { if (!cancelado) setACalcular(false); });
    }, 220);
    return () => { cancelado = true; window.clearTimeout(id); };
  }, [modo, token, horizonte, desde, horarioId]);

  const criar = async () => {
    setACriar(true);
    try {
      if (modo === "calendario") {
        const r = await apiPost("/api/trips/schedule-days/", token!, corpo(false));
        const n = Number(r?.created ?? 0);
        showToast(n > 0 ? "success" : "neutral",
          n > 0 ? `${n} partida(s) programada(s).` : "Nada a criar: estas partidas já existem.");
      } else {
        const body: Record<string, unknown> = { days: horizonte, date_from: desde };
        if (horarioId !== "all") body.schedule_id = Number(horarioId);
        const r = await apiPost("/api/trips/generate/", token!, body);
        showToast("success", `${Number(r?.generated ?? 0)} viagem(ns) programada(s).`);
      }
      navigate("/app/trips");
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro ao programar.");
    } finally {
      setACriar(false);
    }
  };

  const jaProgramados = useMemo(
    () => new Set((previa?.by_day || []).filter((d) => d.existing > 0).map((d) => d.date)),
    [previa],
  );

  const activos = (schedules || []).filter((s) => s.status === "active").length;
  const rotaEscolhida = (routes || []).find((r) => String(r.id) === rota);
  const viaturaEscolhida = (vehicles || []).find((v) => String(v.id) === viatura);

  const totalACriar = modo === "calendario"
    ? (previa?.would_generate ?? 0)
    : (previaH?.would_generate ?? 0);
  const podeCriar = modo === "calendario"
    ? pronto && totalACriar > 0
    : activos > 0 && totalACriar > 0;

  return (
    <PageFrame
      kicker="Operação"
      title="Programar viagens"
      description="Defina a partida e marque os dias. Vê quantas nascem antes de confirmar."
      action={
        <button className="icon-text-button" type="button" onClick={() => navigate("/app/trips")}>
          <ArrowLeft size={16} /><span>Voltar às viagens</span>
        </button>
      }
    >
      <div className="bzsched-modes" role="tablist" aria-label="Modo de programação">
        <button type="button" role="tab" aria-selected={modo === "calendario"}
          className={`bzsched-mode${modo === "calendario" ? " is-on" : ""}`}
          onClick={() => { setModo("calendario"); setErro(""); }}>
          <CalendarDays size={16} />
          <span>
            <b>Calendário</b>
            <small>Marque os dias, um a um</small>
          </span>
        </button>
        <button type="button" role="tab" aria-selected={modo === "horario"}
          className={`bzsched-mode${modo === "horario" ? " is-on" : ""}`}
          onClick={() => { setModo("horario"); setErro(""); }}>
          <Repeat size={16} />
          <span>
            <b>Horário recorrente</b>
            <small>{activos > 0 ? `${activos} horário(s) activo(s)` : "Nenhum horário criado"}</small>
          </span>
        </button>
      </div>

      <div className="bzsched">
        {/* ---- O QUÊ ----------------------------------------------- */}
        <aside className="bzsched-side">
          {modo === "calendario" ? (
            <>
              <div className="bzsched-card">
                <h3 className="bzsched-h3"><RouteIcon size={14} /> A partida</h3>
                <label className="field">
                  <span>Rota</span>
                  <select value={rota} onChange={(e) => setRota(e.target.value)} required>
                    <option value="">Escolher…</option>
                    {(routes || []).map((r) => (
                      <option key={r.id} value={r.id}>{r.code} — {r.name}</option>
                    ))}
                  </select>
                </label>
                <div className="field">
                  <span>Sentido</span>
                  {/* A ida e a volta são duas programações. Fazê-las de uma vez,
                      como duas horas do mesmo dia, criava partidas sem sentido
                      declarado — e o passageiro que procurava Maputo→Nelspruit
                      recebia também as de Nelspruit→Maputo. */}
                  <div className="bzsched-dir">
                    {([["outbound", "Ida"], ["inbound", "Volta"]] as const).map(([v, rotulo]) => (
                      <button key={v} type="button"
                        className={`bzsched-dir-b${sentido === v ? " is-on" : ""}`}
                        aria-pressed={sentido === v}
                        onClick={() => setSentido(v)}>
                        {rotulo}
                      </button>
                    ))}
                  </div>
                </div>
                <label className="field">
                  <span><Bus size={12} style={{ verticalAlign: -2 }} /> Autocarro</span>
                  <select value={viatura} onChange={(e) => setViatura(e.target.value)}>
                    <option value="">Sem autocarro atribuído</option>
                    {(vehicles || []).map((v) => (
                      <option key={v.id} value={v.id}>{v.registration}</option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span><UserRound size={12} style={{ verticalAlign: -2 }} /> Motorista</span>
                  <select value={motorista} onChange={(e) => setMotorista(e.target.value)}>
                    <option value="">Sem motorista atribuído</option>
                    {(drivers || []).map((d) => (
                      <option key={d.id} value={d.id}>{d.full_name}</option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="bzsched-card">
                <h3 className="bzsched-h3"><Clock size={14} /> Horas de partida</h3>
                <div className="bzsched-times">
                  {horas.map((h, i) => (
                    <div className="bzsched-time" key={i}>
                      <input type="time" value={h} required
                        onChange={(e) => setHoras(horas.map((x, j) => (j === i ? e.target.value : x)))} />
                      {horas.length > 1 ? (
                        <button type="button" className="bzsched-time-x" aria-label="Remover hora"
                          onClick={() => setHoras(horas.filter((_, j) => j !== i))}>
                          <X size={13} />
                        </button>
                      ) : null}
                    </div>
                  ))}
                  {horas.length < 6 ? (
                    <button type="button" className="bzsched-add"
                      onClick={() => setHoras([...horas, "15:00"])}>
                      <Plus size={14} /> hora
                    </button>
                  ) : null}
                </div>
                <p className="bzsched-note">
                  Cada hora cria uma partida em cada dia marcado, todas no sentido escolhido acima.
                  A volta programa-se a seguir, trocando o sentido.
                </p>
                <label className="field">
                  <span>Duração da viagem (minutos)</span>
                  <input type="number" min={1} max={2880} placeholder="ex.: 270"
                    value={duracao} onChange={(e) => setDuracao(e.target.value)} />
                </label>
              </div>
            </>
          ) : (
            <div className="bzsched-card">
              <h3 className="bzsched-h3"><Repeat size={14} /> Horário</h3>
              {activos === 0 ? (
                <p className="bzsched-note">
                  Ainda não há horários recorrentes. Crie um no separador «Programações»,
                  ou use o <b>Calendário</b> — é mais directo para uma carreira que sai
                  uma vez por dia.
                </p>
              ) : (
                <>
                  <label className="field">
                    <span>Qual</span>
                    <select value={horarioId} onChange={(e) => setHorarioId(e.target.value)}>
                      <option value="all">Todos os activos ({activos})</option>
                      {(schedules || []).map((s) => (
                        <option key={s.id} value={s.id} disabled={s.status !== "active"}>
                          {s.route_code} · {s.start_time?.slice(0, 5)}–{s.end_time?.slice(0, 5)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>A partir de</span>
                    <input type="date" value={desde} min={todayISO()}
                      onChange={(e) => setDesde(e.target.value || todayISO())} />
                  </label>
                  <label className="field">
                    <span>Horizonte</span>
                    <div className="bzsched-chips">
                      {HORIZONS.map((d) => (
                        <button key={d} type="button"
                          className={`bzsched-chip${horizonte === d ? " is-on" : ""}`}
                          onClick={() => setHorizonte(d)}>
                          {d === 1 ? "Hoje" : `${d} dias`}
                        </button>
                      ))}
                    </div>
                  </label>
                </>
              )}
            </div>
          )}
        </aside>

        {/* ---- QUANDO ---------------------------------------------- */}
        <section className="bzsched-main">
          {modo === "calendario" ? (
            <div className="bzsched-card bzsched-card-flush">
              <div className="bzsched-main-head">
                <h3 className="bzsched-h3"><CalendarDays size={14} /> Dias</h3>
                <span className="bzsched-count-pill">
                  {dias.length} {dias.length === 1 ? "dia marcado" : "dias marcados"}
                </span>
              </div>
              <TripCalendar selected={dias} onChange={setDias} alreadyScheduled={jaProgramados} />
            </div>
          ) : (
            <div className="bzsched-card">
              <div className="bzsched-main-head">
                <h3 className="bzsched-h3"><CalendarClock size={14} /> Distribuição</h3>
                <span className="bzsched-count-pill">
                  {previaH ? `${diaCurto(previaH.date_from)} → ${diaCurto(previaH.date_to)}` : "—"}
                </span>
              </div>
              {previaH && previaH.by_day.length > 0 ? (
                <div className="bzsched-bars">
                  {previaH.by_day.map((d) => {
                    const max = Math.max(1, ...previaH.by_day.map((x) => x.count));
                    return (
                      <div className="bzsched-bar-col" key={d.date} title={`${diaCurto(d.date)}: ${d.count}`}>
                        <div className="bzsched-bar-track">
                          <div className={`bzsched-bar${d.count === 0 ? " is-empty" : ""}`}
                            style={{ height: `${d.count === 0 ? 3 : Math.max(8, (d.count / max) * 100)}%` }} />
                        </div>
                        <span className="bzsched-bar-n">{d.count}</span>
                        <span className="bzsched-bar-d">{diaCurto(d.date).split(" ")[0]}</span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="bzsched-note">Sem nada a mostrar para este intervalo.</p>
              )}
              {previaH && previaH.by_schedule.length > 1 ? (
                <ul className="bzsched-list">
                  {previaH.by_schedule.slice(0, 8).map((s) => (
                    <li key={s.schedule_id}>
                      <span>{s.route_code} — {s.route_name}</span><strong>{s.count}</strong>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          )}
        </section>
      </div>

      {/* ---- Rodapé de confirmação, sempre à vista ------------------- */}
      <div className="bzsched-footer">
        <div className="bzsched-summary">
          {aCalcular ? (
            <span className="bzsched-calc"><Loader2 className="bztw-spin" size={16} /> A calcular…</span>
          ) : erro ? (
            <span className="bzsched-err"><TriangleAlert size={16} /> {erro}</span>
          ) : (
            <>
              <span className={`bzsched-total${totalACriar === 0 ? " is-zero" : ""}`}>
                {totalACriar === 0 ? <TriangleAlert size={18} /> : <Sparkles size={18} />}
                <strong>{totalACriar}</strong>
                <span>{totalACriar === 1 ? "partida a criar" : "partidas a criar"}</span>
              </span>
              {modo === "calendario" && rotaEscolhida ? (
                <span className="bzsched-meta">
                  {rotaEscolhida.code}
                  {viaturaEscolhida ? ` · ${viaturaEscolhida.registration}` : ""}
                  {horasValidas.length > 0 ? ` · ${horasValidas.join(", ")}` : ""}
                </span>
              ) : null}
              {modo === "calendario" && previa && previa.already_scheduled > 0 ? (
                <span className="bzsched-meta">{previa.already_scheduled} já programada(s) — não se repetem</span>
              ) : null}
            </>
          )}
        </div>
        <button className="primary-button" type="button" disabled={!podeCriar || aCriar || aCalcular}
          onClick={() => void criar()}>
          {aCriar ? "A programar…" : (
            <><CheckCircle2 size={16} /> {totalACriar > 0 ? ` Criar ${totalACriar} partidas` : " Criar partidas"}</>
          )}
        </button>
      </div>
    </PageFrame>
  );
}
