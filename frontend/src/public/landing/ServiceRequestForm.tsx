import { useState, type FormEvent } from "react";
import { CheckCircle2, Send } from "lucide-react";

const INTERESTS = [
  { value: "operator", label: "Operador de transporte" },
  { value: "company", label: "Empresa" },
  { value: "school", label: "Escola ou instituição" },
  { value: "other", label: "Outro" },
];

/** Pedido de contacto: fica registado no sistema e avisa a equipa comercial. */
export default function ServiceRequestForm() {
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
      if (!res.ok) throw new Error(body.detail || "Não foi possível enviar. Tente de novo.");
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao enviar.");
    } finally { setBusy(false); }
  };

  if (done) {
    return (
      <div className="bzlp-form bzlp-form-done" role="status">
        <CheckCircle2 size={40} aria-hidden />
        <h3>Pedido recebido</h3>
        <p>A nossa equipa comercial entra em contacto consigo em breve.</p>
      </div>
    );
  }

  return (
    <form className="bzlp-form" onSubmit={submit}>
      <h3>Peça uma demonstração</h3>
      <p className="bzlp-form-lead">Deixe os seus dados e mostramos a plataforma a operar.</p>
      {error && <div className="bzlp-form-error" role="alert">{error}</div>}
      <div className="bzlp-form-grid">
        <label>
          <span>Nome *</span>
          <input required value={form.name} onChange={(e) => set("name", e.target.value)} />
        </label>
        <label>
          <span>Organização</span>
          <input value={form.organization} onChange={(e) => set("organization", e.target.value)} />
        </label>
        <label>
          <span>Telefone *</span>
          <input required inputMode="tel" placeholder="84xxxxxxx"
            value={form.phone} onChange={(e) => set("phone", e.target.value)} />
        </label>
        <label>
          <span>Email</span>
          <input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} />
        </label>
        <label>
          <span>Perfil</span>
          <select value={form.interest} onChange={(e) => set("interest", e.target.value)}>
            {INTERESTS.map((i) => <option key={i.value} value={i.value}>{i.label}</option>)}
          </select>
        </label>
        <label>
          <span>Dimensão da frota</span>
          <input placeholder="ex.: 12 autocarros"
            value={form.fleet_size} onChange={(e) => set("fleet_size", e.target.value)} />
        </label>
      </div>
      <label className="bzlp-form-full">
        <span>Mensagem</span>
        <textarea rows={3} placeholder="Conte-nos o que precisa"
          value={form.message} onChange={(e) => set("message", e.target.value)} />
      </label>
      <button className="bzlp-btn" type="submit" disabled={busy}>
        {busy ? "A enviar…" : <><Send size={17} aria-hidden /> Enviar pedido</>}
      </button>
    </form>
  );
}
