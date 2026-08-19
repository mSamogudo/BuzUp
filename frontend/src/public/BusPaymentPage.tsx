import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertCircle, ArrowRight, Bus, CheckCircle, MapPin, Phone, ShoppingCart, Ticket, Users } from "lucide-react";
import { apiPublic } from "../lib/api";
import { useBranding, pickLogo } from "../lib/branding";
import TermsDialog from "./booking/TermsDialog";

interface BusStop { id: number; code: string; name: string; }
interface ActiveTrip {
  trip_id: number;
  route_id: number;
  route_code: string;
  route_name: string;
  /** Urbana, interprovincial ou internacional — decide o que esta pagina pode fazer. */
  service_type?: string;
  /** Carreira com lugar marcado: o bilhete e nominal e o formulario rapido nao chega. */
  seat_selection?: boolean;
  departure?: string | null;
  stops: BusStop[];
}
interface VehicleInfo {
  uuid: string;
  registration: string;
}
interface BusInfo {
  vehicle: VehicleInfo;
  active_trips: ActiveTrip[];
}
interface CheckoutResult {
  checkout_reference: string;
  payment_reference: string;
  total_amount: string;
  status: string;
  payment_status: string;
  detail_message: string;
  ticket_url: string;
}

const PHONE_REGEX = /^[0-9]{9}$/;

export default function BusPaymentPage() {
  const { branding } = useBranding();
  const { vehicleUuid } = useParams<{ vehicleUuid: string }>();
  const [info, setInfo] = useState<BusInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [originId, setOriginId] = useState("");
  const [destId, setDestId] = useState("");
  const [phone, setPhone] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<CheckoutResult | null>(null);
  // Sem isto o servidor recusa a compra — e recusava-a em silencio, porque esta
  // pagina nem sequer perguntava.
  const [aceitouTermos, setAceitouTermos] = useState(false);
  const [termosAbertos, setTermosAbertos] = useState(false);

  const loadInfo = useCallback(async () => {
    if (!vehicleUuid) return;
    setLoading(true);
    setError("");
    try {
      const data = await apiPublic(`/api/public/bus/${vehicleUuid}/`);
      setInfo(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar dados do autocarro.");
    } finally {
      setLoading(false);
    }
  }, [vehicleUuid]);

  useEffect(() => { void loadInfo(); }, [loadInfo]);

  const trip = info?.active_trips?.[0] || null;
  const temTermos = (branding.terms_sections || []).length > 0;
  // Carreira com lugar marcado: o bilhete e nominal e leva assento, documento e
  // contacto de emergencia. Esta pagina recolhe origem, destino e telemovel —
  // montava uma compra que o servidor recusa. Em vez de copiar aqui o fluxo
  // completo (e ter dois caminhos de dinheiro a divergir), entrega-se ao que ja
  // existe, com o percurso preenchido.
  const precisaFluxoCompleto = Boolean(trip?.seat_selection);

  const linkFluxoCompleto = () => {
    if (!trip) return "/comprar";
    const p = new URLSearchParams();
    if (originId) p.set("origem", originId);
    if (destId) p.set("destino", destId);
    const dia = trip.departure ? trip.departure.slice(0, 10) : "";
    if (dia) p.set("data", dia);
    if (quantity) p.set("pax", quantity);
    return `/comprar?${p}`;
  };

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!trip || precisaFluxoCompleto) return;
    setError("");

    if (!originId || !destId) {
      setError("Selecione origem e destino.");
      return;
    }
    if (originId === destId) {
      setError("O destino deve ser diferente da origem.");
      return;
    }
    if (!PHONE_REGEX.test(phone)) {
      setError("Telefone deve ter 9 digitos.");
      return;
    }
    const qty = Number(quantity);
    if (!Number.isFinite(qty) || qty < 1 || qty > 10) {
      setError("Quantidade deve estar entre 1 e 10.");
      return;
    }

    setSubmitting(true);
    try {
      const origin = trip.stops.find((s) => String(s.id) === originId);
      const dest = trip.stops.find((s) => String(s.id) === destId);
      const data = await apiPublic("/api/guest-checkouts/", {
        method: "POST",
        body: JSON.stringify({
          payer_phone: phone,
          buyer_name: "",
          route_code: trip.route_code,
          route_name: trip.route_name,
          origin_stop: origin?.name || "",
          destination_stop: dest?.name || "",
          origin_stop_id: origin?.id,
          destination_stop_id: dest?.id,
          quantity: qty,
          unit_amount: "0",
          trip_id: trip.trip_id,
          accept_terms: aceitouTermos,
          terms_version: branding.terms_version,
        }),
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao processar pedido.");
    } finally {
      setSubmitting(false);
    }
  }

  function resetForm() {
    setResult(null);
    setOriginId("");
    setDestId("");
    setPhone("");
    setQuantity("1");
    setError("");
    setAceitouTermos(false);
  }

  return (
    <div className="bus-pay">
      <header className="bus-pay-header">
        <img alt="BusUp" src={pickLogo(branding.primary_logo_url, "/assets/busup/logo-dark.png")} className="bus-pay-logo" />
        <div className="bus-pay-header-text">
          <strong>BusUp</strong>
          <span>Comprar Bilhete</span>
        </div>
      </header>

      <main className="bus-pay-body">
        {error && (
          <div className="bus-pay-error" role="alert">
            <AlertCircle size={16} />
            <span>{error}</span>
            <button onClick={() => setError("")} type="button" aria-label="Fechar">&times;</button>
          </div>
        )}

        {loading ? (
          <section className="bus-pay-card bus-pay-empty">
            <Bus size={32} />
            <p>A carregar...</p>
          </section>
        ) : !info || !trip ? (
          <section className="bus-pay-card bus-pay-empty">
            <AlertCircle size={32} />
            <p>{info ? "Este autocarro nao tem viagem activa." : "Autocarro nao encontrado."}</p>
          </section>
        ) : result ? (
          <section className="bus-pay-card bus-pay-success">
            <CheckCircle size={48} className="bus-pay-success-icon" />
            <h2>{result.payment_status === "confirmed" ? "Bilhete Emitido" : "Pedido Recebido"}</h2>
            <p>{result.detail_message}</p>
            <div className="bus-pay-receipt">
              <div><span>Referencia</span><strong>{result.checkout_reference}</strong></div>
              <div><span>Total</span><strong>{result.total_amount} MZN</strong></div>
            </div>
            {result.status === "issued" && result.ticket_url && (
              <a className="bus-pay-btn" href={result.ticket_url} target="_blank" rel="noreferrer">
                <Ticket size={18} /> Ver Bilhete
              </a>
            )}
            <button className="bus-pay-btn-outline" onClick={resetForm} type="button">
              Novo Pedido
            </button>
          </section>
        ) : (
          <>
            <section className="bus-pay-card bus-pay-route-card">
              <div className="bus-pay-route-icon"><Bus size={20} /></div>
              <div className="bus-pay-route-text">
                <strong>{trip.route_code} - {trip.route_name}</strong>
                <span>{info.vehicle.registration}</span>
              </div>
            </section>

            {precisaFluxoCompleto ? (
              <section className="bus-pay-card bus-pay-handoff">
                <h2>Esta viagem tem lugar marcado</h2>
                <p>
                  Numa carreira {trip.service_type === "international" ? "internacional" : "interprovincial"}{" "}
                  o bilhete é nominal: leva o seu lugar, o nome de quem viaja, o
                  documento e um contacto de emergência. Continue na compra
                  completa — o percurso vai preenchido.
                </p>
                <label className="bus-pay-field">
                  <span><MapPin size={14} /> Origem</span>
                  <select value={originId}
                    onChange={(e) => { const v = e.target.value; setOriginId(v); if (v && v === destId) setDestId(""); }}>
                    <option value="">Seleccione</option>
                    {trip.stops.filter((st) => String(st.id) !== destId).map((st) => (
                      <option key={st.id} value={st.id}>{st.name}</option>
                    ))}
                  </select>
                </label>
                <label className="bus-pay-field">
                  <span><MapPin size={14} /> Destino</span>
                  <select value={destId} onChange={(e) => setDestId(e.target.value)}>
                    <option value="">Seleccione</option>
                    {trip.stops.filter((st) => String(st.id) !== originId).map((st) => (
                      <option key={st.id} value={st.id}>{st.name}</option>
                    ))}
                  </select>
                </label>
                <Link className="bus-pay-btn" to={linkFluxoCompleto()}>
                  Continuar a compra <ArrowRight size={18} />
                </Link>
              </section>
            ) : (
            <section className="bus-pay-card">
              <form className="bus-pay-form" onSubmit={handleSubmit}>
                <label className="bus-pay-field">
                  <span><MapPin size={14} /> Origem</span>
                  <select
                    value={originId}
                    onChange={(e) => { const v = e.target.value; setOriginId(v); if (v && v === destId) setDestId(""); }}
                    required
                  >
                    <option value="">Seleccione</option>
                    {trip.stops.filter((s) => String(s.id) !== destId).map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </label>

                <label className="bus-pay-field">
                  <span><MapPin size={14} /> Destino</span>
                  <select
                    value={destId}
                    onChange={(e) => { const v = e.target.value; setDestId(v); if (v && v === originId) setOriginId(""); }}
                    required
                  >
                    <option value="">Seleccione</option>
                    {trip.stops.filter((s) => String(s.id) !== originId).map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </label>

                <label className="bus-pay-field">
                  <span><Users size={14} /> Quantidade</span>
                  <input
                    type="number"
                    inputMode="numeric"
                    min={1}
                    max={10}
                    step={1}
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value.replace(/[^0-9]/g, ""))}
                    required
                  />
                </label>

                <label className="bus-pay-field">
                  <span><Phone size={14} /> Telefone (9 digitos)</span>
                  <input
                    type="tel"
                    inputMode="numeric"
                    pattern="[0-9]{9}"
                    maxLength={9}
                    placeholder="84/85/86/87..."
                    value={phone}
                    onChange={(e) => setPhone(e.target.value.replace(/[^0-9]/g, "").slice(0, 9))}
                    required
                  />
                </label>

                {temTermos && !precisaFluxoCompleto ? (
                  <label className="bus-pay-accept">
                    <input type="checkbox" checked={aceitouTermos} required
                      onChange={(e) => setAceitouTermos(e.target.checked)} />
                    <span>
                      Li e aceito os{" "}
                      <button type="button" className="bus-pay-terms-link"
                        onClick={() => setTermosAbertos(true)}>Termos e Condições</button>
                      {branding.company_name ? ` da ${branding.company_name}` : ""}.
                    </span>
                  </label>
                ) : null}

                <button
                  className="bus-pay-btn"
                  type="submit"
                  disabled={submitting || !originId || !destId || !PHONE_REGEX.test(phone)
                    || (temTermos && !aceitouTermos)}
                >
                  <ShoppingCart size={18} />
                  {submitting ? "A processar..." : "Solicitar Bilhete"}
                </button>
              </form>
            </section>
            )}
          </>
        )}
      </main>

      <TermsDialog
        open={termosAbertos}
        onClose={() => setTermosAbertos(false)}
        sections={branding.terms_sections || []}
        intro={branding.terms_intro}
        closing={branding.terms_closing}
        company={branding.company_name}
        version={branding.terms_version}
        updatedAt={branding.terms_updated_at || undefined}
      />

      <footer className="bus-pay-footer">
        <span>powered by</span>
        <img alt="UpDigital" src={pickLogo(branding.powered_by_logo_url, "/assets/up-digital-logo/up_digital_dark.png")} className="bus-pay-footer-logo" />
      </footer>
    </div>
  );
}
