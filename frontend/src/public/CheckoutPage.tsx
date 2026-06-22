import { useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, Bus, CheckCircle, Clock, MapPin, Search, Ticket } from "lucide-react";
import { formatCurrency, formatDateTime } from "../lib/format";
import { useBranding, pickLogo } from "../lib/branding";

interface RouteOption { id: number; code: string; name: string; }
interface StopOption { id: number; code: string; name: string; }
interface TripResult { trip_id: number; route_id: number; route_code: string; route_name: string; vehicle: string | null; driver: string | null; departure: string | null; started_at: string | null; direction: string; status: string; fare_amount: string | null; }
interface CheckoutResult { checkout_reference: string; payment_reference: string; total_amount: string; status: string; payment_status: string; detail_message: string; ticket_url: string; }

type Step = "search" | "results" | "payment" | "confirmation";

async function api(path: string, opts?: RequestInit) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || `Erro ${res.status}`); }
  return res.json();
}

export default function CheckoutPage() {
  const { branding } = useBranding();
  const [step, setStep] = useState<Step>("search");
  const [routes, setRoutes] = useState<RouteOption[]>([]);
  const [stops, setStops] = useState<StopOption[]>([]);
  const [trips, setTrips] = useState<TripResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [routeId, setRouteId] = useState("");
  const [originId, setOriginId] = useState("");
  const [destId, setDestId] = useState("");
  const [selectedTrip, setSelectedTrip] = useState<TripResult | null>(null);
  const [phone, setPhone] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<CheckoutResult | null>(null);

  useEffect(() => { api("/api/public/trips/").then((d) => { setRoutes(d.routes || []); setStops(d.stops || []); }).catch(() => {}); }, []);
  useEffect(() => {
    setOriginId("");
    setDestId("");
    const path = routeId ? `/api/public/trips/?route=${routeId}` : "/api/public/trips/";
    api(path).then((d) => setStops(d.stops || [])).catch(() => {});
  }, [routeId]);

  const search = async (e: FormEvent) => {
    e.preventDefault(); setLoading(true); setError("");
    try {
      if (originId && destId && originId === destId) {
        throw new Error("O destino deve ser diferente da origem.");
      }
      const p = new URLSearchParams();
      if (routeId) p.set("route", routeId);
      if (originId) p.set("origin", originId);
      if (destId) p.set("destination", destId);
      const d = await api(`/api/public/trips/?${p}`);
      setTrips(d.trips || []); setStep("results");
    } catch (err) { setError(err instanceof Error ? err.message : "Erro."); }
    finally { setLoading(false); }
  };

  const pay = async (e: FormEvent) => {
    e.preventDefault(); if (!selectedTrip) return;
    setSubmitting(true); setError("");
    try {
      const origin = stops.find((s) => String(s.id) === originId);
      const dest = stops.find((s) => String(s.id) === destId);
      if (origin && dest && origin.id === dest.id) {
        throw new Error("O destino deve ser diferente da origem.");
      }
      const d = await api("/api/guest-checkouts/", {
        method: "POST",
        body: JSON.stringify({
          payer_phone: phone,
          route_code: selectedTrip.route_code,
          route_name: selectedTrip.route_name,
          origin_stop: origin?.name || "",
          destination_stop: dest?.name || "",
          origin_stop_id: origin?.id,
          destination_stop_id: dest?.id,
          trip_id: selectedTrip.trip_id,
          quantity,
          unit_amount: selectedTrip.fare_amount || "0",
        }),
      });
      setResult(d); setStep("confirmation");
    } catch (err) { setError(err instanceof Error ? err.message : "Erro."); }
    finally { setSubmitting(false); }
  };

  const reset = () => { setStep("search"); setResult(null); setSelectedTrip(null); setPhone(""); setQuantity(1); setError(""); };

  return (
    <div className="co">
      <header className="co-header">
        <img alt="TPM-TUR" src={pickLogo(branding.primary_logo_url, "/assets/tpm-tur-logo/tpm_dark.png")} className="co-logo" />
        <div className="co-header-text">
          <strong>BusUp</strong>
          <span>Bilhete Electronico</span>
        </div>
      </header>

      <main className="co-body">
        {error && <div className="co-error">{error}<button onClick={() => setError("")}>&times;</button></div>}

        {step === "search" && (
          <section className="co-card co-search">
            <div className="co-card-icon"><Search size={24} /></div>
            <h2>Pesquisar Autocarro</h2>
            <form className="co-form" onSubmit={search}>
              <select className="co-select" value={routeId} onChange={(e) => setRouteId(e.target.value)}>
                <option value="">Todas as rotas</option>
                {routes.map((r) => <option key={r.id} value={r.id}>{r.code} — {r.name}</option>)}
              </select>
              <div className="co-row">
                <select className="co-select" value={originId} onChange={(e) => { const value = e.target.value; setOriginId(value); if (value && value === destId) setDestId(""); }}>
                  <option value="">Origem</option>
                  {stops.filter((s) => String(s.id) !== destId).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
                <select className="co-select" value={destId} onChange={(e) => { const value = e.target.value; setDestId(value); if (value && value === originId) setOriginId(""); }}>
                  <option value="">Destino</option>
                  {stops.filter((s) => String(s.id) !== originId).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <button className="co-btn" type="submit" disabled={loading}>
                <Search size={18} />{loading ? "A pesquisar..." : "Pesquisar"}
              </button>
            </form>
          </section>
        )}

        {step === "results" && (
          <section className="co-card">
            <button className="co-back" onClick={() => setStep("search")} type="button"><ArrowLeft size={16} /> Alterar pesquisa</button>
            <h2><Bus size={20} /> {trips.length} autocarros disponiveis</h2>
            {trips.length === 0 ? (
              <div className="co-empty"><MapPin size={32} /><p>Nenhum autocarro disponivel.</p><button className="co-btn-outline" onClick={() => setStep("search")}>Nova pesquisa</button></div>
            ) : (
              <div className="co-trips">
                {trips.map((t) => (
                  <button key={t.trip_id} className="co-trip" onClick={() => { setSelectedTrip(t); setStep("payment"); }} type="button">
                    <div className="co-trip-left">
                      <span className="co-trip-code">{t.route_code}</span>
                      <div className="co-trip-details">
                        <strong>{t.vehicle || t.route_name}</strong>
                        <span>{t.route_name} · {t.direction === "inbound" ? "Volta" : "Ida"}</span>
                        <span><Clock size={12} /> {t.started_at ? formatDateTime(t.started_at) : t.departure ? formatDateTime(t.departure) : "-"}</span>
                      </div>
                    </div>
                    <div className="co-trip-price">{t.fare_amount ? formatCurrency(t.fare_amount) : "-"}</div>
                  </button>
                ))}
              </div>
            )}
          </section>
        )}

        {step === "payment" && selectedTrip && (
          <section className="co-card">
            <button className="co-back" onClick={() => setStep("results")} type="button"><ArrowLeft size={16} /> Voltar</button>
            <div className="co-pay-summary">
              <div className="co-pay-route">
                <span className="co-trip-code">{selectedTrip.route_code}</span>
                <div><strong>{selectedTrip.vehicle || selectedTrip.route_name}</strong><span><Clock size={12} /> {selectedTrip.started_at ? formatDateTime(selectedTrip.started_at) : selectedTrip.departure ? formatDateTime(selectedTrip.departure) : "-"}</span></div>
              </div>
              <div className="co-pay-amount">{formatCurrency(selectedTrip.fare_amount)}</div>
            </div>
            <form className="co-form" onSubmit={pay}>
              <input className="co-input" required type="tel" placeholder="Telefone (84/85/86/87...)" value={phone} onChange={(e) => setPhone(e.target.value)} />
              <div className="co-row">
                <select className="co-select" value={quantity} onChange={(e) => setQuantity(Number(e.target.value))}>
                  {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n} bilhete{n > 1 ? "s" : ""}</option>)}
                </select>
                <div className="co-total">{formatCurrency(Number(selectedTrip.fare_amount || 0) * quantity)}</div>
              </div>
              <button className="co-btn" type="submit" disabled={submitting}>
                <Ticket size={18} />{submitting ? "A processar..." : "Pagar"}
              </button>
            </form>
          </section>
        )}

        {step === "confirmation" && result && (
          <section className="co-card co-success">
            <CheckCircle size={48} className="co-success-icon" />
            <h2>{result.payment_status === "confirmed" ? "Bilhete Emitido!" : "Pagamento Pendente"}</h2>
            <p>{result.detail_message}</p>
            <div className="co-receipt">
              <div><span>Referencia</span><strong>{result.checkout_reference}</strong></div>
              <div><span>Total</span><strong>{formatCurrency(result.total_amount)}</strong></div>
            </div>
            {result.status === "issued" && result.ticket_url && (
              <a className="co-btn" href={result.ticket_url} target="_blank" rel="noreferrer">
                <Ticket size={18} /> Ver Bilhete
              </a>
            )}
            <button className="co-btn-outline" onClick={reset} type="button">Nova Compra</button>
            {result.payment_status === "pending" && (
              <p className="co-pending">Confirme o pagamento na sua carteira movel.</p>
            )}
          </section>
        )}
      </main>

      <footer className="co-footer">
        <span>powered by</span>
        <img alt="UpDigital" src={pickLogo(branding.powered_by_logo_url, "/assets/up-digital-logo/up_digital_dark.png")} className="co-footer-logo" />
      </footer>
    </div>
  );
}
