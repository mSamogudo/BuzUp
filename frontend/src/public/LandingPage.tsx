import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, CheckCircle2, Download, Menu, Moon, Sun, Ticket, X,
} from "lucide-react";
import Reveal from "./landing/Reveal";
import { useLandingMeta } from "./landing/useLandingMeta";
import ServiceRequestForm from "./landing/ServiceRequestForm";
import EcosystemSection from "./landing/EcosystemSection";
import { useLandingPrefs, type Lang } from "./landing/useLandingPrefs";
import { copyFor } from "./landing/landing-copy";
import {
  ADDRESS, AUDIENCE_ICONS, BENEFIT_ICONS, SALES_EMAIL,
  SALES_PHONE, SALES_PHONE_HREF, TOOL_ICONS,
} from "./landing/landing-content";
import "./landing/landing.css";

/** Site do produto: logótipo BusUp sempre (o branding do portal pertence ao
 *  operador cliente e não deve substituir a marca aqui). */
const LOGO_LIGHT_BG = "/assets/busup/logo-light.png";
const LOGO_DARK_BG = "/assets/busup/logo-dark.png";

function Wordmark({ url, alt, height = 30 }: { url: string; alt: string; height?: number }) {
  return <img src={url} alt={alt} style={{ height, display: "block" }} />;
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
  const { effectiveTheme, toggleTheme, lang, setLang } = useLandingPrefs();
  const t = copyFor(lang);
  useLandingMeta(lang);

  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [active, setActive] = useState("");
  const burgerRef = useRef<HTMLButtonElement | null>(null);

  const NAV_IDS = [
    { id: "produto", label: t.nav.produto },
    { id: "como-funciona", label: t.nav.como },
    { id: "solucoes", label: t.nav.solucoes },
    { id: "plataforma", label: t.nav.plataforma },
    { id: "ecossistema", label: t.nav.eco },
  ];

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
    for (const { id } of NAV_IDS) {
      const el = document.getElementById(id);
      if (el) io.observe(el);
    }
    return () => io.disconnect();
  }, [lang]); // eslint-disable-line react-hooks/exhaustive-deps

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

  const ThemeButton = () => (
    <button className="bzlp-icon-btn" type="button" onClick={toggleTheme}
      aria-label={effectiveTheme === "dark" ? t.themeLight : t.themeDark}
      title={effectiveTheme === "dark" ? t.themeLight : t.themeDark}>
      {effectiveTheme === "dark" ? <Sun size={16} aria-hidden /> : <Moon size={16} aria-hidden />}
    </button>
  );

  const LangSwitch = () => (
    <div className="bzlp-lang" role="group" aria-label={t.language}>
      {(["pt", "en"] as Lang[]).map((l) => (
        <button key={l} type="button" aria-pressed={lang === l} onClick={() => setLang(l)}>
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );

  return (
    <div className="bzlp" data-theme={effectiveTheme}>
      <a className="bzlp-skip" href="#conteudo">{t.skip}</a>

      <header className={`bzlp-nav${scrolled ? " is-scrolled" : ""}`}>
        <div className="bzlp-nav-in">
          <Link to="/" aria-label="BusUp"><Wordmark url={effectiveTheme === "dark" ? LOGO_DARK_BG : LOGO_LIGHT_BG} alt="BusUp" height={28} /></Link>
          <nav className="bzlp-links" aria-label="BusUp">
            {NAV_IDS.map((n) => (
              <a key={n.id} href={`#${n.id}`} aria-current={active === n.id ? "location" : undefined}>{n.label}</a>
            ))}
          </nav>
          <div className="bzlp-nav-cta">
            <div className="bzlp-tools"><LangSwitch /><ThemeButton /></div>
            <Link to="/login" className="bzlp-ghost">{t.signIn}</Link>
            <Link to="/comprar" className="bzlp-btn sm"><Ticket size={16} aria-hidden /> {t.buy}</Link>
            <button ref={burgerRef} className="bzlp-burger" aria-label={t.openMenu} onClick={() => setMenuOpen(true)}>
              <Menu size={24} aria-hidden />
            </button>
          </div>
        </div>
      </header>

      {menuOpen && (
        <div className="bzlp-sheet" onClick={() => setMenuOpen(false)}>
          <div className="bzlp-sheet-panel" onClick={(e) => e.stopPropagation()}>
            <div className="bzlp-sheet-head">
              <Wordmark url={effectiveTheme === "dark" ? LOGO_DARK_BG : LOGO_LIGHT_BG} alt="BusUp" height={24} />
              <button className="bzlp-sheet-close" aria-label={t.closeMenu} onClick={() => setMenuOpen(false)}>
                <X size={24} aria-hidden />
              </button>
            </div>
            {NAV_IDS.map((n) => (
              <a key={n.id} href={`#${n.id}`} onClick={() => setMenuOpen(false)}>{n.label}</a>
            ))}
            <Link to="/login" onClick={() => setMenuOpen(false)}>{t.signInPortal}</Link>
            <Link to="/comprar" className="bzlp-btn" onClick={() => setMenuOpen(false)}>
              <Ticket size={18} aria-hidden /> {t.buy}
            </Link>
            <div className="bzlp-sheet-tools"><LangSwitch /><ThemeButton /></div>
          </div>
        </div>
      )}

      <main id="conteudo">
        {/* HERO */}
        <section className="bzlp-hero">
          <div className="bzlp-hero-in">
            <div className="bzlp-hero-txt">
              <span className="bzlp-badge">{t.hero.badge}</span>
              <h1>{t.hero.h1a}<br /><span>{t.hero.h1b}</span></h1>
              <p>
                <b>BusUp</b> {t.hero.lead1} <b>{t.hero.leadStrong}</b>{t.hero.lead2}
              </p>
              <div className="bzlp-hero-cta">
                <Link to="/comprar" className="bzlp-btn"><Ticket size={18} aria-hidden /> {t.buy}</Link>
                <a href="#pedido" className="bzlp-btn outline light">
                  {t.talkSales} <ArrowRight size={16} aria-hidden />
                </a>
              </div>
              <div className="bzlp-chips">
                {t.hero.chips.map((c) => <span key={c}>{c}</span>)}
              </div>
            </div>
            <div className="bzlp-hero-art">
              <ProductImg src="/landing/hero-all.webp"
                alt="BusUp: autocarro, portal de gestão, terminal POS e app do passageiro"
                width={1003} height={1052} eager />
            </div>
          </div>
        </section>

        <div className="bzlp-stats">
          <div className="bzlp-stats-in">
            {t.stats.map((s) => (
              <div className="bzlp-stat" key={s.l}><b>{s.v}</b><span>{s.l}</span></div>
            ))}
          </div>
        </div>

        {/* BENEFÍCIOS */}
        <section className="bzlp-sec" id="produto">
          <div className="bzlp-wrap">
            <Reveal>
              <div className="bzlp-sechead">
                <div className="bzlp-kicker">{t.benefits.kicker}</div>
                <h2 className="bzlp-h2">{t.benefits.h2}</h2>
                <p className="bzlp-lead">{t.benefits.lead}</p>
              </div>
            </Reveal>
            <div className="bzlp-benefits">
              {t.benefits.items.map((b, i) => {
                const Icon = BENEFIT_ICONS[i];
                return (
                  <Reveal key={b.title} delay={i * 60}>
                    <div className="bzlp-benefit">
                      <div className="bzlp-bi"><Icon size={21} aria-hidden /></div>
                      <h3>{b.title}</h3>
                      <p>{b.text}</p>
                    </div>
                  </Reveal>
                );
              })}
            </div>
          </div>
        </section>

        {/* COMO FUNCIONA — mostrado, não descrito */}
        <section className="bzlp-sec alt" id="como-funciona">
          <div className="bzlp-wrap">
            <Reveal>
              <div className="bzlp-sechead">
                <div className="bzlp-kicker">{t.how.kicker}</div>
                <h2 className="bzlp-h2">{t.how.h2}</h2>
              </div>
            </Reveal>

            {t.how.steps.map((s) => (
              <Reveal key={s.h3}>
                <div className="bzlp-row">
                  <div className="bzlp-row-media">
                    <ProductImg src="/landing/compra.webp" alt="" width={1400} height={900} />
                  </div>
                  <div>
                    <div className="bzlp-kicker left">{s.kicker}</div>
                    <h3>{s.h3}</h3>
                    <p>{s.text}</p>
                    {s.facts.length > 0 && (
                      <ul className="bzlp-facts">
                        {s.facts.map((f) => (
                          <li key={f}><CheckCircle2 size={17} aria-hidden /> {f}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </section>

        {/* PLATAFORMA */}
        <section className="bzlp-sec alt" id="plataforma">
          <div className="bzlp-wrap">
            <div className="bzlp-platform">
              <Reveal>
                <div className="bzlp-shot">
                  <ProductImg src="/landing/portal.webp" alt="" width={1400} height={820} />
                </div>
              </Reveal>
              <Reveal delay={80}>
                <div>
                  <div className="bzlp-kicker left">{t.platform.kicker}</div>
                  <h2 className="bzlp-h2 left">{t.platform.h2}</h2>
                  <p className="bzlp-lead left">{t.platform.lead}</p>
                  <div className="bzlp-pills">
                    {t.platform.pills.map((p) => <span key={p}>{p}</span>)}
                  </div>
                </div>
              </Reveal>
            </div>
          </div>
        </section>

        {/* SEGURANÇA */}
        <section className="bzlp-drench">
          <div className="bzlp-wrap bzlp-drench-in">
            <Reveal>
              <div>
                <div className="bzlp-kicker left light">{t.security.kicker}</div>
                <h2>{t.security.h2}</h2>
                <p>{t.security.lead}</p>
              </div>
            </Reveal>
            <div className="bzlp-checks">
              {t.security.points.map((p, i) => (
                <Reveal key={p} delay={i * 45}>
                  <div className="bzlp-check"><CheckCircle2 size={19} aria-hidden /><span>{p}</span></div>
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
                <div className="bzlp-kicker">{t.audiences.kicker}</div>
                <h2 className="bzlp-h2">{t.audiences.h2}</h2>
                <p className="bzlp-lead">{t.audiences.lead}</p>
              </div>
            </Reveal>
            <div className="bzlp-aud">
              {t.audiences.items.map((a, i) => {
                const Icon = AUDIENCE_ICONS[i];
                return (
                  <Reveal key={a.name} delay={i * 60}>
                    <div className="bzlp-aud-card">
                      <div className="bzlp-aud-ico"><Icon size={21} aria-hidden /></div>
                      <h3>{a.name}</h3>
                      <p>{a.text}</p>
                    </div>
                  </Reveal>
                );
              })}
            </div>
          </div>
        </section>

        {/* FERRAMENTAS */}
        <section className="bzlp-sec alt" id="apps">
          <div className="bzlp-wrap">
            <Reveal>
              <div className="bzlp-sechead">
                <div className="bzlp-kicker">{t.tools.kicker}</div>
                <h2 className="bzlp-h2">{t.tools.h2}</h2>
              </div>
            </Reveal>
            <div className="bzlp-tools-grid">
              {t.tools.items.map((tool, i) => {
                const Icon = TOOL_ICONS[i];
                return (
                  <Reveal key={tool.name} delay={i * 70}>
                    <div className="bzlp-tool">
                      <div className="bzlp-tool-head">
                        <div className="bzlp-ti"><Icon size={25} aria-hidden /></div>
                        <div>
                          <h3>{tool.name}</h3>
                          <span>{tool.tag}</span>
                        </div>
                      </div>
                      <ul>{tool.list.map((x) => <li key={x}>{x}</li>)}</ul>
                    </div>
                  </Reveal>
                );
              })}
            </div>
            <div style={{ textAlign: "center", marginTop: 32 }}>
              <Link to="/baixar" className="bzlp-btn outline">
                <Download size={18} aria-hidden /> {t.tools.download}
              </Link>
            </div>
          </div>
        </section>

        {/* ECOSSISTEMA UPDIGITAL */}
        <EcosystemSection lang={lang} kicker={t.eco.kicker} h2={t.eco.h2} lead={t.eco.lead} visit={t.eco.visit} />

        {/* CTA + contactos */}
        <section className="bzlp-cta" id="contacto">
          <div className="bzlp-wrap">
            <div className="bzlp-cta-in">
              <div>
                <h2>{t.cta.h2}</h2>
                <p>{t.cta.lead}</p>
              </div>
              <div className="bzlp-cta-btns">
                <a href="#pedido" className="bzlp-btn white">{t.talkSales}</a>
                <Link to="/comprar" className="bzlp-btn outline light">
                  <Ticket size={17} aria-hidden /> {t.buy}
                </Link>
              </div>
            </div>
            <div className="bzlp-contact">
              <div className="bzlp-contact-card">
                <small>{t.cta.commercial}</small>
                <a href={`mailto:${SALES_EMAIL}`}>{SALES_EMAIL}</a>
                <a href={`tel:${SALES_PHONE_HREF}`}>{SALES_PHONE}</a>
              </div>
              <div className="bzlp-contact-card">
                <small>{t.cta.address}</small>
                <span>{ADDRESS}</span>
              </div>
              <div className="bzlp-contact-card">
                <small>{t.cta.website}</small>
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
                  <div className="bzlp-kicker left">{t.form.kicker}</div>
                  <h2 className="bzlp-h2 left">{t.form.h2}</h2>
                  <p className="bzlp-lead left">{t.form.lead}</p>
                  <ul className="bzlp-facts" style={{ marginTop: 22 }}>
                    {t.form.facts.map((f) => (
                      <li key={f}><CheckCircle2 size={17} aria-hidden /> {f}</li>
                    ))}
                  </ul>
                </div>
              </Reveal>
              <Reveal delay={80}><ServiceRequestForm lang={lang} /></Reveal>
            </div>
          </div>
        </section>
      </main>

      <footer className="bzlp-foot">
        <div className="bzlp-foot-in">
          <div className="bzlp-foot-brand">
            <Wordmark url={LOGO_DARK_BG} alt="BusUp" height={26} />
            <p>{t.footer.about}</p>
          </div>
          <div className="bzlp-foot-cols">
            <nav aria-label={t.footer.product}>
              <h4>{t.footer.product}</h4>
              <a href="#produto">{t.footer.features}</a>
              <a href="#plataforma">{t.footer.portal}</a>
              <Link to="/comprar">{t.buy}</Link>
              <Link to="/baixar">{t.footer.apps}</Link>
            </nav>
            <nav aria-label={t.footer.access}>
              <h4>{t.footer.access}</h4>
              <Link to="/login">{t.footer.portal}</Link>
              <Link to="/baixar">{t.footer.appPassenger}</Link>
              <Link to="/baixar">{t.footer.appPos}</Link>
            </nav>
            <nav aria-label={t.footer.contact}>
              <h4>{t.footer.contact}</h4>
              <a href={`mailto:${SALES_EMAIL}`}>{SALES_EMAIL}</a>
              <a href={`tel:${SALES_PHONE_HREF}`}>{SALES_PHONE}</a>
              <a href="https://updigital.co.mz" target="_blank" rel="noreferrer">updigital.co.mz</a>
            </nav>
          </div>
        </div>
        <div className="bzlp-foot-bar">© {new Date().getFullYear()} BusUp · UpDigital. {t.footer.rights}</div>
      </footer>
    </div>
  );
}
