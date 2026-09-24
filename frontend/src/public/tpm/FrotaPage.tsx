import { ArrowUpRight } from "lucide-react";
import Reveal from "../landing/Reveal";
import TpmPagina, { TpmCallout, TpmIntro, pedido, useTpmMeta } from "./TpmChrome";
import { useTpmCopy } from "./tpm-copy";

/* Nossa frota.
 *
 * As quatro categorias são as do portefólio oficial. A ficha técnica —
 * lotação, bagagem, comodidades — não existe aqui: a operação ainda não
 * confirmou números, e o repositório só tem `random.choice([28,32,45,50])` no
 * seeding de demonstração, que é dado falso. A página diz o que sabe e manda
 * confirmar com a equipa, em vez de inventar. */

const IDS = ["autocarros", "coaster", "quantum", "suv"] as const;
const FOTOS = [
  "/landing/tpm/coach.webp",
  "/landing/tpm/coaster.webp",
  "/landing/tpm/minibuses.webp",
  "/landing/tpm/suv.webp",
];

export default function FrotaPage() {
  const { t } = useTpmCopy();
  const f = t.frota;
  useTpmMeta(f.meta.titulo, f.meta.descricao);

  return (
    <TpmPagina activa="/tpm-tur/frota">
      <TpmIntro migalha={f.migalha} titulo={f.titulo} descricao={f.descricao} />

      <div className="bzlp-wrap" style={{ marginTop: -46, position: "relative", zIndex: 2 }}>
        <nav className="tpm-indice" aria-label={f.indice}>
          {f.itens.map((v, i) => (
            <a key={IDS[i]} href={`#${IDS[i]}`}>{v.nome}</a>
          ))}
        </nav>
      </div>

      <section className="bzlp-sec">
        <div className="bzlp-wrap">
          <div className="tpm-catalogo">
            {f.itens.map((v, i) => (
              <Reveal key={IDS[i]} className={i % 2 === 1 ? "tpm-invertido" : ""}>
                <article className="tpm-frota-entrada" id={IDS[i]}>
                  <div className="tpm-frota-foto">
                    <img src={FOTOS[i]} alt={v.alt} width={1200} height={750} loading="lazy" decoding="async" />
                  </div>
                  <div className="tpm-frota-corpo">
                    <div className="tpm-frota-topo">
                      <h2>{v.nome}</h2>
                      <span className="tpm-frota-etiqueta">{v.etiqueta}</span>
                    </div>
                    <p>{v.texto}</p>
                    <p>{v.uso}</p>
                    <a href={pedido(`Disponibilidade - ${v.nome}`)} className="bzlp-btn outline">
                      {t.comum.consultarDisponibilidade} <ArrowUpRight size={16} aria-hidden />
                    </a>
                  </div>
                </article>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="bzlp-sec alt">
        <div className="bzlp-wrap">
          <Reveal>
            <div className="tpm-escolher">
              <div>
                <div className="bzlp-kicker left">{f.escolher.kicker}</div>
                <h2>{f.escolher.h2}<br />{f.escolher.h2b}</h2>
              </div>
              <div className="tpm-escolher-passos">
                {f.escolher.passos.map((p) => (
                  <div key={p.n}>
                    <b>{p.n}</b>
                    <h3>{p.h}</h3>
                    <p>{p.p}</p>
                  </div>
                ))}
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      <TpmCallout
        titulo={f.callout.h2}
        texto={f.callout.p}
        assunto="Orçamento - Aluguer de autocarro"
        secundario={{ to: "/tpm-tur/servicos", label: t.comum.verServicos }}
      />
    </TpmPagina>
  );
}
