import { useEffect, useRef } from "react";
import { X } from "lucide-react";

export interface TermsSection { title: string; items: string[] }

/**
 * Termos e Condições, na íntegra.
 *
 * Cada secção é um título e uma lista de parágrafos — texto, nunca marcação.
 * Os termos são editáveis no portal, e um campo de HTML editável seria um campo
 * por onde entra qualquer coisa na página de compra pública.
 *
 * O diálogo prende o foco e fecha com `Esc`: quem está a ler tem de conseguir
 * sair sem apanhar o rato, e quem usa leitor de ecrã não pode cair fora da
 * janela com o `Tab`.
 */
export default function TermsDialog({
  open, onClose, sections, intro, closing, company, version, updatedAt,
}: {
  open: boolean;
  onClose: () => void;
  sections: TermsSection[];
  intro?: string;
  closing?: string;
  company?: string;
  version?: string;
  updatedAt?: string;
}) {
  const caixa = useRef<HTMLDivElement>(null);
  const fechar = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const anterior = document.activeElement as HTMLElement | null;
    fechar.current?.focus();

    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === "Escape") { onClose(); return; }
      if (e.key !== "Tab" || !caixa.current) return;
      const focaveis = caixa.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (focaveis.length === 0) return;
      const primeiro = focaveis[0];
      const ultimo = focaveis[focaveis.length - 1];
      if (e.shiftKey && document.activeElement === primeiro) {
        e.preventDefault(); ultimo.focus();
      } else if (!e.shiftKey && document.activeElement === ultimo) {
        e.preventDefault(); primeiro.focus();
      }
    };

    document.addEventListener("keydown", aoTeclar);
    // Sem isto a página por baixo rola enquanto se lê o diálogo.
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", aoTeclar);
      document.body.style.overflow = overflow;
      anterior?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="bzterms-backdrop" onMouseDown={(e) => {
      if (e.target === e.currentTarget) onClose();
    }}>
      <div className="bzterms" role="dialog" aria-modal="true"
        aria-labelledby="bzterms-titulo" ref={caixa}>
        <header className="bzterms-head">
          <div>
            <h2 id="bzterms-titulo">Termos e Condições</h2>
            {company ? <p className="bzterms-company">{company}</p> : null}
          </div>
          <button ref={fechar} type="button" className="bzterms-x"
            onClick={onClose} aria-label="Fechar">
            <X size={18} />
          </button>
        </header>

        <div className="bzterms-body">
          {intro ? <p className="bzterms-intro">{intro}</p> : null}

          <ol className="bzterms-list">
            {sections.map((s, i) => (
              <li key={`${s.title}-${i}`} className="bzterms-section">
                <h3>{s.title}</h3>
                <ul>
                  {s.items.map((item, j) => <li key={j}>{item}</li>)}
                </ul>
              </li>
            ))}
          </ol>

          {closing ? <p className="bzterms-closing">{closing}</p> : null}

          {version ? (
            <p className="bzterms-version">
              Versão {version}
              {updatedAt ? ` · actualizados a ${new Date(updatedAt).toLocaleDateString("pt-PT")}` : ""}
            </p>
          ) : null}
        </div>

        <footer className="bzterms-foot">
          <button type="button" className="bzbk-btn" onClick={onClose}>
            Li e compreendi
          </button>
        </footer>
      </div>
    </div>
  );
}
