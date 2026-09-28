import { useEffect, useRef } from "react";
import { motion, useMotionTemplate, useMotionValue, useReducedMotion, useScroll, useSpring, useTransform } from "motion/react";

/**
 * As manchas de chita, as riscas e os sinais que o site oficial espalha pela
 * chapa do hero.
 *
 * PURAMENTE DECORATIVO — `aria-hidden`, sem texto e sem eventos. Um leitor de
 * ecrã não vê nada disto, que é o correcto: não leva informação nenhuma.
 *
 * TRÊS CAMADAS A VELOCIDADES DIFERENTES. É daí que vem a profundidade: com
 * tudo a mover-se ao mesmo ritmo lia-se como um fundo colado, e não como
 * camadas. As da frente andam mais do que as de trás, como na janela de um
 * carro. Cada camada responde ao scroll E ao ponteiro.
 *
 * MOLA AQUI, ao contrário do paralaxe da carrinha. A diferença é o gesto: o
 * ponteiro salta, muda de direcção e pode sair do ecrã a meio, e é isso que
 * uma mola trata bem — leva a velocidade consigo em vez de reiniciar. O
 * scroll, esse, já chega suave e entra sem amortecimento.
 */

/* As manchas geradas uma vez, fora do componente: são constantes e não têm de
   voltar a ser sorteadas a cada render. Os valores são à mão e não aleatórios
   — uma chita tem manchas de tamanhos diferentes, mas não caóticas. */
const MANCHAS_A = [
  [22, 18, 13, 9, -18], [58, 10, 9, 7, 24], [88, 30, 12, 8, -8],
  [16, 52, 11, 8, 32], [50, 46, 14, 10, -24], [84, 64, 10, 7, 12],
  [30, 82, 12, 9, -30], [66, 92, 9, 7, 18],
] as const;
const MANCHAS_B = [
  [18, 22, 15, 11, -14], [62, 14, 11, 8, 28], [40, 56, 13, 9, -20],
  [80, 72, 12, 9, 10], [24, 86, 10, 8, -26],
] as const;

function Manchas({ pontos, cor }: { pontos: readonly (readonly number[])[]; cor: string }) {
  return (
    <svg viewBox="0 0 100 100" aria-hidden focusable="false">
      {pontos.map(([cx, cy, rx, ry, rot], i) => (
        <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill={cor} key={i}
          transform={`rotate(${rot} ${cx} ${cy})`} />
      ))}
    </svg>
  );
}

export default function HeroDecoracoes() {
  const reduzido = useReducedMotion();
  const alvo = useRef<HTMLDivElement | null>(null);

  /* Sem mola: o scroll já chega contínuo do browser. */
  const { scrollY } = useScroll();
  const s1 = useTransform(scrollY, [0, 700], [0, 110], { clamp: true });
  const s2 = useTransform(scrollY, [0, 700], [0, 62], { clamp: true });
  const s3 = useTransform(scrollY, [0, 700], [0, 28], { clamp: true });

  /* Com mola: o ponteiro é um gesto, salta e inverte. */
  const px = useMotionValue(0);
  const py = useMotionValue(0);
  const mola = { stiffness: 120, damping: 18, mass: 0.4 };
  const p1x = useSpring(useTransform(px, [-0.5, 0.5], [26, -26]), mola);
  const p1y = useSpring(useTransform(py, [-0.5, 0.5], [18, -18]), mola);
  const p2x = useSpring(useTransform(px, [-0.5, 0.5], [-16, 16]), mola);
  const p2y = useSpring(useTransform(py, [-0.5, 0.5], [-11, 11]), mola);
  const p3x = useSpring(useTransform(px, [-0.5, 0.5], [9, -9]), mola);

  /* String de transformação inteira, e não as abreviaturas do Motion: só esta
     forma vai para a GPU. Com `x`/`y`, estas cinco camadas perdiam frames
     assim que a página tivesse trabalho a fazer. */
  const t1 = useMotionTemplate`translate3d(${p1x}px, calc(${s1}px + ${p1y}px), 0)`;
  const t2 = useMotionTemplate`translate3d(${p2x}px, calc(${s2}px + ${p2y}px), 0)`;
  const t3 = useMotionTemplate`translate3d(${p3x}px, ${s3}px, 0)`;

  /* O ponteiro lê-se na JANELA e não neste elemento: a decoração está por trás
     do texto e do cartão de pesquisa, e com `pointer-events: none` nunca
     receberia um `pointermove` próprio. */
  useEffect(() => {
    if (reduzido) return;
    const mover = (e: PointerEvent) => {
      if (e.pointerType !== "mouse") return;
      px.set(e.clientX / window.innerWidth - 0.5);
      py.set(e.clientY / window.innerHeight - 0.5);
    };
    window.addEventListener("pointermove", mover, { passive: true });
    return () => window.removeEventListener("pointermove", mover);
  }, [reduzido, px, py]);

  const estilo = (t: typeof t1) => (reduzido ? undefined : { transform: t, willChange: "transform" as const });

  return (
    <div className="che-hero-deco" aria-hidden ref={alvo}>
      <motion.div className="che-deco-manchas-1" style={estilo(t1)}>
        <Manchas pontos={MANCHAS_A} cor="#141618" />
      </motion.div>
      <motion.div className="che-deco-manchas-2" style={estilo(t2)}>
        <Manchas pontos={MANCHAS_B} cor="#141618" />
      </motion.div>
      <motion.div className="che-deco-riscas" style={estilo(t3)}>
        <svg viewBox="0 0 100 100" aria-hidden focusable="false">
          {Array.from({ length: 9 }, (_, i) => (
            <line key={i} x1={i * 11} y1="100" x2={i * 11 + 40} y2="0"
              stroke="#fff" strokeWidth="1.6" strokeLinecap="round" />
          ))}
        </svg>
      </motion.div>
      <motion.div className="che-deco-cruz" style={estilo(t1)}>
        <svg viewBox="0 0 24 24" aria-hidden focusable="false">
          <path d="M12 3v18M3 12h18" stroke="#ea1d23" strokeWidth="3" strokeLinecap="round" />
        </svg>
      </motion.div>
      <motion.div className="che-deco-x" style={estilo(t2)}>
        <svg viewBox="0 0 24 24" aria-hidden focusable="false">
          <path d="M5 5l14 14M19 5L5 19" stroke="#fff" strokeWidth="3" strokeLinecap="round" />
        </svg>
      </motion.div>
    </div>
  );
}
