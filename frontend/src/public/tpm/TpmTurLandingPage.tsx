import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  ArrowRight, ArrowUpRight, BusFront, CarFront, CheckCircle2, Download,
  MapPin, Phone, Route, ShieldCheck, Smartphone, Ticket, Users,
} from "lucide-react";
import Reveal from "../landing/Reveal";
import HeroBooking from "./HeroBooking";
import TpmPagina, { EMAIL, TELEFONE, TELEFONE_HREF, pedido, useTpmMeta } from "./TpmChrome";

/* Landing institucional + passageiros da TPM-TUR, cliente da UpDigital.
 * Vive em /tpm-tur, ao lado da landing BusUp (/). O conteúdo vem do site
 * oficial (output/tpm-tur-site) — os factos (serviços, frota, contactos)
 * são os de lá; não se inventam números que a operação não confirmou.
 *
 * A barra e o rodapé saíram daqui para `TpmChrome`: são agora partilhados
 * com as quatro páginas institucionais. Esta página fica só com as secções. */

const SERVICOS = [
  {
    id: "autocarros", icon: BusFront, img: "/landing/tpm/coaches.webp",
    alt: "Autocarros executivos TPM-TUR disponíveis para aluguer",
    h: "Aluguer de autocarros",
    p: "Executivos e normais. A equipa ajuda a identificar a viatura adequada ao percurso e ao número de passageiros.",
    cta: "Pedir orçamento",
  },
  {
    id: "excursoes", icon: Route, img: "/landing/tpm/coach.webp",
    alt: "Autocarro TPM-TUR para excursões e grupos",
    h: "Excursões",
    p: "Reúna o seu grupo e partilhe o destino e o programa. A equipa prepara uma proposta para a viagem.",
    cta: "Planear uma excursão",
  },
  {
    id: "trabalhadores", icon: Users, img: "/landing/tpm/minibuses.webp",
    alt: "Minibuses da TPM-TUR para transporte de equipas",
    h: "Transporte de trabalhadores",
    p: "Apresente as necessidades de deslocação da sua equipa: percursos, turnos e frequência.",
    cta: "Falar com a equipa",
  },
];

const FROTA = [
  { img: "/landing/tpm/coach.webp", nome: "Autocarros", nota: "Percursos longos e grupos inteiros" },
  { img: "/landing/tpm/coaster.webp", nome: "Coaster", nota: "Grupos médios e excursões" },
  { img: "/landing/tpm/minibuses.webp", nome: "Quantum", nota: "Equipas e transfers" },
  { img: "/landing/tpm/suv.webp", nome: "SUV", nota: "Pequenos grupos e rent-a-car" },
];

export default function TpmTurLandingPage() {
  const { hash } = useLocation();

  useTpmMeta(
    "TPM-TUR — Transporte e Turismo",
    "TPM-TUR, S.A. — transporte e turismo em Moçambique. Compre o bilhete online, conheça a frota e os serviços para empresas e grupos.",
  );

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
          alt="Autocarros da frota TPM-TUR" width={1920} height={1920}
          fetchPriority="high" decoding="sync" />
        <div className="tpm-hero-in">
          <span className="bzlp-badge">TPM-TUR, S.A. — Transporte e Turismo</span>
          <h1>A sua próxima viagem<br />começa <span>aqui.</span></h1>
          <p>
            Compre o bilhete online, escolha o seu lugar e embarque sem filas.
            Mais perto do seu destino — viaje com a TPM-TUR.
          </p>
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
              Precisa de transporte para um grupo? <ArrowUpRight size={16} aria-hidden />
            </a>
            <Link to="/comprar" className="bzlp-ghost">
              Ver todas as partidas <ArrowUpRight size={15} aria-hidden />
            </Link>
          </div>
        </div>
      </div>

      {/* FAIXA DE CONFIANÇA — quem somos, em três factos verificáveis, logo
          abaixo da dobra. Nenhum número: não há nenhum confirmado. */}
      <section className="bzlp-wrap" style={{ paddingTop: 40 }}>
        <div className="tpm-confianca">
          <div className="tpm-confianca-item">
            <span className="tpm-confianca-ico"><ShieldCheck size={20} aria-hidden /></span>
            <span><strong>Parceria público-privada</strong>EMTPM · ETM · Sky Rent, Lda.</span>
          </div>
          <span className="tpm-confianca-risca" aria-hidden />
          <div className="tpm-confianca-item">
            <span className="tpm-confianca-ico"><Smartphone size={20} aria-hidden /></span>
            <span><strong>Bilhete no telemóvel</strong>Sem papel, sem filas ao balcão.</span>
          </div>
          <span className="tpm-confianca-risca" aria-hidden />
          <div className="tpm-confianca-item">
            <span className="tpm-confianca-ico"><Ticket size={20} aria-hidden /></span>
            <span><strong>Lugar marcado</strong>Escolha o seu lugar no mapa do autocarro.</span>
          </div>
        </div>
      </section>

      {/* COMO VIAJAR */}
      <section className="bzlp-sec" id="viagens">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="bzlp-sechead">
              <div className="bzlp-kicker">Viagens</div>
              <h2 className="bzlp-h2">O seu bilhete, em três passos</h2>
              <p className="bzlp-lead">
                Do percurso ao lugar sentado, tudo se trata online — antes de sair de casa.
              </p>
            </div>
          </Reveal>
          <div className="tpm-steps">
            {[
              { h: "Escolha a viagem", p: "Indique a origem, o destino e a data. Consulte as partidas e os lugares disponíveis no momento." },
              { h: "Reserve o seu lugar", p: "Seleccione o lugar no mapa do autocarro, preencha os dados de quem viaja e pague online." },
              { h: "Receba o bilhete", p: "O bilhete fica no seu telemóvel logo após o pagamento. Apresente-o ao embarcar." },
            ].map((s, i) => (
              <Reveal key={s.h} delay={i * 70}>
                <div className="tpm-step">
                  <span className="tpm-step-num">{i + 1}</span>
                  <h3>{s.h}</h3>
                  <p>{s.p}</p>
                </div>
              </Reveal>
            ))}
          </div>
          <div style={{ textAlign: "center", marginTop: 32 }}>
            <Link to="/comprar" className="bzlp-btn">Ver partidas e preços <ArrowRight size={17} aria-hidden /></Link>
          </div>
        </div>
      </section>

      {/* SERVIÇOS */}
      <section className="bzlp-sec alt" id="servicos">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="bzlp-sechead">
              <div className="bzlp-kicker">Serviços</div>
              <h2 className="bzlp-h2">O transporte certo para cada ocasião</h2>
              <p className="bzlp-lead">
                Cinco serviços, da viagem em família à deslocação diária da sua equipa.
              </p>
            </div>
          </Reveal>
          <div className="tpm-services">
            {SERVICOS.map((s, i) => (
              <Reveal key={s.h} delay={i * 70}>
                <article className="tpm-service">
                  <img src={s.img} alt={s.alt} width={1200} height={750} loading="lazy" decoding="async" />
                  <div className="tpm-service-body">
                    <h3><s.icon size={18} aria-hidden style={{ verticalAlign: "-3px", marginRight: 8, color: "var(--blue2)" }} />{s.h}</h3>
                    <p>{s.p}</p>
                    <Link to={`/tpm-tur/servicos#${s.id}`}>{s.cta} <ArrowUpRight size={16} aria-hidden /></Link>
                  </div>
                </article>
              </Reveal>
            ))}
          </div>
          <div className="tpm-services-extra">
            <span>Também ao seu dispor:</span>
            <Link to="/tpm-tur/servicos#transfers"><MapPin size={15} aria-hidden /> Transfers e shuttle</Link>
            <Link to="/tpm-tur/servicos#rent-a-car"><CarFront size={15} aria-hidden /> Rent-a-car</Link>
          </div>
          <div style={{ textAlign: "center", marginTop: 28 }}>
            <Link to="/tpm-tur/servicos" className="bzlp-btn outline">
              Ver todos os serviços <ArrowRight size={17} aria-hidden />
            </Link>
          </div>
        </div>
      </section>

      {/* FROTA */}
      <section className="bzlp-sec" id="frota">
        <div className="bzlp-wrap">
          {/* Cabecalho a esquerda, e nao centrado: esta era a terceira
              seccao seguida com a mesma composicao — etiqueta ao meio,
              titulo ao meio, fila de cartoes iguais. Tres iguais em fila
              fazem a pagina parecer gerada. */}
          <Reveal>
            <div className="tpm-frota-head">
              <div>
                <div className="bzlp-kicker left">Frota</div>
                <h2 className="bzlp-h2 left">Conheça a frota,<br />imagine a viagem</h2>
              </div>
              <p className="bzlp-lead left">
                Autocarros, Coaster, Quantum e SUV — quatro categorias para grupos e
                percursos diferentes. Consulte a equipa sobre lotação, comodidades e
                disponibilidade da viatura pretendida.
              </p>
            </div>
          </Reveal>
          <div className="tpm-fleet">
            {FROTA.map((v, i) => (
              <Reveal key={v.nome} delay={i * 60}>
                <figure className="tpm-vehicle">
                  <img src={v.img} alt={`${v.nome} da TPM-TUR`} width={1200} height={1500} loading="lazy" decoding="async" />
                  <figcaption>{v.nome}<small>{v.nota}</small></figcaption>
                </figure>
              </Reveal>
            ))}
          </div>
          <div style={{ textAlign: "center", marginTop: 32 }}>
            <Link to="/tpm-tur/frota" className="bzlp-btn outline">
              Ver a frota completa <ArrowRight size={17} aria-hidden />
            </Link>
          </div>
        </div>
      </section>

      {/* APP DO PASSAGEIRO */}
      <section className="tpm-app" id="app">
        <div className="tpm-app-in">
          <Reveal>
            <div className="tpm-app-shot">
              <img src="/landing/tpm/app-login.png"
                alt="Ecrã de entrada da aplicação BusUp Passageiro"
                width={430} height={900} loading="lazy" decoding="async" />
            </div>
          </Reveal>
          <Reveal delay={90}>
            <div>
              <div className="bzlp-kicker left">App do passageiro</div>
              <h2>A sua viagem, sempre consigo</h2>
              <p>
                Com a app BusUp Passageiro, compra bilhetes, escolhe o seu lugar
                e tem as viagens à mão — sem filas e sem papel.
              </p>
              <ul>
                <li><CheckCircle2 size={18} aria-hidden /> Entre com o seu número de telefone</li>
                <li><CheckCircle2 size={18} aria-hidden /> Escolha a viagem e o seu lugar</li>
                <li><CheckCircle2 size={18} aria-hidden /> Consulte os seus bilhetes na app</li>
              </ul>
              <div className="tpm-app-cta">
                <Link to="/baixar" className="bzlp-btn gold"><Download size={18} aria-hidden /> Descarregar para Android</Link>
                <Link to="/comprar" className="bzlp-btn outline"><Smartphone size={17} aria-hidden /> Comprar no browser</Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* SOBRE — institucional */}
      <section className="bzlp-sec" id="sobre">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="tpm-sobre">
              <div>
                <div className="bzlp-kicker left">A empresa</div>
                <h2>Somos TPM-TUR.<br /><span>Ligamos pessoas aos seus destinos.</span></h2>
              </div>
              <div className="tpm-sobre-copy">
                <p>
                  A TPM-TUR, S.A. é uma empresa moçambicana de transporte e turismo,
                  constituída através de uma parceria entre a EMTPM, a ETM e a Sky Rent, Lda.
                </p>
                <p>
                  Reunimos soluções de transporte para passageiros, empresas e grupos,
                  com uma frota dedicada a diferentes necessidades de mobilidade —
                  das viagens regulares ao aluguer de autocarros.
                </p>
                <div className="tpm-sobre-partners" aria-label="Parceiros fundadores">
                  <span>EMTPM</span><span>ETM</span><span>Sky Rent, Lda</span>
                </div>
                <Link to="/tpm-tur/sobre-nos" className="bzlp-ghost" style={{ paddingLeft: 0, marginTop: 14 }}>
                  A nossa história, missão e valores <ArrowUpRight size={16} aria-hidden />
                </Link>
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
              <div className="bzlp-kicker left">Perguntas frequentes</div>
              <h2 className="bzlp-h2 left">Antes de partir</h2>
            </div>
          </Reveal>
          <div className="tpm-faq">
            <details>
              <summary>Como posso comprar um bilhete?</summary>
              <p>
                Clique em <Link to="/comprar" className="bzlp-ghost" style={{ padding: 0, minHeight: 0, color: "var(--blue2)" }}>Comprar bilhete</Link>,
                escolha a origem, o destino e a data, seleccione o lugar, preencha os dados
                dos passageiros e conclua o pagamento. O bilhete fica no seu telemóvel.
              </p>
            </details>
            <details>
              <summary>Onde consulto horários e preços?</summary>
              <p>
                Os horários, preços e lugares disponíveis são apresentados no portal de compra
                depois de escolher o percurso e a data. A disponibilidade pode variar.
              </p>
            </details>
            <details>
              <summary>Posso pedir transporte para uma empresa ou grupo?</summary>
              <p>
                Sim. Envie um pedido para <a href={`mailto:${EMAIL}`}>{EMAIL}</a> com o percurso,
                as datas e o número de passageiros. A equipa irá indicar as opções disponíveis.
              </p>
            </details>
            <details>
              <summary>Como instalo a aplicação Android?</summary>
              <p>
                Abra a <Link to="/baixar" style={{ color: "var(--blue2)", fontWeight: 600 }}>página oficial de instalação</Link> no
                seu telemóvel e siga as instruções.
              </p>
            </details>
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
            <h2>Qual é o seu próximo destino?</h2>
            <p>Daqui seguem dois caminhos. Escolha o seu.</p>
          </div>
          <div className="tpm-escolha-cartoes">
            <article className="tpm-escolha-cartao">
              <span className="tpm-escolha-ico"><Ticket size={24} aria-hidden /></span>
              <h3>Vou viajar</h3>
              <p>
                Escolha a partida e o lugar no mapa do autocarro. Paga por M-Pesa,
                e-Mola ou cartão, e o bilhete fica no seu telemóvel.
              </p>
              <Link to="/comprar" className="bzlp-btn gold">
                Comprar bilhete <ArrowRight size={17} aria-hidden />
              </Link>
            </article>
            <article className="tpm-escolha-cartao is-grupo">
              <span className="tpm-escolha-ico"><Users size={24} aria-hidden /></span>
              <h3>Preciso de transporte para um grupo</h3>
              <p>
                Empresas, excursões, transfers e aluguer com motorista. Diga o percurso,
                as datas e quantas pessoas — a equipa responde com as opções disponíveis.
              </p>
              <div className="tpm-escolha-accoes">
                <a href={pedido("Pedido de orçamento TPM-TUR")} className="bzlp-btn outline">
                  Pedir orçamento <ArrowUpRight size={16} aria-hidden />
                </a>
                {/* O telefone vem para junto do botao: quem pede orcamento para um
                    grupo quer muitas vezes falar com alguem, e o numero estava so
                    no rodape. */}
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
              <small>Comercial</small>
              <a href={`mailto:${EMAIL}`}>{EMAIL}</a>
              <a href={TELEFONE_HREF}>{TELEFONE}</a>
            </div>
            <div className="bzlp-contact-card">
              <small>Passageiros</small>
              <Link to="/comprar" style={{ color: "inherit" }}>Comprar bilhete</Link>
              <Link to="/baixar" style={{ color: "inherit" }}>App do passageiro</Link>
            </div>
            <div className="bzlp-contact-card">
              <small>Em linha</small>
              <Link to="/login" style={{ color: "inherit" }}>Entrar no portal</Link>
              <a href="https://updigital.co.mz" target="_blank" rel="noreferrer">updigital.co.mz</a>
            </div>
          </div>
        </div>
      </section>
    </TpmPagina>
  );
}
