import { ArrowUpRight } from "lucide-react";
import Reveal from "../landing/Reveal";
import TpmPagina, { TpmCallout, TpmIntro, pedido, useTpmMeta } from "./TpmChrome";

/* Serviços.
 *
 * Os cinco serviços são os da página oficial do operador. O texto que explica
 * o que indicar num pedido é novo, e de propósito não afirma preços, lotação,
 * comodidades nem disponibilidade — nada disso está confirmado pela operação,
 * e um site que promete o que a operação não confirmou cria uma reclamação. */

type Servico = {
  id: string;
  titulo: string;
  intro: string;
  texto: string;
  foto: string;
  alt: string;
  cta: string;
  assunto: string;
  brief: string[];
};

const SERVICOS: Servico[] = [
  {
    id: "autocarros",
    titulo: "Aluguer de autocarros",
    intro: "Executivos e normais. Uma solução para o seu grupo.",
    texto:
      "Escolha o transporte para uma deslocação de grupo, um evento ou uma viagem organizada. " +
      "A equipa TPM-TUR ajuda a identificar a viatura adequada ao percurso e ao número de passageiros.",
    foto: "/landing/tpm/coaches.webp",
    alt: "Autocarros executivos da TPM-TUR alinhados no parque",
    cta: "Pedir orçamento",
    assunto: "Orçamento - Aluguer de autocarro",
    brief: ["Percurso e pontos de embarque", "Número de passageiros", "Data de partida e de regresso"],
  },
  {
    id: "rent-a-car",
    titulo: "Rent-a-car",
    intro: "Uma viatura para o percurso que tem em mente.",
    texto:
      "Consulte a TPM-TUR sobre o aluguer de viaturas. Indique o período e a utilização pretendida " +
      "para receber informação sobre as opções, as condições e a disponibilidade.",
    foto: "/landing/tpm/suv.webp",
    alt: "Pick-up Mazda BT-50 da frota TPM-TUR, numa estrada junto à costa",
    cta: "Consultar disponibilidade",
    assunto: "Orçamento - Rent-a-car",
    brief: ["Datas e duração do aluguer", "Tipo de viatura pretendido", "Local de levantamento e entrega"],
  },
  {
    id: "excursoes",
    titulo: "Excursões",
    intro: "Reúna as pessoas. Comece a planear a viagem.",
    texto:
      "Organize o transporte da sua excursão com a TPM-TUR. Partilhe o destino e o programa para que " +
      "a equipa possa preparar uma proposta para o grupo.",
    foto: "/landing/tpm/coach.webp",
    alt: "Autocarro TPM-TUR para viagens de grupo",
    cta: "Planear uma excursão",
    assunto: "Orçamento - Excursão",
    brief: ["Destino e itinerário", "Tamanho do grupo", "Datas e horários previstos"],
  },
  {
    id: "transfers",
    titulo: "Transfers e shuttle",
    intro: "Entre o ponto de partida e o seu compromisso.",
    texto:
      "Peça uma solução de transporte para a deslocação de pessoas entre locais definidos. " +
      "Partilhe os pontos de recolha e chegada e os horários de que necessita.",
    foto: "/landing/tpm/minibuses.webp",
    alt: "Viaturas Quantum da TPM-TUR",
    cta: "Pedir um transfer",
    assunto: "Pedido de transfer",
    brief: ["Pontos de recolha e chegada", "Horários das deslocações", "Passageiros e bagagem prevista"],
  },
  {
    id: "trabalhadores",
    titulo: "Transporte de trabalhadores",
    intro: "A mobilidade da sua equipa faz parte do trabalho.",
    texto:
      "Apresente as necessidades de deslocação dos seus trabalhadores. A TPM-TUR disponibiliza este " +
      "serviço para empresas; a proposta é preparada de acordo com o percurso e a operação pretendida.",
    foto: "/landing/tpm/coaster.webp",
    alt: "Coaster da frota TPM-TUR",
    cta: "Falar com a equipa",
    assunto: "Orçamento - Transporte de trabalhadores",
    brief: ["Percursos e pontos de recolha", "Turnos e frequência", "Número de colaboradores"],
  },
];

export default function ServicosPage() {
  useTpmMeta(
    "Serviços — TPM-TUR",
    "Aluguer de autocarros, rent-a-car, excursões, transfers e transporte de trabalhadores. Conheça os serviços TPM-TUR.",
  );

  return (
    <TpmPagina activa="/tpm-tur/servicos">
      <TpmIntro
        migalha="Serviços"
        titulo="Cinco serviços. Um percurso de cada vez."
        descricao="Soluções para passageiros, empresas e grupos. Fale connosco sobre o seu próximo percurso."
      />

      <div className="bzlp-wrap" style={{ marginTop: -46, position: "relative", zIndex: 2 }}>
        <nav className="tpm-indice" aria-label="Serviços nesta página">
          {SERVICOS.map((s) => (
            <a key={s.id} href={`#${s.id}`}>{s.titulo}</a>
          ))}
        </nav>
      </div>

      <section className="bzlp-sec">
        <div className="bzlp-wrap">
          <div className="tpm-servicos-lista">
            {SERVICOS.map((s, i) => (
              <Reveal key={s.id} className={i % 2 === 1 ? "tpm-invertido" : ""}>
                <article className="tpm-servico-bloco" id={s.id}>
                  <div className="tpm-servico-foto">
                    <img src={s.foto} alt={s.alt} width={1200} height={750} loading="lazy" decoding="async" />
                  </div>
                  <div>
                    <div className="bzlp-kicker left">Serviço {String(i + 1).padStart(2, "0")}</div>
                    <h2>{s.titulo}</h2>
                    <p className="tpm-servico-intro">{s.intro}</p>
                    <p className="tpm-servico-texto">{s.texto}</p>
                    <p className="tpm-servico-brief-rotulo">No pedido, indique:</p>
                    <ul className="tpm-servico-brief">
                      {s.brief.map((b) => <li key={b}>{b}</li>)}
                    </ul>
                    <a href={pedido(s.assunto)} className="bzlp-btn">
                      {s.cta} <ArrowUpRight size={16} aria-hidden />
                    </a>
                  </div>
                </article>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <TpmCallout
        titulo="Diga-nos para onde quer ir."
        texto="Quanto mais souber sobre o percurso, mais rápida é a resposta. A equipa confirma condições e disponibilidade — nada é adjudicado automaticamente."
        assunto="Pedido de orçamento TPM-TUR"
        secundario={{ to: "/tpm-tur/frota", label: "Ver a frota" }}
      />
    </TpmPagina>
  );
}
