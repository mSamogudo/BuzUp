import { useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { ArrowUpRight, Mail } from "lucide-react";
import { Input } from "@/components/ui/input";
import { CampoSelect } from "../../ui/CampoSelect";
import { EMAIL, TELEFONE, TELEFONE_HREF } from "./TpmChrome";

/* Pedido de orçamento da TPM-TUR.
 *
 * PREPARA UM EMAIL, não submete nada. Isso é deliberado, e não falta de
 * trabalho: o único endereço público que este sistema tem para formulários é
 * `POST /api/public/service-requests/`, e esse é o funil de vendas do BusUp —
 * o modelo não tem campo de operador, as opções de `interest` são
 * operador/empresa/escola, e a notificação por SMS diz "BusUp: novo pedido de
 * contacto" para o telefone comercial da UpDigital. Um pedido de aluguer de
 * autocarro da TPM-TUR entregue ali ia parar à caixa de entrada errada e
 * tocava o telefone errado.
 *
 * Enquanto não existir um endereço de pedidos por operador, o mailto é o que
 * põe a mensagem em mãos da TPM-TUR — e é também o que o site oficial faz. */

const ASSUNTOS: Record<string, string> = {
  autocarros: "Aluguer de autocarros",
  "rent-a-car": "Rent-a-car",
  excursoes: "Excursões",
  transfers: "Transfers e shuttle",
  trabalhadores: "Transporte de trabalhadores",
  coaster: "Disponibilidade de Coaster",
  quantum: "Disponibilidade de Quantum",
  suv: "Disponibilidade de SUV",
  viagem: "Informação sobre uma viagem",
  outro: "Outro assunto",
};

export default function TpmFormularioPedido() {
  /* As páginas de serviços e de frota podem trazer o assunto já escolhido em
   * `?servico=` ou `?viatura=` — quem clicou em "Pedir orçamento" num serviço
   * não devia ter de o escolher outra vez. */
  const [params] = useSearchParams();
  const sugerido = params.get("servico") ?? params.get("viatura") ?? "";

  const [form, setForm] = useState({
    nome: "",
    telefone: "",
    email: "",
    empresa: "",
    assunto: sugerido in ASSUNTOS ? sugerido : "",
    mensagem: "",
  });
  const [preparado, setPreparado] = useState(false);

  const set = (k: keyof typeof form, v: string) => setForm((p) => ({ ...p, [k]: v }));

  const submeter = (e: FormEvent) => {
    e.preventDefault();
    const corpo = [
      `Nome: ${form.nome}`,
      `Contacto: ${form.telefone}`,
      `Email: ${form.email}`,
      `Empresa: ${form.empresa || "Não indicada"}`,
      "",
      form.mensagem,
    ].join("\n");
    const assunto = ASSUNTOS[form.assunto] ?? "Pedido de informação";
    window.location.assign(
      `mailto:${EMAIL}?subject=${encodeURIComponent(`TPM-TUR — ${assunto}`)}` +
        `&body=${encodeURIComponent(corpo)}`,
    );
    setPreparado(true);
  };

  return (
    <form className="bzlp-form tpm-form" onSubmit={submeter}>
      <h3>Conte-nos o que precisa.</h3>
      <p className="bzlp-form-lead">
        Preenche os detalhes e preparamos o email para a nossa equipa. Nada é enviado
        automaticamente — revê a mensagem antes de a mandar.
      </p>

      <div className="bzlp-form-grid">
        <label>
          <span>Nome completo *</span>
          <Input required autoComplete="name" maxLength={120}
            value={form.nome} onChange={(e) => set("nome", e.target.value)} />
        </label>
        <label>
          <span>Contacto telefónico *</span>
          <Input required inputMode="tel" autoComplete="tel" maxLength={30} placeholder="84xxxxxxx"
            value={form.telefone} onChange={(e) => set("telefone", e.target.value)} />
        </label>
        <label>
          <span>Email *</span>
          <Input required type="email" autoComplete="email" maxLength={160}
            value={form.email} onChange={(e) => set("email", e.target.value)} />
        </label>
        <label>
          <span>Empresa (opcional)</span>
          <Input autoComplete="organization" maxLength={160}
            value={form.empresa} onChange={(e) => set("empresa", e.target.value)} />
        </label>
      </div>

      <label className="bzlp-form-full">
        <span>Assunto *</span>
        <CampoSelect className="bzlp-campo" value={form.assunto} onChange={(v) => set("assunto", v)}>
          <option value="" disabled>Seleccione um serviço ou assunto</option>
          {Object.entries(ASSUNTOS).map(([id, rotulo]) => (
            <option key={id} value={id}>{rotulo}</option>
          ))}
        </CampoSelect>
      </label>

      <label className="bzlp-form-full">
        <span>Como podemos ajudar? *</span>
        <textarea required rows={5} minLength={10} maxLength={2000}
          placeholder="Indique o percurso, as datas, o número de passageiros e outras necessidades."
          value={form.mensagem} onChange={(e) => set("mensagem", e.target.value)} />
      </label>

      <button className="bzlp-btn gold" type="submit">
        <Mail size={17} aria-hidden /> Preparar email <ArrowUpRight size={16} aria-hidden />
      </button>

      {/* `<output>` e nao um `<div>`: o leitor de ecra anuncia-o sozinho quando
          aparece, que e o que faz falta a quem nao ve o programa de email
          abrir — ou nao ve nada, porque nao ha nenhum configurado. */}
      {preparado && (
        <output className="tpm-form-aviso">
          Se o seu programa de email não abriu, envie os detalhes para{" "}
          <a href={`mailto:${EMAIL}`}>{EMAIL}</a> ou ligue para{" "}
          <a href={TELEFONE_HREF}>{TELEFONE}</a>.
        </output>
      )}
    </form>
  );
}
