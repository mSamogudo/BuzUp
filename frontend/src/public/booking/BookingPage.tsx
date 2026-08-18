import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft, ArrowRight, Bus, Calendar, CheckCircle2, Download, MapPin, Moon,
  Repeat, Search, Sun, Users,
} from "lucide-react";
import { useBranding, pickLogo } from "../../lib/branding";
import { useUi } from "../../ui/UiPreferences";
import { bt, type BookingKey } from "./booking.i18n";
import SeatMap, { type SeatRow } from "./SeatMap";
import StopCombo from "./StopCombo";
import TermsDialog from "./TermsDialog";
import "./booking.css";

// `rtrips`/`rseats` são a ida e volta: o regresso é outro autocarro, com a
// sua lotação e o seu lugar, por isso escolhe-se à parte.
type Step = "search" | "trips" | "seats" | "rtrips" | "rseats" | "pax" | "pay" | "done";

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

interface StopOpt { id: number; code: string; name: string }
interface TripOpt {
  trip_id: number; route_id: number; route_code: string; route_name: string;
  origin_stop: string; destination_stop: string;
  vehicle: string | null; departure: string | null; fare_amount: string | null;
  seats_available: number | null; on_sale: boolean; sale_unavailable_reason: string;
}
interface Passenger { name: string; document_type: string; document_number: string; seat: string; return_seat: string }

/// Forma de cada tipo de documento. Vem de `/api/public/document-types/`, o
/// mesmo sítio que o servidor usa para validar — escrever as regras outra vez
/// aqui garantia que um dia deixavam de concordar, e o campo passava a aceitar
/// o que a compra recusa.
interface DocRule {
  value: string; label: string; pattern: string; max_length: number;
  placeholder: string; help: string; digits_only: boolean;
}

/// Usada só até as regras chegarem do servidor (e se a rede falhar): deixa o
/// formulário utilizável em vez de o bloquear.
const DOC_FALLBACK: DocRule[] = [
  { value: "bi", label: "Bilhete de Identidade", pattern: "^[A-Z0-9]{4,32}$",
    max_length: 32, placeholder: "", help: "", digits_only: false },
  { value: "passport", label: "Passaporte", pattern: "^[A-Z0-9]{4,32}$",
    max_length: 32, placeholder: "", help: "", digits_only: false },
  { value: "dire", label: "DIRE", pattern: "^[A-Z0-9]{4,32}$",
    max_length: 32, placeholder: "", help: "", digits_only: false },
  { value: "cedula", label: "Cédula", pattern: "^[A-Z0-9]{4,32}$",
    max_length: 32, placeholder: "", help: "", digits_only: false },
  { value: "other", label: "Outro", pattern: "^[A-Z0-9]{4,32}$",
    max_length: 32, placeholder: "", help: "", digits_only: false },
];

/// Tira o que é só aspecto (espaços, traços) e põe em maiúsculas — a mesma
/// normalização que o servidor faz antes de gravar.
function normalizeDoc(raw: string) {
  return raw.replace(/[\s.\-/]/g, "").toUpperCase();
}

/// O que o campo deixa mesmo escrever. Num documento só de dígitos (DIRE,
/// cédula) as letras nem entram: mais vale o campo não as aceitar do que
/// aceitá-las para depois reclamar.
function filterDoc(raw: string, rule: DocRule) {
  const limpo = normalizeDoc(raw);
  return (rule.digits_only ? limpo.replace(/\D/g, "") : limpo)
    .slice(0, rule.max_length);
}

async function getJson(path: string) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" } });
  const body = await res.json().catch(() => ({}));
  // Sem mensagem própria: quem chama tem uma traduzida para o caso. Esta
  // função vive fora do componente e não alcança o dicionário.
  if (!res.ok) throw new Error(body.detail || "");
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
      setPax((prev) => prev.map((p) => ({ ...p, return_seat: "" })));
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
  const [docRules, setDocRules] = useState<DocRule[]>(DOC_FALLBACK);
  const [picked, setPicked] = useState<string[]>([]);
  const [pax, setPax] = useState<Passenger[]>([]);
  const [phone, setPhone] = useState("");
  // Contacto de emergência: obrigatório nas rotas que marcam lugar
  // (interprovincial/internacional), porque é para o manifesto de bordo que
  // serve. Numa carreira urbana o campo nem aparece.
  const [emergName, setEmergName] = useState("");
  const [emergPhone, setEmergPhone] = useState("");
  const [email, setEmail] = useState("");
  const [method, setMethod] = useState<"mpesa" | "emola">("mpesa");
  // Aceitação dos Termos. O servidor recusa a compra sem ela — a caixa aqui é
  // para o passageiro poder ler antes de dizer que sim, não é a barreira.
  const [aceitouTermos, setAceitouTermos] = useState(false);
  const [termosAbertos, setTermosAbertos] = useState(false);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ checkout_reference: string; ticket_url: string; total_amount: string } | null>(null);

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
    getJson("/api/public/document-types/")
      .then((d) => { if (d.document_types?.length) setDocRules(d.document_types); })
      .catch(() => { /* fica a lista de recurso: melhor comprar do que travar */ });
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
      setStep("pax");
      startPax([], Boolean(d.seat_selection));
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
      setStep("pax");
      startPax(picked, needsIdentity, []);
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

  const startPax = useCallback((seats: string[], comDocumento?: boolean, returnSeats?: string[]) => {
    // `needsIdentity` acabou de ser definido no mesmo ciclo em `chooseTrip`;
    // ler o estado aqui traria o valor da partida ANTERIOR.
    const pedeDocumento = comDocumento ?? needsIdentity;
    // Preserva o que já foi escrito. Antes, cada passagem por "Continuar"
    // reconstruía a lista de raiz: quem voltasse atrás para trocar de lugar
    // perdia os nomes e os documentos que já tinha preenchido, sem aviso.
    setPax((prev) => Array.from({ length: qty }, (_, i) => {
      const antes = prev[i];
      return {
        name: antes?.name || "",
        // O tipo só se preenche onde o documento é pedido. Numa carreira
        // urbana o campo do número nem aparece, e mandar o tipo sozinho era
        // mandar meia resposta a uma pergunta que não foi feita.
        document_type: pedeDocumento ? (antes?.document_type || "bi") : "",
        document_number: pedeDocumento ? (antes?.document_number || "") : "",
        seat: seats[i] || "",
        return_seat: (returnSeats ?? rpicked)[i] || "",
      };
    }));
  }, [qty, needsIdentity, rpicked]);

  /** Fim da escolha de lugares da ida: ou vai ao regresso, ou aos passageiros. */
  const goToPax = () => {
    if (idaEVolta && !rtrip) { void procurarVolta(); return; }
    startPax(picked);
    setStep("pax");
  };

  const goToPaxFromReturn = () => { startPax(picked, needsIdentity, rpicked); setStep("pax"); };

  const setPaxField = (i: number, key: keyof Passenger, value: string) => {
    setPax((prev) => prev.map((p, idx) => (idx === i ? { ...p, [key]: value } : p)));
  };

  const docRule = useCallback(
    (type: string) => docRules.find((d) => d.value === type) || docRules[docRules.length - 1],
    [docRules],
  );

  /// O que está errado no documento deste passageiro, por palavras. Vazio
  /// quando está bem — ou quando a viagem nem pede documento.
  const docError = useCallback((p: Passenger) => {
    if (!needsIdentity) return "";
    const rule = docRule(p.document_type);
    const num = normalizeDoc(p.document_number);
    if (!num) return `Indique o número do documento (${rule.label}).`;
    if (!new RegExp(rule.pattern).test(num)) return `${rule.label}: ${rule.help}`;
    return "";
  }, [needsIdentity, docRule]);

  /// O que falta para avançar, por palavras. Um botão cinzento e calado deixa
  /// o comprador sem saber o que corrigir — e o erro só aparecia quando o
  /// servidor recusava a compra, já depois de escolher o lugar.
  const paxMissing = useMemo(() => {
    if (pax.length === 0) return tr("errWhoTravels");
    for (let i = 0; i < pax.length; i++) {
      const p = pax[i];
      const quem = pax.length === 1 ? "" : ` do passageiro ${i + 1}`;
      if (p.name.trim().length < 3) return `Indique o nome completo${quem}.`;
      const erro = docError(p);
      if (erro) return pax.length === 1 ? erro : `Passageiro ${i + 1}: ${erro}`;
    }
    if (needsIdentity) {
      if (emergName.trim().length < 3) return tr("errEmergencyName");
      if (!/^\d{9}$/.test(emergPhone.replace(/\D/g, ""))) {
        return tr("errEmergencyPhone");
      }
    }
    return "";
  }, [pax, docError, needsIdentity, emergName, emergPhone]);

  const paxValid = paxMissing === "";
  const phoneValid = /^\d{9}$/.test(phone.replace(/\D/g, ""));
  const unit = Number(trip?.fare_amount || 0);
  // A volta é cotada para o percurso invertido; o servidor cota-a outra vez e
  // é o valor dele que manda. Aqui só se mostra o que se vai pagar.
  const unitVolta = rtrip ? Number(rtrip.fare_amount || 0) : 0;
  const total = (unit + unitVolta) * qty;

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
          ...(rtrip ? { return_trip_id: rtrip.trip_id } : {}),
          quantity: qty,
          passengers: pax,
          emergency_contact_name: emergName,
          emergency_contact_phone: emergPhone.replace(/\D/g, ""),
          display_currency: currency,
          accept_terms: aceitouTermos,
          terms_version: branding.terms_version,
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || tr("errPurchase"));
      setResult(body);
      setStep("done");
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : tr("errPayment"));
    } finally { setBusy(false); }
  };

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
            <Link to="/" aria-label="BusUp">
              {logo
                ? <img src={logo} alt="BusUp" style={{ height: 30, display: "block" }} />
                : <strong style={{ fontSize: 22 }}>Bus<span style={{ color: "#2D8CF0" }}>Up</span></strong>}
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
              <Link to="/" className="bzbk-kicker" style={{ color: "#a9c2dc" }}>{tr("backToSite")}</Link>
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
                    <input id="dt" className="bzbk-input" type="date" value={date} min={today} required
                      onChange={(e) => setDate(e.target.value)} />
                  </div>
                  {/* Só aparece depois de o passageiro pedir ida e volta:
                      um campo de data a quem só quer ir é uma pergunta a mais. */}
                  {idaEVolta ? (
                    <div className="bzbk-field">
                      <label className="bzbk-label" htmlFor="dtv">
                        <Calendar size={12} style={{ verticalAlign: -2 }} /> Data de volta
                      </label>
                      <input id="dtv" className="bzbk-input" type="date" value={returnDate}
                        min={date || today} required
                        onChange={(e) => setReturnDate(e.target.value)} />
                    </div>
                  ) : null}
                  <div className="bzbk-field">
                    <label className="bzbk-label" htmlFor="q"><Users size={12} style={{ verticalAlign: -2 }} /> {tr("passengersCount")}</label>
                    <select id="q" className="bzbk-select" value={qty}
                      onChange={(e) => setQty(Number(e.target.value))}>
                      {[1, 2, 3, 4, 5].map((n) => (
                        <option key={n} value={n}>{n} {n === 1 ? tr("passenger") : tr("passengersPlural")}</option>
                      ))}
                    </select>
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
                  <button className="bzbk-btn" type="button" disabled={picked.length !== qty} onClick={goToPax}>
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
                    onClick={() => { escolherTipo("ida"); startPax(picked, needsIdentity, []); setStep("pax"); }}>
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
                    disabled={rpicked.length !== qty} onClick={goToPaxFromReturn}>
                    {rpicked.length === qty
                      ? <>{tr("continue")} <ArrowRight size={16} /></>
                      : tr("stillToPick", { n: qty - rpicked.length })}
                  </button>
                </div>
              </div>
            )}

            {step === "pax" && trip && (
              <div>
                <h2 className="bzbk-h2">{tr("whoTravels")}</h2>
                <p className="bzbk-lead">
                  {needsIdentity
                    ? "O bilhete é nominal. Em viagens internacionais o documento é conferido na fronteira."
                    : "Basta o nome de quem viaja. Nesta carreira não é preciso documento."}
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
                    {/* Documento só nas viagens interprovinciais e
                        internacionais. Numa carreira urbana ninguém mostra o BI
                        para apanhar o autocarro do bairro. */}
                    {needsIdentity && (() => {
                      const rule = docRule(p.document_type);
                      const erro = docError(p);
                      // Só se avisa depois de escrever alguma coisa: acusar um
                      // campo ainda vazio é ralhar antes da falta.
                      const mostraErro = p.document_number.trim() !== "" && erro !== "";
                      return (
                        <div className="bzbk-grid" style={{ marginTop: 12 }}>
                          <div className="bzbk-field bzbk-field-wide">
                            <label className="bzbk-label">Documento</label>
                            <select className="bzbk-select" value={p.document_type}
                              onChange={(e) => {
                                // Trocar de tipo depois de escrever: o número
                                // é refiltrado pela regra nova, senão ficavam
                                // letras num campo que passou a ser só dígitos.
                                const novo = e.target.value;
                                setPax((prev) => prev.map((q, idx) => idx === i ? {
                                  ...q,
                                  document_type: novo,
                                  document_number: filterDoc(q.document_number, docRule(novo)),
                                } : q));
                              }}>
                              {docRules.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
                            </select>
                          </div>
                          <div className="bzbk-field bzbk-field-wide">
                            <label className="bzbk-label">Número</label>
                            <input
                              className={`bzbk-input${mostraErro ? " bzbk-input-error" : ""}`}
                              value={p.document_number}
                              required
                              // Sem `maxLength`: ele corta o texto CRU, antes
                              // de os espaços serem tirados. Um BI colado como
                              // "1101 0012 3456 A" (17 caracteres) era truncado
                              // a meio e ficava inválido sem se perceber
                              // porquê. O limite é aplicado em `filterDoc`,
                              // depois de normalizar.
                              placeholder={rule.placeholder}
                              inputMode={rule.digits_only ? "numeric" : "text"}
                              autoCapitalize="characters"
                              autoComplete="off"
                              spellCheck={false}
                              aria-invalid={mostraErro}
                              // Normaliza enquanto se escreve: o campo passa a
                              // recusar o que o servidor recusaria, em vez de
                              // deixar chegar ao pagamento para falhar la.
                              onChange={(e) => setPaxField(i, "document_number", filterDoc(e.target.value, rule))}
                            />
                            <span className={mostraErro ? "bzbk-hint bzbk-hint-error" : "bzbk-hint"}>
                              {mostraErro ? erro : rule.help}
                            </span>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                ))}
                {/* Quem decide é a ROTA, não a existência de planta: uma
                    interprovincial cuja viatura ainda não tem lotação registada
                    vende sem planta e continua a precisar deste contacto. Com
                    `hasSeatMap` aqui, o campo desaparecia e o servidor recusava
                    a compra sem o comprador ter onde o escrever. */}
                {needsIdentity ? (
                  <div className="bzbk-pax bzbk-pax-emergency">
                    <div className="bzbk-pax-head">
                      <span className="bzbk-pax-title">Contacto de emergência</span>
                    </div>
                    <p className="bzbk-lead" style={{ marginTop: -4 }}>
                      Quem avisamos se algo correr mal durante a viagem. Vai no
                      manifesto de bordo que segue com o motorista.
                    </p>
                    <div className="bzbk-grid" style={{ marginTop: 12 }}>
                      <div className="bzbk-field bzbk-field-wide">
                        <label className="bzbk-label">Nome</label>
                        <input className="bzbk-input" value={emergName} required
                          placeholder={tr("nameExample")}
                          onChange={(e) => setEmergName(e.target.value)} />
                      </div>
                      <div className="bzbk-field bzbk-field-wide">
                        <label className="bzbk-label">Telefone</label>
                        <input className="bzbk-input" value={emergPhone} required
                          inputMode="tel" placeholder="84/85/86/87..."
                          onChange={(e) => setEmergPhone(e.target.value)} />
                      </div>
                    </div>
                  </div>
                ) : null}
                {paxMissing && (
                  <p className="bzbk-hint" style={{ marginTop: 14 }}>{paxMissing}</p>
                )}
                <div className="bzbk-actions">
                  <button className="bzbk-btn ghost" type="button"
                    onClick={() => setStep(hasSeatMap ? "seats" : "trips")}>
                    <ArrowLeft size={16} /> {tr("back")}
                  </button>
                  <button className="bzbk-btn" type="button" disabled={!paxValid} onClick={() => setStep("pay")}>
                    Continuar <ArrowRight size={16} />
                  </button>
                </div>
              </div>
            )}

            {step === "pay" && trip && (
              <form onSubmit={pay}>
                <div className="bzbk-h2-row">
                  <h2 className="bzbk-h2">Pagamento</h2>
                  {currencyToggle}
                </div>
                <p className="bzbk-lead">{tr("payLead")}</p>

                <div className="bzbk-summary">
                  <div className="bzbk-sum-row"><span>{rtrip ? tr("outbound") : tr("route")}</span><b>{percurso(trip)}</b></div>
                  <div className="bzbk-sum-row"><span>{tr("departure")}</span><b>{date && longDate(date)} · {timeOf(trip.departure)}</b></div>
                  {rtrip ? (
                    <>
                      <div className="bzbk-sum-row"><span>{tr("returnLeg")}</span><b>{percurso(rtrip)}</b></div>
                      <div className="bzbk-sum-row">
                        <span>{tr("returnDeparture")}</span>
                        <b>{returnDate && longDate(returnDate)} · {timeOf(rtrip.departure)}</b>
                      </div>
                    </>
                  ) : null}
                  <div className="bzbk-sum-row">
                    <span>{tr("passengersCount")}</span>
                    <b>{pax.map((p) => p.name
                      + (p.seat ? ` (${p.seat}${p.return_seat ? ` / ${p.return_seat}` : ""})` : "")).join(", ")}</b>
                  </div>
                  <div className="bzbk-sum-row">
                    <span>{qty} × {rate ? priceLabel(unit) : `${money(unit)} MZN`}{rtrip ? " · ida" : ""}</span>
                    <b>{rate ? priceLabel(unit * qty) : `${money(unit * qty)} MZN`}</b>
                  </div>
                  {rtrip ? (
                    <div className="bzbk-sum-row">
                      <span>{qty} × {rate ? priceLabel(unitVolta) : `${money(unitVolta)} MZN`} · volta</span>
                      <b>{rate ? priceLabel(unitVolta * qty) : `${money(unitVolta * qty)} MZN`}</b>
                    </div>
                  ) : null}
                  <div className="bzbk-sum-total"><span>{tr("totalToPay")}</span><b>{money(total)} MZN</b></div>
                  {rate && (
                    <div className="bzbk-sum-row bzbk-sum-fx">
                      <span>{tr("equivalentIn")} {currency}</span>
                      <b>{money(inDisplay(total))} {currency} · 1 {currency} = {money(rate)} MZN</b>
                    </div>
                  )}
                </div>
                {rate && (
                  <p className="bzbk-hint" style={{ display: "block", marginTop: -8, marginBottom: 14 }}>
                    O débito na carteira móvel é sempre em meticais; o valor em {currency} é indicativo
                    e fica registado no bilhete à taxa de hoje.
                  </p>
                )}

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
                  <div className="bzbk-field bzbk-field-wide">
                    <label className="bzbk-label" htmlFor="ph">{tr("payPhone")}</label>
                    <input id="ph" className="bzbk-input" inputMode="numeric" placeholder="84xxxxxxx / 86xxxxxxx"
                      value={phone} required onChange={(e) => setPhone(e.target.value)} />
                    <span className="bzbk-hint">{tr("payPhoneHint")}</span>
                  </div>
                  <div className="bzbk-field bzbk-field-wide">
                    <label className="bzbk-label" htmlFor="em">{tr("emailOptional")}</label>
                    <input id="em" className="bzbk-input" type="email" placeholder={tr("emailHint")}
                      value={email} onChange={(e) => setEmail(e.target.value)} />
                  </div>
                </div>

                {temTermos ? (
                  <label className="bzbk-accept">
                    <input type="checkbox" checked={aceitouTermos} required
                      onChange={(e) => setAceitouTermos(e.target.checked)} />
                    <span>
                      {tr("acceptPre")}{" "}
                      <button type="button" className="bzbk-terms-link"
                        onClick={() => setTermosAbertos(true)}>
                        {tr("termsLink")}
                      </button>
                      {branding.company_name ? ` ${tr("acceptOf")} ${branding.company_name}` : ""}.
                    </span>
                  </label>
                ) : null}

                <div className="bzbk-actions">
                  <button className="bzbk-btn ghost" type="button" onClick={() => setStep("pax")} disabled={busy}>
                    <ArrowLeft size={16} /> {tr("back")}
                  </button>
                  <button className="bzbk-btn" type="submit"
                    disabled={busy || !phoneValid || (temTermos && !aceitouTermos)}>
                    {busy ? <><span className="bzbk-spin" /> {tr("processing")}</> : <>{tr("pay")} {money(total)} MZN</>}
                  </button>
                </div>
                {busy && (
                  <div className="bzbk-notice info" style={{ marginTop: 16 }}>
                    {tr("pinNotice")}
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
                      <Download size={17} /> {tr("downloadTicket")}
                    </a>
                  )}
                  <Link className="bzbk-btn ghost" to="/">
                    <Bus size={17} /> {tr("backHome")}
                  </Link>
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
