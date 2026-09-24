import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  ArrowRight, ArrowUpRight, BusFront, CarFront, CheckCircle2, Download,
  Check, MapPin, Phone, Route, Smartphone, Ticket, Users,
} from "lucide-react";
import Reveal from "../landing/Reveal";
import HeroBooking from "./HeroBooking";
import TpmPagina, { EMAIL, TELEFONE, TELEFONE_HREF, pedido, useTpmMeta } from "./TpmChrome";
import { useTpmCopy } from "./tpm-copy";

/* Landing institucional + passageiros da TPM-TUR, cliente da UpDigital.
 * Vive em /tpm-tur, ao lado da landing BusUp (/). O conteúdo vem do site
 * oficial (output/tpm-tur-site) — os factos (serviços, frota, contactos)
 * são os de lá; não se inventam números que a operação não confirmou.
 *
 * A barra e o rodapé saíram daqui para `TpmChrome`, e o texto para
 * `tpm-copy.ts`. Esta página fica com a composição das secções. */

/* Os ids das âncoras e as fotografias não mudam com o idioma: os primeiros são
 * URL, as segundas são as mesmas imagens. */
const SERVICOS_IDS = ["autocarros", "excursoes", "trabalhadores"] as const;
const SERVICOS_ICON = [BusFront, Route, Users];
const SERVICOS_IMG = ["/landing/tpm/coaches.webp", "/landing/tpm/coach.webp", "/landing/tpm/minibuses.webp"];
const FROTA_IMG = [
  "/landing/tpm/coach.webp",
  "/landing/tpm/coaster.webp",
  "/landing/tpm/minibuses.webp",
  "/landing/tpm/suv.webp",
];

/* Clientes e parceiros — a seccao que o site oficial tem e esta nao tinha.
 *
 * Os ficheiros sao os do carrossel de tpmtur.co.mz (wp-content/uploads,
 * 2025/10 e 2025/11), copiados para `public/landing/tpm/clientes/` com nomes
 * legiveis. No original NENHUM tem texto alternativo: sao 34 imagens que um
 * leitor de ecra anuncia como nada. Aqui cada uma leva o nome da organizacao,
 * lido do proprio logotipo.
 *
 * Duas notas de honestidade: o oval vermelho e verde traz so a sigla "MM" e
 * nao consegui apurar de quem e — fica a sigla, que e o que la esta escrito. O
 * verde e a CFM, Caminhos de Ferro de Mocambique. */
const CLIENTES: { f: string; nome: string }[] = [
  { f: "banco-de-mocambique.png", nome: "Banco de Moçambique" },
  { f: "assembleia-da-republica.png", nome: "Assembleia da República" },
  { f: "municipio-de-maputo.jpg", nome: "Município de Maputo" },
  { f: "cidade-da-matola.jpg", nome: "Cidade da Matola" },
  { f: "cfm.jpg", nome: "CFM — Caminhos de Ferro de Moçambique" },
  { f: "edm.jpg", nome: "Electricidade de Moçambique, E.P." },
  { f: "petromoc.jpg", nome: "Petromoc" },
  { f: "vodacom.jpg", nome: "Vodacom" },
  { f: "totalenergies.jpg", nome: "TotalEnergies" },
  { f: "millennium-bim.png", nome: "Millennium bim" },
  { f: "bci.png", nome: "BCI" },
  { f: "moza.png", nome: "Moza Banco" },
  { f: "nedbank.png", nome: "Nedbank" },
  { f: "bni.jpg", nome: "BNI — Banco Nacional de Investimento" },
  { f: "bvm.jpg", nome: "BVM — Bolsa de Valores de Moçambique" },
  { f: "inep.jpg", nome: "INEP — Instituto Nacional de Emprego" },
  { f: "iese.jpg", nome: "IESE — Instituto de Estudos Sociais e Económicos" },
  { f: "ocam.png", nome: "OCAM — Ordem dos Contabilistas e Auditores de Moçambique" },
  { f: "radio-mocambique.jpg", nome: "Rádio Moçambique" },
  { f: "fmn.jpg", nome: "Federação Moçambicana de Natação" },
  { f: "aism.jpg", nome: "AISM — American International School of Mozambique" },
  { f: "afecc-gloria-hotel.jpg", nome: "AFECC Gloria Hotel Maputo" },
  { f: "bureau-veritas.jpg", nome: "Bureau Veritas" },
  { f: "ccs-jv.png", nome: "CCS-JV" },
  { f: "impala.png", nome: "Impala" },
  { f: "grindrod.png", nome: "Grindrod" },
  { f: "twigg.jpg", nome: "TWIGG Exploration & Mining" },
  { f: "true-north.jpg", nome: "True North" },
  { f: "tayanna.jpg", nome: "Tayanna" },
  { f: "apco.png", nome: "APCO Heavy Duty Parts" },
  { f: "ronil.png", nome: "Ronil" },
  { f: "yutong.png", nome: "Yutong" },
  { f: "zhongtong.png", nome: "Zhongtong" },
  { f: "mm.png", nome: "MM" },
];

export default function TpmTurLandingPage() {
  const { hash } = useLocation();
  const { t } = useTpmCopy();
  const i = t.inicio;

  useTpmMeta(i.meta.titulo, i.meta.descricao);

  /* As páginas institucionais ligam a `/tpm-tur#faq`. O react-router muda a
   * URL mas não rola para a âncora — sem isto, quem clica em "Perguntas"
   * noutra página aterra no topo da landing e pensa que o link está partido. */
  useEffect(() => {
    if (!hash) return;
    const alvo = document.querySelector(hash);
    if (alvo) alvo.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [hash]);

  return (
    <TpmPagina>
      {/* HERO */}
      <section className="tpm-hero">
        <img className="tpm-hero-photo" src="/landing/tpm/coaches.webp"
          alt={i.hero.fotoAlt} width={1920} height={1920}
          fetchPriority="high" decoding="sync" />
        <div className="tpm-hero-in">
          <span className="bzlp-badge">{i.hero.badge}</span>
          <h1>{i.hero.h1}<br />{i.hero.h1b} <span>{i.hero.h1destaque}</span></h1>
          <p>{i.hero.lead}</p>
        </div>
      </section>

      {/* O cartao de busca atravessa a dobra da fotografia: metade sobre a
          imagem, metade sobre a pagina. Vive FORA do <section>, que tem
          `overflow:hidden` para a foto nao transbordar — la dentro seria
          cortado pela mesma regra. */}
      <div className="tpm-hero-busca">
        <div className="tpm-hero-busca-in">
          <HeroBooking />
          <div className="tpm-hero-cta">
            <a href={pedido("Pedido de orçamento TPM-TUR")} className="bzlp-btn outline">
              {i.hero.grupo} <ArrowUpRight size={16} aria-hidden />
            </a>
            <Link to="/comprar" className="bzlp-ghost">
              {i.hero.todasPartidas} <ArrowUpRight size={15} aria-hidden />
            </Link>
          </div>
        </div>
      </div>

      {/* QUEM SOMOS — a ordem e a do site oficial: quem somos, o que
          fazemos, porque connosco, o que conduzimos. */}
      <section className="bzlp-sec" id="sobre">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="tpm-sobre">
              <div>
                <div className="bzlp-kicker left">{i.sobre.kicker}</div>
                <h2>{i.sobre.h2}<br /><span>{i.sobre.h2b}</span></h2>
              </div>
              <div className="tpm-sobre-copy">
                <p>{i.sobre.p1}</p>
                <p>{i.sobre.p2}</p>
                <div className="tpm-sobre-partners" aria-label={i.sobre.parceiros}>
                  <span>EMTPM</span><span>ETM</span><span>Sky Rent, Lda</span>
                </div>
                <Link to="/tpm-tur/sobre-nos" className="bzlp-ghost" style={{ paddingLeft: 0, marginTop: 14 }}>
                  {i.sobre.link} <ArrowUpRight size={16} aria-hidden />
                </Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* SERVIÇOS */}
      <section className="bzlp-sec alt" id="servicos">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="bzlp-sechead">
              <div className="bzlp-kicker">{i.servicos.kicker}</div>
              <h2 className="bzlp-h2">{i.servicos.h2}</h2>
              <p className="bzlp-lead">{i.servicos.lead}</p>
            </div>
          </Reveal>
          <div className="tpm-services">
            {i.servicos.cards.map((s, n) => {
              const Icone = SERVICOS_ICON[n];
              return (
                <Reveal key={s.h} delay={n * 70}>
                  <article className="tpm-service">
                    <img src={SERVICOS_IMG[n]} alt={s.alt} width={1200} height={750} loading="lazy" decoding="async" />
                    <div className="tpm-service-body">
                      <h3><Icone size={18} aria-hidden style={{ verticalAlign: "-3px", marginRight: 8, color: "var(--blue2)" }} />{s.h}</h3>
                      <p>{s.p}</p>
                      <Link to={`/tpm-tur/servicos#${SERVICOS_IDS[n]}`}>{s.cta} <ArrowUpRight size={16} aria-hidden /></Link>
                    </div>
                  </article>
                </Reveal>
              );
            })}
          </div>
          <div className="tpm-services-extra">
            <span>{i.servicos.tambem}</span>
            <Link to="/tpm-tur/servicos#transfers"><MapPin size={15} aria-hidden /> {i.servicos.transfers}</Link>
            <Link to="/tpm-tur/servicos#rent-a-car"><CarFront size={15} aria-hidden /> {i.servicos.rentACar}</Link>
          </div>
          <div style={{ textAlign: "center", marginTop: 28 }}>
            <Link to="/tpm-tur/servicos" className="bzlp-btn outline">
              {i.servicos.verTodos} <ArrowRight size={17} aria-hidden />
            </Link>
          </div>
        </div>
      </section>

      {/* VANTAGENS — os cinco pontos do site oficial. */}
      <section className="bzlp-sec" id="vantagens">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="bzlp-sechead">
              <div className="bzlp-kicker">{i.vantagens.kicker}</div>
              <h2 className="bzlp-h2">{i.vantagens.h2}</h2>
            </div>
          </Reveal>
          <ul className="tpm-vantagens">
            {i.vantagens.itens.map((v, n) => (
              <Reveal key={v} delay={(n % 3) * 60}>
                <li>
                  <span className="tpm-vantagem-ico"><Check size={18} aria-hidden strokeWidth={2.4} /></span>
                  {v}
                </li>
              </Reveal>
            ))}
          </ul>
        </div>
      </section>

      {/* FROTA */}
      <section className="bzlp-sec alt" id="frota">
        <div className="bzlp-wrap">
          {/* Cabecalho a esquerda, e nao centrado: esta era a terceira
              seccao seguida com a mesma composicao — etiqueta ao meio,
              titulo ao meio, fila de cartoes iguais. Tres iguais em fila
              fazem a pagina parecer gerada. */}
          <Reveal>
            <div className="tpm-frota-head">
              <div>
                <div className="bzlp-kicker left">{i.frota.kicker}</div>
                <h2 className="bzlp-h2 left">{i.frota.h2}<br />{i.frota.h2b}</h2>
              </div>
              <div>
                <p className="bzlp-lead left">{i.frota.lead}</p>
                {/* As marcas da frota, tal como o site oficial as nomeia em
                    NOSSOS AUTOCARROS. */}
                <p className="tpm-frota-marcas">{i.frota.marcas}</p>
              </div>
            </div>
          </Reveal>
          <div className="tpm-fleet">
            {i.frota.itens.map((v, n) => (
              <Reveal key={v.nome} delay={n * 60}>
                <figure className="tpm-vehicle">
                  <img src={FROTA_IMG[n]} alt={`${v.nome} ${i.frota.altSufixo}`}
                    width={1200} height={1500} loading="lazy" decoding="async" />
                  <figcaption>{v.nome}<small>{v.nota}</small></figcaption>
                </figure>
              </Reveal>
            ))}
          </div>
          <div style={{ textAlign: "center", marginTop: 32 }}>
            <Link to="/tpm-tur/frota" className="bzlp-btn outline">
              {i.frota.verCompleta} <ArrowRight size={17} aria-hidden />
            </Link>
          </div>
        </div>
      </section>

      {/* CLIENTES E PARCEIROS — no site oficial fecha a pagina inicial. */}
      <section className="bzlp-sec" id="clientes">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="bzlp-sechead">
              <div className="bzlp-kicker">{i.clientes.kicker}</div>
              <h2 className="bzlp-h2">{i.clientes.h2}</h2>
              <p className="bzlp-lead">{i.clientes.lead}</p>
            </div>
          </Reveal>
          <ul className="tpm-clientes">
            {CLIENTES.map((c) => (
              <li className="tpm-cliente" key={c.f}>
                <img src={`/landing/tpm/clientes/${c.f}`} alt={`${i.clientes.logoDe} ${c.nome}`}
                  width={283} height={188} loading="lazy" decoding="async" />
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* COMO VIAJAR */}
      <section className="bzlp-sec" id="viagens">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="bzlp-sechead">
              <div className="bzlp-kicker">{i.passos.kicker}</div>
              <h2 className="bzlp-h2">{i.passos.h2}</h2>
              <p className="bzlp-lead">{i.passos.lead}</p>
            </div>
          </Reveal>
          <div className="tpm-steps">
            {i.passos.itens.map((s, n) => (
              <Reveal key={s.h} delay={n * 70}>
                <div className="tpm-step">
                  <span className="tpm-step-num">{n + 1}</span>
                  <h3>{s.h}</h3>
                  <p>{s.p}</p>
                </div>
              </Reveal>
            ))}
          </div>
          <div style={{ textAlign: "center", marginTop: 32 }}>
            <Link to="/comprar" className="bzlp-btn">{i.passos.botao} <ArrowRight size={17} aria-hidden /></Link>
          </div>
        </div>
      </section>

      {/* APP DO PASSAGEIRO */}
      <section className="tpm-app" id="app">
        <div className="tpm-app-in">
          <Reveal>
            <div className="tpm-app-shot">
              <img src="/landing/tpm/app-login.png" alt={i.app.shotAlt}
                width={430} height={900} loading="lazy" decoding="async" />
            </div>
          </Reveal>
          <Reveal delay={90}>
            <div>
              <div className="bzlp-kicker left">{i.app.kicker}</div>
              <h2>{i.app.h2}</h2>
              <p>{i.app.p}</p>
              <ul>
                {i.app.itens.map((li) => (
                  <li key={li}><CheckCircle2 size={18} aria-hidden /> {li}</li>
                ))}
              </ul>
              <div className="tpm-app-cta">
                <Link to="/baixar" className="bzlp-btn gold"><Download size={18} aria-hidden /> {i.app.descarregar}</Link>
                <Link to="/comprar" className="bzlp-btn outline"><Smartphone size={17} aria-hidden /> {i.app.browser}</Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* FAQ */}
      <section className="bzlp-sec alt" id="faq">
        <div className="bzlp-wrap tpm-faq-wrap">
          <Reveal>
            <div className="tpm-faq-head">
              <div className="bzlp-kicker left">{i.faq.kicker}</div>
              <h2 className="bzlp-h2 left">{i.faq.h2}</h2>
            </div>
          </Reveal>
          <div className="tpm-faq">
            {i.faq.itens.map((item) => (
              <details key={item.q}>
                <summary>{item.q}</summary>
                {/* O email é a única ligação que sobrevive dentro de uma
                    resposta: vem por marcador, para a frase poder mudar de
                    ordem em inglês sem partir o link. */}
                <p>
                  {item.a.split("{email}").map((parte, n, todas) => (
                    <span key={n}>
                      {parte}
                      {n < todas.length - 1 && <a href={`mailto:${EMAIL}`}>{EMAIL}</a>}
                    </span>
                  ))}
                </p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* CTA FINAL — dois caminhos, e nao dois botoes iguais.
          "Comprar bilhete" e auto-servico, instantaneo, de quem vai viajar;
          "Pedir orcamento" e uma conversa comercial com uma empresa. Lado a
          lado e com o mesmo peso, obrigavam cada visitante a ler os dois para
          descobrir qual era o seu. O dourado — a cor que a marca reserva para
          "olha para aqui" — deixa de pintar a faixa toda e passa a marcar a
          accao do caminho do passageiro. */}
      <section className="tpm-escolha" id="contacto">
        <div className="bzlp-wrap">
          <div className="tpm-escolha-head">
            <h2>{i.escolha.h2}</h2>
            <p>{i.escolha.lead}</p>
          </div>
          <div className="tpm-escolha-cartoes">
            <article className="tpm-escolha-cartao">
              <span className="tpm-escolha-ico"><Ticket size={24} aria-hidden /></span>
              <h3>{i.escolha.viajar.h}</h3>
              <p>{i.escolha.viajar.p}</p>
              <Link to="/comprar" className="bzlp-btn gold">
                {i.escolha.viajar.btn} <ArrowRight size={17} aria-hidden />
              </Link>
            </article>
            <article className="tpm-escolha-cartao is-grupo">
              <span className="tpm-escolha-ico"><Users size={24} aria-hidden /></span>
              <h3>{i.escolha.grupo.h}</h3>
              <p>{i.escolha.grupo.p}</p>
              <div className="tpm-escolha-accoes">
                <a href={pedido("Pedido de orçamento TPM-TUR")} className="bzlp-btn outline">
                  {i.escolha.grupo.btn} <ArrowUpRight size={16} aria-hidden />
                </a>
                {/* O telefone vem para junto do botao: quem pede orcamento para
                    um grupo quer muitas vezes falar com alguem, e o numero
                    estava so no rodape. */}
                <a href={TELEFONE_HREF} className="tpm-escolha-tel">
                  <Phone size={17} aria-hidden /> {TELEFONE}
                </a>
              </div>
            </article>
          </div>
        </div>
      </section>

      <section className="bzlp-cta" style={{ paddingTop: 40, paddingBottom: 40 }}>
        <div className="bzlp-wrap">
          <div className="bzlp-contact" style={{ marginTop: 0 }}>
            <div className="bzlp-contact-card">
              <small>{i.contactoStrip.comercial}</small>
              <a href={`mailto:${EMAIL}`}>{EMAIL}</a>
              <a href={TELEFONE_HREF}>{TELEFONE}</a>
            </div>
            <div className="bzlp-contact-card">
              <small>{i.contactoStrip.passageiros}</small>
              <Link to="/comprar" style={{ color: "inherit" }}>{i.contactoStrip.comprar}</Link>
              <Link to="/baixar" style={{ color: "inherit" }}>{i.contactoStrip.app}</Link>
            </div>
            <div className="bzlp-contact-card">
              <small>{i.contactoStrip.emLinha}</small>
              <Link to="/login" style={{ color: "inherit" }}>{i.contactoStrip.portal}</Link>
              <a href="https://updigital.co.mz" target="_blank" rel="noreferrer">updigital.co.mz</a>
            </div>
          </div>
        </div>
      </section>
    </TpmPagina>
  );
}
