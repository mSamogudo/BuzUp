import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { CampoData } from "../../ui/CampoData";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft, ArrowRight, Calendar, MapPin, Moon, Repeat, Search, Sun, Users,
} from "lucide-react";
import { useBranding, pickLogo } from "../../lib/branding";
import { useUi } from "../../ui/UiPreferences";
import { bt, type BookingKey } from "./booking.i18n";
import SeatMap, { type SeatRow } from "./SeatMap";
import StopCombo from "./StopCombo";
import TermsDialog from "./TermsDialog";
import { CampoSelect } from "../../ui/CampoSelect";
import "./booking.css";

// `rtrips`/`rseats` são a ida e volta: o regresso é outro autocarro, com a
// sua lotação e o seu lugar, por isso escolhe-se à parte.
// `pax` e `pay` continuam na barra de progresso e ja nao sao estados desta
// pagina: vivem no `/checkout`. Ficam porque quem compra deve ver a jornada
// inteira, e nao so o troco que ainda esta neste ecra.
type Step = "search" | "trips" | "seats" | "rtrips" | "rseats" | "pax" | "pay";

const CHAVES_IDA: { key: Step; label: BookingKey }[] = [
  { key: "search", label: "stepTrip" },
  { key: "trips", label: "stepDeparture" },
  { key: "seats", label: "stepSeats" },
  { key: "pax", label: "stepPax" },
  { key: "pay", label: "stepPay" },
];

/** Com regresso, as etapas do caminho de volta entram na barra de progresso.
 *  Escondê-las fazia o passageiro pensar que estava a um passo do fim quando
 *  ainda lhe faltavam dois. */
const CHAVES_IDA_E_VOLTA: { key: Step; label: BookingKey }[] = [
  { key: "search", label: "stepTrip" },
  { key: "trips", label: "stepOutbound" },
  { key: "seats", label: "stepSeats" },
  { key: "rtrips", label: "stepReturn" },
  { key: "rseats", label: "stepSeats" },
  { key: "pax", label: "stepPax" },
  { key: "pay", label: "stepPay" },
];

import {
  getJson, longDate, money, timeOf,
  type StopOpt, type TripOpt,
} from "./compra";
import type { Reserva } from "./CheckoutPage";

export default function BookingPage() {
  const navegar = useNavigate();
  const { branding } = useBranding();
  // Idioma e tema vêm do mesmo sítio que o resto da aplicação: quem escolheu
  // inglês no portal não devia voltar ao português ao clicar em "comprar".
  const { locale, setLocale, theme, toggleTheme } = useUi();
  const tr = (k: Parameters<typeof bt>[1], v?: Record<string, string | number>) => bt(locale, k, v);
  const logo = pickLogo(branding.sidebar_logo_url, branding.primary_logo_url);

  const [step, setStep] = useState<Step>("search");
  const [stops, setStops] = useState<StopOpt[]>([]);
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [date, setDate] = useState("");
  const [qty, setQty] = useState(1);
  // Só ida ou ida e volta. É uma escolha do passageiro e não um campo que se
  // deixa em branco: mostrar sempre a data de regresso pedia uma resposta a
  // quem só quer ir, e obrigava a adivinhar o que "vazio" queria dizer.
  const [tipo, setTipo] = useState<"ida" | "idaevolta">("ida");
  const [returnDate, setReturnDate] = useState("");
  const idaEVolta = tipo === "idaevolta";

  /** Trocar de tipo limpa o regresso: deixar restos era vender o que ninguém pediu. */
  const escolherTipo = (novo: "ida" | "idaevolta") => {
    setTipo(novo);
    if (novo === "ida") {
      setReturnDate(""); setRtrip(null); setRtrips([]); setRpicked([]);
    }
  };

  const [trips, setTrips] = useState<TripOpt[]>([]);
  const [trip, setTrip] = useState<TripOpt | null>(null);
  const [rows, setRows] = useState<SeatRow[]>([]);
  // Regresso: partidas, escolha, planta e lugares — tudo próprio, porque é
  // outro autocarro noutro dia.
  const [rtrips, setRtrips] = useState<TripOpt[]>([]);
  const [rtrip, setRtrip] = useState<TripOpt | null>(null);
  const [rrows, setRrows] = useState<SeatRow[]>([]);
  const [rpicked, setRpicked] = useState<string[]>([]);
  // `hasSeatMap` diz se HÁ PLANTA a desenhar; `needsIdentity` diz se a ROTA é
  // interprovincial/internacional. Não são a mesma coisa: uma rota longa cuja
  // viatura ainda não tem lotação registada vende sem planta, mas continua a
  // precisar de documento e de contacto de emergência. Usar a planta como
  // critério escondia esses campos e a compra era recusada pelo servidor sem
  // o comprador ter onde os escrever.
  const [hasSeatMap, setHasSeatMap] = useState(true);
  const [needsIdentity, setNeedsIdentity] = useState(true);
  const [picked, setPicked] = useState<string[]>([]);
  // Contacto de emergência: obrigatório nas rotas que marcam lugar
  // (interprovincial/internacional), porque é para o manifesto de bordo que
  // serve. Numa carreira urbana o campo nem aparece.
  // Carteira movel ou cartao. O servidor deduz M-Pesa/e-Mola do telefone;
  // o cartao e uma escolha explicita, porque leva o comprador para fora do
  // site (pagina do DPO) e volta por `?ref=`.
  // Aceitação dos Termos. O servidor recusa a compra sem ela — a caixa aqui é
  // para o passageiro poder ler antes de dizer que sim, não é a barreira.
  const [termosAbertos, setTermosAbertos] = useState(false);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Moeda de EXIBIÇÃO (rand nas rotas p/ África do Sul). A cobrança é sempre
  // em meticais; a taxa vem do portal e o bilhete congela a moeda escolhida.
  const [rates, setRates] = useState<Record<string, number>>({});
  // Passo de arredondamento por moeda, tal como o servidor o aplica.
  const [roundings, setRoundings] = useState<Record<string, number>>({});
  const [currency, setCurrency] = useState("MZN");

  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);

  /** O troço que o passageiro escolheu — é a ele que o preço diz respeito. */
  const percurso = (t: TripOpt) =>
    (t.origin_stop && t.destination_stop)
      ? `${t.origin_stop} → ${t.destination_stop}`
      : (t.route_name || t.route_code);

  useEffect(() => {
    document.title = `${tr("pageTitle")} · ${branding.platform_name || "BusUp"}`;
    // sellable=1: só origens/destinos com partidas futuras à venda.
    getJson("/api/public/trips/?sellable=1")
      .then((d) => setStops(d.stops || []))
      .catch(() => setStops([]));
    getJson("/api/public/exchange-rate/")
      .then((d) => {
        const parsed: Record<string, number> = {};
        Object.entries(d.rates || {}).forEach(([k, v]) => {
          const n = Number(v);
          if (n > 0) parsed[k] = n;
        });
        const passos: Record<string, number> = {};
        Object.entries(d.rounding || {}).forEach(([k, v]) => {
          const n = Number(v);
          if (n > 0) passos[k] = n;
        });
        setRates(parsed);
        setRoundings(passos);
      })
      .catch(() => { setRates({}); setRoundings({}); });
  }, []);

  const otherCurrencies = Object.keys(rates).sort();
  const rate = currency !== "MZN" ? rates[currency] : undefined;
  // Preço na moeda escolhida (só visual — o valor cobrado continua em MZN).
  //
  // Arredonda-se PARA CIMA ao passo definido no portal, exactamente como o
  // servidor faz ao congelar o valor no bilhete: uma divisão por uma taxa quase
  // nunca dá um número redondo, e o passageiro ficava a olhar para cêntimos que
  // ninguém no balcão dá em troco. Para cima, e não para baixo, para o valor
  // mostrado nunca ser menor do que aquilo que lhe sai da conta.
  const inDisplay = (mzn: number) => {
    if (!rate) return mzn;
    const bruto = mzn / rate;
    const passo = roundings[currency] || 1;
    return Math.ceil(bruto / passo) * passo;
  };
  const priceLabel = (mzn: number) => (rate
    ? `${money(inDisplay(mzn))} ${currency}`
    : `${money(mzn)} MZN`);

  const currencyToggle = otherCurrencies.length > 0 && (
    <div className="bzbk-currency" role="group" aria-label={tr("currencyGroup")}>
      {["MZN", ...otherCurrencies].map((c) => (
        <button key={c} type="button" aria-pressed={currency === c}
          className={`bzbk-currency-btn${currency === c ? " is-on" : ""}`}
          onClick={() => setCurrency(c)}>
          {c}
        </button>
      ))}
    </div>
  );

  // O DPO devolve a pessoa a `/comprar?ref=GC-...` — endereco construido pelo
  // servidor (ver `tests_cartao_dpo.py`), que esta fora de ambito. Quem sabe
  // mostrar o desfecho e o checkout, por isso o `ref` segue para la.
  useEffect(() => {
    const ref = new URLSearchParams(window.location.search).get("ref");
    if (ref) navegar(`/checkout?ref=${encodeURIComponent(ref)}`, { replace: true });
  }, [navegar]);

  // Link partilhável: /comprar?origem=66&destino=70&data=2026-08-05&pax=2
  // (campanhas e CTAs da landing podem apontar directamente a um percurso).
  //
  // `volta=<data>` acrescenta o regresso. Sem ele, a pesquisa do hero da
  // landing mandava quem queria ida e volta para um formulário de só ida, e a
  // escolha perdia-se pelo caminho.
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const o = p.get("origem"); const d = p.get("destino");
    const dt = p.get("data"); const n = Number(p.get("pax") || 0);
    const v = p.get("volta");
    if (o) setOrigin(o);
    if (d) setDestination(d);
    if (dt) setDate(dt);
    if (n >= 1 && n <= 5) setQty(n);
    // Só o tipo e a data: o resto do que `escolherTipo` limpa ainda não
    // existe nesta altura, e chamá-la aqui apagava a data que acabámos de pôr.
    if (v) { setTipo("idaevolta"); setReturnDate(v); }
  }, []);

  const runSearch = useCallback(async (o: string, d: string, dt: string) => {
    setBusy(true); setError("");
    try {
      const q = new URLSearchParams({ origin: o, destination: d, date: dt });
      const data = await getJson(`/api/public/trips/?${q}`);
      setTrips(data.trips || []);
      setStep("trips");
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : tr("errSearch"));
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
      setNeedsIdentity(Boolean(d.seat_selection));
      setRows(d.rows || []);
      if (d.has_seat_map) { setStep("seats"); return; }
      // Sem planta na ida: segue para o regresso, se houver.
      if (idaEVolta) { await procurarVolta(); return; }
      irParaCheckout({ trip: t, needsIdentity: Boolean(d.seat_selection) });
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : tr("errSeats"));
    } finally { setBusy(false); }
  };

  /** Partidas do regresso: o mesmo percurso ao contrário, na data de volta. */
  const procurarVolta = useCallback(async () => {
    setBusy(true); setError("");
    try {
      const q = new URLSearchParams({ origin: destination, destination: origin, date: returnDate });
      const data = await getJson(`/api/public/trips/?${q}`);
      setRtrips(data.trips || []);
      setStep("rtrips");
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : tr("errReturnSearch"));
    } finally { setBusy(false); }
  }, [destination, origin, returnDate]);

  const chooseReturnTrip = async (t: TripOpt) => {
    setBusy(true); setError(""); setRtrip(t); setRpicked([]);
    try {
      const d = await getJson(`/api/public/trips/${t.trip_id}/seats/`);
      setRrows(d.rows || []);
      if (d.has_seat_map) { setStep("rseats"); return; }
      if (trip) irParaCheckout({ trip, rtrip: t, seats: picked, needsIdentity });
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : tr("errReturnSeats"));
    } finally { setBusy(false); }
  };

  const toggleSeat = (label: string) => {
    setPicked((prev) => prev.includes(label)
      ? prev.filter((s) => s !== label)
      : (prev.length >= qty ? prev : [...prev, label]));
  };

  const toggleReturnSeat = (label: string) => {
    setRpicked((prev) => prev.includes(label)
      ? prev.filter((s) => s !== label)
      : (prev.length >= qty ? prev : [...prev, label]));
  };

  /** Entrega a compra ao checkout.
   *
   *  Recebe `trip` e `needsIdentity` em vez de os ler do estado: quem chama
   *  acabou de os definir no mesmo ciclo, e ler o estado aqui traria o valor
   *  da partida ANTERIOR. E o mesmo cuidado que o assistente ja tinha.
   *
   *  A reserva viaja em `location.state` — nao ha carrinho do lado do
   *  servidor. O checkout trata o caso de ela nao chegar. */
  const irParaCheckout = (o: {
    trip: TripOpt; rtrip?: TripOpt | null;
    seats?: string[]; rseats?: string[]; needsIdentity: boolean;
  }) => {
    const oStop = stops.find((s) => String(s.id) === origin);
    const dStop = stops.find((s) => String(s.id) === destination);
    const reserva: Reserva = {
      origin, destination,
      originName: oStop?.name || "", destinationName: dStop?.name || "",
      date, returnDate,
      trip: o.trip, rtrip: o.rtrip ?? null,
      qty, seats: o.seats ?? [], rseats: o.rseats ?? [],
      needsIdentity: o.needsIdentity,
    };
    navegar("/checkout", { state: { reserva } });
  };

  /** Fim da escolha de lugares da ida: ou vai ao regresso, ou ao checkout. */
  const fecharIda = () => {
    if (idaEVolta && !rtrip) { void procurarVolta(); return; }
    if (trip) irParaCheckout({ trip, seats: picked, needsIdentity });
  };

  const fecharVolta = () => {
    if (trip) irParaCheckout({ trip, rtrip, seats: picked, rseats: rpicked, needsIdentity });
  };

  // A volta é cotada para o percurso invertido; o servidor cota-a outra vez e
  // é o valor dele que manda. Aqui só se mostra o que se vai pagar.

  const temTermos = (branding.terms_sections || []).length > 0;
  // Termos na língua escolhida, com recurso à portuguesa: mais vale mostrá-los
  // na língua errada do que não mostrar termos nenhuns a quem vai aceitar.
  const termos = (locale === "en" && (branding.terms_sections_en || []).length > 0)
    ? { sections: branding.terms_sections_en, intro: branding.terms_intro_en, closing: branding.terms_closing_en }
    : { sections: branding.terms_sections || [], intro: branding.terms_intro, closing: branding.terms_closing };
  // Sem duplicados: o número de apoio costuma estar também na lista geral.
  const telefones = [...new Set([
    ...(branding.contact_phones || []),
    branding.support_phone,
  ].filter(Boolean))];
  const passos = idaEVolta ? CHAVES_IDA_E_VOLTA : CHAVES_IDA;
  const stepIndex = passos.findIndex((s) => s.key === step);

  return (
    <div className="bzbk">
      <header className="bzbk-top">
        <div className="bzbk-wrap">
          <div className="bzbk-top-in">
            {/* A marca vem do operador, e nao do produto. Quem chega do hero
                da TPM-TUR comprava a "BusUp" nesta pagina e pagava a "TPM-TUR"
                na seguinte: a mesma compra com dois donos. */}
            <Link to="/tpm-tur" aria-label={branding.company_name || "Inicio"}>
              {logo
                ? <img src={logo} alt={branding.company_name || ""} style={{ height: 30, display: "block" }} />
                : <strong style={{ fontSize: 22 }}>{branding.company_name}</strong>}
            </Link>
            <div className="bzbk-top-controls">
              <div className="bzbk-lang" role="group" aria-label="PT / EN">
                <button type="button" aria-pressed={locale === "pt"}
                  onClick={() => setLocale("pt")}>PT</button>
                <button type="button" aria-pressed={locale === "en"}
                  onClick={() => setLocale("en")}>EN</button>
              </div>
              <button type="button" className="bzbk-theme" onClick={toggleTheme}
                aria-label={theme === "dark" ? tr("lightTheme") : tr("darkTheme")}
                title={theme === "dark" ? tr("lightTheme") : tr("darkTheme")}>
                {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
              </button>
              <Link to="/tpm-tur" className="bzbk-kicker" style={{ color: "var(--on-navy-soft)" }}>{tr("backToSite")}</Link>
            </div>
          </div>
          <div style={{ position: "relative", zIndex: 2, marginTop: 18 }}>
            <div className="bzbk-kicker">{tr("kicker")}</div>
            <h1 className="bzbk-title">{tr("title")}</h1>
            <p className="bzbk-sub">{tr("sub")}</p>
          </div>
          <nav className="bzbk-steps" aria-label={tr("steps")}>
            {passos.map((s, i) => (
              <span key={s.key}
                className={`bzbk-step${s.key === step ? " is-active" : ""}${i < stepIndex ? " is-done" : ""}`}>
                <b>{i < stepIndex ? "✓" : i + 1}</b>{tr(s.label)}
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
                <h2 className="bzbk-h2">{tr("whereTo")}</h2>
                <p className="bzbk-lead">{tr("searchLead")}</p>

                <div className="bzbk-triptype" role="radiogroup" aria-label={tr("ticketType")}>
                  <button type="button" role="radio" aria-checked={!idaEVolta}
                    className={`bzbk-triptype-opt${!idaEVolta ? " is-on" : ""}`}
                    onClick={() => escolherTipo("ida")}>
                    <ArrowRight size={15} />
                    <span>{tr("oneWay")}</span>
                  </button>
                  <button type="button" role="radio" aria-checked={idaEVolta}
                    className={`bzbk-triptype-opt${idaEVolta ? " is-on" : ""}`}
                    onClick={() => escolherTipo("idaevolta")}>
                    <Repeat size={15} />
                    <span>{tr("roundTrip")}</span>
                  </button>
                </div>

                <div className="bzbk-grid">
                  <div className="bzbk-field bzbk-field-wide">
                    <label className="bzbk-label" htmlFor="o"><MapPin size={12} style={{ verticalAlign: -2 }} /> {tr("origin")}</label>
                    <StopCombo id="o" onChange={setOrigin} placeholder={tr("searchStops")}
                      stops={stops} value={origin} />
                  </div>
                  <div className="bzbk-field bzbk-field-wide">
                    <label className="bzbk-label" htmlFor="d"><MapPin size={12} style={{ verticalAlign: -2 }} /> {tr("destination")}</label>
                    <StopCombo exclude={origin} id="d" onChange={setDestination}
                      placeholder={tr("searchStops")} stops={stops} value={destination} />
                  </div>
                  <div className="bzbk-field">
                    <label className="bzbk-label" htmlFor="dt"><Calendar size={12} style={{ verticalAlign: -2 }} /> {tr("outboundDate")}</label>
                    <CampoData onChange={(v) => setDate(v)} value={date} min={today} />
                  </div>
                  {/* Só aparece depois de o passageiro pedir ida e volta:
                      um campo de data a quem só quer ir é uma pergunta a mais. */}
                  {idaEVolta ? (
                    <div className="bzbk-field">
                      <label className="bzbk-label" htmlFor="dtv">
                        <Calendar size={12} style={{ verticalAlign: -2 }} /> Data de volta
                      </label>
                      <CampoData onChange={(v) => setReturnDate(v)} value={returnDate} min={date || today} />
                    </div>
                  ) : null}
                  <div className="bzbk-field">
                    <label className="bzbk-label" htmlFor="q"><Users size={12} style={{ verticalAlign: -2 }} /> {tr("passengersCount")}</label>
                    <CampoSelect className="bzbk-campo" id="q" onChange={(valor) => setQty(Number(valor))} value={String(qty)}>
                      {[1, 2, 3, 4, 5].map((n) => (
                        <option key={n} value={n}>{n} {n === 1 ? tr("passenger") : tr("passengersPlural")}</option>
                      ))}
                    </CampoSelect>
                  </div>
                </div>
                <div className="bzbk-actions">
                  <span />
                  <button className="bzbk-btn" type="submit"
                    disabled={busy || !origin || !destination || !date || (idaEVolta && !returnDate)}>
                    {busy ? <span className="bzbk-spin" /> : <Search size={17} />} {tr("searchTrips")}
                  </button>
                </div>
              </form>
            )}

            {step === "trips" && (
              <div>
                <div className="bzbk-h2-row">
                  <h2 className="bzbk-h2">{tr("tripsTitle")}</h2>
                  {currencyToggle}
                </div>
                <p className="bzbk-lead">{date && longDate(date)} · {qty} {qty === 1 ? tr("ticket") : tr("ticketsPlural")}</p>
                {trips.length === 0 && (
                  <div className="bzbk-notice warn">
                    {tr("noTrips")}
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
                        {/* O percurso escolhido, e não o nome da rota: o preço
                            ao lado é DESTE troço. "Maputo x Nelspruit · 1500 MZN"
                            dizia ao passageiro que ia pagar a rota inteira. */}
                        <span className="bzbk-trip-route">
                          {t.origin_stop && t.destination_stop
                            ? `${t.origin_stop} → ${t.destination_stop}`
                            : (t.route_name || t.route_code)}
                        </span>
                        <span className="bzbk-trip-meta">
                          {t.route_name ? `${t.route_name} · ` : ""}
                          {t.vehicle ? `Viatura ${t.vehicle} · ` : ""}
                          {!t.on_sale
                            ? <span className="bzbk-seats-none">{t.sale_unavailable_reason}</span>
                            : left === null
                              ? tr("seatsAvailable")
                              : left === 0
                                ? <span className="bzbk-seats-none">{tr("soldOut")}</span>
                                : left <= 5
                                  ? <span className="bzbk-seats-few">{tr("onlyNSeats", { n: left })}</span>
                                  : <span className="bzbk-seats-left">{tr("nSeatsLeft", { n: left })}</span>}
                        </span>
                      </span>
                      <span className="bzbk-trip-price">
                        {priceLabel(Number(t.fare_amount || 0))}
                        <small>{rate ? `${money(t.fare_amount)} MZN · ${tr("perPerson")}` : tr("perPerson")}</small>
                      </span>
                    </button>
                  );
                })}
                <div className="bzbk-actions">
                  <button className="bzbk-btn ghost" type="button" onClick={() => setStep("search")}>
                    <ArrowLeft size={16} /> {tr("changeSearch")}
                  </button>
                </div>
              </div>
            )}

            {step === "seats" && trip && (
              <div>
                <h2 className="bzbk-h2">{qty === 1 ? tr("pickSeat") : tr("pickSeats", { n: qty })}</h2>
                <p className="bzbk-lead">
                  {percurso(trip)} · {date && longDate(date)} · {tr("departsAt")} {timeOf(trip.departure)}
                </p>
                {hasSeatMap
                  ? <SeatMap rows={rows} picked={picked} maxPick={qty} onToggle={toggleSeat} />
                  : <div className="bzbk-notice info">{tr("noSeatMap")}</div>}
                <div className="bzbk-actions">
                  <button className="bzbk-btn ghost" type="button" onClick={() => setStep("trips")}>
                    <ArrowLeft size={16} /> {tr("otherTrip")}
                  </button>
                  <button className="bzbk-btn" type="button" disabled={picked.length !== qty} onClick={fecharIda}>
                    {picked.length === qty
                      ? <>{tr("continue")} <ArrowRight size={16} /></>
                      : tr("stillToPick", { n: qty - picked.length })}
                  </button>
                </div>
              </div>
            )}

            {step === "rtrips" && (
              <div>
                <div className="bzbk-h2-row">
                  <h2 className="bzbk-h2">{tr("returnTripsTitle")}</h2>
                  {currencyToggle}
                </div>
                <p className="bzbk-lead">
                  {returnDate && longDate(returnDate)} · {tr("returnLead")}
                </p>
                {rtrips.length === 0 && (
                  <div className="bzbk-notice warn">
                    {tr("noReturn")}
                  </div>
                )}
                {rtrips.map((t) => {
                  const left = t.seats_available;
                  return (
                    <button key={t.trip_id} className="bzbk-trip" type="button"
                      disabled={!t.on_sale || (left !== null && left < qty)}
                      onClick={() => chooseReturnTrip(t)}>
                      <span className="bzbk-trip-time">{timeOf(t.departure)}</span>
                      <span className="bzbk-trip-main">
                        <span className="bzbk-trip-route">{percurso(t)}</span>
                        <span className="bzbk-trip-meta">
                          {t.vehicle ? `Viatura ${t.vehicle} · ` : ""}
                          {!t.on_sale
                            ? <span className="bzbk-seats-none">{t.sale_unavailable_reason}</span>
                            : left === null
                              ? tr("seatsAvailable")
                              : left === 0
                                ? <span className="bzbk-seats-none">{tr("soldOut")}</span>
                                : left <= 5
                                  ? <span className="bzbk-seats-few">{tr("onlyNSeats", { n: left })}</span>
                                  : <span className="bzbk-seats-left">{tr("nSeatsLeft", { n: left })}</span>}
                        </span>
                      </span>
                      <span className="bzbk-trip-price">
                        {priceLabel(Number(t.fare_amount || 0))}
                        <small>{rate ? `${money(t.fare_amount)} MZN · ${tr("perPerson")}` : tr("perPerson")}</small>
                      </span>
                    </button>
                  );
                })}
                <div className="bzbk-actions">
                  <button className="bzbk-btn ghost" type="button"
                    onClick={() => setStep(hasSeatMap ? "seats" : "trips")}>
                    <ArrowLeft size={16} /> {tr("back")}
                  </button>
                  {/* Desistir do regresso não pode obrigar a recomeçar tudo. */}
                  <button className="bzbk-btn ghost" type="button"
                    onClick={() => { escolherTipo("ida"); if (trip) irParaCheckout({ trip, seats: picked, needsIdentity }); }}>
                    {tr("buyOneWayInstead")}
                  </button>
                </div>
              </div>
            )}

            {step === "rseats" && rtrip && (
              <div>
                <h2 className="bzbk-h2">{tr("returnSeats")}</h2>
                <p className="bzbk-lead">
                  {percurso(rtrip)} · {returnDate && longDate(returnDate)} · {tr("departsAt")} {timeOf(rtrip.departure)}
                </p>
                <SeatMap rows={rrows} picked={rpicked} maxPick={qty} onToggle={toggleReturnSeat} />
                <div className="bzbk-actions">
                  <button className="bzbk-btn ghost" type="button" onClick={() => setStep("rtrips")}>
                    <ArrowLeft size={16} /> {tr("otherReturn")}
                  </button>
                  <button className="bzbk-btn" type="button"
                    disabled={rpicked.length !== qty} onClick={fecharVolta}>
                    {rpicked.length === qty
                      ? <>{tr("continue")} <ArrowRight size={16} /></>
                      : tr("stillToPick", { n: qty - rpicked.length })}
                  </button>
                </div>
              </div>
            )}

          </div>
        </div>

        {/* Contactos do OPERADOR, não os nossos: quem tem um problema com a
            viagem precisa de falar com quem a faz. Vêm da marca, por isso
            mudam no portal sem passar por aqui. */}
        <footer className="bzbk-foot">
          <div className="bzbk-foot-main">
            {branding.company_name ? <b>{branding.company_name}</b> : null}
            {branding.company_address ? <span>{branding.company_address}</span> : null}
          </div>
          <div className="bzbk-foot-contacts">
            {telefones.map((n) => (
              <a key={n} href={`tel:${n.replace(/[^+\d]/g, "")}`}>{n}</a>
            ))}
            {branding.support_email ? (
              <a href={`mailto:${branding.support_email}`}>{branding.support_email}</a>
            ) : null}
            {branding.company_website ? (
              <a href={`https://${branding.company_website.replace(/^https?:\/\//, "")}`}
                target="_blank" rel="noreferrer">{branding.company_website}</a>
            ) : null}
          </div>
          {temTermos ? (
            <button type="button" className="bzbk-terms-link"
              onClick={() => setTermosAbertos(true)}>Termos e Condições</button>
          ) : null}
        </footer>
      </div>

      <TermsDialog
        open={termosAbertos}
        onClose={() => setTermosAbertos(false)}
        sections={termos.sections}
        intro={termos.intro}
        closing={termos.closing}
        company={branding.company_name}
        version={branding.terms_version}
        updatedAt={branding.terms_updated_at || undefined}
      />
    </div>
  );
}
