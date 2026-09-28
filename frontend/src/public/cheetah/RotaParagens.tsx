import { useRef } from "react";
import { useMotionValueEvent, useReducedMotion, useScroll } from "motion/react";

/**
 * As paragens de um lado da rota. A linha que as liga desenha-se ao rolar e os
 * pontos acendem-se um a um, de sul para norte.
 *
 * É a única animação deste site que EXPLICA alguma coisa em vez de decorar:
 * mostra que aquilo é um percurso, com uma ordem e um sentido, e não uma lista
 * de moradas. Por isso está ligada à posição do scroll e não a um temporizador
 * — quem pára a meio vê a linha parada a meio, que é a informação certa.
 *
 * COMO. O progresso do scroll escreve-se em duas variáveis CSS por paragem
 * (`--progresso` para o troço de linha, `--ponto` para o disco), e o CSS faz o
 * resto. Escritas em CADA `li`, e nunca no `ul`: uma variável no pai obriga o
 * browser a recalcular o estilo de todos os filhos a cada frame do scroll.
 *
 * Escreve-se direito no DOM e não por estado do React — isto corre a cada
 * frame de scroll, e um `setState` por frame põe o React a reconciliar a
 * árvore sessenta vezes por segundo para mudar dois números.
 */
export default function RotaParagens({ paragens }: { paragens: readonly string[] }) {
  const ref = useRef<HTMLUListElement | null>(null);
  const reduzido = useReducedMotion();

  /* A lista acaba de se desenhar quando o fundo dela chega a três quartos do
     ecrã: a linha completa-se enquanto ainda está bem à vista, e não no
     instante em que já vai a sair por cima. */
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start 0.85", "end 0.75"],
  });

  useMotionValueEvent(scrollYProgress, "change", (p) => {
    const lista = ref.current;
    if (!lista || reduzido) return;
    const itens = lista.children;
    const n = itens.length;
    for (let i = 0; i < n; i++) {
      const item = itens[i] as HTMLElement;
      /* Cada paragem tem a sua fatia do percurso. `p` global vira progresso
         local dentro da fatia, limitado a [0,1]. */
      const inicio = i / n;
      const local = Math.min(1, Math.max(0, (p - inicio) * n));
      item.style.setProperty("--progresso", String(local));
      /* O disco acende ligeiramente ANTES do troço que sai dele estar cheio —
         a paragem chega primeiro, a estrada vem a seguir. */
      const aceso = Math.min(1, Math.max(0, (p - inicio) * n * 3));
      item.style.setProperty("--ponto", String(0.4 + aceso * 0.6));
      if (aceso > 0.5) item.dataset.aceso = "";
      else delete item.dataset.aceso;
    }
  });

  return (
    <ul className="che-paragens" data-anima={reduzido ? undefined : ""} ref={ref}>
      {paragens.map((p) => (
        <li className="che-paragem" key={p}>{p}</li>
      ))}
    </ul>
  );
}
