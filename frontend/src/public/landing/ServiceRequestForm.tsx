import { useState, type FormEvent } from "react";
import { CheckCircle2, Send } from "lucide-react";

/** Texto do formulário nos dois idiomas — a página traduz, o formulário
 *  também tem de traduzir (antes ficava sempre em PT dentro da versão EN). */
const T = {
  pt: {
    h3: "Peça uma demonstração",
    lead: "Deixe os seus dados e mostramos a plataforma a operar.",
    name: "Nome *", org: "Organização", phone: "Telefone *", email: "Email",
    profile: "Perfil", fleet: "Dimensão da frota", fleetHint: "ex.: 12 autocarros",
    message: "Mensagem", messageHint: "Conte-nos o que precisa",
    send: "Enviar pedido", sending: "A enviar…",
    failed: "Não foi possível enviar. Tente de novo.",
    error: "Erro ao enviar.",
    doneH3: "Pedido recebido",
    doneText: "A nossa equipa comercial entra em contacto consigo em breve.",
    interests: [
      { value: "operator", label: "Operador de transporte" },
      { value: "company", label: "Empresa" },
      { value: "school", label: "Escola ou instituição" },
      { value: "other", label: "Outro" },
    ],
  },
  en: {
    h3: "Request a demo",
    lead: "Leave your details and we will show the platform in action.",
    name: "Name *", org: "Organisation", phone: "Phone *", email: "Email",
    profile: "Profile", fleet: "Fleet size", fleetHint: "e.g. 12 buses",
    message: "Message", messageHint: "Tell us what you need",
    send: "Send request", sending: "Sending…",
    failed: "We could not send it. Please try again.",
    error: "Error while sending.",
    doneH3: "Request received",
    doneText: "Our sales team will get in touch with you shortly.",
    interests: [
      { value: "operator", label: "Transport operator" },
      { value: "company", label: "Company" },
      { value: "school", label: "School or institution" },
      { value: "other", label: "Other" },
    ],
  },
} as const;

/** Pedido de contacto: fica registado no sistema e avisa a equipa comercial. */
export default function ServiceRequestForm({ lang = "pt" }: { lang?: "pt" | "en" }) {
  const t = T[lang] ?? T.pt;
  const [form, setForm] = useState({
    name: "", organization: "", phone: "", email: "",
    interest: "operator", fleet_size: "", message: "",
  });
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  const set = (k: string, v: string) => setForm((p) => ({ ...p, [k]: v }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      const res = await fetch("/api/public/service-requests/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || t.failed);
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.error);
    } finally { setBusy(false); }
  };

  if (done) {
    return (
      <div className="bzlp-form bzlp-form-done" role="status">
        <CheckCircle2 size={40} aria-hidden />
        <h3>{t.doneH3}</h3>
        <p>{t.doneText}</p>
      </div>
    );
  }

  return (
    <form className="bzlp-form" onSubmit={submit}>
      <h3>{t.h3}</h3>
      <p className="bzlp-form-lead">{t.lead}</p>
      {error && <div className="bzlp-form-error" role="alert">{error}</div>}
      <div className="bzlp-form-grid">
        <label>
          <span>{t.name}</span>
          <input required value={form.name} onChange={(e) => set("name", e.target.value)} />
        </label>
        <label>
          <span>{t.org}</span>
          <input value={form.organization} onChange={(e) => set("organization", e.target.value)} />
        </label>
        <label>
          <span>{t.phone}</span>
          <input required inputMode="tel" placeholder="84xxxxxxx"
            value={form.phone} onChange={(e) => set("phone", e.target.value)} />
        </label>
        <label>
          <span>{t.email}</span>
          <input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} />
        </label>
        <label>
          <span>{t.profile}</span>
          <select value={form.interest} onChange={(e) => set("interest", e.target.value)}>
            {t.interests.map((i) => <option key={i.value} value={i.value}>{i.label}</option>)}
          </select>
        </label>
        <label>
          <span>{t.fleet}</span>
          <input placeholder={t.fleetHint}
            value={form.fleet_size} onChange={(e) => set("fleet_size", e.target.value)} />
        </label>
      </div>
      <label className="bzlp-form-full">
        <span>{t.message}</span>
        <textarea rows={3} placeholder={t.messageHint}
          value={form.message} onChange={(e) => set("message", e.target.value)} />
      </label>
      <button className="bzlp-btn" type="submit" disabled={busy}>
        {busy ? t.sending : <><Send size={17} aria-hidden /> {t.send}</>}
      </button>
    </form>
  );
}
