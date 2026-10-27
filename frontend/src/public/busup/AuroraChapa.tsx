import { useEffect, useRef } from "react";

/* O fundo de aurora da chapa: três campos de luz nas cores da marca.
 *
 * É SÓ CSS. Os campos são gradientes radiais — já nascem macios, sem
 * `filter: blur`, que obrigava o browser a refazer o desfoque a cada passo da
 * animação. O movimento é `transform`, que corre no compositor: nada de
 * canvas, nada de laço em JavaScript.
 *
 * O ÚNICO JAVASCRIPT É PARAR. Com a chapa fora do ecrã a animação fica
 * suspensa (`data-parado`), para não gastar bateria a mexer o que ninguém vê.
 * Sem JavaScript a aurora continua a correr — não há nada que esconda.
 *
 * Com `prefers-reduced-motion` fica o primeiro quadro, parado. */
export default function AuroraChapa() {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) delete el.dataset.parado;
      else el.dataset.parado = "";
    });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div aria-hidden className="bzc-aurora" ref={ref}>
      <i className="bzc-aurora-1" />
      <i className="bzc-aurora-2" />
      <i className="bzc-aurora-3" />
    </div>
  );
}
