/**
 * Portal A2.1 — Agentes e turnos.
 *
 * O separador dos turnos deixou de ser proposta: `/api/shifts/` existe, com
 * listar, abrir, fechar, conferir e reabrir, e o `shift_id` já viaja nos
 * bilhetes e nas validações. Os outros dois continuam por construir e dizem-no
 * no topo, em vez de fingirem dados que não existem.
 */
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { apiFetch } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import { Card, DataTable, FilterPill, PageHeader, Pill, ProposalNotice, Tabs, type Column } from "../design/ui";
import { MODULE_TABS } from "../design/portal/nav";

type Tab = "agents" | "shifts" | "day_closes";

interface Shift {
  id: number;
  agent_name: string;
  vehicle_registration: string;
  opened_at: string;
  closed_at: string | null;
  float_amount: string;
  expected_amount: string;
  counted_amount: string;
  difference: string;
  status: string;
  status_label: string;
}

const COLUMNS: Record<Exclude<Tab, "shifts">, string[]> = {
  agents: ["Agente", "Terminal", "Rota", "Sessão", "Turno activo", "Estado"],
  day_closes: ["Dia", "Agente", "Bilhetes", "Validações", "Total apurado", "Estado"],
};

const NEEDS: Record<Exclude<Tab, "shifts">, string> = {
  agents:
    "A lista de agentes existe (`/agents`); falta juntar-lhe a coluna do turno activo, que agora já tem de onde vir.",
  day_closes:
    "O fecho de dia por agente está gravado no servidor (`AgentDayClose`), mas ainda não tem endereço próprio na API para este ecrã o listar.",
};

/** Estados do turno, na ordem do ciclo. */
const ESTADOS: [string, string][] = [
  ["", "Todos"],
  ["open", "Abertos"],
  ["closed", "Fechados"],
  ["verified", "Conferidos"],
];

function tomDoEstado(estado: string): "ok" | "warn" | "mute" {
  if (estado === "verified") return "ok";
  if (estado === "open") return "warn";
  return "mute";
}

export default function ShiftsProposalPage() {
  const [tab, setTab] = useState<Tab>("shifts");
  const tabs = (MODULE_TABS.agentes || []) as [Tab, string][];

  const { token } = useAuth();
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [estado, setEstado] = useState("");
  const [soDivergentes, setSoDivergentes] = useState(false);

  const carregar = useCallback(() => {
    if (!token || tab !== "shifts") return;
    setLoading(true);
    setError(null);
    const params = new URLSearchParams();
    if (estado) params.set("status", estado);
    if (soDivergentes) params.set("divergent", "true");
    apiFetch(`/api/shifts/?${params.toString()}`, token)
      .then((d) => setShifts(d.results || d))
      .catch((e) => setError(e instanceof Error ? e.message : "Não foi possível carregar os turnos."))
      .finally(() => setLoading(false));
  }, [token, tab, estado, soDivergentes]);

  useEffect(carregar, [carregar]);

  const colunas: Column<Shift>[] = [
    { key: "id", header: "Turno", render: (r) => <span className="bz-table-mono">#{r.id}</span> },
    { key: "agent", header: "Agente", render: (r) => r.agent_name },
    { key: "vehicle", header: "Viatura", render: (r) => r.vehicle_registration || "—" },
    { key: "opened", header: "Abertura", render: (r) => formatDateTime(r.opened_at) },
    { key: "closed", header: "Fecho", render: (r) => (r.closed_at ? formatDateTime(r.closed_at) : "—") },
    { key: "float", header: "Fundo de maneio", numeric: true, render: (r) => formatCurrency(r.float_amount) },
    { key: "expected", header: "Apurado esperado", numeric: true, render: (r) => formatCurrency(r.expected_amount) },
    { key: "counted", header: "Contado", numeric: true, render: (r) => formatCurrency(r.counted_amount) },
    {
      key: "difference",
      header: "Diferença",
      numeric: true,
      // A diferença é o único número que interessa quando não dá zero: fica
      // marcada para se ver a olho qual a caixa que não bateu certo.
      render: (r) => {
        const valor = Number(r.difference);
        if (r.status === "open") return <span className="bz-table-mono">—</span>;
        return (
          <Pill tone={valor === 0 ? "ok" : "bad"}>{formatCurrency(r.difference)}</Pill>
        );
      },
    },
    { key: "status", header: "Estado", render: (r) => <Pill tone={tomDoEstado(r.status)}>{r.status_label}</Pill> },
  ];

  return (
    <div className="bz-page">
      <PageHeader
        crumbs={["Operação", "Agentes e turnos"]}
        description="Um turno prende um agente a uma viatura durante um período e fecha caixa: fundo de maneio, apurado esperado, contado e diferença."
        title="Agentes e turnos"
      />

      <Tabs onChange={setTab} options={tabs} value={tab} />

      {tab === "shifts" ? (
        <>
          <div className="bz-toolbar">
            {ESTADOS.map(([chave, rotulo]) => (
              <FilterPill active={estado === chave} key={chave || "todos"} onClick={() => setEstado(chave)}>
                {rotulo}
              </FilterPill>
            ))}
            <span className="bz-toolbar-spacer" />
            <FilterPill active={soDivergentes} onClick={() => setSoDivergentes((v) => !v)}>
              Só os que não bateram certo
            </FilterPill>
          </div>

          <DataTable
            columns={colunas}
            empty={{
              title: "Sem turnos no filtro escolhido",
              text: "Um turno aparece aqui assim que um agente o abrir no terminal ou alguém o abrir por ele no portal.",
            }}
            error={error}
            loading={loading}
            onRetry={carregar}
            rowKey={(r) => String(r.id)}
            rows={shifts}
          />
        </>
      ) : (
        <>
          <ProposalNotice />
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
              <span>Sem endpoint — nada a listar.</span>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
