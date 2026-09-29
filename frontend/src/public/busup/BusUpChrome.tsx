import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { Menu, Moon, Sun, X } from "lucide-react";
import { useLandingPrefs } from "../landing/useLandingPrefs";
import { copyBusUp, type CopyBusUp } from "./busup-copy";
import "./busup.css";

/* A casca do site público do BusUp — barra, rodapé e a caixa que põe o tema.
 *
 * NÃO PARTILHA A CASCA COM A LANDING ANTIGA. `landing.css` é o chassis de três
 * sites — a landing que existia, a TPM-TUR e a Cheetah Express — e reescrevê-lo
 * para este desenho partia os dois sites dos operadores. Ver o cabeçalho de
 * `busup.css`.
 *
 * O tema e o idioma vêm de `useLandingPrefs`, que já era partilhado e já tem o
 * armazém fora do React de que três chamadas independentes precisam.
 */

export const LOGO_CLARO = "/assets/busup/logo-light.png";   // tinta escura → fundo claro
export const LOGO_ESCURO = "/assets/busup/logo-dark.png";   // tinta clara  → fundo escuro
export const MARCA = "/assets/busup/mark.png";
export const UPDIGITAL_CLARO = "/assets/up-digital-logo/up_digital_dark.png";
export const UPDIGITAL_ESCURO = "/assets/up-digital-logo/up_digital_light.png";

export const EMAIL_VENDAS = "sales@updigital.co.mz";
export const TELEFONE_VENDAS = "+258 86 693 0017";
export const TELEFONE_VENDAS_HREF = "tel:+258866930017";
export const MORADA = ["Av. Alberto Massavanhane, 1265", "Matola — Moçambique"];

/** O par de logótipos: um por tema, e só um aparece. É CSS e não JavaScript
 *  para não haver um piscar entre o primeiro pintar e o tema chegar. */
export function Logotipo({ alt, altura = 26 }: { alt: string; altura?: number }) {
  return (
    <>
      <img data-logo="light" src={LOGO_CLARO} alt={alt} style={{ height: altura, width: "auto" }} />
      <img data-logo="dark" src={LOGO_ESCURO} alt={alt} style={{ height: altura, width: "auto" }} />
    </>
  );
}

export function LogotipoUpDigital({ alt, altura = 28 }: { alt: string; altura?: number }) {
  return (
    <>
      <img data-logo="light" src={UPDIGITAL_CLARO} alt={alt} style={{ height: altura, width: "auto" }} />
      <img data-logo="dark" src={UPDIGITAL_ESCURO} alt={alt} style={{ height: altura, width: "auto" }} />
    </>
  );
}

function SelectorIdioma({ t }: { t: CopyBusUp }) {
  const { lang, setLang } = useLandingPrefs();
  return (
    <div className="bzc-idioma" role="group" aria-label={lang === "pt" ? "Idioma" : "Language"}>
      {(["pt", "en"] as const).map((codigo) => (
        <button
          aria-pressed={lang === codigo}
          key={codigo}
          onClick={() => setLang(codigo)}
          type="button"
        >
          {codigo.toUpperCase()}
        </button>
      ))}
      <span className="bzc-sr">{t.navProduct}</span>
    </div>
  );
}

export function BotaoTema() {
  const { effectiveTheme, toggleTheme } = useLandingPrefs();
  const rotulo = effectiveTheme === "dark" ? "Modo claro" : "Modo escuro";
  return (
    <button aria-label={rotulo} className="bzc-icone-btn" onClick={toggleTheme} title={rotulo} type="button">
      {effectiveTheme === "dark" ? <Sun aria-hidden size={17} /> : <Moon aria-hidden size={17} />}
    </button>
  );
}

const LIGACOES = [
  { to: "/#produto", rotulo: (t: CopyBusUp) => t.navProduct },
  { to: "/#recursos", rotulo: (t: CopyBusUp) => t.navFeatures },
  { to: "/#porque", rotulo: (t: CopyBusUp) => t.navWhy },
  { to: "/#casos", rotulo: (t: CopyBusUp) => t.navCases },
  { to: "/precos", rotulo: (t: CopyBusUp) => t.navPricing },
  { to: "/contactos", rotulo: (t: CopyBusUp) => t.navContact },
];

function Barra({ t }: { t: CopyBusUp }) {
  const [menuAberto, setMenuAberto] = useState(false);
  const burgerRef = useRef<HTMLButtonElement | null>(null);
  const { pathname } = useLocation();

  useEffect(() => {
    if (!menuAberto) return;
    const aoTeclar = (e: KeyboardEvent) => { if (e.key === "Escape") setMenuAberto(false); };
    document.addEventListener("keydown", aoTeclar);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", aoTeclar);
      document.body.style.overflow = "";
      burgerRef.current?.focus();
    };
  }, [menuAberto]);

  return (
    <>
      <header className="bzc-nav">
        <div className="bzc-nav-in">
          <Link aria-label="BusUp" className="bzc-nav-marca" to="/">
            <Logotipo alt="BusUp" />
          </Link>

          <nav aria-label="BusUp" className="bzc-nav-links">
            {LIGACOES.map((l) => (
              <Link
                aria-current={l.to === pathname ? "page" : undefined}
                key={l.to}
                to={l.to}
              >
                {l.rotulo(t)}
              </Link>
            ))}
          </nav>

          <div className="bzc-nav-fim">
            <SelectorIdioma t={t} />
            <BotaoTema />
            <Link className="bzc-btn bzc-btn--navy bzc-btn--sm" to="/contactos">{t.talkSales}</Link>
            <button
              aria-label="Abrir menu"
              className="bzc-burger"
              onClick={() => setMenuAberto(true)}
              ref={burgerRef}
              type="button"
            >
              <Menu aria-hidden size={20} />
            </button>
          </div>
        </div>
      </header>

      {menuAberto && (
        <div className="bzc-gaveta" onClick={() => setMenuAberto(false)}>
          <div className="bzc-gaveta-painel" onClick={(e) => e.stopPropagation()}>
            <div className="bzc-gaveta-topo">
              <Logotipo alt="BusUp" altura={24} />
              <button aria-label="Fechar menu" className="bzc-icone-btn" onClick={() => setMenuAberto(false)} type="button">
                <X aria-hidden size={18} />
              </button>
            </div>
            {LIGACOES.map((l) => (
              <Link key={l.to} onClick={() => setMenuAberto(false)} to={l.to}>{l.rotulo(t)}</Link>
            ))}
            <Link className="bzc-btn bzc-btn--navy" onClick={() => setMenuAberto(false)} style={{ marginTop: 14 }} to="/contactos">
              {t.talkSales}
            </Link>
            <div className="bzc-gaveta-tools"><SelectorIdioma t={t} /><BotaoTema /></div>
          </div>
        </div>
      )}
    </>
  );
}

function Rodape({ t }: { t: CopyBusUp }) {
  return (
    <footer style={{ background: "var(--bzc-navy-fundo)", padding: "56px 32px 26px" }}>
      <div className="bzc-foot-in">
        <div>
          <img alt="BusUp" src={LOGO_ESCURO} style={{ height: 26, width: "auto", display: "block", marginBottom: 14 }} />
          <p style={{ maxWidth: "34ch", font: "400 13.5px/1.6 Inter, sans-serif", color: "rgba(234,241,248,.66)" }}>
            {t.footerAbout}
          </p>
        </div>

        <nav aria-label={t.footerProduct} className="bzc-foot-col">
          <b>{t.footerProduct}</b>
          <Link to="/#produto">{t.navProduct}</Link>
          <Link to="/precos">{t.navPricing}</Link>
          <Link to="/contactos">{t.navContact}</Link>
          <Link className="bzc-foot-destaque" to="/login">{t.portalLogin}</Link>
        </nav>

        <nav aria-label={t.footerContact} className="bzc-foot-col">
          <b>{t.footerContact}</b>
          <span style={{ font: "400 13.5px/1.55 Inter, sans-serif", color: "rgba(234,241,248,.66)" }}>
            {MORADA[0]}<br />{MORADA[1]}
          </span>
          <a href={`mailto:${EMAIL_VENDAS}`}>{EMAIL_VENDAS}</a>
          <a href={TELEFONE_VENDAS_HREF}>{TELEFONE_VENDAS}</a>
          <a href="https://www.updigital.co.mz" rel="noopener" target="_blank">www.updigital.co.mz</a>
        </nav>

        <nav aria-label={t.footerEco} className="bzc-foot-col">
          <b>{t.footerEco}</b>
          <span>PayUp · CashUp</span>
          <span>GateUp · Vura</span>
          <span>Ossoma</span>
        </nav>
      </div>

      <div className="bzc-foot-barra">
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <span className="bzc-rotulo" style={{ color: "rgba(234,241,248,.62)", whiteSpace: "nowrap" }}>{t.poweredBy}</span>
          <img alt="UpDigital, Limitada" src={UPDIGITAL_ESCURO} style={{ height: 28, width: "auto", display: "block" }} />
        </div>
        <span style={{ font: "400 12px/1.5 Inter, sans-serif", color: "rgba(234,241,248,.6)", textAlign: "right" }}>
          © {new Date().getFullYear()} UpDigital, Limitada. {t.rights}
        </span>
      </div>
    </footer>
  );
}

/** A caixa do site. O `data-theme` vive AQUI e não em `<html>`: o portal e as
 *  páginas dos operadores têm o seu próprio tema, e escrevê-lo na raiz mudava
 *  o de todos. */
export default function BusUpPagina({ children }: { children: ReactNode }) {
  const { effectiveTheme, lang } = useLandingPrefs();
  const t = copyBusUp(lang);

  return (
    <div className="bzc" data-theme={effectiveTheme}>
      <a className="bzc-saltar" href="#conteudo">{lang === "pt" ? "Saltar para o conteúdo" : "Skip to content"}</a>
      <Barra t={t} />
      <main id="conteudo">{children}</main>
      <Rodape t={t} />
    </div>
  );
}

export function useBusUpCopy() {
  const { lang } = useLandingPrefs();
  return { t: copyBusUp(lang), lang };
}

/** O título e a descrição da página, como as outras cascas do repositório
 *  fazem. Sem isto, cada página do site publicava o `<title>` da anterior. */
export function useBusUpMeta(titulo: string, descricao: string) {
  useEffect(() => {
    document.title = titulo;
    let meta = document.querySelector<HTMLMetaElement>('meta[name="description"]');
    if (!meta) {
      meta = document.createElement("meta");
      meta.name = "description";
      document.head.appendChild(meta);
    }
    meta.content = descricao;
  }, [titulo, descricao]);
}
