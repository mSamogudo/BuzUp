/**
 * Ecrãs de erro (inventário B.7): 404, 401, 403, 500, 503 e sem ligação.
 *
 * Desktop e mobile, PT e EN, tema claro e escuro. O conteúdo é o dos
 * protótipos (`SCREEN_COPY.erros`), verbatim.
 */
import { useNavigate } from "react-router-dom";
import { Moon, Sun } from "lucide-react";
import { useUi } from "../../ui/UiPreferences";
import { Logo } from "../../design/ui/kit";
import { SCREEN_COPY } from "../../design/copy/screens";
import updigitalLight from "../../assets/busup/logo-updigital-dark.png";
import updigitalDark from "../../assets/busup/logo-updigital-white.png";
import "./errors.css";

export type ErrorKey = "404" | "401" | "403" | "500" | "503" | "offline";

interface ErrorEntry {
  key: string;
  code: string;
  tone: string;
  pill: string;
  where: string;
  title: string;
  lead: string;
  cta1: string;
  cta2: string;
  hints: string[][];
  ref: string;
}

/** Destino de cada botão. O rótulo vem do desenho; o destino é do produto. */
const ACTIONS: Record<ErrorKey, { first: string; second: string }> = {
  "404": { first: "/", second: "/comprar" },
  "401": { first: "/login", second: "/" },
  "403": { first: "/app", second: "/contactos" },
  "500": { first: "reload", second: "/contactos" },
  "503": { first: "/contactos", second: "/contactos" },
  offline: { first: "reload", second: "back" },
};

export default function ErrorScreen({
  code,
  reference,
}: {
  code: ErrorKey;
  /** Referência técnica real; sem ela usa-se a do desenho como exemplo. */
  reference?: string;
}) {
  const { locale, theme, toggleTheme } = useUi();
  const navigate = useNavigate();
  const pack = SCREEN_COPY.erros[locale === "en" ? "EN" : "PT"] as unknown as {
    help: string;
    statusPage: string;
    poweredBy: string;
    errors: ErrorEntry[];
  };
  const entry = pack.errors.find((e) => e.key === code) || pack.errors[0];
  const actions = ACTIONS[code];

  const go = (target: string) => {
    if (target === "reload") {
      window.location.reload();
      return;
    }
    if (target === "back") {
      navigate(-1);
      return;
    }
    navigate(target);
  };

  return (
    <div className={`bze bze-${entry.tone}`}>
      <header className="bze-head">
        <Logo height={26} />
        <div className="bze-headtools">
          <button
            aria-label={theme === "dark" ? "Tema claro" : "Tema escuro"}
            className="bz-iconbtn"
            onClick={toggleTheme}
            type="button"
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <span className="bze-help">{pack.help}</span>
          <a className="bzs-cta bzs-cta-navy" href="/contactos">
            {pack.statusPage}
          </a>
        </div>
      </header>

      <main className="bze-body">
        <div className="bze-card">
          <span className="bze-pill">
            <i aria-hidden="true" />
            {entry.pill}
          </span>
          <span className="bze-code">{entry.code === "offline" ? "⚡" : entry.code}</span>
          <h1 className="bze-title">{entry.title}</h1>
          <p className="bze-lead">{entry.lead}</p>

          <div className="bze-ctas">
            <button className="bzs-cta bzs-cta-primary" onClick={() => go(actions.first)} type="button">
              {entry.cta1}
            </button>
            <button className="bzs-cta bzs-cta-ghost" onClick={() => go(actions.second)} type="button">
              {entry.cta2}
            </button>
          </div>

          <div className="bze-hints">
            {entry.hints.map(([title, body], i) => (
              <div className="bze-hint" key={i}>
                <b>{title}</b>
                <span>{body}</span>
              </div>
            ))}
          </div>

          <span className="bze-ref">{reference || entry.ref}</span>
        </div>
      </main>

      <footer className="bze-foot">
        <span className="bz-label">{pack.poweredBy}</span>
        <img alt="UpDigital, Limitada" data-logo="light" src={updigitalLight} />
        <img alt="UpDigital, Limitada" data-logo="dark" src={updigitalDark} />
      </footer>
    </div>
  );
}

/** 403 dentro do portal: ecrã inteiro, sem shell (A0.10). */
export function ForbiddenScreen({ reference }: { reference?: string }) {
  return <ErrorScreen code="403" reference={reference} />;
}
