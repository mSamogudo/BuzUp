import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft, ArrowRight, Bus, Calendar, CheckCircle2, Download, MapPin, Search, Users,
} from "lucide-react";
import { useBranding, pickLogo } from "../../lib/branding";
import SeatMap, { type SeatRow } from "./SeatMap";
import "./booking.css";

type Step = "search" | "trips" | "seats" | "pax" | "pay" | "done";

const STEPS: { key: Step; label: string }[] = [
  { key: "search", label: "Viagem" },
  { key: "trips", label: "Partida" },
  { key: "seats", label: "Lugares" },
  { key: "pax", label: "Passageiros" },
  { key: "pay", label: "Pagamento" },
];

interface StopOpt { id: number; code: string; name: string }
interface TripOpt {
  trip_id: number; route_id: number; route_code: string; route_name: string;
  vehicle: string | null; departure: string | null; fare_amount: string | null;
  seats_available: number | null; on_sale: boolean; sale_unavailable_reason: string;
}
interface Passenger { name: string; document_type: string; document_number: string; seat: string }

const DOC_TYPES = [
  { value: "bi", label: "Bilhete de Identidade" },
  { value: "passport", label: "Passaporte" },
  { value: "dire", label: "DIRE" },
  { value: "cedula", label: "Cédula" },
  { value: "other", label: "Outro" },
];

async function getJson(path: string) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" } });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || "Não foi possível contactar o servidor.");
  return body;
}

function money(v: string | number | null | undefined) {
  const n = Number(v || 0);
  return n.toLocaleString("pt-PT", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function timeOf(iso: string | null) {
  if (!iso) return "--:--";
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function longDate(iso: string) {
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString("pt-PT", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}

export default function BookingPage() {
  const { branding } = useBranding();
  const logo = pickLogo(branding.sidebar_logo_url, branding.primary_logo_url);

  const [step, setStep] = useState<Step>("search");
  const [stops, setStops] = useState<StopOpt[]>([]);
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [date, setDate] = useState("");
  const [qty, setQty] = useState(1);

  const [trips, setTrips] = useState<TripOpt[]>([]);
  const [trip, setTrip] = useState<TripOpt | null>(null);
  const [rows, setRows] = useState<SeatRow[]>([]);
  const [hasSeatMap, setHasSeatMap] = useState(true);
  const [picked, setPicked] = useState<string[]>([]);
  const [pax, setPax] = useState<Passenger[]>([]);
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [method, setMethod] = useState<"mpesa" | "emola">("mpesa");

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ checkout_reference: string; ticket_url: string; total_amount: string } | null>(null);

  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);

  useEffect(() => {
    document.title = "Comprar bilhete · BusUp";
    // sellable=1: só origens/destinos com partidas futuras à venda.
    getJson("/api/public/trips/?sellable=1")
      .then((d) => setStops(d.stops || []))
      .catch(() => setStops([]));
  }, []);

  // Link partilhável: /comprar?origem=66&destino=70&data=2026-08-05&pax=2
  // (campanhas e CTAs da landing podem apontar directamente a um percurso).
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const o = p.get("origem"); const d = p.get("destino");
    const dt = p.get("data"); const n = Number(p.get("pax") || 0);
    if (o) setOrigin(o);
    if (d) setDestination(d);
    if (dt) setDate(dt);
    if (n >= 1 && n <= 5) setQty(n);
  }, []);

  const runSearch = useCallback(async (o: string, d: string, dt: string) => {
    setBusy(true); setError("");
    try {
      const q = new URLSearchParams({ origin: o, destination: d, date: dt });
      const data = await getJson(`/api/public/trips/?${q}`);
      setTrips(data.trips || []);
      setStep("trips");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro na pesquisa.");
    } finally { setBusy(false); }
  }, []);

  // Pesquisa automática quando o link já traz percurso e data completos.
  const [autoDone, setAutoDone] = useState(false);
  useEffect(() => {
    if (autoDone || step !== "search" || !origin || !destination || !date) return;
    const p = new URLSearchParams(window.location.search);
    if (!p.get("origem") || !p.get("destino") || !p.get("data")) return;
    setAutoDone(true);
    void runSearch(origin, destination, date);
  }, [autoDone, step, origin, destination, date, runSearch]);

  // ?partida=<id> salta directamente para a escolha de lugares dessa partida.
  const [autoTripDone, setAutoTripDone] = useState(false);
  useEffect(() => {
    if (autoTripDone || step !== "trips" || trips.length === 0) return;
    const wanted = Number(new URLSearchParams(window.location.search).get("partida") || 0);
    if (!wanted) return;
    const found = trips.find((t) => t.trip_id === wanted);
    setAutoTripDone(true);
    if (found) void chooseTrip(found);
  }, [autoTripDone, step, trips]); // eslint-disable-line react-hooks/exhaustive-deps

  const search = (e: FormEvent) => {
    e.preventDefault();
    void runSearch(origin, destination, date);
  };

  const chooseTrip = async (t: TripOpt) => {
    setBusy(true); setError(""); setTrip(t); setPicked([]);
    try {
      const d = await getJson(`/api/public/trips/${t.trip_id}/seats/`);
      setHasSeatMap(Boolean(d.has_seat_map));
      setRows(d.rows || []);
      setStep(d.has_seat_map ? "seats" : "pax");
      if (!d.has_seat_map) startPax([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível carregar os lugares.");
    } finally { setBusy(false); }
  };

  const toggleSeat = (label: string) => {
    setPicked((prev) => prev.includes(label)
      ? prev.filter((s) => s !== label)
      : (prev.length >= qty ? prev : [...prev, label]));
  };

  const startPax = useCallback((seats: string[]) => {
    setPax(Array.from({ length: qty }, (_, i) => ({
      name: "", document_type: "bi", document_number: "", seat: seats[i] || "",
    })));
  }, [qty]);

  const goToPax = () => { startPax(picked); setStep("pax"); };

  const setPaxField = (i: number, key: keyof Passenger, value: string) => {
    setPax((prev) => prev.map((p, idx) => (idx === i ? { ...p, [key]: value } : p)));
  };

  const paxValid = pax.length > 0 && pax.every((p) => p.name.trim().length >= 3 && p.document_number.trim().length >= 4);
  const phoneValid = /^\d{9}$/.test(phone.replace(/\D/g, ""));
  const unit = Number(trip?.fare_amount || 0);
  const total = unit * qty;

  const pay = async (e: FormEvent) => {
    e.preventDefault();
    if (!trip) return;
    setBusy(true); setError("");
    try {
      const originStop = stops.find((s) => String(s.id) === origin);
      const destStop = stops.find((s) => String(s.id) === destination);
      const res = await fetch("/api/guest-checkouts/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          payer_phone: phone.replace(/\D/g, ""),
          buyer_name: pax[0]?.name || "",
          buyer_email: email,
          route_code: trip.route_code,
          route_name: trip.route_name,
          origin_stop: originStop?.name || "",
          destination_stop: destStop?.name || "",
          origin_stop_id: Number(origin),
          destination_stop_id: Number(destination),
          trip_id: trip.trip_id,
          quantity: qty,
          passengers: pax,
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || "Não foi possível concluir a compra.");
      setResult(body);
      setStep("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro no pagamento.");
    } finally { setBusy(false); }
  };

  const stepIndex = STEPS.findIndex((s) => s.key === step);

  return (
    <div className="bzbk">
      <header className="bzbk-top">
        <div className="bzbk-wrap">
          <div className="bzbk-top-in">
            <Link to="/" aria-label="BusUp">
              {logo
                ? <img src={logo} alt="BusUp" style={{ height: 30, display: "block" }} />
                : <strong style={{ fontSize: 22 }}>Bus<span style={{ color: "#2D8CF0" }}>Up</span></strong>}
            </Link>
            <Link to="/" className="bzbk-kicker" style={{ color: "#a9c2dc" }}>Voltar ao site</Link>
          </div>
          <div style={{ position: "relative", zIndex: 2, marginTop: 18 }}>
            <div className="bzbk-kicker">Bilhetes interurbanos</div>
            <h1 className="bzbk-title">Compre a sua viagem</h1>
            <p className="bzbk-sub">Escolha a data, o lugar e receba o bilhete no telemóvel.</p>
          </div>
          <nav className="bzbk-steps" aria-label="Etapas da compra">
            {STEPS.map((s, i) => (
              <span key={s.key}
                className={`bzbk-step${s.key === step ? " is-active" : ""}${i < stepIndex ? " is-done" : ""}`}>
                <b>{i < stepIndex ? "✓" : i + 1}</b>{s.label}
              </span>
            ))}
          </nav>
        </div>
      </header>

      <div className="bzbk-wrap">
        <div className="bzbk-card">
          <div className="bzbk-card-in">
            {error && <div className="bzbk-notice error" role="alert">{error}</div>}

            {step === "search" && (
              <form onSubmit={search}>
                <h2 className="bzbk-h2">Para onde vai?</h2>
                <p className="bzbk-lead">Indique o percurso, a data da viagem e quantos bilhetes precisa.</p>
                <div className="bzbk-grid">
                  <div className="bzbk-field">
                    <label className="bzbk-label" htmlFor="o"><MapPin size={12} style={{ verticalAlign: -2 }} /> Origem</label>
                    <select id="o" className="bzbk-select" value={origin} required
                      onChange={(e) => setOrigin(e.target.value)}>
                      <option value="">Seleccione a origem</option>
                      {stops.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                    </select>
                  </div>
                  <div className="bzbk-field">
                    <label className="bzbk-label" htmlFor="d"><MapPin size={12} style={{ verticalAlign: -2 }} /> Destino</label>
                    <select id="d" className="bzbk-select" value={destination} required
                      onChange={(e) => setDestination(e.target.value)}>
                      <option value="">Seleccione o destino</option>
                      {stops.filter((s) => String(s.id) !== origin).map((s) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="bzbk-field">
                    <label className="bzbk-label" htmlFor="dt"><Calendar size={12} style={{ verticalAlign: -2 }} /> Data da viagem</label>
                    <input id="dt" className="bzbk-input" type="date" value={date} min={today} required
                      onChange={(e) => setDate(e.target.value)} />
                  </div>
                  <div className="bzbk-field">
                    <label className="bzbk-label" htmlFor="q"><Users size={12} style={{ verticalAlign: -2 }} /> Passageiros</label>
                    <select id="q" className="bzbk-select" value={qty}
                      onChange={(e) => setQty(Number(e.target.value))}>
                      {[1, 2, 3, 4, 5].map((n) => (
                        <option key={n} value={n}>{n} {n === 1 ? "passageiro" : "passageiros"}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="bzbk-actions">
                  <span />
                  <button className="bzbk-btn" type="submit" disabled={busy || !origin || !destination || !date}>
                    {busy ? <span className="bzbk-spin" /> : <Search size={17} />} Procurar partidas
                  </button>
                </div>
              </form>
            )}

            {step === "trips" && (
              <div>
                <h2 className="bzbk-h2">Partidas disponíveis</h2>
                <p className="bzbk-lead">{date && longDate(date)} · {qty} {qty === 1 ? "bilhete" : "bilhetes"}</p>
                {trips.length === 0 && (
                  <div className="bzbk-notice warn">
                    Não há partidas nesta data para o percurso escolhido. Experimente outro dia.
                  </div>
                )}
                {trips.map((t) => {
                  const left = t.seats_available;
                  return (
                    <button key={t.trip_id} className="bzbk-trip" type="button"
                      disabled={!t.on_sale || (left !== null && left < qty)}
                      onClick={() => chooseTrip(t)}>
                      <span className="bzbk-trip-time">{timeOf(t.departure)}</span>
                      <span className="bzbk-trip-main">
                        <span className="bzbk-trip-route">{t.route_name || t.route_code}</span>
                        <span className="bzbk-trip-meta">
                          {t.vehicle ? `Viatura ${t.vehicle} · ` : ""}
                          {!t.on_sale
                            ? <span className="bzbk-seats-none">{t.sale_unavailable_reason}</span>
                            : left === null
                              ? "Lugares disponíveis"
                              : left === 0
                                ? <span className="bzbk-seats-none">Esgotado</span>
                                : left <= 5
                                  ? <span className="bzbk-seats-few">Só {left} lugares</span>
                                  : <span className="bzbk-seats-left">{left} lugares livres</span>}
                        </span>
                      </span>
                      <span className="bzbk-trip-price">{money(t.fare_amount)} MZN<small>por pessoa</small></span>
                    </button>
                  );
                })}
                <div className="bzbk-actions">
                  <button className="bzbk-btn ghost" type="button" onClick={() => setStep("search")}>
                    <ArrowLeft size={16} /> Alterar pesquisa
                  </button>
                </div>
              </div>
            )}

            {step === "seats" && trip && (
              <div>
                <h2 className="bzbk-h2">Escolha {qty === 1 ? "o seu lugar" : `os ${qty} lugares`}</h2>
                <p className="bzbk-lead">
                  {trip.route_name} · {date && longDate(date)} · partida às {timeOf(trip.departure)}
                </p>
                {hasSeatMap
                  ? <SeatMap rows={rows} picked={picked} maxPick={qty} onToggle={toggleSeat} />
                  : <div className="bzbk-notice info">Esta partida não tem lugares marcados.</div>}
                <div className="bzbk-actions">
                  <button className="bzbk-btn ghost" type="button" onClick={() => setStep("trips")}>
                    <ArrowLeft size={16} /> Outra partida
                  </button>
                  <button className="bzbk-btn" type="button" disabled={picked.length !== qty} onClick={goToPax}>
                    {picked.length === qty
                      ? <>Continuar <ArrowRight size={16} /></>
                      : `Falta escolher ${qty - picked.length}`}
                  </button>
                </div>
              </div>
            )}

            {step === "pax" && trip && (
              <div>
                <h2 className="bzbk-h2">Quem viaja?</h2>
                <p className="bzbk-lead">
                  O bilhete é nominal. Em viagens internacionais o documento é conferido na fronteira.
                </p>
                {pax.map((p, i) => (
                  <div className="bzbk-pax" key={i}>
                    <div className="bzbk-pax-head">
                      {p.seat && <span className="bzbk-pax-seat">{p.seat}</span>}
                      <span className="bzbk-pax-title">Passageiro {i + 1}</span>
                    </div>
                    <div className="bzbk-field">
                      <label className="bzbk-label">Nome completo</label>
                      <input className="bzbk-input" value={p.name} required
                        placeholder="Como está no documento"
                        onChange={(e) => setPaxField(i, "name", e.target.value)} />
                    </div>
                    <div className="bzbk-grid" style={{ marginTop: 12 }}>
                      <div className="bzbk-field">
                        <label className="bzbk-label">Documento</label>
                        <select className="bzbk-select" value={p.document_type}
                          onChange={(e) => setPaxField(i, "document_type", e.target.value)}>
                          {DOC_TYPES.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
                        </select>
                      </div>
                      <div className="bzbk-field">
                        <label className="bzbk-label">Número</label>
                        <input className="bzbk-input" value={p.document_number} required
                          onChange={(e) => setPaxField(i, "document_number", e.target.value)} />
                      </div>
                    </div>
                  </div>
                ))}
                <div className="bzbk-actions">
                  <button className="bzbk-btn ghost" type="button"
                    onClick={() => setStep(hasSeatMap ? "seats" : "trips")}>
                    <ArrowLeft size={16} /> Voltar
                  </button>
                  <button className="bzbk-btn" type="button" disabled={!paxValid} onClick={() => setStep("pay")}>
                    Continuar <ArrowRight size={16} />
                  </button>
                </div>
              </div>
            )}

            {step === "pay" && trip && (
              <form onSubmit={pay}>
                <h2 className="bzbk-h2">Pagamento</h2>
                <p className="bzbk-lead">Confirme os dados e pague com a sua carteira móvel.</p>

                <div className="bzbk-summary">
                  <div className="bzbk-sum-row"><span>Percurso</span><b>{trip.route_name}</b></div>
                  <div className="bzbk-sum-row"><span>Partida</span><b>{date && longDate(date)} · {timeOf(trip.departure)}</b></div>
                  <div className="bzbk-sum-row">
                    <span>Passageiros</span>
                    <b>{pax.map((p) => p.name + (p.seat ? ` (${p.seat})` : "")).join(", ")}</b>
                  </div>
                  <div className="bzbk-sum-row"><span>{qty} × {money(unit)} MZN</span><b>{money(total)} MZN</b></div>
                  <div className="bzbk-sum-total"><span>TOTAL A PAGAR</span><b>{money(total)} MZN</b></div>
                </div>

                <div className="bzbk-methods">
                  {(["mpesa", "emola"] as const).map((m) => (
                    <button key={m} type="button"
                      className={`bzbk-method${method === m ? " is-on" : ""}`}
                      onClick={() => setMethod(m)} aria-pressed={method === m}>
                      <span className="dot" />
                      {m === "mpesa" ? "M-Pesa" : "e-Mola"}
                    </button>
                  ))}
                </div>

                <div className="bzbk-grid">
                  <div className="bzbk-field">
                    <label className="bzbk-label" htmlFor="ph">Telemóvel para pagamento</label>
                    <input id="ph" className="bzbk-input" inputMode="numeric" placeholder="84xxxxxxx / 86xxxxxxx"
                      value={phone} required onChange={(e) => setPhone(e.target.value)} />
                    <span className="bzbk-hint">Vai receber um pedido de PIN neste número.</span>
                  </div>
                  <div className="bzbk-field">
                    <label className="bzbk-label" htmlFor="em">Email (opcional)</label>
                    <input id="em" className="bzbk-input" type="email" placeholder="para receber o bilhete"
                      value={email} onChange={(e) => setEmail(e.target.value)} />
                  </div>
                </div>

                <div className="bzbk-actions">
                  <button className="bzbk-btn ghost" type="button" onClick={() => setStep("pax")} disabled={busy}>
                    <ArrowLeft size={16} /> Voltar
                  </button>
                  <button className="bzbk-btn" type="submit" disabled={busy || !phoneValid}>
                    {busy ? <><span className="bzbk-spin" /> A processar…</> : <>Pagar {money(total)} MZN</>}
                  </button>
                </div>
                {busy && (
                  <div className="bzbk-notice info" style={{ marginTop: 16 }}>
                    Confirme o pagamento no seu telemóvel se lhe for pedido o PIN. Não feche esta página.
                  </div>
                )}
              </form>
            )}

            {step === "done" && result && (
              <div className="bzbk-done">
                <div className="bzbk-done-mark"><CheckCircle2 size={40} /></div>
                <h2>Bilhete emitido</h2>
                <p>
                  Pagámento confirmado. Enviámos o link do bilhete por SMS para o número indicado —
                  guarde o PDF no telemóvel e apresente o QR ao embarcar.
                </p>
                <div className="bzbk-ref">{result.checkout_reference}</div>
                <div style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
                  {result.ticket_url && (
                    <a className="bzbk-btn" href={result.ticket_url} target="_blank" rel="noreferrer">
                      <Download size={17} /> Descarregar bilhete
                    </a>
                  )}
                  <Link className="bzbk-btn ghost" to="/">
                    <Bus size={17} /> Voltar ao início
                  </Link>
                </div>
              </div>
            )}
          </div>
        </div>

        <p className="bzbk-foot">
          Precisa de ajuda? <a href="mailto:comercial@updigital.co.mz">comercial@updigital.co.mz</a> · BusUp by UpDigital
        </p>
      </div>
    </div>
  );
}
