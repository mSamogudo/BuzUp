import {
  ArrowUpRight, Award, BadgeCheck, Globe2, HeartHandshake, Link2Off, Scale, ShieldCheck, Users,
} from "lucide-react";
import Reveal from "../landing/Reveal";
import TpmPagina, { EMAIL, TpmCallout, TpmIntro, useTpmMeta } from "./TpmChrome";
import { useTpmCopy } from "./tpm-copy";

/* Nossas políticas.
 *
 * As nove políticas são as que a TPM-TUR publica. NÃO há resumo por baixo de
 * cada título: o texto integral é da empresa e é ele que vale — inventar um
 * resumo de uma política de compliance ou de direitos humanos seria pôr na
 * boca da empresa um compromisso que ela não escreveu. Cada cartão leva à
 * fonte oficial.
 *
 * Os documentos estão publicados em português. Com a página em inglês, os
 * títulos traduzidos são uma tradução de trabalho — a ligação continua a levar
 * ao original, que é o que vale.
 *
 * O `rel="noreferrer"` acompanha o `target="_blank"` em todas: sem ele a
 * página aberta recebe `window.opener`. */

const FONTE = "https://tpmtur.co.mz/nossas-politicas/";

const ICONES = [Award, ShieldCheck, Globe2, BadgeCheck, Scale, Users, HeartHandshake, Link2Off, BadgeCheck];

export default function PoliticasPage() {
  const { t } = useTpmCopy();
  const p = t.politicas;
  useTpmMeta(p.meta.titulo, p.meta.descricao);

  return (
    <TpmPagina activa="/tpm-tur/nossas-politicas">
      <TpmIntro migalha={p.migalha} titulo={p.titulo} descricao={p.descricao} />

      <section className="bzlp-sec">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="bzlp-sechead left">
              <div className="bzlp-kicker left">{p.kicker}</div>
              <h2 className="bzlp-h2 left">{p.h2}</h2>
              <p className="bzlp-lead left">{p.lead}</p>
            </div>
          </Reveal>
          <div className="tpm-politicas">
            {p.itens.map((titulo, i) => {
              const Icone = ICONES[i];
              return (
                <Reveal key={titulo} delay={(i % 3) * 60}>
                  <article className="tpm-politica">
                    <span className="tpm-politica-ico"><Icone size={22} aria-hidden /></span>
                    <h3>{titulo}</h3>
                    <p>{p.subtitulo}</p>
                    <a href={FONTE} target="_blank" rel="noreferrer">
                      {p.ler} <ArrowUpRight size={15} aria-hidden />
                    </a>
                  </article>
                </Reveal>
              );
            })}
          </div>
        </div>
      </section>

      <TpmCallout
        titulo={p.callout.h2}
        texto={p.callout.p.replace("{email}", EMAIL)}
        assunto="Questão sobre as políticas da TPM-TUR"
        cta={p.callout.cta}
        secundario={{ to: "/tpm-tur/sobre-nos", label: p.callout.secundario }}
      />
    </TpmPagina>
  );
}
