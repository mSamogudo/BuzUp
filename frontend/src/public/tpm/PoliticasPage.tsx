import {
  ArrowUpRight, Award, BadgeCheck, Globe2, HeartHandshake, Link2Off, Scale, ShieldCheck, Users,
} from "lucide-react";
import Reveal from "../landing/Reveal";
import TpmPagina, { EMAIL, TpmCallout, TpmIntro, useTpmMeta } from "./TpmChrome";

/* Nossas políticas.
 *
 * As nove políticas são as que a TPM-TUR publica. NÃO há resumo por baixo de
 * cada título: o texto integral é da empresa e é ele que vale — inventar um
 * resumo de uma política de compliance ou de direitos humanos seria pôr na
 * boca da empresa um compromisso que ela não escreveu. Cada cartão leva à
 * fonte oficial.
 *
 * O `rel="noreferrer"` acompanha o `target="_blank"` em todas: sem ele a
 * página aberta recebe `window.opener`. */

const FONTE = "https://tpmtur.co.mz/nossas-politicas/";

const POLITICAS = [
  { titulo: "Política de Qualidade", Icone: Award },
  { titulo: "Política de Saúde e Segurança no Trabalho", Icone: ShieldCheck },
  { titulo: "Política de Responsabilidade Social", Icone: Globe2 },
  { titulo: "Política de Compliance", Icone: BadgeCheck },
  { titulo: "Política de Ética e Conduta Profissional", Icone: Scale },
  { titulo: "Política de Inclusão e Diversidade", Icone: Users },
  { titulo: "Política de Direitos Humanos", Icone: HeartHandshake },
  { titulo: "Política de Combate à Escravatura Moderna", Icone: Link2Off },
  { titulo: "Política de Recrutamento e Selecção Transparente", Icone: BadgeCheck },
];

export default function PoliticasPage() {
  useTpmMeta(
    "Nossas políticas — TPM-TUR",
    "As políticas que a TPM-TUR assume na sua actividade: qualidade, segurança, compliance, ética, inclusão e direitos humanos.",
  );

  return (
    <TpmPagina activa="/tpm-tur/nossas-politicas">
      <TpmIntro
        migalha="Nossas políticas"
        titulo="Como nos comprometemos a trabalhar."
        descricao="As nove políticas que a TPM-TUR assume na sua actividade — da qualidade do serviço à conduta de quem o presta."
      />

      <section className="bzlp-sec">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="bzlp-sechead left">
              <div className="bzlp-kicker left">Políticas institucionais</div>
              <h2 className="bzlp-h2 left">Nove compromissos</h2>
              <p className="bzlp-lead left">
                Cada política tem um documento próprio. O texto integral publicado pela
                empresa é o que vale, e prevalece sobre qualquer apresentação feita aqui.
              </p>
            </div>
          </Reveal>
          <div className="tpm-politicas">
            {POLITICAS.map(({ titulo, Icone }, i) => (
              <Reveal key={titulo} delay={(i % 3) * 60}>
                <article className="tpm-politica">
                  <span className="tpm-politica-ico"><Icone size={22} aria-hidden /></span>
                  <h3>{titulo}</h3>
                  <p>Documento institucional publicado pela TPM-TUR, S.A.</p>
                  <a href={FONTE} target="_blank" rel="noreferrer">
                    Ler a política <ArrowUpRight size={15} aria-hidden />
                  </a>
                </article>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <TpmCallout
        titulo="Tem uma questão sobre estas políticas?"
        texto={`Escreva para ${EMAIL} e a equipa encaminha o pedido para quem o pode responder.`}
        assunto="Questão sobre as políticas da TPM-TUR"
        cta="Contactar a TPM-TUR"
        secundario={{ to: "/tpm-tur/sobre-nos", label: "Sobre a TPM-TUR" }}
      />
    </TpmPagina>
  );
}
