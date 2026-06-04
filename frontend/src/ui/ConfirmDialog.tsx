import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { AlertTriangle, HelpCircle } from "lucide-react";

export interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "default" | "danger";
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  tone = "default",
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const confirmRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) onCancel();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, busy, onCancel]);

  useEffect(() => {
    if (open) {
      const id = window.setTimeout(() => confirmRef.current?.focus(), 30);
      return () => window.clearTimeout(id);
    }
  }, [open]);

  if (!open) return null;
  const isDanger = tone === "danger";

  return (
    <>
      <div className="confirm-dialog-overlay" onClick={() => { if (!busy) onCancel(); }} />
      <div className="confirm-dialog-shell" role="dialog" aria-modal="true" aria-label={title}>
        <div className="confirm-dialog-card">
          <div className="confirm-dialog-head">
            <div className={`confirm-dialog-icon${isDanger ? " confirm-dialog-icon-danger" : ""}`}>
              {isDanger ? <AlertTriangle size={20} /> : <HelpCircle size={20} />}
            </div>
            <div className="confirm-dialog-copy">
              <h3>{title}</h3>
              <p>{message}</p>
            </div>
          </div>
          <div className="confirm-dialog-actions">
            <button
              className="secondary-button"
              disabled={busy}
              onClick={onCancel}
              type="button"
            >
              {cancelLabel}
            </button>
            <button
              ref={confirmRef}
              className={isDanger ? "danger-button" : "primary-button"}
              disabled={busy}
              onClick={onConfirm}
              type="button"
            >
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

interface ConfirmOptions {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "default" | "danger";
}

type Resolver = (value: boolean) => void;

export function useConfirm() {
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<ConfirmOptions>({ title: "", message: "" });
  const resolverRef = useRef<Resolver | null>(null);

  const confirm = useCallback((opts: ConfirmOptions): Promise<boolean> => {
    setOptions(opts);
    setOpen(true);
    return new Promise<boolean>((resolve) => {
      resolverRef.current = resolve;
    });
  }, []);

  const close = useCallback((result: boolean) => {
    setOpen(false);
    const resolve = resolverRef.current;
    resolverRef.current = null;
    if (resolve) resolve(result);
  }, []);

  const dialog: ReactNode = (
    <ConfirmDialog
      open={open}
      title={options.title}
      message={options.message}
      confirmLabel={options.confirmLabel}
      cancelLabel={options.cancelLabel}
      tone={options.tone}
      onConfirm={() => close(true)}
      onCancel={() => close(false)}
    />
  );

  return { confirm, dialog };
}
