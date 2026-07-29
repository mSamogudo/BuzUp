import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, CheckCircle2, Download, Menu, Ticket, X,
} from "lucide-react";
import { useBranding, pickLogo } from "../lib/branding";
import Reveal from "./landing/Reveal";
import { useLandingMeta } from "./landing/useLandingMeta";
import ServiceRequestForm from "./landing/ServiceRequestForm";
import {
  ADDRESS, AUDIENCES, BENEFITS, ECOSYSTEM, MODULES, NAV,
  PLATFORM_PILLS, SALES_EMAIL, SALES_PHONE, SALES_PHONE_HREF, SECURITY_POINTS, STATS, TOOLS,
} from "./landing/landing-content";
import "./landing/landing.css";

function Wordmark({ url, alt, height = 30 }: { url: string; alt: string; height?: number }) {
  if (url) return <img src={url} alt={alt} style={{ height, display: "block" }} />;
  return (
    <span style={{ fontWeight: 800, fontSize: height * 0.8, letterSpacing: "-0.02em" }}>
      Bus<span style={{ color: "#2D8CF0" }}>Up</span>
    </span>
  );
}

/** Imagem de produto: dimensões intrínsecas (zero CLS), lazy excepto o hero. */
function ProductImg({ src, alt, width, height, eager = false }: {
  src: string; alt: string; width: number; height: number; eager?: boolean;
}) {
  return (
    <img
      src={src} alt={alt} width={width} height={height}
      loading={eager ? "eager" : "lazy"}
      decoding={eager ? "sync" : "async"}
      fetchPriority={eager ? "high" : undefined}
    />
  );
}

export default function LandingPage() {
  const { branding } = useBranding();
  // Duas variantes: a barra é clara (logo de tinta escura) e o rodapé é
  // navy (logo em branco). Usar a mesma nas duas fazia sumir o "BUS".
  const lightBgLogo = pickLogo(branding.primary_logo_url, "/assets/tpm-tur-logo/tpm_light.png");
  const darkBgLogo = pickLogo(branding.sidebar_logo_url, "/assets/tpm-tur-logo/tpm_dark.png");
  useLandingMeta();

  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [active, setActive] = useState("");
  const burgerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const io = new IntersectionObserver(
      (entries) => { for (const e of entries) if (e.isIntersecting) setActive(e.target.id); },
      { rootMargin: "-88px 0px -65% 0px" },
    );
    for (const { id } of NAV) {
      const el = document.getElementById(id);
      if (el) io.observe(el);
    }
    return () => io.disconnect();
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

  return (
    <div className="bzlp">
      <a className="bzlp-skip" href="#conteudo">Saltar para o conteúdo</a>

      <header className={`bzlp-nav${scrolled ? " is-scrolled" : ""}`}>
        <div className="bzlp-nav-in">
          <Link to="/" aria-label="BusUp — início"><Wordmark url={lightBgLogo} alt="BusUp" height={28} /></Link>
          <nav className="bzlp-links" aria-label="Navegação principal">
            {NAV.map((n) => (
              <a key={n.id} href={`#${n.id}`} aria-current={active === n.id ? "location" : undefined}>{n.label}</a>
            ))}
          </nav>
          <div className="bzlp-nav-cta">
            <Link to="/login" className="bzlp-ghost">Entrar</Link>
            <Link to="/comprar" className="bzlp-btn sm"><Ticket size={16} aria-hidden /> Comprar bilhete</Link>
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
              <Wordmark url={lightBgLogo} alt="BusUp" height={24} />
              <button className="bzlp-sheet-close" aria-label="Fechar menu" onClick={() => setMenuOpen(false)}>
                <X size={24} aria-hidden />
              </button>
            </div>
            {NAV.map((n) => (
              <a key={n.id} href={`#${n.id}`} onClick={() => setMenuOpen(false)}>{n.label}</a>
            ))}
            <Link to="/login" onClick={() => setMenuOpen(false)}>Entrar no portal</Link>
            <Link to="/comprar" className="bzlp-btn" onClick={() => setMenuOpen(false)}>
              <Ticket size={18} aria-hidden /> Comprar bilhete
            </Link>
          </div>
        </div>
      )}

      <main id="conteudo">
        {/* HERO */}
        <section className="bzlp-hero">
          <div className="bzlp-hero-in">
            <div className="bzlp-hero-txt">
              <span className="bzlp-badge">Bilhética digital · Moçambique</span>
              <h1>Bilhetes, frota e receita<br /><span>numa só plataforma.</span></h1>
              <p>
                O <b>BusUp</b> digitaliza a venda e a validação de bilhetes no transporte de passageiros —
                do bairro à viagem internacional. O passageiro compra no telemóvel ou no agente;
                o operador vê <b>cada viagem e cada metical</b>, em tempo real.
              </p>
              <div className="bzlp-hero-cta">
                <Link to="/comprar" className="bzlp-btn"><Ticket size={18} aria-hidden /> Comprar bilhete</Link>
                <a href={`mailto:${SALES_EMAIL}`} className="bzlp-btn outline light">
                  Falar com vendas <ArrowRight size={16} aria-hidden />
                </a>
              </div>
              <div className="bzlp-chips">
                <span><b>QR</b> no telemóvel</span>
                <span><b>Cartão NFC</b></span>
                <span><b>M-Pesa</b></span>
                <span><b>e-Mola</b></span>
              </div>
            </div>
            <div className="bzlp-hero-art">
              <ProductImg
                src="/landing/hero-all.webp"
                alt="Plataforma BusUp: autocarro, portal de gestão, terminal POS e app do passageiro"
                width={1003} height={1052} eager
              />
            </div>
          </div>
        </section>

        <div className="bzlp-stats">
          <div className="bzlp-stats-in">
            {STATS.map((s) => (
              <div className="bzlp-stat" key={s.l}><b>{s.v}</b><span>{s.l}</span></div>
            ))}
          </div>
        </div>

        {/* PRODUTO / benefícios */}
        <section className="bzlp-sec" id="produto">
          <div className="bzlp-wrap">
            <Reveal>
              <div className="bzlp-sechead">
                <div className="bzlp-kicker">O que o BusUp resolve</div>
                <h2 className="bzlp-h2">Menos dinheiro na mão. Mais controlo na operação.</h2>
                <p className="bzlp-lead">
                  Substitui o dinheiro vivo por pagamento digital e dá ao operador a informação que
                  hoje se perde entre o passageiro e a tesouraria.
                </p>
              </div>
            </Reveal>
            <div className="bzlp-benefits">
              {BENEFITS.map((b, i) => (
                <Reveal key={b.title} delay={i * 60}>
                  <div className="bzlp-benefit">
                    <div className="bzlp-bi"><b.icon size={21} aria-hidden /></div>
                    <h3>{b.title}</h3>
                    <p>{b.text}</p>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* COMO FUNCIONA — mostrado, não descrito */}
        <section className="bzlp-sec alt" id="como-funciona">
          <div className="bzlp-wrap">
            <Reveal>
              <div className="bzlp-sechead">
                <div className="bzlp-kicker">Como funciona</div>
                <h2 className="bzlp-h2">Veja o produto a trabalhar.</h2>
              </div>
            </Reveal>

            <Reveal>
              <div className="bzlp-row">
                <div className="bzlp-row-media">
                  <ProductImg src="/landing/compra.webp" alt="Compra de bilhete online com escolha de lugar"
                    width={1400} height={900} />
                </div>
                <div>
                  <div className="bzlp-kicker left">Passo 1 · Comprar</div>
                  <h3>Escolhe o dia, a partida e o lugar.</h3>
                  <p>No site ou na app, em menos de um minuto.</p>
                  <ul className="bzlp-facts">
                    <li><CheckCircle2 size={17} aria-hidden /> Partidas com semanas de antecedência</li>
                    <li><CheckCircle2 size={17} aria-hidden /> Planta do autocarro com lugares livres</li>
                    <li><CheckCircle2 size={17} aria-hidden /> Pagamento M-Pesa ou e-Mola</li>
                  </ul>
                </div>
              </div>
            </Reveal>

            <Reveal>
              <div className="bzlp-row flip">
                <div className="bzlp-row-media">
                  <ProductImg src="/landing/bilhete.webp" alt="Bilhete BusUp em PDF com QR e dados do passageiro"
                    width={1400} height={900} />
                </div>
                <div>
                  <div className="bzlp-kicker left">Passo 2 · Receber</div>
                  <h3>O bilhete chega ao telemóvel.</h3>
                  <p>PDF nominal com QR, lugar e hora de partida. Também por SMS.</p>
                </div>
              </div>
            </Reveal>

            <Reveal>
              <div className="bzlp-row">
                <div className="bzlp-row-media">
                  <img src="/landing/bordo-anim.webp" alt="Agente a vender e validar no terminal POS"
                    width={760} height={900} loading="lazy" decoding="async" />
                </div>
                <div>
                  <div className="bzlp-live"><i aria-hidden />App real</div>
                  <div className="bzlp-kicker left">Passo 3 · Embarcar</div>
                  <h3>O agente valida em segundos.</h3>
                  <p>QR ou cartão NFC no terminal. Sem smartphone? Compra ali mesmo.</p>
                </div>
              </div>
            </Reveal>

            <Reveal>
              <div className="bzlp-row flip">
                <div className="bzlp-row-media">
                  <img src="/landing/mapa-anim.webp" alt="Autocarro a mover-se no mapa em tempo real"
                    width={760} height={900} loading="lazy" decoding="async" />
                </div>
                <div>
                  <div className="bzlp-live"><i aria-hidden />GPS real</div>
                  <div className="bzlp-kicker left">Passo 4 · Seguir</div>
                  <h3>O autocarro no mapa, ao vivo.</h3>
                  <p>Quando o motorista inicia a viagem, o passageiro vê onde ele está.</p>
                </div>
              </div>
            </Reveal>
          </div>
        </section>

        {/* MÓDULOS — hairline matrix */}
        <section className="bzlp-sec">
          <div className="bzlp-wrap">
            <Reveal>
              <div className="bzlp-sechead">
                <div className="bzlp-kicker">Funcionalidades</div>
                <h2 className="bzlp-h2">Tudo o que a operação precisa.</h2>
              </div>
            </Reveal>
            <Reveal>
              <div className="bzlp-matrix">
                {MODULES.map((m) => (
                  <div className="bzlp-cell" key={m.title}>
                    <div className="bzlp-cell-ico"><m.icon size={19} aria-hidden /></div>
                    <h3>{m.title}</h3>
                    <p>{m.text}</p>
                  </div>
                ))}
              </div>
            </Reveal>
          </div>
        </section>

        {/* PLATAFORMA */}
        <section className="bzlp-sec alt" id="plataforma">
          <div className="bzlp-wrap">
            <div className="bzlp-platform">
              <Reveal>
                <div className="bzlp-shot">
                  <ProductImg src="/landing/portal.webp" alt="Portal de gestão BusUp: receita, rotas e frota"
                    width={1400} height={697} />
                </div>
              </Reveal>
              <Reveal delay={80}>
                <div>
                  <div className="bzlp-kicker left">Portal de gestão</div>
                  <h2 className="bzlp-h2 left">A operação inteira num ecrã.</h2>
                  <p className="bzlp-lead left">
                    Receita do dia, rotas, horários, frota, agentes e terminais. Com relatórios
                    exportáveis e registo de auditoria de ponta a ponta.
                  </p>
                  <div className="bzlp-pills">
                    {PLATFORM_PILLS.map((p) => <span key={p}>{p}</span>)}
                  </div>
                </div>
              </Reveal>
            </div>
          </div>
        </section>

        {/* SEGURANÇA — drench */}
        <section className="bzlp-drench">
          <div className="bzlp-wrap bzlp-drench-in">
            <Reveal>
              <div>
                <div className="bzlp-kicker left light">Confiança</div>
                <h2>A receita deixa de depender de confiança.</h2>
                <p>
                  Cada bilhete, validação e recarga fica registado com autor, terminal e hora.
                  O que antes era palavra passa a ser dado auditável.
                </p>
              </div>
            </Reveal>
            <div className="bzlp-checks">
              {SECURITY_POINTS.map((p, i) => (
                <Reveal key={p} delay={i * 45}>
                  <div className="bzlp-check">
                    <CheckCircle2 size={19} aria-hidden />
                    <span>{p}</span>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* SOLUÇÕES */}
        <section className="bzlp-sec" id="solucoes">
          <div className="bzlp-wrap">
            <Reveal>
              <div className="bzlp-sechead">
                <div className="bzlp-kicker">Para quem é</div>
                <h2 className="bzlp-h2">Feito para quem move pessoas.</h2>
                <p className="bzlp-lead">
                  Operadores privados, empresas e instituições — a mesma plataforma, configurada
                  para a realidade de cada frota.
                </p>
              </div>
            </Reveal>
            <div className="bzlp-aud">
              {AUDIENCES.map((a, i) => (
                <Reveal key={a.name} delay={i * 60}>
                  <div className="bzlp-aud-card">
                    <div className="bzlp-aud-ico"><a.icon size={21} aria-hidden /></div>
                    <h3>{a.name}</h3>
                    <p>{a.text}</p>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* FERRAMENTAS */}
        <section className="bzlp-sec alt" id="apps">
          <div className="bzlp-wrap">
            <Reveal>
              <div className="bzlp-sechead">
                <div className="bzlp-kicker">Uma plataforma, três ferramentas</div>
                <h2 className="bzlp-h2">Do passageiro à direcção — tudo ligado.</h2>
              </div>
            </Reveal>
            <div className="bzlp-tools">
              {TOOLS.map((t, i) => (
                <Reveal key={t.name} delay={i * 70}>
                  <div className="bzlp-tool">
                    <div className="bzlp-tool-head">
                      <div className="bzlp-ti"><t.icon size={25} aria-hidden /></div>
                      <div>
                        <h3>{t.name}</h3>
                        <span>{t.tag}</span>
                      </div>
                    </div>
                    <ul>{t.items.map((i2) => <li key={i2}>{i2}</li>)}</ul>
                  </div>
                </Reveal>
              ))}
            </div>
            <div style={{ textAlign: "center", marginTop: 32 }}>
              <Link to="/baixar" className="bzlp-btn outline"><Download size={18} aria-hidden /> Descarregar as aplicações</Link>
            </div>
          </div>
        </section>

        {/* ECOSSISTEMA */}
        <section className="bzlp-sec" id="ecossistema">
          <div className="bzlp-wrap">
            <Reveal>
              <div className="bzlp-sechead">
                <div className="bzlp-kicker">Ecossistema UpDigital</div>
                <h2 className="bzlp-h2">O BusUp não anda sozinho.</h2>
                <p className="bzlp-lead">
                  Faz parte de uma família de produtos que já opera em Moçambique — pagamentos,
                  tesouraria, mobilidade e controlo de acessos.
                </p>
              </div>
            </Reveal>
            <div className="bzlp-eco">
              {ECOSYSTEM.map((e, i) => (
                <Reveal key={e.name} delay={i * 45}>
                  <div className="bzlp-eco-card">
                    <b>{e.name}</b>
                    <span>{e.text}</span>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* CTA + contactos */}
        <section className="bzlp-cta" id="contacto">
          <div className="bzlp-wrap">
            <div className="bzlp-cta-in">
              <div>
                <h2>Leve o BusUp para a sua frota.</h2>
                <p>Marcamos uma demonstração e mostramos a plataforma a operar com os seus dados.</p>
              </div>
              <div className="bzlp-cta-btns">
                <a href={`mailto:${SALES_EMAIL}`} className="bzlp-btn white">Falar com vendas</a>
                <Link to="/comprar" className="bzlp-btn outline light">
                  <Ticket size={17} aria-hidden /> Comprar bilhete
                </Link>
              </div>
            </div>
            <div className="bzlp-contact">
              <div className="bzlp-contact-card">
                <small>Comercial</small>
                <a href={`mailto:${SALES_EMAIL}`}>{SALES_EMAIL}</a>
                <a href={`tel:${SALES_PHONE_HREF}`}>{SALES_PHONE}</a>
              </div>
              <div className="bzlp-contact-card">
                <small>Endereço</small>
                <span>{ADDRESS}</span>
              </div>
              <div className="bzlp-contact-card">
                <small>Website</small>
                <a href="https://updigital.co.mz" target="_blank" rel="noreferrer">updigital.co.mz</a>
                <a href="https://busup.updigital.co.mz">busup.updigital.co.mz</a>
              </div>
            </div>
          </div>
        </section>

        {/* PEDIDO DE CONTACTO */}
        <section className="bzlp-sec" id="pedido">
          <div className="bzlp-wrap">
            <div className="bzlp-contact-split">
              <Reveal>
                <div>
                  <div className="bzlp-kicker left">Fale connosco</div>
                  <h2 className="bzlp-h2 left">Vamos ver isto na sua operação.</h2>
                  <p className="bzlp-lead left">
                    Preenchemos a plataforma com as suas rotas e horários e mostramos o fluxo
                    completo — venda, embarque e fecho de contas.
                  </p>
                  <ul className="bzlp-facts" style={{ marginTop: 22 }}>
                    <li><CheckCircle2 size={17} aria-hidden /> Demonstração com os seus dados</li>
                    <li><CheckCircle2 size={17} aria-hidden /> Instalação sem obra na frota</li>
                    <li><CheckCircle2 size={17} aria-hidden /> Suporte local em Moçambique</li>
                  </ul>
                </div>
              </Reveal>
              <Reveal delay={80}>
                <ServiceRequestForm />
              </Reveal>
            </div>
          </div>
        </section>
      </main>

      <footer className="bzlp-foot">
        <div className="bzlp-foot-in">
          <div className="bzlp-foot-brand">
            <Wordmark url={darkBgLogo} alt="BusUp" height={26} />
            <p>Plataforma de bilhética digital para o transporte de passageiros. Desenvolvido em Moçambique.</p>
          </div>
          <div className="bzlp-foot-cols">
            <nav aria-label="Produto">
              <h4>Produto</h4>
              <a href="#produto">Funcionalidades</a>
              <a href="#plataforma">Portal de gestão</a>
              <Link to="/comprar">Comprar bilhete</Link>
              <Link to="/baixar">Descarregar apps</Link>
            </nav>
            <nav aria-label="Acesso">
              <h4>Acesso</h4>
              <Link to="/login">Portal de gestão</Link>
              <Link to="/baixar">App Passageiro</Link>
              <Link to="/baixar">App POS</Link>
            </nav>
            <nav aria-label="Contacto">
              <h4>Contacto</h4>
              <a href={`mailto:${SALES_EMAIL}`}>{SALES_EMAIL}</a>
              <a href={`tel:${SALES_PHONE_HREF}`}>{SALES_PHONE}</a>
              <a href="https://updigital.co.mz" target="_blank" rel="noreferrer">updigital.co.mz</a>
            </nav>
          </div>
        </div>
        <div className="bzlp-foot-bar">© {new Date().getFullYear()} BusUp · UpDigital. Todos os direitos reservados.</div>
      </footer>
    </div>
  );
}
