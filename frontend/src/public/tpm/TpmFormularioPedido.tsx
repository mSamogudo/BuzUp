import { useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { ArrowUpRight, Mail } from "lucide-react";
import { Input } from "@/components/ui/input";
import { CampoSelect } from "../../ui/CampoSelect";
import { EMAIL, TELEFONE, TELEFONE_HREF } from "./TpmChrome";
import { useTpmCopy } from "./tpm-copy";

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


export default function TpmFormularioPedido() {
  const { t } = useTpmCopy();
  const f = t.contactos.form;
  const ASSUNTOS = f.assuntos as Record<string, string>;

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
      `${f.corpo.nome}: ${form.nome}`,
      `${f.corpo.contacto}: ${form.telefone}`,
      `${f.corpo.email}: ${form.email}`,
      `${f.corpo.empresa}: ${form.empresa || f.corpo.naoIndicada}`,
      "",
      form.mensagem,
    ].join("\n");
    const assunto = ASSUNTOS[form.assunto] ?? f.assuntoGenerico;
    window.location.assign(
      `mailto:${EMAIL}?subject=${encodeURIComponent(`TPM-TUR — ${assunto}`)}` +
        `&body=${encodeURIComponent(corpo)}`,
    );
    setPreparado(true);
  };

  return (
    <form className="bzlp-form tpm-form" onSubmit={submeter}>
      <h3>{f.h3}</h3>
      <p className="bzlp-form-lead">{f.lead}</p>

      <div className="bzlp-form-grid">
        <label>
          <span>{f.nome}</span>
          <Input required autoComplete="name" maxLength={120}
            value={form.nome} onChange={(e) => set("nome", e.target.value)} />
        </label>
        <label>
          <span>{f.telefone}</span>
          <Input required inputMode="tel" autoComplete="tel" maxLength={30} placeholder="84xxxxxxx"
            value={form.telefone} onChange={(e) => set("telefone", e.target.value)} />
        </label>
        <label>
          <span>{f.email}</span>
          <Input required type="email" autoComplete="email" maxLength={160}
            value={form.email} onChange={(e) => set("email", e.target.value)} />
        </label>
        <label>
          <span>{f.empresa}</span>
          <Input autoComplete="organization" maxLength={160}
            value={form.empresa} onChange={(e) => set("empresa", e.target.value)} />
        </label>
      </div>

      <label className="bzlp-form-full">
        <span>{f.assunto}</span>
        <CampoSelect className="bzlp-campo" value={form.assunto} onChange={(v) => set("assunto", v)}>
          <option value="" disabled>{f.assuntoVazio}</option>
          {Object.entries(ASSUNTOS).map(([id, rotulo]) => (
            <option key={id} value={id}>{rotulo}</option>
          ))}
        </CampoSelect>
      </label>

      <label className="bzlp-form-full">
        <span>{f.mensagem}</span>
        <textarea required rows={5} minLength={10} maxLength={2000}
          placeholder={f.mensagemDica}
          value={form.mensagem} onChange={(e) => set("mensagem", e.target.value)} />
      </label>

      <button className="bzlp-btn gold" type="submit">
        <Mail size={17} aria-hidden /> {f.submeter} <ArrowUpRight size={16} aria-hidden />
      </button>

      {/* `<output>` e nao um `<div>`: o leitor de ecra anuncia-o sozinho quando
          aparece, que e o que faz falta a quem nao ve o programa de email
          abrir — ou nao ve nada, porque nao ha nenhum configurado. */}
      {preparado && (
        <output className="tpm-form-aviso">
          {/* A frase vem do dicionario com dois marcadores, para o email e o
              telefone poderem ser ligacoes e a ordem das duas partes mudar
              com o idioma. */}
          {f.aviso.split(/(\{email\}|\{telefone\})/).map((parte, i) =>
            parte === "{email}" ? <a key={i} href={`mailto:${EMAIL}`}>{EMAIL}</a>
              : parte === "{telefone}" ? <a key={i} href={TELEFONE_HREF}>{TELEFONE}</a>
                : <span key={i}>{parte}</span>,
          )}
        </output>
      )}
    </form>
  );
}
