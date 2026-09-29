import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Check, Clock3, Mail, MapPin, Phone } from "lucide-react";
import BusUpPagina, {
  EMAIL_VENDAS, LogotipoUpDigital, MORADA, TELEFONE_VENDAS, TELEFONE_VENDAS_HREF, useBusUpMeta,
} from "./BusUpChrome";
import { useLandingPrefs } from "../landing/useLandingPrefs";
import { copyContactos } from "./busup-contactos-copy";

/* Contactos — portado do protótipo `Contactos BusUp.dc.html`.
 *
 * O FORMULÁRIO É EM TRÊS GRUPOS e não em passos: são onze campos, e o
 * protótipo mostra-os todos de uma vez com três separadores por cima. A regra
 * dos passos automáticos da entrega ("acima de 8 campos") é do PORTAL, onde os
 * formulários vivem em modal; aqui a página é toda dela e um passo de cada vez
 * só acrescentava cliques.
 *
 * O envio abre o programa de email do visitante, como o resto do site público
 * já faz — não há endpoint de contacto no backend e inventar um seria prometer
 * uma entrega que ninguém garante.
 */

const LOGOS_ECO = [
  { src: "/ecosystem/logos/payup.webp", nome: "PayUp", url: "https://payup.updigital.co.mz" },
  { src: "/ecosystem/logos/cashup.webp", nome: "CashUp", url: "https://cashup.updigital.co.mz" },
  { src: "/ecosystem/logos/gateup.webp", nome: "GateUp", url: "https://gateup.updigital.co.mz" },
  { src: "/ecosystem/logos/vura.webp", nome: "Vura", url: "https://vura.updigital.co.mz" },
  { src: "/ecosystem/logos/ossoma.webp", nome: "Ossoma", url: "https://ossoma.updigital.co.mz" },
];

type Campos = {
  nome: string; cargo: string; empresa: string; telefone: string; email: string;
  frota: string; tipo: string; interesse: string; mensagem: string;
};

const VAZIO: Campos = {
  nome: "", cargo: "", empresa: "", telefone: "", email: "",
  frota: "", tipo: "", interesse: "", mensagem: "",
};

export default function BusUpContactosPage() {
  const { lang } = useLandingPrefs();
  const t = copyContactos(lang);
  const [form, setForm] = useState<Campos>(VAZIO);
  const [enviado, setEnviado] = useState(false);

  useBusUpMeta(`${t.h1} · BusUp`, t.lead);

  const set = (chave: keyof Campos) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [chave]: e.target.value }));

  const submeter = (e: FormEvent) => {
    e.preventDefault();
    const corpo = [
      `${t.fName}: ${form.nome}`,
      `${t.fRole}: ${form.cargo || "—"}`,
      `${t.fCompany}: ${form.empresa}`,
      `${t.fPhone}: ${form.telefone}`,
      `${t.fEmail}: ${form.email || "—"}`,
      `${t.fFleet}: ${form.frota || "—"}`,
      `${t.fType}: ${form.tipo || "—"}`,
      `${t.fInterest}: ${form.interesse || "—"}`,
      "",
      form.mensagem,
    ].join("\n");
    window.location.href =
      `mailto:${EMAIL_VENDAS}?subject=${encodeURIComponent(`BusUp — ${t.formTitle}`)}&body=${encodeURIComponent(corpo)}`;
    setEnviado(true);
  };

  return (
    <BusUpPagina>
      <section className="bzc-contacto-topo">
        <div aria-hidden className="bzc-hero-luz" />
        <div className="bzc-contacto-cab">
          <span className="bzc-distintivo"><i className="bzc-ponto bzc-pulsa" style={{ background: "#2A9D8F" }} />{t.badge}</span>
          <h1 className="bzc-h1" style={{ fontSize: 48 }}>{t.h1}</h1>
          <p className="bzc-lead" style={{ maxWidth: "50ch" }}>{t.lead}</p>
        </div>

        <div className="bzc-wrap-md" style={{ paddingBottom: 88 }}>
          <div className="bzc-contacto-grelha">
            {/* ── O formulário ─────────────────────────────────── */}
            <div className="bzc-contacto-form">
              {enviado ? (
                <div className="bzc-enviado">
                  <span><Check aria-hidden size={24} /></span>
                  <b>{t.sentTitle}</b>
                  <p>{t.sentText}</p>
                  <button className="bzc-btn bzc-btn--linha" onClick={() => { setForm(VAZIO); setEnviado(false); }} type="button">
                    {t.sendAnother}
                  </button>
                </div>
              ) : (
                <form onSubmit={submeter}>
                  <div>
                    <b className="bzc-h3" style={{ display: "block", marginBottom: 6 }}>{t.formTitle}</b>
                    <span className="bzc-lead" style={{ fontSize: 14 }}>{t.formSub}</span>
                  </div>

                  <p className="bzc-grupo"><span>{t.g1}</span><i /></p>
                  <div className="bzc-par">
                    <label><span>{t.fName}</span><input onChange={set("nome")} required type="text" value={form.nome} /></label>
                    <label><span>{t.fRole}</span><input onChange={set("cargo")} type="text" value={form.cargo} /></label>
                  </div>
                  <label><span>{t.fCompany}</span><input onChange={set("empresa")} required type="text" value={form.empresa} /></label>
                  <div className="bzc-par">
                    <label><span>{t.fPhone}</span><input inputMode="tel" onChange={set("telefone")} required type="tel" value={form.telefone} /></label>
                    <label><span>{t.fEmail}</span><input onChange={set("email")} type="email" value={form.email} /></label>
                  </div>

                  <p className="bzc-grupo"><span>{t.g2}</span><i /></p>
                  <div className="bzc-par">
                    <label><span>{t.fFleet}</span><input inputMode="numeric" onChange={set("frota")} type="text" value={form.frota} /></label>
                    <label>
                      <span>{t.fType}</span>
                      <select onChange={set("tipo")} value={form.tipo}>
                        <option value="">—</option>
                        {t.types.map((x) => <option key={x} value={x}>{x}</option>)}
                      </select>
                    </label>
                  </div>

                  <p className="bzc-grupo"><span>{t.g3}</span><i /></p>
                  <label>
                    <span>{t.fInterest}</span>
                    <select onChange={set("interesse")} value={form.interesse}>
                      <option value="">—</option>
                      {t.interests.map((x) => <option key={x} value={x}>{x}</option>)}
                    </select>
                  </label>
                  <label><span>{t.fMsg}</span><textarea onChange={set("mensagem")} rows={4} value={form.mensagem} /></label>

                  <button className="bzc-btn bzc-btn--azul" style={{ width: "100%" }} type="submit">
                    {t.formCta} <ArrowRight aria-hidden size={16} />
                  </button>
                  <p className="bzc-lead" style={{ fontSize: 12.5 }}>{t.formNote}</p>
                </form>
              )}
            </div>

            {/* ── Os cartões da direita ────────────────────────── */}
            <div className="bzc-contacto-lado">
              <div className="bzc-cartao">
                <span className="bzc-rotulo">{t.directTitle}</span>
                <ul className="bzc-contacto-lista">
                  <li>
                    <Phone aria-hidden size={17} />
                    <span><b>{t.commercial}</b><a href={TELEFONE_VENDAS_HREF}>{TELEFONE_VENDAS}</a></span>
                  </li>
                  <li>
                    <Mail aria-hidden size={17} />
                    <span><b>{t.emailNote}</b><a href={`mailto:${EMAIL_VENDAS}`}>{EMAIL_VENDAS}</a></span>
                  </li>
                </ul>
              </div>

              <div className="bzc-cartao">
                <span className="bzc-rotulo">{t.hoursTitle}</span>
                <p className="bzc-contacto-linha"><Clock3 aria-hidden size={17} />{t.hours}</p>
              </div>

              <div className="bzc-cartao">
                <span className="bzc-rotulo">{t.addressTitle}</span>
                <p className="bzc-contacto-linha"><MapPin aria-hidden size={17} />{MORADA[0]}<br />{MORADA[1]}</p>
                <div className="bzc-mapa" style={{ marginTop: 14, minHeight: 120 }}>
                  <span className="bzc-rotulo">{t.mapNote}</span>
                  <p>{t.mapPlaceholder}</p>
                </div>
              </div>

              <div className="bzc-cartao">
                <span className="bzc-rotulo">{t.quickTitle}</span>
                <div className="bzc-contacto-atalhos">
                  <Link className="bzc-btn bzc-btn--linha bzc-btn--sm" to="/baixar">{t.apps}</Link>
                  <Link className="bzc-btn bzc-btn--linha bzc-btn--sm" to="/login">{t.portalLogin}</Link>
                  <Link className="bzc-btn bzc-btn--linha bzc-btn--sm" to="/#precos">{t.navPricing}</Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Quem constrói ─────────────────────────────────────── */}
      <section className="bzc-sec bzc-sec-alt">
        <div className="bzc-wrap-md">
          <div className="bzc-eco">
            <div>
              <span className="bzc-rotulo" style={{ display: "block", marginBottom: 18 }}>{t.ecoLabel}</span>
              <div style={{ marginBottom: 22 }}><LogotipoUpDigital alt="UpDigital, Limitada" altura={54} /></div>
              <h2 className="bzc-h2" style={{ fontSize: 34, marginBottom: 12, textAlign: "left" }}>{t.ecoH2}</h2>
              <p className="bzc-lead" style={{ maxWidth: "46ch" }}>{t.ecoLead}</p>
              <p className="bzc-lead" style={{ maxWidth: "46ch", marginTop: 12 }}>{t.ecoNote}</p>
            </div>
            <ul className="bzc-eco-grelha">
              {LOGOS_ECO.map((l) => (
                <li key={l.nome}>
                  <a href={l.url} rel="noopener" target="_blank"><img alt={l.nome} src={l.src} /></a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </BusUpPagina>
  );
}
