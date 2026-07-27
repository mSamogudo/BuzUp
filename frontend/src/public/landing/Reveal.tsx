import { PropsWithChildren, useEffect, useRef, useState } from "react";

/**
 * Revela o conteúdo ao entrar no viewport (fade + translate). Sem dependências:
 * IntersectionObserver + transição CSS (`.bzlp-reveal`). Respeita
 * prefers-reduced-motion — nesse caso renderiza estático.
 */
export default function Reveal({ children, delay = 0, className = "" }: PropsWithChildren<{ delay?: number; className?: string }>) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [shown, setShown] = useState(false);
  const reduce = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => {
    if (reduce || shown) return;
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setShown(true);
          io.disconnect();
        }
      },
      { rootMargin: "-64px 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [reduce, shown]);

  if (reduce) return <div className={className}>{children}</div>;
  return (
    <div
      ref={ref}
      className={`bzlp-reveal${shown ? " is-in" : ""} ${className}`}
      style={delay ? { transitionDelay: `${delay}ms` } : undefined}
    >
      {children}
    </div>
  );
}
