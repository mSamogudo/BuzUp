/**
 * Portal A2.1 — Agentes e turnos (proposta).
 *
 * Este módulo está desenhado mas não existe no backend: não há `/shifts` nem
 * `shift_id` em bilhetes e validações. O ecrã mostra o desenho e diz, no topo,
 * exactamente o que falta — em vez de fingir dados que não existem.
 */
import { useState } from "react";
import { Card, PageHeader, ProposalNotice, Tabs } from "../design/ui";
import { MODULE_TABS } from "../design/portal/nav";

type Tab = "agents" | "shifts" | "day_closes";

const COLUMNS: Record<Tab, string[]> = {
  agents: ["Agente", "Terminal", "Rota", "Sessão", "Turno activo", "Estado"],
  shifts: ["Turno", "Agente", "Viatura", "Abertura", "Fecho", "Fundo de maneio", "Apurado esperado", "Contado", "Diferença", "Estado"],
  day_closes: ["Dia", "Agente", "Bilhetes", "Validações", "Total apurado", "Estado"],
};

const NEEDS: Record<Tab, string> = {
  agents:
    "A lista de agentes existe (`/agents`), mas a coluna do turno activo depende de `/shifts`.",
  shifts:
    "Falta `/shifts` com listar, abrir, fechar, conferir e reabrir, e o campo `shift_id` em bilhetes e validações para o apurado ser calculado no servidor.",
  day_closes:
    "Falta o fecho de dia por agente, que agrega os turnos de um dia — depende de `/shifts` existir primeiro.",
};

export default function ShiftsProposalPage() {
  const [tab, setTab] = useState<Tab>("shifts");
  const tabs = (MODULE_TABS.agentes || []) as [Tab, string][];

  return (
    <div className="bz-page">
      <PageHeader
        crumbs={["Propostas", "Agentes e turnos"]}
        description="Um turno prende um agente a uma viatura durante um período e fecha caixa: fundo de maneio, apurado esperado, contado e diferença."
        title="Agentes e turnos"
      />

      <ProposalNotice />

      <Tabs onChange={setTab} options={tabs} value={tab} />

      <Card flush large>
        <div className="bz-tablescroll">
          <table className="bz-table">
            <thead>
              <tr>
                {COLUMNS[tab].map((column) => (
                  <th key={column}>{column}</th>
                ))}
              </tr>
            </thead>
          </table>
        </div>
        <div style={{ padding: "40px 24px", textAlign: "center" }}>
          <p style={{ margin: 0, font: "500 14px/1.6 var(--font-ui)", color: "var(--muted)", maxWidth: "62ch", marginInline: "auto" }}>
            {NEEDS[tab]}
          </p>
        </div>
        <div className="bz-tablefoot">
          <span>Sem endpoints — nada a listar.</span>
        </div>
      </Card>
    </div>
  );
}
