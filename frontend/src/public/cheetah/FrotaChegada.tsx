import { useRef } from "react";
import { useInView } from "motion/react";

/* A frota a estacionar.
 *
 * Três viaturas recortadas da mesma fotografia, que entram pela direita e
 * travam nos seus lugares. Quando param, voltam a formar exactamente a fila da
 * fotografia original — as posições abaixo são as que cada uma ocupa nela, em
 * percentagem, e é isso que faz a fila fechar sem folgas nem sobreposições.
 *
 * PORQUE É QUE ISTO NÃO SÃO TRÊS FOTOGRAFIAS. Na fotografia as viaturas
 * TAPAM-SE umas às outras: a traseira de cada uma está escondida atrás da
 * seguinte. Recortes verdadeiramente independentes não existem ali. Por isso
 * cada uma foi cortada na fronteira de oclusão — acaba onde o nariz da
 * seguinte começa — e a ordem de desenho é de trás para a frente. Ver
 * `scripts/extrair-frota-cheetah.py`, que faz o recorte e é repetível.
 *
 * A CONSEQUÊNCIA PARA O MOVIMENTO: como as arestas de corte só ficam
 * escondidas quando as três estão nos seus lugares, o percurso é CURTO. Não
 * atravessam o ecrã — rolam o último metro e travam, que é o que estacionar
 * parece de perto. Um percurso longo deixaria as arestas à vista.
 *
 * É CSS e não JS. A chegada dispara uma vez, não se interrompe e não segue
 * gesto nenhum: uma transição faz isto, corre fora da thread principal e não
 * perde frames enquanto o resto da página ainda carrega. O JS aqui só decide
 * QUANDO, e mais nada.
 */

type Viatura = {
  f: string;
  /** Posição e tamanho dentro da fotografia original, em percentagem. */
  x: number; y: number; w: number;
  /** Quanto recua para entrar, e a ordem de chegada. A de trás chega primeiro
   *  e as da frente vão-na tapando — é assim que uma fila se forma. */
  de: number; ordem: number;
  alt: string;
};

const FROTA: Viatura[] = [
  { f: "sprinter.webp",  x: 1.698,  y: 42.662, w: 40.570, de: 16, ordem: 0,
    alt: "Mercedes-Benz Sprinter da Cheetah Express" },
  { f: "hiace-bus.webp", x: 41.722, y: 47.275, w: 29.351, de: 21, ordem: 1,
    alt: "Toyota Hiace de passageiros da Cheetah Express" },
  { f: "hiace-van.webp", x: 70.103, y: 49.686, w: 29.715, de: 26, ordem: 2,
    alt: "Toyota Hiace de transferes da Cheetah Express" },
];

/** A proporção da fotografia de origem. A caixa reserva esta altura antes de as
 *  imagens chegarem, para a página não saltar. */
const PROPORCAO = 1649 / 954;

export default function FrotaChegada() {
  const ref = useRef<HTMLDivElement | null>(null);
  /* `-120px` faz disparar um pouco antes de a faixa tocar a borda: quem rola a
     velocidade normal vê as viaturas a chegar, e não já estacionadas. */
  const chegou = useInView(ref, { once: true, margin: "-120px" });

  return (
    <div
      className="che-frota"
      ref={ref}
      data-chegou={chegou || undefined}
      style={{ aspectRatio: String(PROPORCAO) }}
    >
      {FROTA.map((v) => (
        <img
          key={v.f}
          className="che-frota-v"
          src={`/landing/cheetah/frota/${v.f}`}
          alt={v.alt}
          style={{
            left: `${v.x}%`,
            top: `${v.y}%`,
            width: `${v.w}%`,
            "--de": `${v.de}%`,
            "--ordem": v.ordem,
          } as React.CSSProperties}
          loading="lazy"
          decoding="async"
        />
      ))}
    </div>
  );
}
