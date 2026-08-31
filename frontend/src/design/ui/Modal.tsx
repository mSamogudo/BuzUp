/**
 * Modal do portal (02-tokens-e-padroes.md §8).
 *
 * 720px, raio 20px, cabeçalho fixo, corpo com scroll, rodapé fixo. Acima de
 * oito campos o formulário faz-se em passos — `StepBar` desenha-os e
 * `autoSteps` decide quando aparecem.
 *
 * Acessibilidade: Escape fecha, o foco fica preso dentro do diálogo enquanto
 * está aberto e volta ao elemento que o abriu quando fecha.
 */
import { useCallback, useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, X } from "lucide-react";
import { Button, IconButton } from "./kit";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function Modal({
  open,
  onClose,
  title,
  description,
  size = "md",
  steps,
  footer,
  children,
  labelledBy,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  size?: "sm" | "md" | "lg";
  /** Barra de passos, quando o formulário é faseado. */
  steps?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  labelledBy?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const opener = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    opener.current = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const node = ref.current;
    const first = node?.querySelector<HTMLElement>(FOCUSABLE);
    first?.focus();

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== "Tab" || !node) return;
      const items = Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => el.offsetParent !== null,
      );
      if (!items.length) return;
      const firstEl = items[0];
      const lastEl = items[items.length - 1];
      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    };

    window.addEventListener("keydown", onKey, true);
    return () => {
      window.removeEventListener("keydown", onKey, true);
      document.body.style.overflow = overflow;
      opener.current?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <>
      <div className="bz-overlay" onClick={onClose} />
      <div className="bz-modal-shell">
        <div
          aria-describedby={description ? "bz-modal-desc" : undefined}
          aria-labelledby={labelledBy || "bz-modal-title"}
          aria-modal="true"
          className={`bz-modal${size === "sm" ? " bz-modal-sm" : size === "lg" ? " bz-modal-lg" : ""}`}
          ref={ref}
          role="dialog"
        >
          <header className="bz-modal-head">
            <div>
              <h2 className="bz-modal-title" id="bz-modal-title">
                {title}
              </h2>
              {description ? (
                <p className="bz-modal-desc" id="bz-modal-desc">
                  {description}
                </p>
              ) : null}
            </div>
            <IconButton bare icon={<X size={18} />} label="Fechar" onClick={onClose} />
          </header>
          {steps}
          <div className="bz-modal-body">{children}</div>
          {footer ? <footer className="bz-modal-foot">{footer}</footer> : null}
        </div>
      </div>
    </>,
    document.body,
  );
}

export type Step = { key: string; label: string; invalid?: boolean };

export function StepBar({
  steps,
  current,
  onSelect,
}: {
  steps: Step[];
  current: string;
  onSelect: (key: string) => void;
}) {
  if (steps.length < 2) return null;
  return (
    <nav aria-label="Passos do formulário" className="bz-steps">
      {steps.map((s, i) => (
        <button
          aria-current={s.key === current ? "step" : undefined}
          className={`bz-step${s.invalid ? " bz-step-bad" : ""}`}
          key={s.key}
          onClick={() => onSelect(s.key)}
          type="button"
        >
          <span className="bz-step-n">{String(i + 1).padStart(2, "0")}</span>
          {s.label}
        </button>
      ))}
    </nav>
  );
}

/**
 * Regra do handoff: acima de oito campos o formulário divide-se em passos.
 * Recebe os grupos declarados pelo ecrã e devolve-os achatados num só passo
 * quando o total de campos não justifica a divisão.
 */
export function autoSteps<T extends { key: string; label: string; fields: unknown[] }>(
  groups: T[],
): { stepped: boolean; groups: T[] } {
  const total = groups.reduce((n, g) => n + g.fields.length, 0);
  if (total <= 8 || groups.length < 2) {
    return {
      stepped: false,
      groups: [{ ...groups[0], fields: groups.flatMap((g) => g.fields) } as T],
    };
  }
  return { stepped: true, groups };
}

/**
 * Confirmação destrutiva (A0.8). Arquivar é reversível: quem chama mostra o
 * aviso com "Desfazer" durante 8 segundos depois de confirmar.
 */
export function ConfirmDestructive({
  open,
  title,
  message,
  confirmLabel = "Arquivar",
  loading,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <Modal
      footer={
        <>
          <Button onClick={onCancel} variant="ghost">
            Cancelar
          </Button>
          <Button loading={loading} onClick={onConfirm} variant="danger">
            {confirmLabel}
          </Button>
        </>
      }
      onClose={onCancel}
      open={open}
      size="sm"
      title={title}
    >
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
        <span
          aria-hidden="true"
          style={{
            display: "grid",
            placeItems: "center",
            width: 38,
            height: 38,
            borderRadius: 12,
            background: "var(--tone-bad-bg)",
            color: "var(--tone-bad-fg)",
            flex: "none",
          }}
        >
          <AlertTriangle size={19} />
        </span>
        <p style={{ margin: 0, font: "400 14px/1.6 var(--font-ui)", color: "var(--muted)" }}>{message}</p>
      </div>
    </Modal>
  );
}

/** Aviso com "Desfazer" durante 8 segundos, mostrado depois de arquivar. */
export function useUndoWindow(seconds = 8) {
  const timer = useRef<number | null>(null);
  const clear = useCallback(() => {
    if (timer.current) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
  }, []);
  const start = useCallback(
    (onExpire: () => void) => {
      clear();
      timer.current = window.setTimeout(onExpire, seconds * 1000);
    },
    [clear, seconds],
  );
  useEffect(() => clear, [clear]);
  return { start, clear };
}
