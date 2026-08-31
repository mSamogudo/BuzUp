import type { ReactNode } from "react";

/** A moldura de um grafico: titulo, icone e corpo.
 *
 * Vive fora de `Charts.tsx` de proposito. Nao usa recharts, e enquanto la
 * estava obrigava quem so quisesse a moldura a descarregar 430 kB de
 * biblioteca de graficos.
 */
export function ChartCard({ title, subtitle, icon, action, children }: {
  title: string; subtitle?: string; icon: ReactNode; action?: ReactNode; children: ReactNode;
}) {
  return (
    <div className="dashboard-chart-card">
      <div className="dashboard-chart-header">
        {icon}
        <div style={{ minWidth: 0 }}>
          <h3>{title}</h3>
          {subtitle ? (
            <p style={{ margin: "2px 0 0", fontSize: 11.5, color: "var(--app-text-muted)", fontWeight: 500 }}>
              {subtitle}
            </p>
          ) : null}
        </div>
        {action ? <div style={{ marginLeft: "auto" }}>{action}</div> : null}
      </div>
      <div className="dashboard-chart-body" style={{ flexDirection: "column" }}>{children}</div>
    </div>
  );
}
