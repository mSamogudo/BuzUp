/**
 * Formulário de pedido de contacto do site (bloco `form`).
 *
 * Os campos são declarados no CMS; o destino é o endpoint público que já
 * existe (`POST /api/public/service-requests/`), o mesmo que alimenta a lista
 * "Pedidos recebidos" do portal.
 */
import { useMemo, useState } from "react";
import { apiPublic } from "../../lib/api";

export interface FormFieldSpec {
  key: string;
  label: string;
  required?: boolean;
  options?: string[];
}

/** Campos que a API aceita. Um campo declarado fora desta lista é ignorado. */
const KNOWN = new Set(["name", "organization", "phone", "email", "interest", "fleet_size", "message", "role"]);

const INTEREST_VALUES = ["operator", "company", "school", "other"];

export function ServiceRequestForm({
  fields,
  submitLabel,
  note,
  sentTitle,
  sentText,
  inert,
}: {
  fields: FormFieldSpec[];
  submitLabel: string;
  note?: string;
  sentTitle?: string;
  sentText?: string;
  inert?: boolean;
}) {
  const usable = useMemo(() => fields.filter((f) => KNOWN.has(f.key)), [fields]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  const set = (key: string, value: string) => setValues((v) => ({ ...v, [key]: value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (inert) return;
    setErrors({});

    const missing: Record<string, string> = {};
    for (const field of usable) {
      if (field.required && !(values[field.key] || "").trim()) {
        missing[field.key] = "Campo obrigatório.";
      }
    }
    if (Object.keys(missing).length) {
      setErrors(missing);
      return;
    }

    setSending(true);
    try {
      await apiPublic("/api/public/service-requests/", {
        method: "POST",
        body: JSON.stringify({
          name: values.name || "",
          organization: values.organization || "",
          phone: values.phone || "",
          email: values.email || "",
          interest: values.interest || "operator",
          fleet_size: values.fleet_size || "",
          message: [values.role ? `Cargo: ${values.role}` : "", values.message || ""]
            .filter(Boolean)
            .join("\n"),
          source: window.location.pathname === "/contactos" ? "contactos" : "landing",
        }),
      });
      setSent(true);
    } catch (error) {
      setErrors({ phone: (error as Error).message });
    } finally {
      setSending(false);
    }
  };

  if (sent) {
    return (
      <div className="bzs-formcard">
        <div className="bzs-sent">
          <span aria-hidden="true" className="bzs-sent-icon">
            ✓
          </span>
          <strong style={{ font: "800 20px/1.25 var(--font-display)" }}>{sentTitle || "Pedido enviado."}</strong>
          <p style={{ margin: 0, font: "400 15px/1.6 var(--font-ui)", color: "var(--muted)" }}>{sentText}</p>
          <button
            className="bzs-cta bzs-cta-ghost"
            onClick={() => {
              setValues({});
              setSent(false);
            }}
            type="button"
          >
            Enviar outro
          </button>
        </div>
      </div>
    );
  }

  return (
    <form className="bzs-formcard" noValidate onSubmit={submit}>
      {usable.map((field) => {
        const invalid = Boolean(errors[field.key]);
        const id = `srq-${field.key}`;
        return (
          <div className="bz-field" key={field.key}>
            <label className="bz-field-label" htmlFor={id}>
              {field.label}
              {field.required ? <span className="bz-field-req">*</span> : null}
            </label>
            {field.key === "message" ? (
              <textarea
                className={`bz-textarea${invalid ? " bz-textarea-invalid" : ""}`}
                id={id}
                onChange={(e) => set(field.key, e.target.value)}
                value={values[field.key] || ""}
              />
            ) : field.key === "interest" && field.options?.length ? (
              <span className="bz-selectwrap">
                <select
                  className="bz-select"
                  id={id}
                  onChange={(e) => set(field.key, e.target.value)}
                  value={values[field.key] || ""}
                >
                  <option value="">—</option>
                  {field.options.map((option, i) => (
                    <option key={option} value={INTEREST_VALUES[i] || "other"}>
                      {option}
                    </option>
                  ))}
                </select>
              </span>
            ) : (
              <input
                autoComplete={field.key === "phone" ? "tel" : field.key === "email" ? "email" : "on"}
                className={`bz-input${invalid ? " bz-input-invalid" : ""}`}
                id={id}
                inputMode={field.key === "phone" ? "tel" : undefined}
                onChange={(e) => set(field.key, e.target.value)}
                type={field.key === "email" ? "email" : "text"}
                value={values[field.key] || ""}
              />
            )}
            {invalid ? <span className="bz-field-error">{errors[field.key]}</span> : null}
          </div>
        );
      })}

      <button className="bzs-cta bzs-cta-primary" disabled={sending || inert} style={{ justifyContent: "center" }} type="submit">
        {sending ? "A enviar…" : submitLabel || "Enviar pedido"}
      </button>
      {note ? <span className="bz-field-hint">{note}</span> : null}
    </form>
  );
}
