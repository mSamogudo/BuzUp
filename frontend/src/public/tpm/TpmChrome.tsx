import { PropsWithChildren, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Menu, Moon, Sun, Ticket, X } from "lucide-react";
import { useLandingPrefs, type Lang } from "../landing/useLandingPrefs";
import { useTpmCopy } from "./tpm-copy";
import "../landing/landing.css";
import "../comum/busca.css";
import "../comum/formulario.css";
import "./tpm.css";
import "./tpm-paginas.css";

/* A moldura das páginas da TPM-TUR — barra, menu de telemóvel e rodapé.
 *
 * Vivia dentro da landing, que era a única página do operador. Com as cinco
 * páginas institucionais passou a haver seis cópias possíveis da mesma barra;
 * uma só é o que garante que acrescentar uma entrada de menu não deixa cinco
 * páginas para trás.
 *
 * A ordem dos imports de CSS é deliberada e não se troca: landing.css põe o
 * vocabulário `bzlp-*`, os de `comum/` acrescentam o cartão de pesquisa e o
 * formulário de pedido (partilhados com a Cheetah Express), tpm.css veste tudo
 * com a marca e tpm-paginas.css junta o que só as páginas novas têm. Quem
 * importar isto recebe a cascata já certa.
 */

export const EMAIL = "info@tpmtur.co.mz";
export const TELEFONE = "+258 84 314 2681";
export const TELEFONE_HREF = "tel:+258843142681";
export const TELEFONE_FIXO = "+258 21 418 684";
export const TELEFONE_FIXO_HREF = "tel:+258214186884";
export const MORADA = "Maputo, Moçambique · 1104";

/* Os PNG de origem tem 2172px e 2508px de largura e pesavam 1093KB e 285KB —
 * mais de um megabyte so para uma barra que os mostra a 64px de altura. Estes
 * sao os mesmos logotipos a 180px, que e o DOBRO da maior utilizacao na web (o
 * ecra de arranque, a 84px), em WebP SEM PERDAS.
 *
 * Sem perdas e nao com perdas, e isso foi medido: a 92 de qualidade o erro
 * chegava a 161/255 nos pixeis com tinta e um quarto deles desviava mais de
 * 12. Num logotipo com "TRANSPORTE E TURISMO" em corpo miudo isso ve-se, e um
 * logotipo e um bem de marca. Os 14KB que se poupavam nao pagam isso.
 *
 * Os PNG grandes ficam para os PDF, mas do lado do BACKEND — ele le de
 * `backend/static/assets/`, que e uma copia separada desta. */
const LOGO_CLARO = "/assets/tpm-tur-logo/tpm_light.webp"; // wordmark escuro, para fundo claro
const LOGO_ESCURO = "/assets/tpm-tur-logo/tpm_dark.webp"; // wordmark claro, para fundo escuro

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
type Rotulos = ReturnType<typeof useTpmCopy>["t"]["nav"];

const navegacao = (t: Rotulos) => [
  { to: "/tpm-tur/servicos", label: t.servicos },
  { to: "/tpm-tur/frota", label: t.frota },
  { to: "/tpm-tur/sobre-nos", label: t.sobre },
  { to: "/tpm-tur/nossas-politicas", label: t.politicas },
  { to: "/tpm-tur#faq", label: t.perguntas },
  { to: "/tpm-tur/contactos", label: t.contactos },
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
  const { t } = useTpmCopy();
  const escuro = effectiveTheme === "dark";
  const rotulo = escuro ? t.nav.temaClaro : t.nav.temaEscuro;
  return (
    <button className="bzlp-icon-btn" type="button" onClick={toggleTheme} aria-label={rotulo} title={rotulo}>
      {escuro ? <Sun size={16} aria-hidden /> : <Moon size={16} aria-hidden />}
    </button>
  );
}

/* Um botão só, do mesmo feitio do tema, e não a caixa segmentada PT|EN.
 *
 * A caixa ocupava 75px na barra — quase o dobro do botão de tema ao lado — e
 * com dois feitios diferentes lado a lado os dois controlos não se liam como
 * o par que são. Um par de discos iguais lê-se de relance.
 *
 * MOSTRA O IDIOMA ACTUAL, não o de destino. É o contrário do botão de tema,
 * que mostra a lua para onde vai — mas é o que a caixa segmentada já dizia
 * (o PT vinha realçado), e é a convenção da web para selectores de idioma.
 * Trocar o sentido agora deixava a mesma letra a querer dizer o oposto.
 *
 * O `aria-label` inclui a letra visível de propósito: quem usa comando de voz
 * diz "carregar PT", e um nome acessível que não contenha o rótulo visível
 * quebra essa ligação. */
function SelectorIdioma() {
  const { t, lang, setLang } = useTpmCopy();
  const outro: Lang = lang === "pt" ? "en" : "pt";
  const accao = t.nav.mudarIdioma;
  return (
    <button
      aria-label={`${t.nav.idioma}: ${lang.toUpperCase()} — ${accao}`}
      className="bzlp-icon-btn tpm-btn-idioma"
      onClick={() => setLang(outro)}
      title={accao}
      type="button"
    >
      {lang.toUpperCase()}
    </button>
  );
}

function TpmNav({ activa }: { activa?: string }) {
  const { effectiveTheme } = useLandingPrefs();
  const { t } = useTpmCopy();
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const burgerRef = useRef<HTMLButtonElement | null>(null);
  const logo = effectiveTheme === "dark" ? LOGO_ESCURO : LOGO_CLARO;
  const NAV = navegacao(t.nav);

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
          {/* O logótipo fica DENTRO do link. Na tela o editor deixou-o ao lado
              de uma âncora vazia — é artefacto de arrastar, não desenho: assim
              o logótipo não seria clicável nem teria nome acessível. */}
          <Link to="/tpm-tur" aria-label={t.nav.paginaInicial}>
            <img src={logo} alt={t.nav.logoAlt} height={64} style={{ display: "block" }} />
          </Link>
          <nav className="bzlp-links" aria-label="TPM-TUR">
            {NAV.map((n) => (
              <Link key={n.to} to={n.to} aria-current={activa === n.to ? "page" : undefined}>
                {n.label}
              </Link>
            ))}
          </nav>
          <div className="bzlp-nav-cta">
            <div className="bzlp-tools"><SelectorIdioma /><BotaoTema /></div>
            <Link to="/login" className="bzlp-ghost">{t.nav.entrar}</Link>
            <Link to="/comprar" className="bzlp-btn sm gold"><Ticket size={16} aria-hidden /> {t.nav.comprar}</Link>
            <button ref={burgerRef} className="bzlp-burger" aria-label={t.nav.abrirMenu} onClick={() => setMenuOpen(true)}>
              <Menu size={24} aria-hidden />
            </button>
          </div>
        </div>
      </header>

      {menuOpen && (
        <div className="bzlp-sheet" onClick={() => setMenuOpen(false)}>
          <div className="bzlp-sheet-panel" onClick={(e) => e.stopPropagation()}>
            <div className="bzlp-sheet-head">
              <img src={logo} alt="TPM-TUR" height={40} />
              <button className="bzlp-sheet-close" aria-label={t.nav.fecharMenu} onClick={() => setMenuOpen(false)}>
                <X size={24} aria-hidden />
              </button>
            </div>
            {NAV.map((n) => (
              <Link key={n.to} to={n.to} onClick={() => setMenuOpen(false)}>{n.label}</Link>
            ))}
            <Link to="/login" onClick={() => setMenuOpen(false)}>{t.nav.entrarPortal}</Link>
            <Link to="/comprar" className="bzlp-btn gold" onClick={() => setMenuOpen(false)}>
              <Ticket size={18} aria-hidden /> {t.nav.comprar}
            </Link>
            <div className="bzlp-sheet-tools"><SelectorIdioma /><BotaoTema /></div>
          </div>
        </div>
      )}
    </>
  );
}

function TpmFooter() {
  const { t } = useTpmCopy();
  return (
    <footer className="bzlp-foot">
      <div className="bzlp-foot-in">
        <div className="bzlp-foot-brand">
          <img src={LOGO_ESCURO} alt="TPM-TUR, S.A." height={64} style={{ display: "block" }} />
          <p>{t.rodape.tagline}</p>
        </div>
        <div className="bzlp-foot-cols">
          <nav aria-label={t.rodape.viagens}>
            <h4>{t.rodape.viagens}</h4>
            <Link to="/comprar">{t.nav.comprar}</Link>
            <Link to="/baixar">{t.rodape.app}</Link>
            <Link to="/login">{t.nav.entrarPortal}</Link>
          </nav>
          <nav aria-label={t.rodape.empresa}>
            <h4>{t.rodape.empresa}</h4>
            <Link to="/tpm-tur/sobre-nos">{t.nav.sobre}</Link>
            <Link to="/tpm-tur/servicos">{t.nav.servicos}</Link>
            <Link to="/tpm-tur/frota">{t.nav.frota}</Link>
            <Link to="/tpm-tur/nossas-politicas">{t.nav.politicas}</Link>
            <Link to="/tpm-tur/contactos">{t.nav.contactos}</Link>
          </nav>
          <nav aria-label={t.rodape.contactos}>
            <h4>{t.rodape.contactos}</h4>
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
          <span>© {new Date().getFullYear()} {t.rodape.direitos}</span>
          <div className="tpm-creditos">
            <span>{t.rodape.tecnologia}</span>
            <Link to="/">
              <img src={LOGO_BUSUP} alt="BusUp" width={70} height={26} />
            </Link>
            <span className="tpm-creditos-sep" aria-hidden>·</span>
            <span>{t.rodape.desenvolvidoPor}</span>
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
  const { t } = useTpmCopy();
  return (
    <div className="bzlp bzlp-tpm" data-theme={effectiveTheme}>
      <a className="bzlp-skip" href="#conteudo">{t.nav.saltar}</a>
      <TpmNav activa={activa} />
      <main id="conteudo">{children}</main>
      <TpmFooter />
    </div>
  );
}

/** Faixa de entrada das páginas institucionais: migalha, título e resumo. */
export function TpmIntro({ migalha, titulo, descricao }: { migalha: string; titulo: string; descricao: string }) {
  const { t } = useTpmCopy();
  return (
    <section className="tpm-intro">
      <div className="bzlp-wrap">
        <nav className="tpm-intro-migalha" aria-label={t.comum.caminho}>
          <Link to="/tpm-tur">{t.nav.inicio}</Link>
          <span aria-hidden>/</span>
          <span aria-current="page">{migalha}</span>
        </nav>
        <h1>{titulo}</h1>
        <p>{descricao}</p>
      </div>
    </section>
  );
}

/** Chamada final, igual nas páginas institucionais: falar com a equipa. */
export function TpmCallout({
  titulo,
  texto,
  assunto,
  cta,
  secundario,
}: {
  titulo: string;
  texto: string;
  assunto: string;
  cta?: string;
  secundario?: { to: string; label: string };
}) {
  const { t } = useTpmCopy();
  return (
    <section className="tpm-callout">
      <div className="bzlp-wrap tpm-callout-in">
        <div>
          <h2>{titulo}</h2>
          <p>{texto}</p>
        </div>
        <div className="bzlp-cta-btns">
          <a href={pedido(assunto)} className="bzlp-btn">{cta ?? t.comum.pedirOrcamento}</a>
          {secundario && <Link to={secundario.to} className="bzlp-btn outline">{secundario.label}</Link>}
        </div>
      </div>
    </section>
  );
}
