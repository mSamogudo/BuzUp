import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Check, ChevronDown } from "lucide-react";
import BusUpPagina, { LogotipoUpDigital, useBusUpMeta } from "./BusUpChrome";
import { useLandingPrefs } from "../landing/useLandingPrefs";
import { copyPrecos } from "./busup-precos-copy";
import { LOGOS_ECO } from "./logos-ecossistema";

/* Preços — portado do protótipo `Precos BusUp.dc.html`.
 *
 * O QUADRO COMPARATIVO É UMA `<table>` A SÉRIO. São dados tabulares — dez
 * funcionalidades por três planos — e quem usa leitor de ecrã precisa de os
 * navegar por linha e coluna. Abaixo de 768px cada linha vira cartão, por CSS,
 * sem mudar o markup: a semântica não depende da largura do ecrã.
 *
 * Os valores são "Sob consulta" no protótipo e ficam assim. Inventar um preço
 * numa página que existe para dizer que o preço se negocia seria o contrário
 * do que ela diz.
 */

export default function BusUpPrecosPage() {
  const { lang } = useLandingPrefs();
  const t = copyPrecos(lang);
  const [aberta, setAberta] = useState<number | null>(0);

  useBusUpMeta(`${t.h1a} ${t.h1b} · BusUp`, t.lead);

  return (
    <BusUpPagina>
      {/* ── Cabeçalho ─────────────────────────────────────────── */}
      <section className="bzc-contacto-topo">
        <div aria-hidden className="bzc-hero-luz" />
        <div className="bzc-contacto-cab">
          <span className="bzc-distintivo"><i className="bzc-ponto bzc-pulsa" />{t.badge}</span>
          <h1 className="bzc-h1" style={{ fontSize: 52 }}>{t.h1a}<span>{t.h1b}</span></h1>
          <p className="bzc-lead" style={{ maxWidth: "56ch" }}>{t.lead}</p>
        </div>

        {/* ── Os três planos ──────────────────────────────────── */}
        <div className="bzc-wrap-md" style={{ paddingTop: 44, paddingBottom: 80 }}>
          <div className="bzc-grelha-3">
            {t.plans.map((p) => {
              const destaque = "featured" in p && p.featured;
              return (
                <article className="bzc-plano" data-destaque={destaque ? "" : undefined} key={p.name}>
                  <div className="bzc-plano-topo">
                    <h2 className="bzc-h3">{p.name}</h2>
                    {"badge" in p && p.badge ? <span className="bzc-plano-selo">{p.badge}</span> : null}
                  </div>
                  <p className="bzc-lead" style={{ fontSize: 14 }}>{p.who}</p>
                  <p className="bzc-plano-preco">{p.price}</p>
                  <p className="bzc-plano-unidade">{p.unit}</p>
                  <ul className="bzc-lista-check">
                    {p.items.map((i) => <li key={i}><Check aria-hidden size={16} />{i}</li>)}
                  </ul>
                  <Link className={`bzc-btn ${destaque ? "bzc-btn--azul" : "bzc-btn--linha"}`} to="/contactos">
                    {p.cta} <ArrowRight aria-hidden size={16} />
                  </Link>
                </article>
              );
            })}
          </div>

          {/* ── As três notas ─────────────────────────────────── */}
          <ul className="bzc-notas">
            {t.notes.map((n) => (
              <li key={n.h}>
                <h3 className="bzc-h3" style={{ fontSize: 16 }}>{n.h}</h3>
                <p className="bzc-lead" style={{ fontSize: 14 }}>{n.p}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* ── O quadro comparativo ──────────────────────────────── */}
      <section className="bzc-sec bzc-sec-alt">
        <div className="bzc-wrap-md">
          <div className="bzc-sechead">
            <h2 className="bzc-h2">{t.tableH2}</h2>
            <p className="bzc-lead">{t.tableLead}</p>
          </div>

          <div className="bzc-quadro-caixa">
            <table className="bzc-quadro">
              <caption className="bzc-sr">{t.tableH2} — {t.tableLead}</caption>
              <thead>
                <tr>
                  <th scope="col">{t.tableCol}</th>
                  <th scope="col">{t.p1}</th>
                  <th scope="col">{t.p2}</th>
                  <th scope="col">{t.p3}</th>
                </tr>
              </thead>
              <tbody>
                {t.rows.map((r) => (
                  <tr key={r.label}>
                    <th scope="row">{r.label}</th>
                    <td data-rot={t.p1}>{r.a}</td>
                    <td data-rot={t.p2}>{r.b}</td>
                    <td data-rot={t.p3}>{r.c}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <th scope="row">{t.tableFoot}</th>
                  {[t.p1, t.p2, t.p3].map((plano) => (
                    <td data-rot={plano} key={plano}>
                      <Link className="bzc-quadro-cta" to="/contactos">{t.quote}</Link>
                    </td>
                  ))}
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </section>

      {/* ── Perguntas ─────────────────────────────────────────── */}
      <section className="bzc-sec">
        <div className="bzc-wrap-sm">
          <div className="bzc-sechead">
            <h2 className="bzc-h2">{t.faqH2}</h2>
            <p className="bzc-lead">{t.faqLead}</p>
          </div>
          <ul className="bzc-faq">
            {t.faqs.map((f, n) => {
              const on = aberta === n;
              return (
                <li key={f.q}>
                  <button aria-expanded={on} onClick={() => setAberta(on ? null : n)} type="button">
                    <span>{f.q}</span>
                    <ChevronDown aria-hidden size={18} style={{ transform: on ? "rotate(180deg)" : undefined }} />
                  </button>
                  {on && <p>{f.a}</p>}
                </li>
              );
            })}
          </ul>
        </div>
      </section>

      {/* ── Chamada ───────────────────────────────────────────── */}
      <section className="bzc-chamada">
        <div className="bzc-wrap-sm" style={{ textAlign: "center" }}>
          <h2 className="bzc-h2" style={{ color: "#fff" }}>{t.ctaH2}</h2>
          <p className="bzc-lead" style={{ color: "rgba(234,241,248,.78)", margin: "14px auto 0", maxWidth: "52ch" }}>
            {t.ctaLead}
          </p>
          <div className="bzc-chamada-accoes">
            <Link className="bzc-btn bzc-btn--branco" to="/contactos">{t.ctaContact} <ArrowRight aria-hidden size={16} /></Link>
            <Link className="bzc-btn bzc-btn--fantasma" to="/#produto">{t.ctaProduct}</Link>
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
                  <a href={l.url} rel="noopener" target="_blank">
                    <img alt={l.nome} data-logo="light" src={l.claro} />
                    <img alt={l.nome} data-logo="dark" src={l.escuro} />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </BusUpPagina>
  );
}
