import { PropsWithChildren, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Menu, Moon, Sun, Ticket, X } from "lucide-react";
import { useLandingPrefs } from "../landing/useLandingPrefs";
import "../landing/landing.css";
import "./tpm.css";
import "./tpm-paginas.css";

/* A moldura das páginas da TPM-TUR — barra, menu de telemóvel e rodapé.
 *
 * Vivia dentro da landing, que era a única página do operador. Com as quatro
 * páginas institucionais passou a haver cinco cópias possíveis da mesma barra;
 * uma só é o que garante que acrescentar uma entrada de menu não deixa quatro
 * páginas para trás.
 *
 * A ordem dos imports de CSS é deliberada e não se troca: landing.css põe o
 * vocabulário `bzlp-*`, tpm.css veste-o com a marca, tpm-paginas.css acrescenta
 * o que só as páginas novas têm. Quem importar isto recebe a cascata já certa.
 */

export const EMAIL = "info@tpmtur.co.mz";
export const TELEFONE = "+258 84 314 2681";
export const TELEFONE_HREF = "tel:+258843142681";
export const TELEFONE_FIXO = "+258 21 418 684";
export const TELEFONE_FIXO_HREF = "tel:+258214186884";
export const MORADA = "Maputo, Moçambique · 1104";

const LOGO_CLARO = "/assets/tpm-tur-logo/tpm_light.png"; // wordmark escuro, para fundo claro
const LOGO_ESCURO = "/assets/tpm-tur-logo/tpm_dark.png"; // wordmark claro, para fundo escuro

/* Créditos do rodapé: o sistema e quem o fez.
 *
 * ATENÇÃO à nomenclatura, que NÃO é a mesma nas duas pastas — medi a
 * luminância da tinta de cada ficheiro em vez de confiar no nome:
 *   busup/logo-dark.png        tinta clara (181) → é esta que vai sobre navy
 *   up-digital-logo/up_digital_light.png  tinta clara (206) → idem
 * Ou seja, na BusUp "dark" quer dizer "para fundo escuro" e na UpDigital
 * "light" quer dizer "tinta clara". Trocá-las dá um logótipo invisível. */
const LOGO_BUSUP = "/assets/busup/logo-dark.png";
const LOGO_UPDIGITAL = "/assets/up-digital-logo/up_digital_light.png";

/** Endereço de email com assunto já preenchido, para os pedidos de orçamento. */
export const pedido = (assunto: string) =>
  `mailto:${EMAIL}?subject=${encodeURIComponent(assunto)}`;

/* A barra deixou de ser uma lista de âncoras da própria página: as secções
 * institucionais passaram a ter páginas próprias, e é para lá que aponta.
 * `Perguntas` continua a ser uma âncora da landing — a FAQ não justifica
 * página. */
const NAV: { to: string; label: string }[] = [
  { to: "/tpm-tur/servicos", label: "Serviços" },
  { to: "/tpm-tur/frota", label: "Nossa frota" },
  { to: "/tpm-tur/sobre-nos", label: "Sobre nós" },
  { to: "/tpm-tur/nossas-politicas", label: "Nossas políticas" },
  { to: "/tpm-tur#faq", label: "Perguntas" },
  { to: "/tpm-tur/contactos", label: "Contactos" },
];

/**
 * Põe title e description enquanto a página está montada e REPÕE no unmount.
 * A SPA partilha o index.html com o portal de gestão: sem isto, o título da
 * página institucional ficava preso na tab de quem entrasse depois no /app.
 */
export function useTpmMeta(titulo: string, descricao: string) {
  useEffect(() => {
    const anterior = document.title;
    document.title = titulo;

    const meta = document.querySelector<HTMLMetaElement>('meta[name="description"]');
    const descricaoAnterior = meta?.content;
    meta?.setAttribute("content", descricao);

    return () => {
      document.title = anterior;
      if (meta && descricaoAnterior !== undefined) meta.content = descricaoAnterior;
    };
  }, [titulo, descricao]);
}

function BotaoTema() {
  const { effectiveTheme, toggleTheme } = useLandingPrefs();
  const escuro = effectiveTheme === "dark";
  return (
    <button
      className="bzlp-icon-btn"
      type="button"
      onClick={toggleTheme}
      aria-label={escuro ? "Modo claro" : "Modo escuro"}
      title={escuro ? "Modo claro" : "Modo escuro"}
    >
      {escuro ? <Sun size={16} aria-hidden /> : <Moon size={16} aria-hidden />}
    </button>
  );
}

function TpmNav({ activa }: { activa?: string }) {
  const { effectiveTheme } = useLandingPrefs();
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const burgerRef = useRef<HTMLButtonElement | null>(null);
  const logo = effectiveTheme === "dark" ? LOGO_ESCURO : LOGO_CLARO;

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

  return (
    <>
      <header className={`bzlp-nav${scrolled ? " is-scrolled" : ""}`}>
        <div className="bzlp-nav-in">
          <Link to="/tpm-tur" aria-label="TPM-TUR — página inicial">
            <img src={logo} alt="TPM-TUR, S.A. — Transporte e Turismo" height={30} style={{ display: "block" }} />
          </Link>
          <nav className="bzlp-links" aria-label="TPM-TUR">
            {NAV.map((n) => (
              <Link key={n.to} to={n.to} aria-current={activa === n.to ? "page" : undefined}>
                {n.label}
              </Link>
            ))}
          </nav>
          <div className="bzlp-nav-cta">
            <div className="bzlp-tools"><BotaoTema /></div>
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
              <Link key={n.to} to={n.to} onClick={() => setMenuOpen(false)}>{n.label}</Link>
            ))}
            <Link to="/login" onClick={() => setMenuOpen(false)}>Entrar no portal</Link>
            <Link to="/comprar" className="bzlp-btn gold" onClick={() => setMenuOpen(false)}>
              <Ticket size={18} aria-hidden /> Comprar bilhete
            </Link>
            <div className="bzlp-sheet-tools"><BotaoTema /></div>
          </div>
        </div>
      )}
    </>
  );
}

function TpmFooter() {
  return (
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
            <Link to="/tpm-tur/sobre-nos">Sobre nós</Link>
            <Link to="/tpm-tur/servicos">Serviços</Link>
            <Link to="/tpm-tur/frota">Nossa frota</Link>
            <Link to="/tpm-tur/nossas-politicas">Nossas políticas</Link>
            <Link to="/tpm-tur/contactos">Contactos</Link>
          </nav>
          <nav aria-label="Contactos">
            <h4>Contactos</h4>
            <a href={`mailto:${EMAIL}`}>{EMAIL}</a>
            <a href={TELEFONE_FIXO_HREF}>{TELEFONE_FIXO}</a>
            <a href={TELEFONE_HREF}>{TELEFONE}</a>
            <span>{MORADA}</span>
          </nav>
        </div>
      </div>
      {/* A barra inferior deixou de dizer "Tecnologia BusUp · UpDigital" por
          extenso: os dois passam a assinar com o seu logótipo, e cada um leva
          ao sítio respectivo. O rodapé é navy nos dois temas — por isso as
          variantes de tinta clara servem sempre, sem alternância. */}
      <div className="bzlp-foot-bar">
        <div className="tpm-foot-bar-in">
          <span>© {new Date().getFullYear()} TPM-TUR, S.A. · Transporte e Turismo.</span>
          <div className="tpm-creditos">
            <span>Tecnologia</span>
            <Link to="/">
              <img src={LOGO_BUSUP} alt="BusUp" width={70} height={26} />
            </Link>
            <span className="tpm-creditos-sep" aria-hidden>·</span>
            <span>Desenvolvido por</span>
            <a href="https://updigital.co.mz" target="_blank" rel="noreferrer">
              <img src={LOGO_UPDIGITAL} alt="UpDigital, Limitada" width={75} height={30} />
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}

/**
 * A casca comum: tema, salto para o conteúdo, barra, `main` e rodapé.
 * As páginas só escrevem as suas secções.
 */
export default function TpmPagina({ activa, children }: PropsWithChildren<{ activa?: string }>) {
  const { effectiveTheme } = useLandingPrefs();
  return (
    <div className="bzlp bzlp-tpm" data-theme={effectiveTheme}>
      <a className="bzlp-skip" href="#conteudo">Saltar para o conteúdo</a>
      <TpmNav activa={activa} />
      <main id="conteudo">{children}</main>
      <TpmFooter />
    </div>
  );
}

/** Faixa de entrada das páginas institucionais: migalha, título e resumo. */
export function TpmIntro({ migalha, titulo, descricao }: { migalha: string; titulo: string; descricao: string }) {
  return (
    <section className="tpm-intro">
      <div className="bzlp-wrap">
        <nav className="tpm-intro-migalha" aria-label="Caminho">
          <Link to="/tpm-tur">Início</Link>
          <span aria-hidden>/</span>
          <span aria-current="page">{migalha}</span>
        </nav>
        <h1>{titulo}</h1>
        <p>{descricao}</p>
      </div>
    </section>
  );
}

/** Chamada final, igual nas quatro páginas: falar com a equipa. */
export function TpmCallout({
  titulo,
  texto,
  assunto,
  cta = "Pedir orçamento",
  secundario,
}: {
  titulo: string;
  texto: string;
  assunto: string;
  cta?: string;
  secundario?: { to: string; label: string };
}) {
  return (
    <section className="tpm-callout">
      <div className="bzlp-wrap tpm-callout-in">
        <div>
          <h2>{titulo}</h2>
          <p>{texto}</p>
        </div>
        <div className="bzlp-cta-btns">
          <a href={pedido(assunto)} className="bzlp-btn">{cta}</a>
          {secundario && <Link to={secundario.to} className="bzlp-btn outline">{secundario.label}</Link>}
        </div>
      </div>
    </section>
  );
}
