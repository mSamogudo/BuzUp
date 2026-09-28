import { useRef, type PropsWithChildren } from "react";
import { useInView } from "motion/react";

/**
 * Revela o conteúdo quando ele entra no ecrã, UMA vez.
 *
 * O movimento em si é CSS (`.che-rev`, em cheetah-motion.css) — aqui só se
 * decide quando disparar. É deliberado: uma revelação não é interrompível nem
 * dirigida por gesto, e o CSS corre fora da thread principal, por isso não
 * perde frames enquanto o resto da página ainda carrega. O JS não tem nada a
 * acrescentar à animação, só ao momento dela.
 *
 * `margin: "-80px"` faz disparar um pouco ANTES do elemento tocar a borda:
 * quem rola a velocidade normal vê a revelação a acontecer, e não já feita.
 *
 * `once: true` porque re-animar sempre que se passa por ali é a página a
 * discutir com quem a lê.
 */
export default function CheRevela({
  children,
  ordem = 0,
  className = "",
  as: Elemento = "div",
}: PropsWithChildren<{
  /**
   * Posição no escalonamento do grupo — 80ms entre cada, definido no CSS.
   * SÓ para itens que entram no ecrã JUNTOS, como uma fila de cartões. Numa
   * coluna de secções, onde cada uma entra por si, isto só atrasaria conteúdo
   * que já está à vista.
   */
  ordem?: number;
  className?: string;
  /**
   * O elemento a desenhar. Existe porque envolver um `<li>` num `<div>` dentro
   * de um `<ul>` é HTML inválido: o leitor de ecrã deixa de anunciar a lista
   * como lista e perde a contagem dos itens.
   */
  as?: "div" | "li";
}>) {
  const ref = useRef<HTMLElement | null>(null);
  const visivel = useInView(ref, { once: true, margin: "-80px" });

  return (
    <Elemento
      ref={ref as never}
      className={`che-rev ${className}`.trim()}
      data-visivel={visivel || undefined}
      style={ordem ? ({ "--i": ordem } as React.CSSProperties) : undefined}
    >
      {children}
    </Elemento>
  );
}
