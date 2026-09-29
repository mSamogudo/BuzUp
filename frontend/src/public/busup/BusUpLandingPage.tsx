import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Check, ChevronDown, Minus, Plus } from "lucide-react";
import BusUpPagina, { MARCA, useBusUpCopy, useBusUpMeta, LogotipoUpDigital, LOGO_CLARO, LOGO_ESCURO } from "./BusUpChrome";

/* A landing pública do BusUp — o desenho "Céu", portado do protótipo
 * `Landing BusUp - Ceu.dc.html` do projecto de desenho.
 *
 * O texto vem de `busup-copy.ts` VERBATIM, nos dois idiomas. A regra da
 * entrega é explícita: nada de texto novo inventado. Onde o protótipo deixou
 * espaço por preencher — os depoimentos — o espaço vem marcado.
 *
 * AS VINHETAS SÃO MARKUP E NÃO IMAGENS. Cada cartão de funcionalidade traz um
 * pedaço de interface desenhado em HTML: o passo da compra, os quatro estados
 * da validação, a lista de cartões, as barras da receita. Em PNG ficavam
 * desfocadas em ecrã denso, não acompanhavam o tema escuro e não se
 * traduziam. Em markup fazem as três coisas de graça.
 */

const LOGOS_ECO = [
  { src: "/ecosystem/logos/payup.webp", nome: "PayUp", url: "https://payup.updigital.co.mz" },
  { src: "/ecosystem/logos/cashup.webp", nome: "CashUp", url: "https://cashup.updigital.co.mz" },
  { src: "/ecosystem/logos/gateup.webp", nome: "GateUp", url: "https://gateup.updigital.co.mz" },
  { src: "/ecosystem/logos/vura.webp", nome: "Vura", url: "https://vura.updigital.co.mz" },
  { src: "/ecosystem/logos/ossoma.webp", nome: "Ossoma", url: "https://ossoma.updigital.co.mz" },
];

/* A ocupação da viatura no painel: 32 lugares, 22 ocupados. Os números são os
   do protótipo; o padrão é fixo para o painel não mudar a cada render. */
const LUGARES = Array.from({ length: 32 }, (_, n) => n < 22);

/* ── O painel do portal, por baixo do hero ─────────────────────────── */

function PainelPortal() {
  return (
    <div className="bzc-painel-corte">
      <div className="bzc-painel">
        <div className="bzc-painel-barra">
          <div className="bzc-painel-marca">
            <img alt="" src={MARCA} style={{ height: 17, width: "auto" }} />
            <b>BusUp</b>
          </div>
          <div className="bzc-painel-abas">
            {["Dashboard", "Rotas", "Viaturas", "Viagens", "Cartões", "Relatórios", "Auditoria"].map((a, n) => (
              <span className={n === 0 ? "is-on" : undefined} key={a}>{a}</span>
            ))}
          </div>
          <div className="bzc-painel-conta">
            <span className="bzc-painel-busca">Pesquisar…</span>
            <span className="bzc-painel-avatar">AM</span>
          </div>
        </div>

        <div className="bzc-painel-corpo">
          <div className="bzc-painel-titulo">
            <b>Painel de operação</b>
            <span className="bzc-vivo"><i className="bzc-pulsa" />Ao vivo</span>
            <div className="bzc-painel-filtros">
              {["Hoje", "Todas as rotas", "Exportar"].map((f) => <span key={f}>{f}</span>)}
            </div>
          </div>

          <div className="bzc-painel-metricas">
            <div className="bzc-metrica"><small>Receita hoje</small><b>13 300 <span>MZN</span></b></div>
            <div className="bzc-metrica"><small>Bilhetes validados</small><b>140</b></div>
            <div className="bzc-metrica">
              <small>Ocupação</small><b>69<span>%</span></b>
              <span className="bzc-barra"><i style={{ width: "69%" }} /></span>
            </div>
            <div className="bzc-metrica"><small>Viagens activas</small><b>12</b></div>
          </div>

          <div className="bzc-painel-baixo">
            <div className="bzc-painel-lista">
              <div className="bzc-painel-lista-topo">
                <b>Validações recentes</b><span>últimos 30 min</span>
              </div>
              <div className="bzc-painel-linhas">
                {[
                  ["L5 · Baixa — Aeroporto", "84 123 4567"],
                  ["L2 · Museu — Costa do Sol", "86 998 1122"],
                  ["L6 · Junta — Marracuene", "85 447 9080"],
                  ["L5 · Baixa — Aeroporto", "87 210 3345"],
                ].map(([rota, numero], n) => (
                  <div key={`${rota}-${n}`}>
                    <span>{rota}</span>
                    <span className="bzc-num">{numero}</span>
                    <span className="bzc-ok">validado</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bzc-painel-lugares">
              <b>ABC-123-MP</b>
              <small>32 lugares · 22 ocupados</small>
              <div className="bzc-lugares">
                {LUGARES.map((ocupado, n) => <i data-ocupado={ocupado || undefined} key={n} />)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── As vinhetas dos cartões de funcionalidade ─────────────────────── */

function VinhetaCompra() {
  return (
    <div className="bzc-vinheta">
      <div className="bzc-vinheta-in">
        <div className="bzc-vinheta-topo"><b>Comprar bilhete</b><span className="bzc-azul">1 / 3</span></div>
        <div className="bzc-vinheta-campos">
          <span>Maputo — Beira<i>›</i></span>
          <span>06:30 · Lugar 14<i>›</i></span>
        </div>
        <div className="bzc-vinheta-par">
          <span className="is-on">M-Pesa</span>
          <span>e-Mola</span>
        </div>
        <span className="bzc-vinheta-accao">Pagar 850 MZN</span>
      </div>
    </div>
  );
}

function VinhetaValidacao() {
  const estados: Array<[string, "ok" | "aviso" | "mau"]> = [
    ["Bilhete QR · aceite", "ok"],
    ["Cartão NFC · aceite", "ok"],
    ["Saldo insuficiente", "aviso"],
    ["Bilhete já usado", "mau"],
  ];
  return (
    <div className="bzc-vinheta">
      <div className="bzc-vinheta-in">
        <div className="bzc-vinheta-topo">
          <b>Validação a bordo</b>
          <span className="bzc-ok"><i />POS ligado</span>
        </div>
        <div className="bzc-vinheta-estados">
          {estados.map(([rotulo, tom]) => <span data-tom={tom} key={rotulo}><i />{rotulo}</span>)}
        </div>
        <p className="bzc-vinheta-nota">Pacote especial › saldo normal › nega</p>
      </div>
    </div>
  );
}

function VinhetaCartoes() {
  const cartoes: Array<[string, string, "ok" | "aviso" | "mute"]> = [
    ["NFC · 0042 1187", "activo", "ok"],
    ["NFC · 0042 1188", "activo", "ok"],
    ["QR · maria.j", "pendente", "aviso"],
    ["NFC · 0042 1190", "bloqueado", "mute"],
  ];
  return (
    <div className="bzc-vinheta">
      <div className="bzc-vinheta-in">
        <div className="bzc-vinheta-abas"><span className="is-on">Físicos</span><span>Digitais</span></div>
        <div className="bzc-vinheta-cartoes">
          {cartoes.map(([id, estado, tom]) => (
            <div key={id}><span>{id}</span><span data-tom={tom}>{estado}</span></div>
          ))}
        </div>
        <span className="bzc-vinheta-importar">Importar Excel (.xlsx)</span>
      </div>
    </div>
  );
}

const BARRAS = [46, 62, 38, 74, 55, 88, 70];

function VinhetaReceita() {
  return (
    <div className="bzc-vinheta bzc-vinheta--plana">
      <div className="bzc-vinheta-receita">
        <div>
          <small>Receita da semana</small>
          <b className="bzc-num">412 850 <span>MZN</span></b>
        </div>
        <span className="bzc-ok">reconciliado</span>
      </div>
      <div className="bzc-grafico">
        {BARRAS.map((h, n) => <i data-cheia={n === BARRAS.length - 1 || undefined} key={n} style={{ height: `${h}%` }} />)}
      </div>
    </div>
  );
}

function VinhetaMapa({ rotulo, texto }: { rotulo: string; texto: string }) {
  return (
    <div className="bzc-mapa">
      <span className="bzc-rotulo">{rotulo}</span>
      <p>{texto}</p>
    </div>
  );
}

/* ── A página ──────────────────────────────────────────────────────── */

export default function BusUpLandingPage() {
  const { t } = useBusUpCopy();
  const [passoAberto, setPassoAberto] = useState(0);
  const [perguntaAberta, setPerguntaAberta] = useState<number | null>(0);

  useBusUpMeta(
    `BusUp · ${t.heroH1a} ${t.heroH1b}`,
    t.heroLead,
  );

  return (
    <BusUpPagina>
      {/* ── CHAPA ─────────────────────────────────────────────────── */}
      <section className="bzc-hero" id="topo">
        <div aria-hidden className="bzc-hero-luz" />

        <div className="bzc-hero-in">
          <span className="bzc-distintivo"><i className="bzc-ponto bzc-pulsa" />{t.heroBadge}</span>
          <h1 className="bzc-h1">{t.heroH1a}<span>{t.heroH1b}</span></h1>
          <p className="bzc-lead" style={{ maxWidth: "54ch", fontSize: 17.5 }}>{t.heroLead}</p>

          <div className="bzc-hero-accoes">
            <Link className="bzc-btn bzc-btn--azul" to="/contactos">{t.ctaPrimary}</Link>
            <Link className="bzc-btn bzc-btn--ceu" to="/comprar">{t.buyTicket}</Link>
            <a className="bzc-btn bzc-btn--linha" href="#produto">{t.ctaSecondary}</a>
          </div>

          <ul className="bzc-hero-chips">
            {t.chips.map((c) => <li className="bzc-chip" key={c}>{c}</li>)}
          </ul>
        </div>

        {/* As quatro etiquetas que apontam para quem usa o quê. São decorativas:
            o painel por baixo já diz tudo o que elas dizem. */}
        <div aria-hidden className="bzc-hero-painel" id="produto">
          <span className="bzc-etiqueta bzc-etiqueta--1"><i style={{ background: "#2A9D8F" }} />{t.tag1}</span>
          <span className="bzc-etiqueta bzc-etiqueta--2"><i style={{ background: "#2D8CF0" }} />{t.tag2}</span>
          <span className="bzc-etiqueta bzc-etiqueta--3"><i style={{ background: "#FFB703" }} />{t.tag3}</span>
          <span className="bzc-etiqueta bzc-etiqueta--4"><i style={{ background: "#0D3B66" }} />{t.tag4}</span>
          <PainelPortal />
        </div>
      </section>

      {/* ── FITA DO ECOSSISTEMA ───────────────────────────────────── */}
      <div className="bzc-fita">
        <div className="bzc-wrap-md">
          <h2 style={{ font: "800 26px/1.2 Manrope, sans-serif", letterSpacing: "-.025em", textAlign: "center" }}>
            {t.ecoStripTitle}
          </h2>
          <p className="bzc-lead" style={{ fontSize: 14, textAlign: "center", margin: "6px auto 22px" }}>{t.logosLead}</p>
          <div className="bzc-desfile">
            {/* Duas cópias e um deslize de metade: ao fim do percurso a segunda
                está onde a primeira estava, e o laço fecha sem se ver o corte. */}
            <ul className="bzc-desfile-fita">
              {[0, 1].flatMap((copia) => [
                <li key={`u-${copia}`} aria-hidden={copia > 0 || undefined}>
                  <LogotipoUpDigital alt={copia === 0 ? "UpDigital, Limitada" : ""} altura={26} />
                </li>,
                ...LOGOS_ECO.map((l) => (
                  <li aria-hidden={copia > 0 || undefined} key={`${copia}-${l.nome}`}>
                    <img alt={copia === 0 ? l.nome : ""} src={l.src} />
                  </li>
                )),
              ])}
            </ul>
          </div>
        </div>
      </div>

      {/* ── FUNCIONALIDADES ───────────────────────────────────────── */}
      <section className="bzc-sec bzc-sec-alt" id="recursos">
        <div className="bzc-wrap-md">
          <div className="bzc-sechead">
            <h2 className="bzc-h2">{t.featH2}</h2>
            <p className="bzc-lead">{t.featLead}</p>
          </div>

          <div className="bzc-grelha-3">
            <article className="bzc-cartao-func">
              <div><h3 className="bzc-h3">{t.f1t}</h3><p className="bzc-lead">{t.f1p}</p></div>
              <VinhetaCompra />
            </article>
            <article className="bzc-cartao-func">
              <div><h3 className="bzc-h3">{t.f2t}</h3><p className="bzc-lead">{t.f2p}</p></div>
              <VinhetaValidacao />
            </article>
            <article className="bzc-cartao-func">
              <div><h3 className="bzc-h3">{t.f3t}</h3><p className="bzc-lead">{t.f3p}</p></div>
              <VinhetaCartoes />
            </article>
          </div>

          <div className="bzc-grelha-2">
            <article className="bzc-cartao bzc-cartao--grande" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              <div><h3 className="bzc-h3">{t.f4t}</h3><p className="bzc-lead">{t.f4p}</p></div>
              <VinhetaReceita />
            </article>
            <article className="bzc-cartao bzc-cartao--grande" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              <div><h3 className="bzc-h3">{t.f5t}</h3><p className="bzc-lead">{t.f5p}</p></div>
              <ul className="bzc-lista-check">
                {[t.f5a, t.f5b, t.f5c].map((x) => (
                  <li key={x}><Check aria-hidden size={16} />{x}</li>
                ))}
              </ul>
              <VinhetaMapa rotulo={t.mapPanel} texto={t.mapPlaceholder} />
            </article>
          </div>
        </div>
      </section>

      {/* ── PORQUÊ / NÚMEROS ──────────────────────────────────────── */}
      <section className="bzc-sec" id="porque">
        <div className="bzc-wrap-md">
          <div className="bzc-sechead">
            <h2 className="bzc-h2">{t.statsH2}</h2>
            <p className="bzc-lead">{t.statsLead}</p>
          </div>
          <dl className="bzc-numeros">
            {t.stats.map((s) => (
              <div key={s.l}>
                <dt className="bzc-num">{s.v}</dt>
                <dd>{s.l}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* ── COMEÇAR EM TRÊS PASSOS ────────────────────────────────── */}
      <section className="bzc-sec bzc-sec-alt">
        <div className="bzc-wrap-md">
          <div className="bzc-sechead">
            <h2 className="bzc-h2">{t.stepsH2}</h2>
            <p className="bzc-lead">{t.stepsLead}</p>
          </div>

          <div className="bzc-passos">
            <div className="bzc-passos-painel">
              <b>{t.stepsPanelTitle}</b>
              <p>{t.stepsPanelText}</p>
              <div className="bzc-passos-mock">
                <div className="bzc-passos-mock-nav">
                  <div className="bzc-passos-mock-marca"><img alt="" src={MARCA} /><b>BusUp</b></div>
                  {["Dashboard", "Rotas", "Paragens", "Viaturas", "Motoristas", "Tarifas", "Cartões", "Financeiro", "Auditoria"].map((x, n) => (
                    <span className={n === 0 ? "is-on" : undefined} key={x}>{x}</span>
                  ))}
                </div>
                <div className="bzc-passos-mock-corpo">
                  <b>Rotas</b>
                  {[
                    ["L5 · Baixa — Aeroporto", "activa", "ok"],
                    ["L2 · Museu — Costa do Sol", "activa", "ok"],
                    ["Maputo — Beira", "rascunho", "aviso"],
                    ["Maputo — Nelspruit", "activa", "ok"],
                  ].map(([nome, estado, tom]) => (
                    <div key={nome}><span>{nome}</span><span data-tom={tom}>{estado}</span></div>
                  ))}
                </div>
              </div>
            </div>

            <ol className="bzc-passos-lista">
              {t.steps.map((p, n) => {
                const aberto = passoAberto === n;
                return (
                  <li key={p.n}>
                    <button
                      aria-expanded={aberto}
                      onClick={() => setPassoAberto(aberto ? -1 : n)}
                      type="button"
                    >
                      <span className="bzc-passo-n">{p.n}</span>
                      <span className="bzc-passo-txt">
                        <b>{p.title}</b>
                        <span>{p.text}</span>
                      </span>
                      <span className="bzc-passo-sinal">
                        {aberto ? <Minus aria-hidden size={15} /> : <Plus aria-hidden size={15} />}
                      </span>
                    </button>
                    {aberto && (
                      <div className="bzc-passo-detalhe">
                        <div><b>{p.m1}</b><span>{p.m1cta}</span></div>
                        <div><b>{p.m2}</b><span>{p.m2a}</span><span>{p.m2b}</span></div>
                      </div>
                    )}
                  </li>
                );
              })}
            </ol>
          </div>
        </div>
      </section>

      {/* ── CASOS ─────────────────────────────────────────────────── */}
      <section className="bzc-sec" id="casos">
        <div className="bzc-wrap-md">
          <div className="bzc-sechead">
            <h2 className="bzc-h2">{t.casesH2}</h2>
            {/* O protótipo deixou isto por preencher e não fui eu que o
                preenchi: são depoimentos de operadores reais, e inventá-los
                era a única coisa nesta página que não se podia desfazer. */}
            <p className="bzc-lead">{t.casesLead}</p>
          </div>
          <div className="bzc-grelha-3">
            {t.cases.map((c) => (
              <figure className="bzc-caso" key={c.kind}>
                <span className="bzc-rotulo">{c.kind}</span>
                <blockquote>{c.quote}</blockquote>
                <figcaption>{c.who}</figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>

      {/* ── PREÇOS ────────────────────────────────────────────────── */}
      <section className="bzc-sec bzc-sec-alt" id="precos">
        <div className="bzc-wrap-md">
          <div className="bzc-sechead">
            <h2 className="bzc-h2">{t.priceH2}</h2>
            <p className="bzc-lead">{t.priceLead}</p>
          </div>
          <div className="bzc-grelha-3">
            {t.plans.map((p) => (
              <article className="bzc-plano" data-destaque={"featured" in p && p.featured ? "" : undefined} key={p.name}>
                <div className="bzc-plano-topo">
                  <h3 className="bzc-h3">{p.name}</h3>
                  {"badge" in p && p.badge ? <span className="bzc-plano-selo">{p.badge}</span> : null}
                </div>
                <p className="bzc-plano-preco">{p.price}</p>
                <p className="bzc-lead" style={{ fontSize: 14 }}>{p.unit}</p>
                <ul className="bzc-lista-check">
                  {p.items.map((i) => <li key={i}><Check aria-hidden size={16} />{i}</li>)}
                </ul>
                <Link className={`bzc-btn ${"featured" in p && p.featured ? "bzc-btn--azul" : "bzc-btn--linha"}`} to="/contactos">
                  {p.cta} <ArrowRight aria-hidden size={16} />
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── PERGUNTAS ─────────────────────────────────────────────── */}
      <section className="bzc-sec">
        <div className="bzc-wrap-sm">
          <div className="bzc-sechead">
            <h2 className="bzc-h2">{t.faqH2}</h2>
            <p className="bzc-lead">{t.faqLead}</p>
          </div>
          <ul className="bzc-faq">
            {t.faqs.map((f, n) => {
              const aberta = perguntaAberta === n;
              return (
                <li key={f.q}>
                  <button aria-expanded={aberta} onClick={() => setPerguntaAberta(aberta ? null : n)} type="button">
                    <span>{f.q}</span>
                    <ChevronDown aria-hidden size={18} style={{ transform: aberta ? "rotate(180deg)" : undefined }} />
                  </button>
                  {aberta && <p>{f.a}</p>}
                </li>
              );
            })}
          </ul>
        </div>
      </section>

      {/* ── CHAMADA ───────────────────────────────────────────────── */}
      <section className="bzc-chamada">
        <div className="bzc-wrap-sm" style={{ textAlign: "center" }}>
          <h2 className="bzc-h2" style={{ color: "#fff" }}>{t.ctaH2}</h2>
          <p className="bzc-lead" style={{ color: "rgba(234,241,248,.78)", margin: "14px auto 0", maxWidth: "52ch" }}>
            {t.ctaLead}
          </p>
          <div className="bzc-chamada-accoes">
            <Link className="bzc-btn bzc-btn--branco" to="/contactos">{t.ctaContact} <ArrowRight aria-hidden size={16} /></Link>
            <a className="bzc-btn bzc-btn--fantasma" href="#precos">{t.ctaPricing}</a>
          </div>
        </div>
      </section>

      {/* ── QUEM CONSTRÓI ─────────────────────────────────────────── */}
      <section className="bzc-sec bzc-sec-alt" id="ecossistema">
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
              <li>
                <a href="https://busup.updigital.co.mz" rel="noopener" target="_blank">
                  <img alt="BusUp" data-logo="light" src={LOGO_CLARO} />
                  <img alt="BusUp" data-logo="dark" src={LOGO_ESCURO} />
                </a>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </BusUpPagina>
  );
}
