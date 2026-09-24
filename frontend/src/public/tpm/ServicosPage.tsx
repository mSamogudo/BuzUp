import { ArrowUpRight } from "lucide-react";
import Reveal from "../landing/Reveal";
import TpmPagina, { TpmCallout, TpmIntro, pedido, useTpmMeta } from "./TpmChrome";
import { useTpmCopy } from "./tpm-copy";

/* Serviços.
 *
 * Os cinco serviços são os da página oficial do operador. O texto que explica
 * o que indicar num pedido é novo, e de propósito não afirma preços, lotação,
 * comodidades nem disponibilidade — nada disso está confirmado pela operação,
 * e um site que promete o que a operação não confirmou cria uma reclamação.
 *
 * Os `id` e os assuntos de email ficam em português nos dois idiomas: os
 * primeiros são âncoras de URL que não devem mudar com o idioma, e os segundos
 * são o rótulo por onde a TPM-TUR encaminha o pedido. */

const IDS = ["autocarros", "rent-a-car", "excursoes", "transfers", "trabalhadores"] as const;
const FOTOS = [
  "/landing/tpm/coaches.webp",
  "/landing/tpm/suv.webp",
  "/landing/tpm/coach.webp",
  "/landing/tpm/minibuses.webp",
  "/landing/tpm/coaster.webp",
];
const ASSUNTOS = [
  "Orçamento - Aluguer de autocarro",
  "Orçamento - Rent-a-car",
  "Orçamento - Excursão",
  "Pedido de transfer",
  "Orçamento - Transporte de trabalhadores",
];

export default function ServicosPage() {
  const { t } = useTpmCopy();
  const s = t.servicos;
  useTpmMeta(s.meta.titulo, s.meta.descricao);

  return (
    <TpmPagina activa="/tpm-tur/servicos">
      <TpmIntro migalha={s.migalha} titulo={s.titulo} descricao={s.descricao} />

      <div className="bzlp-wrap" style={{ marginTop: -46, position: "relative", zIndex: 2 }}>
        <nav className="tpm-indice" aria-label={s.indice}>
          {s.itens.map((item, i) => (
            <a key={IDS[i]} href={`#${IDS[i]}`}>{item.titulo}</a>
          ))}
        </nav>
      </div>

      <section className="bzlp-sec">
        <div className="bzlp-wrap">
          <div className="tpm-servicos-lista">
            {s.itens.map((item, i) => (
              <Reveal key={IDS[i]} className={i % 2 === 1 ? "tpm-invertido" : ""}>
                <article className="tpm-servico-bloco" id={IDS[i]}>
                  <div className="tpm-servico-foto">
                    <img src={FOTOS[i]} alt={item.alt} width={1200} height={750} loading="lazy" decoding="async" />
                  </div>
                  <div>
                    <div className="bzlp-kicker left">{s.servico} {String(i + 1).padStart(2, "0")}</div>
                    <h2>{item.titulo}</h2>
                    <p className="tpm-servico-intro">{item.intro}</p>
                    <p className="tpm-servico-texto">{item.texto}</p>
                    <p className="tpm-servico-brief-rotulo">{s.rotuloBrief}</p>
                    <ul className="tpm-servico-brief">
                      {item.brief.map((b) => <li key={b}>{b}</li>)}
                    </ul>
                    <a href={pedido(ASSUNTOS[i])} className="bzlp-btn">
                      {item.cta} <ArrowUpRight size={16} aria-hidden />
                    </a>
                  </div>
                </article>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <TpmCallout
        titulo={s.callout.h2}
        texto={s.callout.p}
        assunto="Pedido de orçamento TPM-TUR"
        secundario={{ to: "/tpm-tur/frota", label: t.comum.verFrota }}
      />
    </TpmPagina>
  );
}
