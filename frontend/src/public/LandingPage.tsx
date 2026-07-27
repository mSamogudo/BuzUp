import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Wallet, ScanLine, CreditCard, BarChart3, ShieldCheck, Users,
  Smartphone, Store, LayoutDashboard, Bus, Download, ArrowRight,
  CheckCircle2, TrendingUp, Route as RouteIcon, RefreshCw, Banknote,
  Menu, X, MapPin,
} from "lucide-react";
import { useBranding, pickLogo } from "../lib/branding";
import Reveal from "./landing/Reveal";
import { useLandingMeta } from "./landing/useLandingMeta";
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
      src={src}
      alt={alt}
      width={width}
      height={height}
      loading={eager ? "eager" : "lazy"}
      decoding={eager ? "sync" : "async"}
      fetchPriority={eager ? "high" : undefined}
    />
  );
}

const NAV = [
  { id: "funcionalidades", label: "Funcionalidades" },
  { id: "produto", label: "Produto" },
  { id: "apps", label: "Aplicações" },
  { id: "municipios", label: "Municípios" },
];

const STATS = [
  { v: "3", l: "canais de venda e validação" },
  { v: "2", l: "carteiras móveis: M-Pesa e e-Mola" },
  { v: "100%", l: "da receita registada e auditável" },
  { v: "0", l: "obras — funciona na frota actual" },
];

const BENEFITS = [
  { icon: Banknote, title: "Fim do dinheiro na mão", text: "Sem troco nem notas a circular. Menos furtos, menos erros e mais higiene a bordo." },
  { icon: TrendingUp, title: "Receita 100% rastreável", text: "Cada bilhete fica registado. Combate direto à evasão de receita e ao desvio de fundos." },
  { icon: BarChart3, title: "Dados para decidir", text: "Fluxo de passageiros por rota, horário e veículo — informação real para planear o transporte." },
  { icon: Users, title: "Inclusão de todos", text: "Quem não tem smartphone usa um cartão recarregável. Ninguém fica de fora do sistema." },
];

const STEPS = [
  { icon: Wallet, title: "1. Carrega saldo", text: "O passageiro carrega a carteira por M-Pesa ou e-Mola — no telemóvel ou num agente." },
  { icon: ScanLine, title: "2. Embarca", text: "Mostra o QR Code ou aproxima o cartão NFC. O agente valida num segundo." },
  { icon: CheckCircle2, title: "3. Viaja", text: "O bilhete é debitado na hora e a viagem fica registada no sistema." },
];

const SHOTS = [
  { src: "/landing/ticket.webp", caption: "Bilhete QR no telemóvel, validado à porta do autocarro" },
  { src: "/landing/pos.webp", caption: "Terminal POS do agente e do motorista, com NFC e impressão" },
  { src: "/landing/phone.webp", caption: "App do passageiro: carteira, recargas e mapa em tempo real" },
];

const TOOLS = [
  {
    icon: Smartphone, name: "App Passageiro", tag: "Android · telemóvel",
    items: ["Carteira digital em Meticais", "Recarga M-Pesa e e-Mola", "Bilhete por QR Code", "Mapa dos autocarros em tempo real"],
  },
  {
    icon: Store, name: "App POS", tag: "Agente / Motorista",
    items: ["Venda e validação de bilhetes", "Leitura QR + cartão NFC", "Início e fecho de viagens", "Terminais SUNMI / Urovo"],
  },
  {
    icon: LayoutDashboard, name: "Portal de Gestão", tag: "Município / Operador",
    items: ["Rotas, viagens e frota", "Motoristas e passageiros", "Relatórios PDF de receita", "Auditoria e segurança"],
  },
];

const CITY = [
  "Transparência total — receita do transporte auditável ao cêntimo.",
  "Combate à corrupção — o dinheiro deixa de passar de mão em mão.",
  "Imagem inovadora — a cidade referência em transporte digital.",
  "Relatórios oficiais — mapas de receita e uso prontos a exportar.",
  "Rápido de implementar — funciona nos autocarros atuais, sem obra.",
  "Feito em Moçambique — suporte local e pagamentos nacionais.",
];

const FEATURES = [
  { icon: Banknote, label: "Pagamento cashless" },
  { icon: ScanLine, label: "Bilhete por QR Code" },
  { icon: CreditCard, label: "Cartão NFC recarregável" },
  { icon: Wallet, label: "Recarga M-Pesa / e-Mola" },
  { icon: MapPin, label: "Rastreio da frota no mapa" },
  { icon: BarChart3, label: "Relatórios em tempo real" },
  { icon: ShieldCheck, label: "Auditoria e segurança" },
  { icon: RouteIcon, label: "Gestão de rotas e viagens" },
  { icon: Bus, label: "Frota e livrete de veículos" },
  { icon: RefreshCw, label: "Atualização remota das apps" },
];

export default function LandingPage() {
  const { branding } = useBranding();
  const darkLogo = pickLogo(branding.sidebar_logo_url, branding.primary_logo_url);
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

  // Scroll-spy: sublinha na nav a secção visível.
  useEffect(() => {
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) if (e.isIntersecting) setActive(e.target.id);
      },
      { rootMargin: "-88px 0px -65% 0px" },
    );
    for (const { id } of NAV) {
      const el = document.getElementById(id);
      if (el) io.observe(el);
    }
    return () => io.disconnect();
  }, []);

  // Menu mobile: Escape fecha, scroll fica bloqueado, foco volta ao botão.
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

      {/* HEADER */}
      <header className={`bzlp-nav${scrolled ? " is-scrolled" : ""}`}>
        <div className="bzlp-nav-in">
          <Link to="/" className="bzlp-logo"><Wordmark url={darkLogo} alt="BusUp" height={28} /></Link>
          <nav className="bzlp-links" aria-label="Navegação principal">
            {NAV.map((n) => (
              <a key={n.id} href={`#${n.id}`} aria-current={active === n.id ? "location" : undefined}>
                {n.label}
              </a>
            ))}
          </nav>
          <div className="bzlp-nav-cta">
            <Link to="/login" className="bzlp-ghost">Entrar</Link>
            <Link to="/baixar" className="bzlp-btn sm"><Download size={16} aria-hidden /> Baixar app</Link>
            <button ref={burgerRef} className="bzlp-burger" aria-label="Abrir menu" onClick={() => setMenuOpen(true)}>
              <Menu size={24} aria-hidden />
            </button>
          </div>
        </div>
      </header>

      {/* MENU MOBILE */}
      {menuOpen && (
        <div className="bzlp-sheet" onClick={() => setMenuOpen(false)}>
          <div className="bzlp-sheet-panel" onClick={(e) => e.stopPropagation()}>
            <div className="bzlp-sheet-head">
              <Wordmark url={darkLogo} alt="BusUp" height={24} />
              <button className="bzlp-sheet-close" aria-label="Fechar menu" onClick={() => setMenuOpen(false)}>
                <X size={24} aria-hidden />
              </button>
            </div>
            {NAV.map((n) => (
              <a key={n.id} href={`#${n.id}`} onClick={() => setMenuOpen(false)}>{n.label}</a>
            ))}
            <Link to="/login" onClick={() => setMenuOpen(false)}>Entrar no portal</Link>
            <Link to="/baixar" className="bzlp-btn" onClick={() => setMenuOpen(false)}>
              <Download size={18} aria-hidden /> Baixar aplicação
            </Link>
          </div>
        </div>
      )}

      <main id="conteudo">
        {/* HERO */}
        <section className="bzlp-hero">
          <div className="bzlp-hero-in">
            <div className="bzlp-hero-txt">
              <span className="bzlp-badge">Transporte público · Cashless</span>
              <h1>O transporte da sua cidade,<br /><span>agora sem dinheiro físico.</span></h1>
              <p>O <b>BusUp</b> digitaliza o pagamento nos autocarros e chapas. O passageiro paga com o
                telemóvel ou cartão — <b>sem troco, sem filas, sem perdas</b> — e o município passa a ver,
                em tempo real, cada viagem e cada metical.</p>
              <div className="bzlp-hero-cta">
                <Link to="/baixar" className="bzlp-btn"><Download size={18} aria-hidden /> Baixar aplicação</Link>
                <a href="#funcionalidades" className="bzlp-btn outline">Ver funcionalidades <ArrowRight size={16} aria-hidden /></a>
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
                width={1003}
                height={1052}
                eager
              />
            </div>
          </div>
        </section>

        {/* NÚMEROS */}
        <div className="bzlp-stats">
          <div className="bzlp-stats-in">
            {STATS.map((s) => (
              <div className="bzlp-stat" key={s.l}><b>{s.v}</b><span>{s.l}</span></div>
            ))}
          </div>
        </div>

        {/* BENEFITS */}
        <section className="bzlp-sec" id="funcionalidades">
          <div className="bzlp-wrap">
            <Reveal>
              <div className="bzlp-kicker">O QUE O BUSUP RESOLVE</div>
              <h2 className="bzlp-h2">Menos dinheiro na mão. Mais controlo na cidade.</h2>
            </Reveal>
            <div className="bzlp-benefits">
              {BENEFITS.map((b, i) => (
                <Reveal key={b.title} delay={i * 60}>
                  <div className="bzlp-benefit">
                    <div className="bzlp-bi"><b.icon size={22} aria-hidden /></div>
                    <h3>{b.title}</h3>
                    <p>{b.text}</p>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* HOW */}
        <section className="bzlp-sec alt">
          <div className="bzlp-wrap">
            <Reveal>
              <div className="bzlp-kicker">COMO FUNCIONA</div>
              <h2 className="bzlp-h2">Três passos. Uma viagem sem atrito.</h2>
            </Reveal>
            <div className="bzlp-steps">
              {STEPS.map((s, i) => (
                <Reveal key={s.title} delay={i * 80}>
                  <div className="bzlp-step">
                    <div className="bzlp-si"><s.icon size={26} aria-hidden /></div>
                    <h3>{s.title}</h3>
                    <p>{s.text}</p>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* PRODUTO EM ACÇÃO */}
        <section className="bzlp-sec" id="produto">
          <div className="bzlp-wrap">
            <Reveal>
              <div className="bzlp-kicker">PRODUTO REAL, EM OPERAÇÃO</div>
              <h2 className="bzlp-h2">Do bilhete no telemóvel ao terminal a bordo.</h2>
            </Reveal>
            <div className="bzlp-shots">
              {SHOTS.map((s, i) => (
                <Reveal key={s.src} delay={i * 80}>
                  <figure className="bzlp-shot">
                    <ProductImg src={s.src} alt={s.caption} width={1000} height={1250} />
                    <figcaption>{s.caption}</figcaption>
                  </figure>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* APPS */}
        <section className="bzlp-sec alt" id="apps">
          <div className="bzlp-wrap">
            <Reveal>
              <div className="bzlp-kicker">UMA PLATAFORMA, TRÊS FERRAMENTAS</div>
              <h2 className="bzlp-h2">Do passageiro ao gestor — tudo ligado.</h2>
            </Reveal>
            <div className="bzlp-tools">
              {TOOLS.map((t, i) => (
                <Reveal key={t.name} delay={i * 80}>
                  <div className="bzlp-tool">
                    <div className="bzlp-tool-head">
                      <div className="bzlp-ti"><t.icon size={26} aria-hidden /></div>
                      <div>
                        <h3>{t.name}</h3>
                        <span>{t.tag}</span>
                      </div>
                    </div>
                    <ul>
                      {t.items.map((i2) => <li key={i2}>{i2}</li>)}
                    </ul>
                  </div>
                </Reveal>
              ))}
            </div>
            <div className="bzlp-tools-cta">
              <Link to="/baixar" className="bzlp-btn"><Download size={18} aria-hidden /> Descarregar as aplicações</Link>
            </div>
          </div>
        </section>

        {/* MUNICÍPIOS */}
        <section className="bzlp-city" id="municipios">
          <div className="bzlp-wrap">
            <div className="bzlp-city-in">
              <Reveal>
                <div className="bzlp-city-txt">
                  <div className="bzlp-kicker light">PARA O SEU MUNICÍPIO</div>
                  <h2>Uma cidade mais moderna, transparente e eficiente.</h2>
                  <p>Modernize o transporte urbano, aumente a receita e ofereça aos cidadãos uma viagem mais
                    simples e digna — com controlo total nas suas mãos.</p>
                </div>
              </Reveal>
              <div className="bzlp-city-list">
                {CITY.map((c, i) => {
                  const [b, ...rest] = c.split(" — ");
                  return (
                    <Reveal key={c} delay={i * 50}>
                      <div className="bzlp-city-item">
                        <span className="bzlp-tick"><CheckCircle2 size={18} aria-hidden /></span>
                        <span><b>{b}</b>{rest.length ? ` — ${rest.join(" — ")}` : ""}</span>
                      </div>
                    </Reveal>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        {/* FEATURES GRID */}
        <section className="bzlp-sec alt">
          <div className="bzlp-wrap">
            <Reveal>
              <div className="bzlp-kicker">TUDO O QUE O BUSUP FAZ</div>
              <h2 className="bzlp-h2">Funcionalidades numa só plataforma.</h2>
            </Reveal>
            <div className="bzlp-feats">
              {FEATURES.map((f, i) => (
                <Reveal key={f.label} delay={i * 40}>
                  <div className="bzlp-feat">
                    <div className="bzlp-fi"><f.icon size={20} aria-hidden /></div>
                    <span>{f.label}</span>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="bzlp-cta">
          <div className="bzlp-wrap bzlp-cta-in">
            <div>
              <h2>Traga o BusUp para o seu município.</h2>
              <p>Comece hoje: descarregue as aplicações ou fale connosco para uma demonstração.</p>
            </div>
            <div className="bzlp-cta-btns">
              <Link to="/baixar" className="bzlp-btn white"><Download size={18} aria-hidden /> Baixar app</Link>
              <a href="mailto:comercial@updigital.co.mz" className="bzlp-btn outline light">
                Falar connosco <ArrowRight size={16} aria-hidden />
              </a>
            </div>
          </div>
        </section>
      </main>

      {/* FOOTER */}
      <footer className="bzlp-foot">
        <div className="bzlp-wrap bzlp-foot-in">
          <div className="bzlp-foot-brand">
            <Wordmark url={darkLogo} alt="BusUp" height={26} />
            <p>Plataforma de bilhética cashless para transporte público. Desenvolvido em Moçambique.</p>
          </div>
          <div className="bzlp-foot-cols">
            <nav aria-label="Produto">
              <h4>Produto</h4>
              <a href="#funcionalidades">Funcionalidades</a>
              <a href="#apps">Aplicações</a>
              <Link to="/baixar">Descarregar</Link>
            </nav>
            <nav aria-label="Acesso">
              <h4>Acesso</h4>
              <Link to="/login">Portal de gestão</Link>
              <Link to="/baixar">App Passageiro</Link>
              <Link to="/baixar">App POS</Link>
            </nav>
            <nav aria-label="Contacto">
              <h4>Contacto</h4>
              <a href="https://updigital.co.mz" target="_blank" rel="noreferrer">updigital.co.mz</a>
              <a href="mailto:comercial@updigital.co.mz">comercial@updigital.co.mz</a>
            </nav>
          </div>
        </div>
        <div className="bzlp-foot-bar">© {new Date().getFullYear()} BusUp · UP Digital. Todos os direitos reservados.</div>
      </footer>
    </div>
  );
}
