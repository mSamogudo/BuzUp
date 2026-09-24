import { Link } from "react-router-dom";
import { ArrowUpRight, Check, Compass, Target } from "lucide-react";
import Reveal from "../landing/Reveal";
import TpmPagina, { TpmCallout, TpmIntro, useTpmMeta } from "./TpmChrome";

/* Sobre nós.
 *
 * Os factos são os da apresentação institucional da TPM-TUR: a parceria
 * público-privada, o propósito que lhe deu origem, missão, visão e os oito
 * valores. Não se acrescenta história, datas nem números que a empresa não
 * tenha publicado. */

const VALORES = [
  "Comprometimento",
  "Respeito",
  "Integridade",
  "Humildade",
  "Empatia",
  "Educação",
  "Solidariedade",
  "Ética",
];

const PARCEIROS = [
  { sigla: "EMTPM", nome: "Empresa Municipal Transportes Públicos de Maputo" },
  { sigla: "ETM", nome: "Empresa Municipal de Transportes Públicos da Matola" },
  { sigla: "Sky Rent", nome: "Sky Rent, Lda." },
];

export default function SobreNosPage() {
  useTpmMeta(
    "Sobre nós — TPM-TUR",
    "Conheça a TPM-TUR, a sua parceria público-privada, missão, visão e valores no transporte e turismo em Moçambique.",
  );

  return (
    <TpmPagina activa="/tpm-tur/sobre-nos">
      <TpmIntro
        migalha="Sobre nós"
        titulo="Somos TPM-TUR. Transporte e turismo."
        descricao="Uma empresa moçambicana dedicada à mobilidade de pessoas, empresas e grupos."
      />

      <section className="bzlp-sec">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="tpm-historia">
              <div className="tpm-historia-foto">
                <img
                  src="/landing/tpm/coaches.webp"
                  alt="Autocarros com a identidade da TPM-TUR alinhados no parque"
                  width={1200}
                  height={900}
                  loading="lazy"
                  decoding="async"
                />
              </div>
              <div>
                <div className="bzlp-kicker left">A parceria</div>
                <h2>Uma parceria para<br />pôr pessoas em movimento.</h2>
                <p>
                  A TPM-TUR, S.A. resulta de uma parceria público-privada entre a Empresa
                  Municipal Transportes Públicos de Maputo (EMTPM), a Empresa Municipal de
                  Transportes Públicos da Matola (ETM) e a Sky Rent, Lda.
                </p>
                <p>
                  A parceria foi criada para rentabilizar o investimento numa frota de
                  autocarros executivos, com gestão independente e autónoma.
                </p>
                <Link to="/tpm-tur/frota" className="bzlp-ghost" style={{ paddingLeft: 0, marginTop: 8 }}>
                  Conheça a nossa frota <ArrowUpRight size={16} aria-hidden />
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
                <h2>A nossa missão</h2>
                <p>
                  Disponibilizar serviços de aluguer e transporte que tratem os clientes
                  com dignidade e valorizem a segurança e o conforto.
                </p>
              </article>
            </Reveal>
            <Reveal delay={80}>
              <article className="tpm-proposito-visao">
                <span className="tpm-proposito-ico"><Compass size={26} aria-hidden /></span>
                <h2>A nossa visão</h2>
                <p>
                  Tornar a TPM-TUR uma referência no aluguer de autocarros executivos,
                  correspondendo às expectativas dos seus clientes.
                </p>
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
                <div className="bzlp-kicker left">Valores</div>
                <h2>Os valores<br />que nos orientam.</h2>
                <p>Princípios que a TPM-TUR assume na sua apresentação institucional.</p>
              </div>
              <ul>
                {VALORES.map((v) => (
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
            <h2 className="bzlp-h2 left">Uma parceria público-privada.</h2>
            <div className="tpm-parceiros-grid">
              {PARCEIROS.map((p) => (
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
        titulo="Fale com a nossa equipa."
        texto="Indique o percurso, as datas e o número de passageiros — respondemos com as opções disponíveis."
        assunto="Pedido de orçamento TPM-TUR"
        secundario={{ to: "/tpm-tur/servicos", label: "Ver os serviços" }}
      />
    </TpmPagina>
  );
}
