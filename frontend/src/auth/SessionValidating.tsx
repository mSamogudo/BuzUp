/**
 * B6.4 — "A validar a sua sessão".
 *
 * Cobre o ecrã depois de as credenciais serem aceites e mostra os três passos
 * do desenho: credenciais confirmadas, a carregar permissões, a preparar o
 * painel. Não é decoração: é a diferença entre "não aconteceu nada" e "está a
 * acontecer isto".
 */
import { useEffect, useState } from "react";
import { Check, Loader2 } from "lucide-react";
import { Logo } from "../design/ui/kit";

export default function SessionValidating({
  title,
  lead,
  steps,
}: {
  title: string;
  lead: string;
  steps: string[];
}) {
  const [done, setDone] = useState(0);

  useEffect(() => {
    if (done >= steps.length) return;
    const timer = window.setTimeout(() => setDone((n) => n + 1), 320);
    return () => window.clearTimeout(timer);
  }, [done, steps.length]);

  return (
    <div aria-busy="true" aria-live="polite" className="bzl-validating" role="status">
      <div className="bzl-validating-card">
        <Logo height={26} />
        <h2>{title}</h2>
        <p>{lead}</p>
        <ol>
          {steps.map((step, index) => {
            const state = index < done ? "done" : index === done ? "busy" : "idle";
            return (
              <li className={`bzl-step bzl-step-${state}`} key={step}>
                <span className="bzl-step-icon">
                  {state === "done" ? (
                    <Check size={13} />
                  ) : state === "busy" ? (
                    <Loader2 className="bz-spin" size={13} />
                  ) : null}
                </span>
                {step}
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}
