import { useRef } from "react";
import {
  motion, useMotionTemplate, useMotionValue, useReducedMotion, useScroll,
  useSpring, useTransform,
} from "motion/react";

/**
 * A composição do hero — a carrinha, o passageiro, a praia — com paralaxe ao
 * rolar e uma inclinação que segue o ponteiro.
 *
 * PORQUE É QUE ISTO É JS E O RESTO NÃO. As duas coisas que faz são as duas que
 * o CSS não sabe fazer bem hoje: ligar uma transformação à POSIÇÃO do scroll
 * (o `animation-timeline` do CSS ainda não chega ao Safari nem ao Firefox
 * estáveis) e seguir o ponteiro com mola. Tudo o resto neste site é CSS.
 *
 * MOLA E NÃO CURVA. Ambos os movimentos são interrompíveis — a pessoa pode
 * inverter o scroll ou atirar o rato para o outro lado a meio. Uma curva de
 * duração fixa reinicia do zero e salta; uma mola leva a velocidade consigo
 * através da interrupção, que é o que faz isto parecer que tem peso.
 *
 * O `bounce` fica em 0.15: o suficiente para não parecer amortecido, longe do
 * ressalto que faria uma fotografia institucional parecer um brinquedo.
 *
 * A INCLINAÇÃO é decoração de página de marca — e é o único sítio onde isso se
 * admite. Está atrás de duas portas: rato a sério (num telemóvel o `hover` é
 * mentira) e quem não pediu menos movimento.
 */
export default function HeroArte({ src, alt }: { src: string; alt: string }) {
  const ref = useRef<HTMLDivElement | null>(null);
  const reduzido = useReducedMotion();

  /* Paralaxe: a imagem sobe mais devagar do que a página. É o que dá a
     sensação de que está atrás, e não colada ao texto. 80px ao longo dos
     primeiros 600px de scroll — mais do que isso e a composição sai da chapa.
     Aos 600px o hero já saiu do ecrã, por isso não há nada a ganhar depois.

     USA `scrollY` DIRECTAMENTE, e não `useScroll({ target })`, por ser a
     ferramenta mais barata que serve: este elemento está sempre no topo da
     página, portanto a posição de scroll JÁ É o progresso dele. Medir o alvo
     seria maquinaria para descobrir uma coisa que se sabe de antemão.

     SEM MOLA, e isso foi medido e não escolhido. Pus lá uma primeiro, por
     reflexo; o que ela fez foi pôr a imagem a perseguir o scroll com atraso —
     numa descida de 800px a imagem tinha andado 17 dos 80px que lhe cabiam.
     Uma paralaxe é um mapeamento directo de POSIÇÃO: o scroll já chega suave e
     contínuo do browser, e não há aqui gesto nenhum a interromper. Amortecer
     um valor que já é suave não acrescenta profundidade, acrescenta atraso.
     A mola fica para a inclinação, lá em baixo, onde há mesmo um ponteiro a
     saltar e a mudar de direcção. */
  const { scrollY } = useScroll();
  const desloca = useTransform(scrollY, [0, 600], [0, -80], { clamp: true });

  /* Inclinação pelo ponteiro. Os valores crus vão de -0.5 a 0.5 e a mola
     transforma-os em graus — assim a mola trabalha sobre um número pequeno e
     estável, e não sobre pixels que mudam com o tamanho do ecrã. */
  const px = useMotionValue(0);
  const py = useMotionValue(0);
  const mola = { stiffness: 150, damping: 20, mass: 0.5 };
  const rotX = useSpring(useTransform(py, [-0.5, 0.5], [7, -7]), mola);
  const rotY = useSpring(useTransform(px, [-0.5, 0.5], [-9, 9]), mola);

  /* String de transformação inteira, e não as abreviaturas `x`/`rotateX` do
     Motion: só esta forma vai para a GPU. Com as abreviaturas, a imagem perde
     frames assim que a página tem trabalho a fazer. */
  const transform = useMotionTemplate`translate3d(0, ${desloca}px, 0) perspective(900px) rotateX(${rotX}deg) rotateY(${rotY}deg)`;

  const seguir = (e: React.PointerEvent<HTMLDivElement>) => {
    if (reduzido || e.pointerType !== "mouse") return;
    const r = e.currentTarget.getBoundingClientRect();
    px.set((e.clientX - r.left) / r.width - 0.5);
    py.set((e.clientY - r.top) / r.height - 0.5);
  };
  const largar = () => { px.set(0); py.set(0); };

  return (
    <div
      className="che-hero-art"
      ref={ref}
      onPointerMove={seguir}
      onPointerLeave={largar}
    >
      <motion.img
        src={src}
        alt={alt}
        width={1000}
        height={1444}
        decoding="async"
        style={reduzido ? undefined : { transform, willChange: "transform" }}
      />
    </div>
  );
}
