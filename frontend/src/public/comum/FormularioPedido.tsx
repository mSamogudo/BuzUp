import { useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { ArrowUpRight, Mail } from "lucide-react";
import { Input } from "@/components/ui/input";
import { CampoSelect } from "../../ui/CampoSelect";

/* Pedido de orcamento dos sites dos operadores.
 *
 * PREPARA UM EMAIL, nao submete nada. Isso e deliberado, e nao falta de
 * trabalho: o unico endereco publico que este sistema tem para formularios e
 * `POST /api/public/service-requests/`, e esse e o funil de vendas do BusUp —
 * o modelo nao tem campo de operador, as opcoes de `interest` sao
 * operador/empresa/escola, e a notificacao por SMS diz "BusUp: novo pedido de
 * contacto" para o telefone comercial da UpDigital. Um pedido de aluguer de
 * autocarro entregue ali ia parar a caixa de entrada errada e tocava o
 * telefone errado.
 *
 * Enquanto nao existir um endereco de pedidos por operador, o mailto e o que
 * poe a mensagem em maos do operador — e e tambem o que os sites oficiais
 * fazem, tanto o da TPM-TUR como o da Cheetah Express.
 *
 * VIVE AQUI, e nao na pasta de um operador, porque so tres coisas mudam entre
 * eles: o texto, o endereco de destino e o prefixo do assunto. Todas entram
 * por propriedade. */

export type TextosFormulario = {
  h3: string;
  lead: string;
  nome: string;
  telefone: string;
  email: string;
  empresa: string;
  assunto: string;
  assuntoVazio: string;
  assuntoGenerico: string;
  assuntos: Record<string, string>;
  mensagem: string;
  mensagemDica: string;
  submeter: string;
  /** Com `{email}` e `{telefone}` onde as ligacoes entram. */
  aviso: string;
  corpo: { nome: string; contacto: string; email: string; empresa: string; naoIndicada: string };
};

export default function FormularioPedido({
  textos: f,
  email: EMAIL,
  telefone,
  telefoneHref,
  prefixoAssunto,
  dicaTelefone = "84xxxxxxx",
}: {
  textos: TextosFormulario;
  email: string;
  /* Opcionais: a Cheetah Express nao publica telefone — so enderecos de
     email — e o aviso dela nao usa o marcador `{telefone}`. */
  telefone?: string;
  telefoneHref?: string;
  /** Vai a frente do assunto do email — "TPM-TUR", "Cheetah Express". Sem
   *  ele, quem recebe ve so "Aluguer de autocarro" sem saber de onde veio. */
  prefixoAssunto: string;
  dicaTelefone?: string;
}) {
  const ASSUNTOS = f.assuntos;

  /* As paginas de servicos e de frota podem trazer o assunto ja escolhido em
   * `?servico=` ou `?viatura=` — quem clicou em "Pedir orcamento" num servico
   * nao devia ter de o escolher outra vez. */
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
      `mailto:${EMAIL}?subject=${encodeURIComponent(`${prefixoAssunto} — ${assunto}`)}` +
        `&body=${encodeURIComponent(corpo)}`,
    );
    setPreparado(true);
  };

  return (
    <form className="bzlp-form bz-form" onSubmit={submeter}>
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
          <Input required inputMode="tel" autoComplete="tel" maxLength={30} placeholder={dicaTelefone}
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
        <output className="bz-form-aviso">
          {/* A frase vem do dicionario com dois marcadores, para o email e o
              telefone poderem ser ligacoes e a ordem das duas partes mudar
              com o idioma. */}
          {f.aviso.split(/(\{email\}|\{telefone\})/).map((parte, i) =>
            parte === "{email}" ? <a key={i} href={`mailto:${EMAIL}`}>{EMAIL}</a>
              : parte === "{telefone}" && telefone
                ? <a key={i} href={telefoneHref}>{telefone}</a>
                : parte === "{telefone}" ? null
                  : <span key={i}>{parte}</span>,
          )}
        </output>
      )}
    </form>
  );
}
