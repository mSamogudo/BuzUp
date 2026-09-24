import { ArrowUpRight } from "lucide-react";
import Reveal from "../landing/Reveal";
import TpmPagina, { TpmCallout, TpmIntro, pedido, useTpmMeta } from "./TpmChrome";

/* Nossa frota.
 *
 * As quatro categorias são as do portefólio oficial. A ficha técnica —
 * lotação, bagagem, comodidades — está preparada mas VAZIA: a operação ainda
 * não confirmou números, e o repositório só tem `random.choice([28,32,45,50])`
 * no seeding de demonstração, que é dado falso. Quando os números chegarem,
 * preenche-se `ficha` e a tabela aparece sozinha; até lá a página diz o que
 * sabe e manda confirmar com a equipa, em vez de inventar. */

type Viatura = {
  id: string;
  nome: string;
  etiqueta: string;
  foto: string;
  alt: string;
  texto: string;
  uso: string;
  ficha?: { rotulo: string; valor: string }[];
};

const FROTA: Viatura[] = [
  {
    id: "autocarros",
    nome: "Autocarros",
    etiqueta: "Executivos e normais",
    foto: "/landing/tpm/coach.webp",
    alt: "Autocarro executivo da TPM-TUR estacionado, visto de frente",
    texto:
      "Autocarros executivos e normais — a escolha para percursos longos e para mover um grupo inteiro de uma vez.",
    uso: "Viagens, excursões e aluguer com motorista.",
  },
  {
    id: "coaster",
    nome: "Coaster",
    etiqueta: "Midibus",
    foto: "/landing/tpm/coaster.webp",
    alt: "Dois midibuses Coaster da TPM-TUR lado a lado",
    texto:
      "Os midibuses Coaster, para quando o grupo não enche um autocarro mas já não cabe numa carrinha.",
    uso: "Transfers, excursões e deslocações de equipas.",
  },
  {
    id: "quantum",
    nome: "Quantum",
    etiqueta: "Minibus",
    foto: "/landing/tpm/minibuses.webp",
    alt: "Minibuses Quantum da TPM-TUR alinhados no parque",
    texto: "Os minibuses Quantum são a opção mais ágil da frota, feita para grupos pequenos.",
    uso: "Transfers, shuttle e transporte de trabalhadores.",
  },
  {
    id: "suv",
    nome: "SUV",
    etiqueta: "Rent-a-car",
    foto: "/landing/tpm/suv.webp",
    alt: "Pick-up Mazda BT-50 da categoria SUV da TPM-TUR, numa estrada junto à costa",
    texto:
      "A categoria de ligeiros do rent-a-car, para quem precisa da viatura inteira e não de um lugar no autocarro.",
    uso: "Aluguer de viatura, mediante consulta de condições e disponibilidade.",
  },
];

const PASSOS = [
  { n: "01", h: "Diga o percurso", p: "Origem, destino e paragens previstas. A distância condiciona a categoria." },
  { n: "02", h: "Conte o grupo", p: "O número de passageiros e a bagagem determinam a lotação necessária." },
  { n: "03", h: "Confirme connosco", p: "A equipa confirma lotação, comodidades e disponibilidade da viatura." },
];

export default function FrotaPage() {
  useTpmMeta(
    "Nossa frota — TPM-TUR",
    "Conheça os autocarros, Coaster, Quantum e SUV da frota TPM-TUR e consulte a disponibilidade com a nossa equipa.",
  );

  return (
    <TpmPagina activa="/tpm-tur/frota">
      <TpmIntro
        migalha="Nossa frota"
        titulo="Conheça a frota. Imagine a viagem."
        descricao="Diferentes viaturas para diferentes percursos. Explore as quatro categorias e encontre a solução com a nossa equipa."
      />

      <div className="bzlp-wrap" style={{ marginTop: -46, position: "relative", zIndex: 2 }}>
        <nav className="tpm-indice" aria-label="Categorias nesta página">
          {FROTA.map((v) => (
            <a key={v.id} href={`#${v.id}`}>{v.nome}</a>
          ))}
        </nav>
      </div>

      <section className="bzlp-sec">
        <div className="bzlp-wrap">
          <div className="tpm-catalogo">
            {FROTA.map((v, i) => (
              <Reveal key={v.id} className={i % 2 === 1 ? "tpm-invertido" : ""}>
                <article className="tpm-frota-entrada" id={v.id}>
                  <div className="tpm-frota-foto">
                    <img src={v.foto} alt={v.alt} width={1200} height={750} loading="lazy" decoding="async" />
                  </div>
                  <div className="tpm-frota-corpo">
                    <div className="tpm-frota-topo">
                      <h2>{v.nome}</h2>
                      <span className="tpm-frota-etiqueta">{v.etiqueta}</span>
                    </div>
                    <p>{v.texto}</p>
                    <p>{v.uso}</p>
                    {v.ficha && (
                      <dl className="tpm-frota-ficha">
                        {v.ficha.map((f) => (
                          <div key={f.rotulo}>
                            <dt>{f.rotulo}</dt>
                            <dd>{f.valor}</dd>
                          </div>
                        ))}
                      </dl>
                    )}
                    <a href={pedido(`Disponibilidade - ${v.nome}`)} className="bzlp-btn outline">
                      Consultar disponibilidade <ArrowUpRight size={16} aria-hidden />
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
                <div className="bzlp-kicker left">Como escolher</div>
                <h2>Uma viatura adequada<br />à sua necessidade.</h2>
              </div>
              <div className="tpm-escolher-passos">
                {PASSOS.map((p) => (
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
        titulo="Precisa de uma viatura para um grupo?"
        texto="Indique o percurso e o número de passageiros — confirmamos a viatura disponível."
        assunto="Orçamento - Aluguer de autocarro"
        secundario={{ to: "/tpm-tur/servicos", label: "Ver os serviços" }}
      />
    </TpmPagina>
  );
}
