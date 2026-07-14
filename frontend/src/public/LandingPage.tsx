import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, Wallet, Ticket, Activity, Timer, Smartphone, Leaf,
  Zap, RefreshCw, ShieldCheck, Users, Briefcase, GraduationCap,
  Bus, Building2, MapPin, Check, Apple, Play, Menu, X,
} from "lucide-react";
import { useUi } from "../ui/UiPreferences";
import { useMkt } from "./site/mkt-i18n";
import { LangToggle } from "./site/LangToggle";
import { BrandLogo } from "./site/BrandLogo";
import { openWaitlist } from "./site/waitlist";
import { Seo } from "../ui/Seo";
import { PAGES, localizedPath, organizationLd, websiteLd, type Lang } from "../lib/seo";
import "./site/buzup-site.css";

export default function LandingPage({ lang = "pt" }: { lang?: Lang }) {
  const { toggleTheme } = useUi();
  const { t } = useMkt(lang);
  const lp = (p: string) => localizedPath(p, lang);
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useLayoutEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    // Content is visible by default. Opt into the hide-then-reveal ONLY on a real,
    // interactive browser — never under react-snap prerender (headless), automation,
    // or when IntersectionObserver is missing — so the static HTML and slow/no-JS
    // clients always ship visible content. Added pre-paint and imperatively (no React
    // re-render) so there's no visible flash and it never clobbers the observer's
    // `.in` classes.
    const ua = typeof navigator !== "undefined" ? navigator.userAgent : "";
    const canReveal =
      typeof window !== "undefined" &&
      !navigator.webdriver &&
      !/HeadlessChrome/i.test(ua) &&
      "IntersectionObserver" in window;
    if (!canReveal) return;
    root.classList.add("js-reveal");
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting) {
            en.target.classList.add("in");
            io.unobserve(en.target);
          }
        });
      },
      { threshold: 0.14, rootMargin: "0px 0px -8% 0px" }
    );
    root.querySelectorAll(".reveal, .step").forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  const close = () => setOpen(false);

  return (
    <div className="bz bz-home" ref={rootRef}>
      <Seo page={PAGES.landing} lang={lang} jsonLd={[organizationLd(), websiteLd()]} />
      <a className="skip-link" href="#main">{t("Saltar para o conteúdo")}</a>
      {/* NAV */}
      <nav className={`nav${scrolled ? " scrolled" : ""}`}>
        <div className="wrap nav-inner">
          <Link to={lp("/")} className="brand" aria-label="BusUp">
            <BrandLogo tone="auto" />
          </Link>
          <div className="nav-links">
            <a href="#funcionalidades">{t("Funcionalidades")}</a>
            <a href="#como-funciona">{t("Como funciona")}</a>
            <a href="#cartao">{t("Cartão")}</a>
            <Link to={lp("/tarifas")}>{t("Tarifas")}</Link>
            <Link to={lp("/contacto")}>{t("Contacto")}</Link>
          </div>
          <div className="nav-cta">
            <div className="nav-tools">
              <button className="ttbtn" onClick={toggleTheme} aria-label="Alternar tema claro/escuro" title="Tema">
                <svg className="ico-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></svg>
                <svg className="ico-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4.2" /><path d="M12 2.5v2M12 19.5v2M4.6 4.6l1.4 1.4M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4" /></svg>
              </button>
              <LangToggle lang={lang} ptPath="/" enPath="/en" />
            </div>
            <Link to="/login" className="btn btn-ghost btn-sm">{t("Entrar")}</Link>
            <button type="button" className="btn btn-primary btn-sm" onClick={openWaitlist}>{t("Baixar a app")}</button>
            <button className="menu-btn" onClick={() => setOpen(true)} aria-label="Abrir menu"><Menu /></button>
          </div>
        </div>
      </nav>

      {/* mobile drawer */}
      <div className={`drawer${open ? " open" : ""}`} onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
        <div className="drawer-panel">
          <div className="row">
            <span className="brand"><BrandLogo tone="auto" /></span>
            <button className="close-btn" onClick={close} aria-label="Fechar menu"><X /></button>
          </div>
          <a href="#funcionalidades" onClick={close}>{t("Funcionalidades")}</a>
          <a href="#como-funciona" onClick={close}>{t("Como funciona")}</a>
          <a href="#cartao" onClick={close}>{t("Cartão")}</a>
          <Link to={lp("/tarifas")} onClick={close}>{t("Tarifas")}</Link>
          <Link to={lp("/contacto")} onClick={close}>{t("Contacto")}</Link>
          <Link to="/login" className="btn btn-ghost" onClick={close}>{t("Entrar")}</Link>
          <button type="button" className="btn btn-primary" onClick={() => { close(); openWaitlist(); }}>{t("Baixar a app")}</button>
        </div>
      </div>

      <span id="top" />

      {/* HERO */}
      <header className="hero" id="main" tabIndex={-1}>
        <div className="wrap hero-grid">
          <div className="hero-copy">
            <span className="eyebrow reveal">{t("Transporte público sem contacto")}</span>
            <h1 className="reveal d1">{t("Pague a sua viagem com um")} <span className="accent">{t("simples toque.")}</span></h1>
            <p className="sub reveal d2">{t("A BusUp é a forma mais rápida e segura de pagar o transporte público em Moçambique. Recarregue, toque e viaje — sem filas, sem trocos, sem papel.")}</p>
            <div className="hero-actions reveal d2">
              <button type="button" className="btn btn-primary" onClick={openWaitlist}>{t("Baixar a app")} <ArrowRight /></button>
              <a href="#como-funciona" className="btn btn-ghost">{t("Ver como funciona")}</a>
            </div>
            <div className="stores reveal d3">
              <button type="button" className="store soon" onClick={openWaitlist} aria-label={`${t("Em breve na")} App Store — ${t("inscreva-se para ser avisado")}`}>
                <Apple />
                <span><small>{t("Em breve na")}</small><strong>App Store</strong></span>
              </button>
              <button type="button" className="store soon" onClick={openWaitlist} aria-label={`${t("Em breve no")} Google Play — ${t("inscreva-se para ser avisado")}`}>
                <Play />
                <span><small>{t("Em breve no")}</small><strong>Google Play</strong></span>
              </button>
            </div>
          </div>
          <div className="hero-visual reveal d2">
            <img src="/assets/buzup/hero-person.png" alt="Agente BusUp apresenta a app e o cartão sem contacto" width={1086} height={1448} decoding="async" {...({ fetchpriority: "high" } as Record<string, string>)} />
          </div>
        </div>
      </header>

      {/* TRUST STRIP */}
      <section className="trust">
        <div className="wrap trust-grid">
          <div className="trust-item reveal">
            <div className="ic"><Timer /></div>
            <div><h4>{t("Menos de 1 segundo")}</h4><p>{t("por validação a bordo, com tecnologia sem contacto.")}</p></div>
          </div>
          <div className="trust-item reveal d1">
            <div className="ic"><Smartphone /></div>
            <div><h4>{t("Recargas 24/7")}</h4><p>{t("adicione saldo a qualquer hora, direto do telemóvel.")}</p></div>
          </div>
          <div className="trust-item reveal d2">
            <div className="ic"><Leaf /></div>
            <div><h4>{t("100% sem papel")}</h4><p>{t("bilhetes digitais e histórico sempre consigo.")}</p></div>
          </div>
        </div>
      </section>

      {/* BENEFITS */}
      <section className="section" id="funcionalidades">
        <div className="wrap">
          <div className="head reveal">
            <h2>{t("Tudo o que a sua viagem precisa, num só toque.")}</h2>
            <p>{t("Uma plataforma completa para passageiros e operadores — do pagamento sem contacto ao controlo em tempo real.")}</p>
          </div>
          <div className="cards">
            <div className="card reveal">
              <div className="ic">
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none"><path d="M6 8.5a8 8 0 0 1 0 7M10 6.5a12 12 0 0 1 0 11M14 4.5a16 16 0 0 1 0 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
              </div>
              <h3>{t("Pagamento sem contacto")}</h3>
              <p>{t("Aproxime o cartão ou o telemóvel do validador e siga viagem em menos de um segundo.")}</p>
            </div>
            <div className="card reveal d1">
              <div className="ic"><Wallet /></div>
              <h3>{t("Recarga instantânea")}</h3>
              <p>{t("Adicione saldo por M-Pesa, e-Mola ou cartão e use de imediato, onde estiver.")}</p>
            </div>
            <div className="card reveal d2">
              <div className="ic"><Ticket /></div>
              <h3>{t("Bilhetes digitais")}</h3>
              <p>{t("Diário, semanal ou mensal. Compre e guarde todos os seus bilhetes na app.")}</p>
            </div>
            <div className="card reveal d3">
              <div className="ic"><Activity /></div>
              <h3>{t("Tudo em tempo real")}</h3>
              <p>{t("Acompanhe saldo, viagens e cada transação ao instante, sem surpresas.")}</p>
            </div>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="section how" id="como-funciona">
        <div className="wrap how-grid">
          <div className="how-visual reveal">
            <img src="/assets/buzup/validator-pole.png" alt="Validador BusUp a confirmar uma viagem válida com cartão sem contacto" width={1086} height={1448} loading="lazy" decoding="async" />
          </div>
          <div className="how-copy">
            <div className="head reveal" style={{ marginBottom: "34px" }}>
              <h2>{t("Comece a viajar em quatro passos.")}</h2>
            </div>
            <div className="steps">
              <div className="step reveal">
                <div className="num">1</div>
                <div><h3>{t("Crie a sua conta")}</h3><p>{t("Descarregue a app BusUp e registe-se em segundos, direto do telemóvel.")}</p></div>
              </div>
              <div className="step reveal d1">
                <div className="num">2</div>
                <div><h3>{t("Recarregue o saldo")}</h3><p>{t("Carregue por M-Pesa, e-Mola, cartão bancário ou nos pontos BusUp.")}</p></div>
              </div>
              <div className="step reveal d2">
                <div className="num">3</div>
                <div><h3>{t("Toque para viajar")}</h3><p>{t("Aproxime o cartão ou o telemóvel do validador a bordo. Viagem válida!")}</p></div>
              </div>
              <div className="step reveal d3">
                <div className="num">4</div>
                <div><h3>{t("Acompanhe tudo")}</h3><p>{t("Veja viagens, saldo e bilhetes em tempo real, sempre na palma da mão.")}</p></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* APP SHOWCASE */}
      <section className="section" id="app">
        <div className="wrap app-grid">
          <div className="app-copy">
            <div className="head reveal" style={{ marginBottom: "6px" }}>
              <h2>{t("Toda a sua mobilidade numa só app.")}</h2>
              <p>{t("Saldo, recargas, bilhetes e histórico — uma experiência simples, rápida e elegante, feita para o dia a dia.")}</p>
            </div>
            <ul className="flist">
              <li className="reveal"><div className="tick"><Check /></div><div><strong>{t("Saldo e recarga rápida")}</strong><span>{t("Veja o saldo disponível e recarregue em poucos toques.")}</span></div></li>
              <li className="reveal d1"><div className="tick"><Check /></div><div><strong>{t("Compra de bilhetes")}</strong><span>{t("Diário, semanal e mensal, sempre disponíveis na app.")}</span></div></li>
              <li className="reveal d2"><div className="tick"><Check /></div><div><strong>{t("Histórico de viagens")}</strong><span>{t("Cada viagem e transação registada, ao detalhe.")}</span></div></li>
              <li className="reveal d3"><div className="tick"><Check /></div><div><strong>{t("Gestão do cartão")}</strong><span>{t("Associe, bloqueie e recarregue o seu cartão físico.")}</span></div></li>
            </ul>
          </div>
          <div className="app-visual reveal d1">
            <img src="/assets/buzup/phone-float.png" alt="App BusUp com saldo, transações e compra de bilhetes" width={1122} height={1402} loading="lazy" decoding="async" />
          </div>
        </div>
      </section>

      {/* CARD SECTION */}
      <section className="section cardsec" id="cartao">
        <div className="wrap cardsec-grid">
          <div className="cardsec-visual reveal">
            <img src="/assets/buzup/validator-card.png" alt="Validador e cartão BusUp sem contacto" width={1122} height={1402} loading="lazy" decoding="async" />
          </div>
          <div className="cardsec-copy">
            <div className="head reveal" style={{ marginBottom: "6px" }}>
              <h2>{t("Sem smartphone? Sem problema.")}</h2>
              <p>{t("O cartão BusUp funciona de forma independente. Recarregue numa agência ou ponto BusUp e viaje com um único toque — acessível a todos os passageiros.")}</p>
            </div>
            <div className="chips">
              <span className="chip reveal"><Zap /> {t("Toque e siga")}</span>
              <span className="chip reveal d1"><RefreshCw /> {t("Recarregável")}</span>
              <span className="chip reveal d2"><ShieldCheck /> {t("Seguro")}</span>
              <span className="chip reveal d3"><Users /> {t("Para toda a família")}</span>
            </div>
            <div style={{ marginTop: "32px" }} className="reveal d2">
              <Link to={lp("/contacto")} className="btn btn-primary">{t("Obter o cartão")} <ArrowRight /></Link>
            </div>
          </div>
        </div>
      </section>

      {/* TARIFAS */}
      <section className="section tarifas" id="tarifas">
        <div className="wrap">
          <div className="head center reveal">
            <h2>{t("Escolha o bilhete certo para si.")}</h2>
            <p>{t("Preços simples e transparentes. Sem taxas escondidas, sem surpresas.")}</p>
          </div>
          <div className="plan-grid">
            <div className="plan reveal">
              <span className="tag">{t("Diário")}</span>
              <div className="price">12,00 <small>MZN</small></div>
              <p className="desc">{t("Viagens ilimitadas durante todo o dia.")}</p>
              <ul>
                <li><Check /> {t("Válido por 24 horas")}</li>
                <li><Check /> {t("Viagens ilimitadas")}</li>
                <li><Check /> {t("Ideal para o dia a dia")}</li>
              </ul>
              <a href="#download" className="btn btn-ghost">{t("Comprar bilhete")}</a>
            </div>
            <div className="plan feat reveal d1">
              <span className="badge">{t("Mais popular")}</span>
              <span className="tag">{t("Semanal")}</span>
              <div className="price">60,00 <small>MZN</small></div>
              <p className="desc">{t("Sete dias de viagens sem preocupações.")}</p>
              <ul>
                <li><Check /> {t("Válido por 7 dias")}</li>
                <li><Check /> {t("Viagens ilimitadas")}</li>
                <li><Check /> {t("Poupe face ao diário")}</li>
              </ul>
              <a href="#download" className="btn btn-white">{t("Comprar bilhete")}</a>
            </div>
            <div className="plan reveal d2">
              <span className="tag">{t("Mensal")}</span>
              <div className="price">180,00 <small>MZN</small></div>
              <p className="desc">{t("Um mês inteiro de mobilidade livre.")}</p>
              <ul>
                <li><Check /> {t("Válido por 30 dias")}</li>
                <li><Check /> {t("Viagens ilimitadas")}</li>
                <li><Check /> {t("Melhor valor por viagem")}</li>
              </ul>
              <a href="#download" className="btn btn-ghost">{t("Comprar bilhete")}</a>
            </div>
          </div>
          <p className="payg reveal d1">{t("Prefere pagar por viagem? A")} <b>{t("viagem avulsa")}</b> {t("custa apenas")} <b>8,00 MZN</b>{t(", debitada do seu saldo a cada validação.")}</p>
        </div>
      </section>

      {/* SEGMENTS */}
      <section className="section" id="segmentos" style={{ background: "var(--soft)" }}>
        <div className="wrap">
          <div className="head center reveal">
            <h2>{t("Feita para toda a cidade em movimento.")}</h2>
          </div>
          <div className="seg-group reveal">
            <h3 className="seg-label">{t("Para passageiros")}</h3>
            <div className="seg-grid">
              <div className="seg reveal"><div className="ic"><Briefcase /></div><div><strong>{t("Trabalhadores")}</strong><span>{t("Deslocações diárias sem filas.")}</span></div></div>
              <div className="seg reveal d1"><div className="ic"><GraduationCap /></div><div><strong>{t("Estudantes")}</strong><span>{t("Tarifas e bilhetes acessíveis.")}</span></div></div>
              <div className="seg reveal d2"><div className="ic"><MapPin /></div><div><strong>{t("Turistas")}</strong><span>{t("Viaje na cidade sem complicações.")}</span></div></div>
              <div className="seg reveal d3"><div className="ic"><Users /></div><div><strong>{t("Famílias")}</strong><span>{t("Vários cartões, uma só conta.")}</span></div></div>
            </div>
          </div>
          <div className="seg-group reveal d1">
            <h3 className="seg-label">{t("Para operadores e cidades")}</h3>
            <div className="seg-grid duo">
              <div className="seg reveal"><div className="ic"><Bus /></div><div><strong>{t("Operadores")}</strong><span>{t("Receitas e frota sob controlo.")}</span></div></div>
              <div className="seg reveal d1"><div className="ic"><Building2 /></div><div><strong>{t("Municípios")}</strong><span>{t("Transporte público modernizado.")}</span></div></div>
            </div>
          </div>
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="cta" id="download">
        <div className="wrap">
          <div className="cta-card reveal">
            <div className="inner">
              <h2>{t("Comece a viajar com a BusUp hoje.")}</h2>
              <p>{t("Junte-se a milhares de passageiros que já trocaram o troco por um simples toque.")}</p>
            </div>
            <div className="cta-actions">
              <button type="button" className="btn btn-white" onClick={openWaitlist}><Apple /> {t("Avisem-me quando abrir (iOS)")}</button>
              <button type="button" className="btn btn-white" onClick={openWaitlist}><Play /> {t("Avisem-me quando abrir (Android)")}</button>
              <Link to={lp("/contacto")} className="btn btn-ghost on-dark">{t("Falar com a equipa BusUp")}</Link>
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer id="contacto">
        <div className="wrap">
          <div className="foot-top">
            <div className="foot-brand">
              <span className="brand">
                <BrandLogo tone="onDark" />
              </span>
              <p>{t("O transporte público de Moçambique, mais rápido, seguro e sem papel.")}</p>
            </div>
            <div className="foot-col">
              <h5>{t("Produto")}</h5>
              <a href="#funcionalidades">{t("Funcionalidades")}</a>
              <a href="#como-funciona">{t("Como funciona")}</a>
              <a href="#cartao">{t("Cartão BusUp")}</a>
              <Link to={lp("/tarifas")}>{t("Tarifas")}</Link>
            </div>
            <div className="foot-col">
              <h5>{t("Empresa")}</h5>
              <a href="https://www.updigital.co.mz" target="_blank" rel="noopener">{t("Sobre a UpDigital")}</a>
              <Link to={`${lp("/tarifas")}#operadores`}>{t("Operadores parceiros")}</Link>
              <a href="https://www.updigital.co.mz" target="_blank" rel="noopener">{t("Carreiras")}</a>
              <a href="mailto:sales@updigital.co.mz?subject=Imprensa%20BusUp">{t("Imprensa")}</a>
            </div>
            <div className="foot-col">
              <h5>{t("Suporte")}</h5>
              <Link to={lp("/contacto")}>{t("Central de ajuda")}</Link>
              <a href="mailto:sales@updigital.co.mz">sales@updigital.co.mz</a>
              <a href="tel:+258866930017">+258 86 693 0017</a>
              <a href="https://www.updigital.co.mz" target="_blank" rel="noopener">www.updigital.co.mz</a>
              <Link to={lp("/contacto")}>{t("Pontos de recarga")}</Link>
            </div>
          </div>
          <div className="foot-bottom">
            <span>{t("© 2026 BusUp · UpDigital. Todos os direitos reservados.")}</span>
            <a className="powered" href="https://www.updigital.co.mz" target="_blank" rel="noopener" aria-label="Powered by UpDigital">
              <span className="pb-label">Powered by</span>
              <img src="/assets/up-digital-logo/up_digital_light.png" alt="UpDigital" />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
