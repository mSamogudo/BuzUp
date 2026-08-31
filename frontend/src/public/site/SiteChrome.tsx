/**
 * Moldura do site público: barra de navegação e rodapé.
 *
 * Os itens vêm dos menus do CMS (`/api/public/site/{locale}/`); as frases da
 * moldura vêm de `chrome.ts`. Em mobile a navegação passa a gaveta com alvos
 * de toque de 48px.
 */
import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Menu, Moon, Sun, X } from "lucide-react";
import { useUi } from "../../ui/UiPreferences";
import { Logo } from "../../design/ui/kit";
import updigitalWhite from "../../assets/busup/logo-updigital-white.png";
import { CHROME } from "./chrome";
import type { SiteData } from "./usePublicSite";

function MenuLink({ href, label, target }: { href: string; label: string; target?: string }) {
  const location = useLocation();
  if (href.startsWith("http") || href.startsWith("mailto:") || target === "_blank") {
    return (
      <a href={href} rel="noopener noreferrer" target="_blank">
        {label}
      </a>
    );
  }
  if (href.includes("#")) {
    return <a href={href}>{label}</a>;
  }
  return (
    <Link aria-current={location.pathname === href ? "page" : undefined} to={href}>
      {label}
    </Link>
  );
}

export function SiteHeader({ site }: { site: SiteData | null }) {
  const { locale, setLocale, theme, toggleTheme } = useUi();
  const [drawer, setDrawer] = useState(false);
  const copy = CHROME[locale === "en" ? "en" : "pt"];
  const items = site?.menus?.header?.items || [];

  return (
    <>
      <header className="bzs-header">
        <Link aria-label="BusUp" to="/">
          <Logo height={26} />
        </Link>

        <nav className="bzs-nav">
          {items.map((item, i) => (
            <MenuLink href={item.href} key={i} label={item.label} target={item.target} />
          ))}
        </nav>

        <div className="bzs-headtools">
          <div aria-label="Idioma" className="bzs-lang" role="group">
            <button aria-pressed={locale !== "en"} onClick={() => setLocale("pt")} type="button">
              PT
            </button>
            <button aria-pressed={locale === "en"} onClick={() => setLocale("en")} type="button">
              EN
            </button>
          </div>
          <button
            aria-label={theme === "dark" ? "Tema claro" : "Tema escuro"}
            className="bz-iconbtn bz-iconbtn-lg"
            onClick={toggleTheme}
            type="button"
          >
            {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
          </button>
          {/* A barra do protótipo tem só idioma, tema e "falar com vendas".
              A entrada no portal está no rodapé e no menu de telemóvel, como
              no desenho. */}
          <Link className="bzs-cta bzs-cta-navy" to="/contactos">
            {copy.talkSales}
          </Link>
          <button
            aria-label="Abrir menu"
            className="bz-iconbtn bz-iconbtn-lg bzs-burger"
            onClick={() => setDrawer(true)}
            type="button"
          >
            <Menu size={18} />
          </button>
        </div>
      </header>

      {drawer ? (
        <div className="bzs-drawer">
          <div className="bzs-drawer-head">
            <Logo height={24} />
            <button aria-label="Fechar menu" className="bz-iconbtn bz-iconbtn-lg" onClick={() => setDrawer(false)} type="button">
              <X size={18} />
            </button>
          </div>
          <div onClick={() => setDrawer(false)} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {items.map((item, i) => (
              <MenuLink href={item.href} key={i} label={item.label} target={item.target} />
            ))}
            <Link to="/login">{copy.portalLogin}</Link>
            <Link to="/comprar">{copy.buyTicket}</Link>
          </div>
        </div>
      ) : null}
    </>
  );
}

export function SiteFooter({ site }: { site: SiteData | null }) {
  const { locale } = useUi();
  const copy = CHROME[locale === "en" ? "en" : "pt"];
  const menus = site?.menus || {};
  const year = new Date().getFullYear();
  const company = site?.branding?.company_name || "UpDigital, Limitada";

  const column = (key: string, fallback: string) => {
    const menu = menus[key];
    if (!menu || !menu.items?.length) return null;
    return (
      <div key={key}>
        <h4>{menu.label || fallback}</h4>
        <ul>
          {menu.items.map((item, i) => (
            <li key={i}>
              <MenuLink href={item.href} label={item.label} target={item.target} />
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <footer className="bzs-footer">
      <div className="bzs-wrap">
        <div className="bzs-footer-grid">
          <div>
            <Logo height={24} />
            <p>{copy.footerAbout}</p>
          </div>
          {column("footer_product", copy.footerProduct)}
          {column("footer_contact", copy.footerContact)}
          {column("footer_eco", copy.footerEco)}
        </div>
        <div className="bzs-footer-bottom">
          <span>
            © {year} {company}. {copy.rights}
          </span>
          <span className="bzs-poweredby">
            {copy.poweredBy}
            <img alt="UpDigital" src={updigitalWhite} />
          </span>
        </div>
      </div>
    </footer>
  );
}
