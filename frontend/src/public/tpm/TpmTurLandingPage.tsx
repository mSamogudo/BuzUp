import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, ArrowUpRight, Backpack, BusFront, CarFront, CheckCircle2,
  Download, KeyRound, Menu, Moon, Smartphone, Sun, Ticket, Users, X,
} from "lucide-react";
import Reveal from "../landing/Reveal";
import { useLandingPrefs } from "../landing/useLandingPrefs";
import "../landing/landing.css";
import "./tpm.css";

/* Landing institucional + passageiros da TPM-TUR, cliente da UpDigital.
 * Vive em /tpm-tur, ao lado da landing BusUp (/). O conteúdo vem do site
 * oficial (output/tpm-tur-site) — os factos (serviços, frota, contactos)
 * são os de lá; não se inventam números que a operação não confirmou. */

const LOGO_CLARO = "/assets/tpm-tur-logo/tpm_light.png";      // wordmark escuro, para fundo claro
const LOGO_ESCURO = "/assets/tpm-tur-logo/tpm_dark.png";      // wordmark claro, para fundo escuro
const EMAIL = "info@tpmtur.co.mz";
const TELEFONE = "+258 84 314 2681";
const TELEFONE_HREF = "tel:+258843142681";

const NAV = [
  { id: "viagens", label: "Viagens" },
  { id: "servicos", label: "Serviços" },
  { id: "frota", label: "Frota" },
  { id: "app", label: "App" },
  { id: "sobre", label: "Sobre" },
  { id: "faq", label: "Perguntas" },
];

export default function TpmTurLandingPage() {
  const { effectiveTheme, toggleTheme } = useLandingPrefs();
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const burgerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    document.title = "TPM-TUR — Transportes e Turismo";
    const meta = document.querySelector('meta[name="description"]');
    meta?.setAttribute(
      "content",
      "TPM-TUR, S.A. — transporte e turismo em Moçambique. Compre o bilhete online, conheça a frota e os serviços para empresas e grupos.",
    );
  }, []);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setMenuOpen(false); };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      burgerRef.current?.focus();
    };
  }, [menuOpen]);

  const logo = effectiveTheme === "dark" ? LOGO_ESCURO : LOGO_CLARO;

  const ThemeButton = () => (
    <button className="bzlp-icon-btn" type="button" onClick={toggleTheme}
      aria-label={effectiveTheme === "dark" ? "Modo claro" : "Modo escuro"}
      title={effectiveTheme === "dark" ? "Modo claro" : "Modo escuro"}>
      {effectiveTheme === "dark" ? <Sun size={16} aria-hidden /> : <Moon size={16} aria-hidden />}
    </button>
  );

  return (
    <div className="bzlp bzlp-tpm" data-theme={effectiveTheme}>
      <a className="bzlp-skip" href="#conteudo">Saltar para o conteúdo</a>

      <header className={`bzlp-nav${scrolled ? " is-scrolled" : ""}`}>
        <div className="bzlp-nav-in">
          <Link to="/tpm-tur" aria-label="TPM-TUR — página inicial">
            <img src={logo} alt="TPM-TUR, S.A. — Transporte e Turismo" height={30} style={{ display: "block" }} />
          </Link>
          <nav className="bzlp-links" aria-label="TPM-TUR">
            {NAV.map((n) => <a key={n.id} href={`#${n.id}`}>{n.label}</a>)}
          </nav>
          <div className="bzlp-nav-cta">
            <div className="bzlp-tools"><ThemeButton /></div>
            <Link to="/login" className="bzlp-ghost">Entrar</Link>
            <Link to="/comprar" className="bzlp-btn sm gold"><Ticket size={16} aria-hidden /> Comprar bilhete</Link>
            <button ref={burgerRef} className="bzlp-burger" aria-label="Abrir menu" onClick={() => setMenuOpen(true)}>
              <Menu size={24} aria-hidden />
            </button>
          </div>
        </div>
      </header>

      {menuOpen && (
        <div className="bzlp-sheet" onClick={() => setMenuOpen(false)}>
          <div className="bzlp-sheet-panel" onClick={(e) => e.stopPropagation()}>
            <div className="bzlp-sheet-head">
              <img src={logo} alt="TPM-TUR" height={24} />
              <button className="bzlp-sheet-close" aria-label="Fechar menu" onClick={() => setMenuOpen(false)}>
                <X size={24} aria-hidden />
              </button>
            </div>
            {NAV.map((n) => (
              <a key={n.id} href={`#${n.id}`} onClick={() => setMenuOpen(false)}>{n.label}</a>
            ))}
            <Link to="/login" onClick={() => setMenuOpen(false)}>Entrar no portal</Link>
            <Link to="/comprar" className="bzlp-btn gold" onClick={() => setMenuOpen(false)}>
              <Ticket size={18} aria-hidden /> Comprar bilhete
            </Link>
            <div className="bzlp-sheet-tools"><ThemeButton /></div>
          </div>
        </div>
      )}

      <main id="conteudo">
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
            <div className="tpm-hero-cta">
              <Link to="/comprar" className="bzlp-btn gold"><Ticket size={18} aria-hidden /> Comprar bilhete</Link>
              <a href={`mailto:${EMAIL}?subject=${encodeURIComponent("Pedido de orçamento TPM-TUR")}`} className="bzlp-btn outline light">
                Precisa de transporte para um grupo? <ArrowUpRight size={16} aria-hidden />
              </a>
            </div>
            <div className="tpm-hero-chips">
              <span>Bilhetes online</span>
              <span>Lugar escolhido por si</span>
              <span>Sem dinheiro em mão</span>
              <span>App do passageiro</span>
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
                  Da viagem em família à deslocação diária da sua equipa, encontre a solução para o seu percurso.
                </p>
              </div>
            </Reveal>
            <div className="tpm-services">
              {[
                {
                  icon: Users, img: "/landing/tpm/minibuses.webp", alt: "Minibuses da TPM-TUR para transporte de equipas",
                  h: "Transporte de equipas",
                  p: "Organize as deslocações dos seus trabalhadores com uma solução ajustada à sua empresa.",
                  cta: "Pedir orçamento", assunto: "Orçamento - Transporte de trabalhadores",
                },
                {
                  icon: Backpack, img: "/landing/tpm/coach.webp", alt: "Autocarro TPM-TUR para excursões e grupos",
                  h: "Excursões e grupos",
                  p: "Reúna o seu grupo. Fale connosco sobre o transporte para a próxima viagem ou evento.",
                  cta: "Planear uma excursão", assunto: "Orçamento - Excursão",
                },
                {
                  icon: KeyRound, img: "/landing/tpm/coaches.webp", alt: "Autocarros executivos TPM-TUR disponíveis para aluguer",
                  h: "Aluguer de autocarros",
                  p: "Autocarros executivos e normais para diferentes necessidades de transporte.",
                  cta: "Encontrar uma solução", assunto: "Orçamento - Aluguer de autocarro",
                },
              ].map((s, i) => (
                <Reveal key={s.h} delay={i * 70}>
                  <article className="tpm-service">
                    <img src={s.img} alt={s.alt} width={1200} height={750} loading="lazy" decoding="async" />
                    <div className="tpm-service-body">
                      <h3><s.icon size={18} aria-hidden style={{ verticalAlign: "-3px", marginRight: 8, color: "var(--blue)" }} />{s.h}</h3>
                      <p>{s.p}</p>
                      <a href={`mailto:${EMAIL}?subject=${encodeURIComponent(s.assunto)}`}>{s.cta} <ArrowUpRight size={16} aria-hidden /></a>
                    </div>
                  </article>
                </Reveal>
              ))}
            </div>
            <div className="tpm-services-extra">
              <span>Também ao seu dispor:</span>
              <a href={`mailto:${EMAIL}?subject=${encodeURIComponent("Pedido de transfer")}`}>
                <CheckCircle2 size={15} aria-hidden /> Transfers e shuttle
              </a>
              <a href={`mailto:${EMAIL}?subject=${encodeURIComponent("Pedido de rent-a-car")}`}>
                <CarFront size={15} aria-hidden /> Rent-a-car
              </a>
            </div>
          </div>
        </section>

        {/* FROTA */}
        <section className="bzlp-sec" id="frota">
          <div className="bzlp-wrap">
            <Reveal>
              <div className="bzlp-sechead">
                <div className="bzlp-kicker">Frota</div>
                <h2 className="bzlp-h2">Conheça a frota, imagine a viagem</h2>
                <p className="bzlp-lead">
                  Autocarros executivos e normais, Coaster, Quantum e SUV — opções para cada grupo e cada destino.
                </p>
              </div>
            </Reveal>
            <div className="tpm-fleet">
              {[
                { img: "/landing/tpm/coach.webp", nome: "Autocarro executivo", nota: "Longos percursos com conforto" },
                { img: "/landing/tpm/coaster.webp", nome: "Coaster", nota: "Grupos médios e excursões" },
                { img: "/landing/tpm/minibuses.webp", nome: "Quantum", nota: "Equipas e transfers" },
                { img: "/landing/tpm/suv.webp", nome: "SUV", nota: "Pequenos grupos e rent-a-car" },
              ].map((v, i) => (
                <Reveal key={v.nome} delay={i * 60}>
                  <figure className="tpm-vehicle">
                    <img src={v.img} alt={`${v.nome} da TPM-TUR`} width={1200} height={1500} loading="lazy" decoding="async" />
                    <figcaption>{v.nome}<small>{v.nota}</small></figcaption>
                  </figure>
                </Reveal>
              ))}
            </div>
            <p className="bzlp-lead" style={{ marginTop: 22, fontSize: 13.5 }}>
              Consulte a equipa sobre lotação, comodidades e disponibilidade da viatura pretendida.
            </p>
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
                </div>
              </div>
            </Reveal>
          </div>
        </section>

        {/* FAQ */}
        <section className="bzlp-sec alt" id="faq">
          <div className="bzlp-wrap" style={{ maxWidth: 820 }}>
            <Reveal>
              <div className="bzlp-sechead">
                <div className="bzlp-kicker">Perguntas frequentes</div>
                <h2 className="bzlp-h2">Antes de partir</h2>
              </div>
            </Reveal>
            <div className="tpm-faq">
              <details>
                <summary>Como posso comprar um bilhete?</summary>
                <p>
                  Clique em <Link to="/comprar" className="bzlp-ghost" style={{ padding: 0, minHeight: 0, color: "var(--blue)" }}>Comprar bilhete</Link>,
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
                  Abra a <Link to="/baixar" style={{ color: "var(--blue)", fontWeight: 600 }}>página oficial de instalação</Link> no
                  seu telemóvel e siga as instruções.
                </p>
              </details>
            </div>
          </div>
        </section>

        {/* CTA + CONTACTOS */}
        <section className="tpm-cta-final" id="contacto">
          <div className="tpm-cta-final-in">
            <div>
              <h2>Qual é o seu próximo destino?</h2>
              <p>A viagem começa com uma conversa — ou com um bilhete.</p>
            </div>
            <div className="bzlp-cta-btns">
              <Link to="/comprar" className="bzlp-btn"><Ticket size={17} aria-hidden /> Comprar bilhete</Link>
              <a href={`mailto:${EMAIL}?subject=${encodeURIComponent("Pedido de orçamento TPM-TUR")}`} className="bzlp-btn outline">
                Pedir orçamento <ArrowUpRight size={16} aria-hidden />
              </a>
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
      </main>

      <footer className="bzlp-foot">
        <div className="bzlp-foot-in">
          <div className="bzlp-foot-brand">
            <img src={LOGO_ESCURO} alt="TPM-TUR, S.A." height={30} style={{ display: "block" }} />
            <p>
              Empresa moçambicana de transporte e turismo. Ligamos pessoas
              aos seus destinos — passageiros, empresas e grupos.
            </p>
          </div>
          <div className="bzlp-foot-cols">
            <nav aria-label="Viagens">
              <h4>Viagens</h4>
              <Link to="/comprar">Comprar bilhete</Link>
              <Link to="/baixar">App do passageiro</Link>
              <Link to="/login">Entrar no portal</Link>
            </nav>
            <nav aria-label="Empresa">
              <h4>Empresa</h4>
              <a href="#servicos">Serviços</a>
              <a href="#frota">Frota</a>
              <a href="#sobre">Sobre a TPM-TUR</a>
            </nav>
            <nav aria-label="Contactos">
              <h4>Contactos</h4>
              <a href={`mailto:${EMAIL}`}>{EMAIL}</a>
              <a href={TELEFONE_HREF}>{TELEFONE}</a>
              <a href="https://updigital.co.mz" target="_blank" rel="noreferrer">UpDigital</a>
            </nav>
          </div>
        </div>
        <div className="bzlp-foot-bar">
          © {new Date().getFullYear()} TPM-TUR, S.A. · Transporte e Turismo. Tecnologia BusUp · UpDigital.
        </div>
      </footer>
    </div>
  );
}
