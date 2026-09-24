import { Link } from "react-router-dom";
import { ArrowUpRight, Check, Compass, Target } from "lucide-react";
import Reveal from "../landing/Reveal";
import TpmPagina, { TpmCallout, TpmIntro, useTpmMeta } from "./TpmChrome";
import { useTpmCopy } from "./tpm-copy";

/* Sobre nós.
 *
 * Os factos são os da apresentação institucional da TPM-TUR: a parceria
 * público-privada, o propósito que lhe deu origem, missão, visão e os oito
 * valores. Não se acrescenta história, datas nem números que a empresa não
 * tenha publicado.
 *
 * O assunto do email fica SEMPRE em português, mesmo com a página em inglês:
 * é o rótulo por onde a TPM-TUR encaminha o pedido na sua caixa de entrada,
 * e essa trabalha em português. */

export default function SobreNosPage() {
  const { t } = useTpmCopy();
  const s = t.sobre;
  useTpmMeta(s.meta.titulo, s.meta.descricao);

  return (
    <TpmPagina activa="/tpm-tur/sobre-nos">
      <TpmIntro migalha={s.migalha} titulo={s.titulo} descricao={s.descricao} />

      <section className="bzlp-sec">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="tpm-historia">
              <div className="tpm-historia-foto">
                <img src="/landing/tpm/coaches.webp" alt={s.parceria.fotoAlt}
                  width={1200} height={750} loading="lazy" decoding="async" />
              </div>
              <div>
                <div className="bzlp-kicker left">{s.parceria.kicker}</div>
                <h2>{s.parceria.h2}<br />{s.parceria.h2b}</h2>
                <p>{s.parceria.p1}</p>
                <p>{s.parceria.p2}</p>
                <Link to="/tpm-tur/frota" className="bzlp-ghost" style={{ paddingLeft: 0, marginTop: 8 }}>
                  {s.parceria.link} <ArrowUpRight size={16} aria-hidden />
                </Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      <section className="bzlp-sec alt">
        <div className="bzlp-wrap">
          <div className="tpm-proposito">
            <Reveal>
              <article>
                <span className="tpm-proposito-ico"><Target size={26} aria-hidden /></span>
                <h2>{s.missao.h}</h2>
                <p>{s.missao.p}</p>
              </article>
            </Reveal>
            <Reveal delay={80}>
              <article className="tpm-proposito-visao">
                <span className="tpm-proposito-ico"><Compass size={26} aria-hidden /></span>
                <h2>{s.visao.h}</h2>
                <p>{s.visao.p}</p>
              </article>
            </Reveal>
          </div>
        </div>
      </section>

      <section className="bzlp-sec">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="tpm-valores">
              <div>
                <div className="bzlp-kicker left">{s.valores.kicker}</div>
                <h2>{s.valores.h2}<br />{s.valores.h2b}</h2>
                <p>{s.valores.lead}</p>
              </div>
              <ul>
                {s.valores.itens.map((v) => (
                  <li key={v}><Check size={19} aria-hidden strokeWidth={2.2} />{v}</li>
                ))}
              </ul>
            </div>
          </Reveal>
        </div>
      </section>

      <section className="bzlp-sec alt">
        <div className="bzlp-wrap">
          <Reveal>
            <h2 className="bzlp-h2 left">{s.parceiros.h2}</h2>
            <div className="tpm-parceiros-grid">
              {s.parceiros.itens.map((p) => (
                <div key={p.sigla}>
                  <strong>{p.sigla}</strong>
                  <span>{p.nome}</span>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      <TpmCallout
        titulo={s.callout.h2}
        texto={s.callout.p}
        assunto="Pedido de orçamento TPM-TUR"
        secundario={{ to: "/tpm-tur/servicos", label: t.comum.verServicos }}
      />
    </TpmPagina>
  );
}
