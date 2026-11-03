import { useEffect, type RefObject } from "react";

/* O que sobe ao entrar no ecrã. Uma lista só, aqui, em vez de um atributo
 * espalhado pelo markup das três páginas. */
const ALVOS = [
  ".bzc-sechead",
  ".bzc-produtos > li",
  ".bzc-grelha-3 > *",
  ".bzc-grelha-2 > *",
  ".bzc-passos-painel",
  ".bzc-passos-lista > li",
  ".bzc-faq > li",
  ".bzc-chamada .bzc-wrap-sm",
  ".bzc-eco > *",
].join(",");

/* Irmãos do mesmo grupo entram em escada, mas só até ao sexto: a oitava
 * célula da faixa não pode esperar meio segundo. */
const ESCADA_MAX = 6;

/* O CONTEÚDO É VISÍVEL POR OMISSÃO. Quem esconde é este código, e só esconde
 * o que vai voltar a mostrar: sem IntersectionObserver, com movimento
 * reduzido ou se o script falhar, nada fica marcado e tudo aparece. O que já
 * está no ecrã ao montar fica quieto — não pisca.
 *
 * Só `opacity` e `transform`: não mexe na caixa, por isso não há CLS. Depois
 * de entrar o atributo sai, e o elemento volta às suas transições (a subida
 * do cartão ao passar o rato não herda o atraso da escada). */
export function useRevelar(raiz: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = raiz.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const limite = window.innerHeight * 0.92;
    const porRevelar = Array.from(el.querySelectorAll<HTMLElement>(ALVOS)).filter(
      (a) => a.getBoundingClientRect().top > limite,
    );

    const ordem = new Map<Element, number>();
    for (const a of porRevelar) {
      const n = ordem.get(a.parentElement!) ?? 0;
      ordem.set(a.parentElement!, n + 1);
      a.style.setProperty("--bzc-ordem", String(Math.min(n, ESCADA_MAX)));
      a.dataset.revela = "";
    }

    const largar = (a: HTMLElement) => {
      delete a.dataset.revela;
      a.style.removeProperty("--bzc-ordem");
    };

    const io = new IntersectionObserver(
      (entradas) => {
        for (const e of entradas) {
          if (!e.isIntersecting) continue;
          const a = e.target as HTMLElement;
          io.unobserve(a);
          a.dataset.revela = "visto";
          // O `transitionend` dos filhos (um botão no cartão) também sobe até
          // aqui; só conta o do próprio elemento. O relógio é a rede: se a
          // transição não correr, o atributo sai na mesma.
          const fim = (ev: TransitionEvent) => {
            if (ev.target !== a || ev.propertyName !== "transform") return;
            a.removeEventListener("transitionend", fim);
            largar(a);
          };
          a.addEventListener("transitionend", fim);
          window.setTimeout(() => largar(a), 1500);
        }
      },
      { rootMargin: "0px 0px -8% 0px" },
    );
    porRevelar.forEach((a) => io.observe(a));

    return () => {
      io.disconnect();
      porRevelar.forEach(largar);
    };
  }, [raiz]);
}
