import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Download, Moon, Sun } from "lucide-react";
import { useBranding, pickLogo } from "../../lib/branding";
import { useUi } from "../../ui/UiPreferences";
import { bt, type BookingKey } from "./booking.i18n";
import TermsDialog from "./TermsDialog";
import { CampoSelect } from "../../ui/CampoSelect";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  DOC_FALLBACK, filterDoc, filterPhone, getJson, longDate, money, normalizeDoc,
  readServerError, timeOf,
  type CheckoutResult, type DocRule, type Passenger, type TripOpt,
} from "./compra";
import "./booking.css";

/** O checkout.
 *
 *  Quem viaja e como se paga numa so pagina, com o resumo da encomenda
 *  sempre a vista. Eram dois passos de um assistente: a pessoa preenchia os
 *  nomes sem ver o preco, e so descobria o total depois de carregar em
 *  continuar.
 *
 *  A reserva chega por `location.state` — nao ha carrinho do lado do
 *  servidor, e o backend esta fora de ambito. Recarregar a pagina perde-a,
 *  por isso ha um regresso gracioso a pesquisa em vez de um ecra partido.
 *
 *  O regresso do pagamento por cartao e a excepcao: o DPO devolve a pessoa a
 *  `/comprar?ref=GC-...` (endereco construido pelo servidor, ver
 *  `tests_cartao_dpo.py`), e essa pagina reencaminha para aqui com o `ref`.
 *  Nesse caso nao ha reserva nenhuma em memoria — ha uma referencia para
 *  confirmar. */

export interface Reserva {
  origin: string;
  destination: string;
  originName: string;
  destinationName: string;
  date: string;
  returnDate: string;
  trip: TripOpt;
  rtrip: TripOpt | null;
  qty: number;
  seats: string[];
  rseats: string[];
  needsIdentity: boolean;
}

export default function CheckoutPage() {
  const navegar = useNavigate();
  const local = useLocation();
  const { branding } = useBranding();
  const { locale, setLocale, theme, toggleTheme } = useUi();
  const tr = useCallback((k: BookingKey) => bt(locale, k), [locale]);

  const reserva = (local.state as { reserva?: Reserva } | null)?.reserva ?? null;
  const refDoCartao = new URLSearchParams(local.search).get("ref");

  const [docRules, setDocRules] = useState<DocRule[]>(DOC_FALLBACK);
  const [pax, setPax] = useState<Passenger[]>([]);
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [emergName, setEmergName] = useState("");
  const [emergPhone, setEmergPhone] = useState("");
  const [method, setMethod] = useState<"mpesa" | "emola" | "card">("mpesa");
  const [aceitouTermos, setAceitouTermos] = useState(false);
  const [termosAbertos, setTermosAbertos] = useState(false);
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<CheckoutResult | null>(null);

  const needsIdentity = reserva?.needsIdentity ?? true;
  const trip = reserva?.trip ?? null;
  const rtrip = reserva?.rtrip ?? null;
  const qty = reserva?.qty ?? 0;

  /** O tipo de documento, garantidamente entre os que ESTA rota aceita.
   *  Numa rota internacional so o passaporte e oferecido; um valor fora da
   *  lista fazia o campo mostrar uma coisa e o estado guardar outra. */
  const tipoPermitido = useCallback((tipo: string) => {
    if (docRules.some((d) => d.value === tipo)) return tipo;
    return docRules[0]?.value || "";
  }, [docRules]);

  /** A regra deste tipo. Cai no PRIMEIRO permitido, para coincidir com o que
   *  `tipoPermitido` poe no campo. */
  const docRule = useCallback(
    (type: string) => docRules.find((d) => d.value === type) || docRules[0],
    [docRules],
  );

  // Os passageiros nascem do numero de lugares reservados, com o lugar de
  // cada um ja preso ao seu nome.
  useEffect(() => {
    if (!reserva) return;
    setPax(Array.from({ length: reserva.qty }, (_, i) => ({
      name: "",
      // O tipo so se preenche onde o documento e pedido: numa carreira urbana
      // o campo do numero nem aparece, e mandar o tipo sozinho era mandar
      // meia resposta a uma pergunta que nao foi feita.
      document_type: reserva.needsIdentity ? tipoPermitido("bi") : "",
      document_number: "",
      seat: reserva.seats[i] || "",
      return_seat: reserva.rseats[i] || "",
    })));
  }, [reserva?.qty]); // eslint-disable-line react-hooks/exhaustive-deps

  // Os documentos aceites dependem da carreira.
  useEffect(() => {
    const tipo = trip?.service_type;
    if (!tipo) return;
    let cancelado = false;
    getJson(`/api/public/document-types/?service_type=${encodeURIComponent(tipo)}`)
      .then((d) => {
        if (cancelado || !d.document_types?.length) return;
        setDocRules(d.document_types);
        const permitidos = new Set(d.document_types.map((r: DocRule) => r.value));
        setPax((prev) => prev.map((p) => (
          p.document_type && !permitidos.has(p.document_type)
            ? { ...p, document_type: d.document_types[0].value, document_number: "" }
            : p
        )));
      })
      .catch(() => { /* fica a lista geral: melhor comprar do que travar */ });
    return () => { cancelado = true; };
  }, [trip?.service_type]);

  /** Confirma um pagamento pela referencia. Enquanto o servidor disser
   *  pendente, volta a perguntar: o DPO leva uns segundos a assentar. */
  const verify = useCallback(async (ref: string, tentativas = 4) => {
    setChecking(true); setError("");
    try {
      for (let i = 0; i < tentativas; i++) {
        const res = await fetch(`/api/guest-checkouts/${encodeURIComponent(ref)}/verify/`, { method: "POST" });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(readServerError(body, tr("errPayment")));
        setResult(body);
        if (body.payment_status !== "pending") break;
        await new Promise((r) => setTimeout(r, 2500));
      }
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : tr("errPayment"));
    } finally { setChecking(false); }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { if (refDoCartao) void verify(refDoCartao); }, [refDoCartao, verify]);

  // Pagamento por carteira que ficou pendente (o PIN demorou mais do que a
  // cobranca esperou): em vez de mandar o passageiro esperar pelo SMS, a
  // pagina pergunta ao servidor de 5 em 5 s durante 3 minutos — e o servidor
  // pergunta a operadora. O bilhete aparece no segundo em que o PIN entra.
  const inicioDaEspera = useRef(0);
  useEffect(() => {
    if (!result || result.payment_status !== "pending") { inicioDaEspera.current = 0; return; }
    if (checking) return;
    // O relogio dos tres minutos tem de viver FORA do efeito. Cada `verify`
    // liga e desliga `checking`, o efeito volta a correr, e um `inicio`
    // declarado aqui dentro recomecava a contar a cada volta: o limite nunca
    // chegava e a pagina ficava a perguntar para sempre.
    if (!inicioDaEspera.current) inicioDaEspera.current = Date.now();
    const id = window.setInterval(() => {
      if (Date.now() - inicioDaEspera.current > 180_000) { window.clearInterval(id); return; }
      void verify(result.checkout_reference, 1);
    }, 5000);
    return () => window.clearInterval(id);
  }, [result, checking, verify]);

  const setPaxField = (i: number, key: keyof Passenger, value: string) => {
    setPax((prev) => prev.map((p, idx) => (idx === i ? { ...p, [key]: value } : p)));
  };

  /** O que esta errado no documento deste passageiro, por palavras. */
  const docError = useCallback((p: Passenger) => {
    if (!needsIdentity) return "";
    const rule = docRule(p.document_type);
    const num = normalizeDoc(p.document_number);
    if (!num) return `Indique o número do documento (${rule.label}).`;
    if (!new RegExp(rule.pattern).test(num)) return `${rule.label}: ${rule.help}`;
    return "";
  }, [needsIdentity, docRule]);

  /** O que falta para pagar, por palavras. Um botao cinzento e calado deixa o
   *  comprador sem saber o que corrigir. */
  const emFalta = useMemo(() => {
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
      if (!/^\d{9}$/.test(emergPhone.replace(/\D/g, ""))) return tr("errEmergencyPhone");
    }
    return "";
  }, [pax, docError, needsIdentity, emergName, emergPhone, tr]);

  const phoneValid = /^\d{9}$/.test(phone.replace(/\D/g, ""));
  const temTermos = (branding.terms_sections || []).length > 0;
  const unit = Number(trip?.fare_amount || 0);
  const unitVolta = rtrip ? Number(rtrip.fare_amount || 0) : 0;
  const total = (unit + unitVolta) * qty;
  const podePagar = emFalta === "" && phoneValid && (!temTermos || aceitouTermos);

  const percurso = (t: TripOpt) =>
    `${t.route_code ? `${t.route_code} · ` : ""}${t.route_name || ""}`;

  const pagar = async (e: FormEvent) => {
    e.preventDefault();
    if (!reserva || !trip) return;
    setBusy(true); setError("");
    try {
      const res = await fetch("/api/guest-checkouts/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          payer_phone: phone.replace(/\D/g, ""),
          buyer_name: pax[0]?.name || "",
          buyer_email: email,
          route_code: trip.route_code,
          route_name: trip.route_name,
          origin_stop: reserva.originName,
          destination_stop: reserva.destinationName,
          origin_stop_id: Number(reserva.origin),
          destination_stop_id: Number(reserva.destination),
          trip_id: trip.trip_id,
          ...(rtrip ? { return_trip_id: rtrip.trip_id } : {}),
          quantity: qty,
          passengers: pax,
          emergency_contact_name: emergName,
          emergency_contact_phone: emergPhone.replace(/\D/g, ""),
          display_currency: "MZN",
          accept_terms: aceitouTermos,
          terms_version: branding.terms_version,
          payment_method: method === "card" ? "card" : "mobile_wallet",
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(readServerError(body, tr("errPurchase")));
      if (body.redirect_url) {
        // Cartao: o pagamento acontece na pagina do DPO. Fica-se em `busy`
        // ate o browser sair — soltar o botao aqui era convidar a segundo toque.
        window.location.assign(body.redirect_url);
        return;
      }
      setResult(body);
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : tr("errPayment"));
      setBusy(false);
    }
  };

  const logo = pickLogo(branding.sidebar_logo_url, branding.primary_logo_url);
  const telefones = [...new Set([
    ...(branding.contact_phones || []),
    branding.support_phone,
  ].filter(Boolean))];

  /* Contactos do OPERADOR, nao os nossos: quem tem um problema com a viagem
     precisa de falar com quem a faz. Vem da marca, por isso mudam no portal
     sem passar por aqui. */
  const rodape = (
    <footer className="bzbk-foot">
      <div className="bzbk-foot-main">
        {branding.company_name ? <b>{branding.company_name}</b> : null}
        {branding.company_address ? <span>{branding.company_address}</span> : null}
      </div>
      <div className="bzbk-foot-contacts">
        {telefones.map((n) => <a href={`tel:${n.replace(/[^+\d]/g, "")}`} key={n}>{n}</a>)}
        {branding.support_email ? (
          <a href={`mailto:${branding.support_email}`}>{branding.support_email}</a>
        ) : null}
      </div>
      {temTermos ? (
        <button className="bzbk-terms-link" onClick={() => setTermosAbertos(true)} type="button">
          Termos e Condições
        </button>
      ) : null}
    </footer>
  );

  const cabecalho = (
    <header className="bzbk-top">
      {/* A mesma coluna do conteudo, e nao a de 940px do resto do fluxo:
          com duas larguras diferentes o titulo "Finalizar compra" ficava
          a 190px e o cartao por baixo a 72px, desalinhados a olho. */}
      <div className="bzbk-wrap bzbk-checkout-wrap"><div className="bzbk-top-in">
        <Link to="/tpm-tur" className="bzbk-brand" aria-label={branding.company_name || "Início"}>
          {logo ? <img alt={branding.company_name || ""} src={logo} style={{ height: 30 }} />
            : <strong style={{ fontSize: 20 }}>{branding.company_name}</strong>}
        </Link>
        <div className="bzbk-top-tools">
          <div className="bzbk-lang" role="group" aria-label="Idioma">
            <button aria-pressed={locale === "pt"} onClick={() => setLocale("pt")} type="button">PT</button>
            <button aria-pressed={locale === "en"} onClick={() => setLocale("en")} type="button">EN</button>
          </div>
          <button aria-label={theme === "dark" ? "Tema claro" : "Tema escuro"} className="bzbk-theme"
            onClick={toggleTheme} type="button">
            {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
          </button>
        </div>
      </div>
      {/* A faixa precisa de altura: os cartoes sobem 40px para dentro dela de
          proposito, e sem titulo a sobreposicao lia-se como corte. */}
      <div style={{ position: "relative", zIndex: 2, marginTop: 18 }}>
        <div className="bzbk-kicker">{tr("kicker")}</div>
        <h1 className="bzbk-title">Finalizar compra</h1>
        <p className="bzbk-sub">Confirme quem viaja e pague — o bilhete fica no seu telemóvel.</p>
        </div>
      </div>
    </header>
  );

  // ── Sem reserva: quem recarregou ou chegou de fora ────────────────────
  if (!reserva && !refDoCartao) {
    return (
      <div className="bzbk">
        {cabecalho}
        <main className="bzbk-wrap bzbk-checkout-wrap" style={{ paddingTop: 26, paddingBottom: 40 }}>
          <div className="bzbk-card bzbk-checkout-vazio">
            <h1 className="bzbk-h2">A sua compra não está aqui</h1>
            <p className="bzbk-lead">
              Esta página guarda a compra enquanto a está a fazer, e não depois de
              recarregar. Escolha outra vez o percurso — é rápido, e nada foi cobrado.
            </p>
            <Link className="bzbk-btn" to="/comprar">Escolher viagem</Link>
          </div>
        </main>
        {rodape}
      </div>
    );
  }

  // ── Depois de pagar ───────────────────────────────────────────────────
  if (result) {
    // Dizia "Bilhete emitido" fosse qual fosse o estado. Desde que o timeout
    // do M-Pesa passou a ficar pendente em vez de falhado, "pendente" e um
    // fim possivel — e mentir aqui e o passageiro pagar duas vezes ou
    // ir-se embora sem bilhete.
    const pago = result.payment_status === "confirmed" || result.status === "issued";
    const falhou = result.status === "cancelled" || result.status === "expired"
      || result.payment_status === "failed";
    return (
      <div className="bzbk">
        {cabecalho}
        <main className="bzbk-wrap bzbk-checkout-wrap" style={{ paddingTop: 26, paddingBottom: 40 }}>
          <div className="bzbk-card">
            <div className="bzbk-done">
              <div className="bzbk-done-mark" style={pago ? undefined : { opacity: .55 }}>
                {checking ? <span className="bzbk-spin" /> : <CheckCircle2 size={40} />}
              </div>
              <h1 className="bzbk-h2">
                {checking ? tr("returnChecking")
                  : pago ? tr("ticketIssued")
                  : falhou ? tr("returnFailedTitle")
                  : tr("pendingTitle")}
              </h1>
              <p className="bzbk-lead">
                {pago ? tr("ticketIssuedText")
                  : falhou ? tr("returnFailedText")
                  : refDoCartao ? tr("returnPendingText") : tr("pendingText")}
                {result.detail_message && !pago ? ` ${result.detail_message}` : ""}
              </p>

              {/* A referencia e o que a pessoa leva consigo: sem ela nao ha
                  como reclamar um pagamento que o operador nao ve. */}
              <div className="bzbk-ref">{result.checkout_reference}</div>
              {result.total_amount ? (
                // `so`: aqui o total esta sozinho, sem as linhas do percurso por
                // cima. O tracejado que o separa delas ficava a dividir o bloco
                // do nada — uma faixa vazia por cima de uma linha.
                <div className="bzbk-summary so" style={{ marginTop: 14, textAlign: "left" }}>
                  <div className="bzbk-sum-total">
                    <span>{pago ? tr("totalPaid") : tr("totalToPay")}</span>
                    <b>{money(result.total_amount)} MZN</b>
                  </div>
                </div>
              ) : null}

              {error ? <div className="bzbk-notice error" style={{ marginTop: 14 }}>{error}</div> : null}

              <div className="bzbk-actions" style={{ justifyContent: "center", marginTop: 18 }}>
                {!pago && !falhou && (
                  <button className="bzbk-btn ghost" disabled={checking} type="button"
                    onClick={() => void verify(result.checkout_reference)}>
                    {checking ? <><span className="bzbk-spin" /> {tr("returnChecking")}</> : tr("checkAgain")}
                  </button>
                )}
                {pago && result.ticket_url && (
                  <a className="bzbk-btn" href={result.ticket_url} rel="noreferrer" target="_blank">
                    <Download size={16} /> {tr("downloadTicket")}
                  </a>
                )}
                {falhou && <Link className="bzbk-btn" to="/comprar">{tr("tryAgain")}</Link>}
                <Link className="bzbk-btn ghost" to="/tpm-tur">{tr("backHome")}</Link>
              </div>
            </div>
          </div>
        </main>
        {rodape}
      </div>
    );
  }

  // ── A confirmar um regresso do cartao, ainda sem resposta ─────────────
  if (!reserva) {
    return (
      <div className="bzbk">
        {cabecalho}
        <main className="bzbk-wrap bzbk-checkout-wrap" style={{ paddingTop: 26, paddingBottom: 40 }}>
          <div className="bzbk-card bzbk-checkout-vazio">
            <span className="bzbk-spin" />
            <h1 className="bzbk-h2">{tr("returnChecking")}</h1>
            {error ? <div className="bzbk-notice error">{error}</div> : null}
          </div>
        </main>
        {rodape}
      </div>
    );
  }

  // ── O checkout ────────────────────────────────────────────────────────
  return (
    <div className="bzbk">
      {cabecalho}
      <main className="bzbk-wrap bzbk-checkout-wrap" style={{ paddingTop: 26, paddingBottom: 40 }}>
        <form className="bzbk-checkout" onSubmit={pagar}>
          <div className="bzbk-checkout-form">
            <div className="bzbk-card">
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
                    <label className="bzbk-label" htmlFor={`nome-${i}`}>Nome completo</label>
                    <Input className="bzbk-input" id={`nome-${i}`} placeholder="Como está no documento"
                      required value={p.name} onChange={(e) => setPaxField(i, "name", e.target.value)} />
                  </div>

                  {/* Documento so nas viagens interprovinciais e internacionais.
                      Numa carreira urbana ninguem mostra o BI para apanhar o
                      autocarro do bairro. */}
                  {needsIdentity && (() => {
                    const rule = docRule(p.document_type);
                    const erro = docError(p);
                    // So se avisa depois de escrever alguma coisa: acusar um
                    // campo ainda vazio e ralhar antes da falta.
                    const mostraErro = p.document_number.trim() !== "" && erro !== "";
                    return (
                      <div className="bzbk-grid" style={{ marginTop: 12 }}>
                        <div className="bzbk-field bzbk-field-wide">
                          <CampoSelect className="bzbk-campo" label="Documento"
                            value={tipoPermitido(p.document_type)}
                            onChange={(novo) => {
                              // Trocar de tipo depois de escrever: o numero e
                              // refiltrado pela regra nova, senao ficavam letras
                              // num campo que passou a ser so digitos.
                              setPax((prev) => prev.map((q, idx) => idx === i ? {
                                ...q,
                                document_type: novo,
                                document_number: filterDoc(q.document_number, docRule(novo)),
                              } : q));
                            }}>
                            {docRules.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
                          </CampoSelect>
                        </div>
                        <div className="bzbk-field bzbk-field-wide">
                          <label className="bzbk-label" htmlFor={`doc-${i}`}>Número</label>
                          <Input
                            aria-invalid={mostraErro}
                            autoCapitalize="characters"
                            autoComplete="off"
                            className={`bzbk-input${mostraErro ? " bzbk-input-error" : ""}`}
                            id={`doc-${i}`}
                            inputMode={rule.digits_only ? "numeric" : "text"}
                            // Sem `maxLength`: ele corta o texto CRU, antes de
                            // os espacos serem tirados. Um BI colado como
                            // "1101 0012 3456 A" era truncado a meio e ficava
                            // invalido sem se perceber porque. O limite e
                            // aplicado em `filterDoc`, depois de normalizar.
                            placeholder={rule.placeholder}
                            required
                            spellCheck={false}
                            value={p.document_number}
                            onChange={(e) => setPaxField(i, "document_number", filterDoc(e.target.value, rule))}
                          />
                          {mostraErro ? <span className="bzbk-hint-error">{erro}</span>
                            : <span className="bzbk-hint">{rule.help}</span>}
                        </div>
                      </div>
                    );
                  })()}
                </div>
              ))}

              {needsIdentity && (
                <div className="bzbk-pax bzbk-pax-emergency">
                  <div className="bzbk-pax-head">
                    <span className="bzbk-pax-title">{tr("emergencyContact")}</span>
                  </div>
                  <div className="bzbk-grid">
                    <div className="bzbk-field bzbk-field-wide">
                      <label className="bzbk-label" htmlFor="emg-nome">Nome</label>
                      <Input className="bzbk-input" id="emg-nome" required value={emergName}
                        onChange={(e) => setEmergName(e.target.value)} />
                    </div>
                    <div className="bzbk-field bzbk-field-wide">
                      <label className="bzbk-label" htmlFor="emg-tel">Telefone</label>
                      <Input className="bzbk-input" id="emg-tel" inputMode="numeric"
                        placeholder="84/85/86/87..." required value={emergPhone}
                        onChange={(e) => setEmergPhone(filterPhone(e.target.value))} />
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="bzbk-card">
              <h2 className="bzbk-h2">Pagamento</h2>
              <p className="bzbk-lead">{tr("payLead")}</p>

              <div className="bzbk-methods">
                {(["mpesa", "emola", ...(branding.card_payments_enabled ? ["card" as const] : [])] as const).map((m) => (
                  <button aria-pressed={method === m} className={`bzbk-method${method === m ? " is-on" : ""}`}
                    key={m} onClick={() => setMethod(m)} type="button">
                    <span className="dot" />
                    {m === "mpesa" ? "M-Pesa" : m === "emola" ? "e-Mola" : tr("cardMethod")}
                  </button>
                ))}
              </div>

              <div className="bzbk-grid">
                <div className="bzbk-field bzbk-field-wide">
                  <label className="bzbk-label" htmlFor="ph">{tr("payPhone")}</label>
                  <Input autoComplete="off" className="bzbk-input" id="ph" inputMode="numeric"
                    placeholder="84xxxxxxx / 86xxxxxxx" required value={phone}
                    onChange={(e) => setPhone(filterPhone(e.target.value))} />
                  <span className="bzbk-hint">{method === "card" ? tr("cardPhoneHint") : tr("payPhoneHint")}</span>
                </div>
                <div className="bzbk-field bzbk-field-wide">
                  <label className="bzbk-label" htmlFor="em">{tr("emailOptional")}</label>
                  <Input className="bzbk-input" id="em" placeholder={tr("emailHint")} type="email"
                    value={email} onChange={(e) => setEmail(e.target.value)} />
                </div>
              </div>

              {/* O ultimo `<input type=checkbox>` nativo do fluxo. Todo o resto
                  do produto usa o `Checkbox` do shadcn, e este ficava a
                  desenho do sistema operativo — no tema escuro saia um
                  quadrado castanho no meio do navy. O `required` nao faz
                  falta: `podePagar` ja exige os termos. */}
              {temTermos ? (
                <div
                  className="bzbk-accept"
                  onClick={(e) => {
                    // O gatilho do Radix e um `<button>`, e um `<label htmlFor>`
                    // nao o activa: cliquei na frase e a caixa ficou por marcar.
                    // A linha inteira volta a ser area de clique, menos o link
                    // dos termos — esse abre o dialogo — e a propria caixa.
                    //
                    // A caixa sao DOIS elementos: o `<button>` e um
                    // `<input type=checkbox>` escondido que o Radix poe ao lado
                    // para o formulario. Clicar no botao sintetiza mais dois
                    // cliques nesse input, que sobem ate aqui. Guardar so o
                    // `[data-slot=checkbox]` deixava passar esses dois — a linha
                    // alternava duas vezes e ficava como estava.
                    const alvo = e.target as HTMLElement;
                    if (alvo.closest("[data-slot=checkbox],.bzbk-terms-link")) return;
                    if (alvo instanceof HTMLInputElement && alvo.type === "checkbox") return;
                    setAceitouTermos((v) => !v);
                  }}
                >
                  <Checkbox aria-labelledby="aceitar-termos-txt" checked={aceitouTermos}
                    id="aceitar-termos" onCheckedChange={(v) => setAceitouTermos(v === true)} />
                  <span id="aceitar-termos-txt">
                    {tr("acceptPre")}{" "}
                    <button className="bzbk-terms-link" onClick={() => setTermosAbertos(true)} type="button">
                      {tr("termsLink")}
                    </button>
                    {branding.company_name ? ` ${tr("acceptOf")} ${branding.company_name}` : ""}.
                  </span>
                </div>
              ) : null}

              {error ? <div className="bzbk-notice error" style={{ marginTop: 14 }}>{error}</div> : null}
              {method === "card" && !busy && (
                <div className="bzbk-notice info" style={{ marginTop: 16 }}>{tr("cardNotice")}</div>
              )}
              {busy && method !== "card" && (
                <div className="bzbk-notice info" style={{ marginTop: 16 }}>{tr("pinNotice")}</div>
              )}
            </div>
          </div>

          {/* O resumo acompanha o scroll: o preco tem de estar a vista quando
              se carrega em pagar, e nao tres ecras acima. */}
          <aside className="bzbk-checkout-resumo">
            <div className="bzbk-card">
              <h2 className="bzbk-h3">Resumo da compra</h2>
              <div className="bzbk-summary">
                <div className="bzbk-sum-row">
                  <span>{rtrip ? tr("outbound") : tr("route")}</span><b>{percurso(trip!)}</b>
                </div>
                {/* Uma linha cada, e nao os dois lados da mesma. Numa coluna de
                    420px, "Baixa → Estadio do Zimpeto" e "sexta-feira, 25 de
                    setembro de 2026 · 16:03" quebravam ambos ao meio: quatro
                    fragmentos encavalitados em vez de duas informacoes. */}
                <div className="bzbk-sum-leg">
                  <b>{reserva.originName} → {reserva.destinationName}</b>
                  <span>{reserva.date && longDate(reserva.date)} · {timeOf(trip!.departure)}</span>
                </div>
                {rtrip ? (
                  <div className="bzbk-sum-leg">
                    <b>{tr("returnLeg")}</b>
                    <span>{reserva.returnDate && longDate(reserva.returnDate)} · {timeOf(rtrip.departure)}</span>
                  </div>
                ) : null}
                <div className="bzbk-sum-row">
                  <span>{qty} × {money(unit)} MZN{rtrip ? " · ida" : ""}</span>
                  <b>{money(unit * qty)} MZN</b>
                </div>
                {rtrip ? (
                  <div className="bzbk-sum-row">
                    <span>{qty} × {money(unitVolta)} MZN · volta</span>
                    <b>{money(unitVolta * qty)} MZN</b>
                  </div>
                ) : null}
                <div className="bzbk-sum-total"><span>{tr("totalToPay")}</span><b>{money(total)} MZN</b></div>
              </div>

              {/* O que falta, por palavras, ao lado do botao — e nao um botao
                  cinzento e calado. */}
              {emFalta && !busy ? <p className="bzbk-hint" style={{ marginTop: 12 }}>{emFalta}</p> : null}

              <button className="bzbk-btn bzbk-checkout-pagar" disabled={busy || !podePagar} type="submit">
                {busy
                  ? <><span className="bzbk-spin" /> {method === "card" ? tr("cardRedirecting") : tr("processing")}</>
                  : <>{tr("pay")} {money(total)} MZN</>}
              </button>

              <button className="bzbk-btn ghost" disabled={busy} type="button"
                onClick={() => navegar(-1)} style={{ width: "100%", marginTop: 8 }}>
                <ArrowLeft size={16} /> {tr("back")}
              </button>
            </div>
          </aside>
        </form>
      </main>
      {rodape}

      <TermsDialog
        closing={branding.terms_closing || undefined}
        company={branding.company_name}
        intro={branding.terms_intro || undefined}
        onClose={() => setTermosAbertos(false)}
        open={termosAbertos}
        sections={branding.terms_sections || []}
        updatedAt={branding.terms_updated_at || undefined}
        version={branding.terms_version}
      />
    </div>
  );
}
