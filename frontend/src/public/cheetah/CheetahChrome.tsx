import { PropsWithChildren, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Menu, Moon, Sun, Ticket, X } from "lucide-react";
import { useLandingPrefs } from "../landing/useLandingPrefs";
import { useCheetahCopy } from "./cheetah-copy";
import "../landing/landing.css";
import "../comum/busca.css";
import "../comum/formulario.css";
import "./cheetah.css";
import "./cheetah-paginas.css";
import "./cheetah-motion.css";

/* A moldura das páginas da Cheetah Express — barra, menu de telemóvel e rodapé.
 *
 * A ordem dos imports de CSS é deliberada e não se troca: landing.css põe o
 * vocabulário `bzlp-*`, os de `comum/` acrescentam o cartão de pesquisa e o
 * formulário, cheetah.css veste tudo com a marca e cheetah-paginas.css junta o
 * que só as páginas internas têm. Quem importar isto recebe a cascata já certa.
 *
 * PORQUE NÃO PARTILHA A CASCA COM A TPM-TUR. Só três coisas seriam iguais — a
 * estrutura da barra, o menu de telemóvel e a barra de créditos —, e as outras
 * todas divergem: a TPM-TUR tem seis páginas, FAQ e um selector de idioma de
 * dois botões; esta tem quatro páginas, quadros de horários e um alternador de
 * um botão. Uma casca parametrizada desenhada a partir destes dois casos seria
 * abstrair cedo demais. O que era genérico de verdade — o cartão de pesquisa e
 * o formulário — esse sim saiu para `public/comum/`.
 */

export const EMAIL_RESERVAS = "bookings@cheetah-express.com";
export const EMAIL_GERAL = "cheetahexpressmaputo@gmail.com";
export const MORADA = "Maputo, Moçambique · 1100";

/* Um só ficheiro de origem, duas variantes. A do site oficial tem a chita
 * contornada a PRETO — sobre o preto da marca o animal desaparecia e ficava só
 * o wordmark vermelho a flutuar. A variante escura troca essa tinta preta por
 * branca e deixa o vermelho e o amarelo como estão: medidos, dão 4,06:1 e
 * 11,37:1 sobre o preto da marca e não precisam de ajuda. */
const LOGO_CLARO = "/assets/cheetah-logo/cheetah-logo.png";
const LOGO_ESCURO = "/assets/cheetah-logo/cheetah-logo-escuro.png";

/* Créditos do rodapé: o sistema e quem o fez.
 *
 * ATENÇÃO à nomenclatura, que NÃO é a mesma nas duas pastas — a luminância da
 * tinta de cada ficheiro foi medida em vez de se confiar no nome:
 *   busup/logo-dark.png                   tinta clara (181) → vai sobre escuro
 *   up-digital-logo/up_digital_light.png  tinta clara (206) → idem
 * Ou seja, na BusUp "dark" quer dizer "para fundo escuro" e na UpDigital
 * "light" quer dizer "tinta clara". Trocá-las dá um logótipo invisível. */
const LOGO_BUSUP = "/assets/busup/logo-dark.png";
const LOGO_UPDIGITAL = "/assets/up-digital-logo/up_digital_light.png";

/** Endereço de email com assunto já preenchido, para os pedidos. */
export const pedido = (assunto: string) =>
  `mailto:${EMAIL_RESERVAS}?subject=${encodeURIComponent(assunto)}`;

type Rotulos = ReturnType<typeof useCheetahCopy>["t"]["nav"];

const navegacao = (t: Rotulos) => [
  { to: "/cheetah-express/horarios", label: t.horarios },
  { to: "/cheetah-express/contactos", label: t.contactos },
  { to: "/cheetah-express/termos", label: t.termos },
];

/**
 * Põe title e description enquanto a página está montada e REPÕE no unmount.
 * A SPA partilha o index.html com o portal de gestão: sem isto, o título da
 * página institucional ficava preso na tab de quem entrasse depois no /app.
 */
export function useCheetahMeta(titulo: string, descricao: string) {
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
  const { t } = useCheetahCopy();
  const escuro = effectiveTheme === "dark";
  const rotulo = escuro ? t.nav.temaClaro : t.nav.temaEscuro;
  return (
    <button className="bzlp-icon-btn" type="button" onClick={toggleTheme} aria-label={rotulo} title={rotulo}>
      {escuro ? <Sun size={16} aria-hidden /> : <Moon size={16} aria-hidden />}
    </button>
  );
}

/* Um botão que ALTERNA, e não dois lado a lado: a barra tem quatro entradas
 * mais dois controlos mais o CTA, e o par PT|EN gastava largura que a entrada
 * "Comprar bilhete" precisava para não quebrar em duas linhas. O botão mostra
 * a língua PARA ONDE se vai, que é a pergunta que quem carrega está a fazer. */
function BotaoIdioma() {
  const { t, lang, setLang } = useCheetahCopy();
  const outra = lang === "pt" ? "en" : "pt";
  return (
    <button
      className="bzlp-icon-btn"
      type="button"
      onClick={() => setLang(outra)}
      aria-label={t.nav.mudarIdioma}
      title={t.nav.mudarIdioma}
    >
      {outra.toUpperCase()}
    </button>
  );
}

function CheetahNav({ activa }: { activa?: string }) {
  const { effectiveTheme } = useLandingPrefs();
  const { t } = useCheetahCopy();
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
          <Link to="/cheetah-express" aria-label={t.nav.paginaInicial}>
            {/* `width` e `height` explícitos: sem eles a barra saltava de
                altura enquanto o PNG carregava. */}
            <img src={logo} alt={t.nav.logoAlt} width={143} height={44} style={{ display: "block" }} />
          </Link>
          <nav className="bzlp-links" aria-label="Cheetah Express">
            {NAV.map((n) => (
              <Link key={n.to} to={n.to} aria-current={activa === n.to ? "page" : undefined}>
                {n.label}
              </Link>
            ))}
          </nav>
          <div className="bzlp-nav-cta">
            <div className="bzlp-tools"><BotaoIdioma /><BotaoTema /></div>
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
              <img src={logo} alt="Cheetah Express" width={117} height={36} />
              <button className="bzlp-sheet-close" aria-label={t.nav.fecharMenu} onClick={() => setMenuOpen(false)}>
                <X size={24} aria-hidden />
              </button>
            </div>
            <Link to="/cheetah-express" onClick={() => setMenuOpen(false)}>{t.nav.inicio}</Link>
            {NAV.map((n) => (
              <Link key={n.to} to={n.to} onClick={() => setMenuOpen(false)}>{n.label}</Link>
            ))}
            <Link to="/login" onClick={() => setMenuOpen(false)}>{t.nav.entrarPortal}</Link>
            <Link to="/comprar" className="bzlp-btn gold" onClick={() => setMenuOpen(false)}>
              <Ticket size={18} aria-hidden /> {t.nav.comprar}
            </Link>
            <div className="bzlp-sheet-tools"><BotaoIdioma /><BotaoTema /></div>
          </div>
        </div>
      )}
    </>
  );
}

function CheetahFooter() {
  const { t } = useCheetahCopy();
  return (
    <footer className="bzlp-foot">
      <div className="bzlp-foot-in">
        <div className="bzlp-foot-brand">
          {/* O rodapé é preto nos dois temas, por isso é sempre a variante de
              tinta clara — não alterna. */}
          <img src={LOGO_ESCURO} alt="Cheetah Express" width={182} height={56} style={{ display: "block" }} />
          <p>{t.rodape.tagline}</p>
        </div>
        <div className="bzlp-foot-cols">
          <nav aria-label={t.rodape.viagens}>
            <h4>{t.rodape.viagens}</h4>
            <Link to="/comprar">{t.nav.comprar}</Link>
            <Link to="/cheetah-express/horarios">{t.nav.horarios}</Link>
            <Link to="/baixar">{t.rodape.app}</Link>
            <Link to="/login">{t.nav.entrarPortal}</Link>
          </nav>
          <nav aria-label={t.rodape.empresa}>
            <h4>{t.rodape.empresa}</h4>
            <Link to="/cheetah-express">{t.nav.inicio}</Link>
            <Link to="/cheetah-express/contactos">{t.nav.contactos}</Link>
            <Link to="/cheetah-express/termos">{t.nav.termos}</Link>
          </nav>
          <nav aria-label={t.rodape.contactos}>
            <h4>{t.rodape.contactos}</h4>
            <a href={`mailto:${EMAIL_RESERVAS}`}>{EMAIL_RESERVAS}</a>
            <a href={`mailto:${EMAIL_GERAL}`}>{EMAIL_GERAL}</a>
            <span>{MORADA}</span>
          </nav>
        </div>
      </div>
      {/* A BusUp e a UpDigital assinam com o seu logótipo, e cada um leva ao
          sítio respectivo. */}
      <div className="bzlp-foot-bar">
        <div className="che-foot-bar-in">
          <span>© {new Date().getFullYear()} {t.rodape.direitos}</span>
          <div className="che-creditos">
            <span>{t.rodape.tecnologia}</span>
            <Link to="/">
              <img src={LOGO_BUSUP} alt="BusUp" width={70} height={26} />
            </Link>
            <span className="che-creditos-sep" aria-hidden>·</span>
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
export default function CheetahPagina({ activa, children }: PropsWithChildren<{ activa?: string }>) {
  const { effectiveTheme } = useLandingPrefs();
  const { t } = useCheetahCopy();
  return (
    <div className="bzlp bzlp-cheetah" data-theme={effectiveTheme}>
      <a className="bzlp-skip" href="#conteudo">{t.nav.saltar}</a>
      <CheetahNav activa={activa} />
      <main id="conteudo">{children}</main>
      <CheetahFooter />
    </div>
  );
}

/** Faixa de entrada das páginas internas: migalha, título e resumo. */
export function CheetahIntro({ migalha, titulo, descricao }: { migalha: string; titulo: string; descricao: string }) {
  const { t } = useCheetahCopy();
  return (
    <section className="che-intro">
      <div className="bzlp-wrap">
        <nav className="che-intro-migalha" aria-label={t.comum.caminho}>
          <Link to="/cheetah-express">{t.nav.inicio}</Link>
          <span aria-hidden>/</span>
          <span aria-current="page">{migalha}</span>
        </nav>
        <h1>{titulo}</h1>
        <p>{descricao}</p>
      </div>
    </section>
  );
}
