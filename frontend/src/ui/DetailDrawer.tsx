import { X } from "lucide-react";
import type { ReactNode } from "react";

interface DetailField {
  label: string;
  value: ReactNode;
}

export function DetailDrawer({
  open,
  onClose,
  title,
  fields,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  fields?: DetailField[];
  children?: ReactNode;
}) {
  if (!open) return null;

  return (
    <>
      <div className="detail-drawer-overlay" onClick={onClose} />
      <aside className="detail-drawer">
        <div className="detail-drawer-head">
          <h3>{title}</h3>
          <button className="icon-button" onClick={onClose} type="button">
            <X size={18} />
          </button>
        </div>
        <div className="detail-drawer-body">
          {fields && (
            <dl className="detail-fields">
              {fields.map((f) => (
                <div key={f.label} className="detail-field">
                  <dt>{f.label}</dt>
                  <dd>{f.value ?? "-"}</dd>
                </div>
              ))}
            </dl>
          )}
          {children}
        </div>
      </aside>
    </>
  );
}
