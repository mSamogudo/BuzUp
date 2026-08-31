/**
 * Histórico de recuperações de cartão (04-lacunas-backend.md, secção Cartões).
 *
 * A taxa `card_recovery` já aparecia nas Taxas administrativas, mas o processo
 * que a gera não tinha lista: não se sabia quem recuperou, que cartões ficaram
 * bloqueados nem se o pagamento chegou a confirmar. É isso que este separador
 * mostra.
 */
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { PageFrame } from "../ui/common";
import { apiFetch } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import { DataTable, EnumPill, FilterPill, Pill, type Column } from "../design/ui";

interface Recovery {
  id: number;
  reference: string;
  status: string;
  amount: string;
  currency: string;
  created_at: string;
  finalised_at: string | null;
  reason: string;
  blocked_cards: number;
  passenger_id: number | null;
  passenger_name: string;
  passenger_phone: string;
  new_card_id: number | null;
  new_card_number: string;
  new_card_uid: string;
}

const STATES: [string, string][] = [
  ["all", "Todas"],
  ["confirmed", "Confirmadas"],
  ["pending", "Pendentes"],
  ["failed", "Falhadas"],
];

export default function CardRecoveriesTab() {
  const { token } = useAuth();
  const [items, setItems] = useState<Recovery[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [state, setState] = useState("all");

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    apiFetch(`/api/card-recoveries/${state === "all" ? "" : `?status=${state}`}`, token)
      .then((data) => setItems(data.results || []))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, state]);

  useEffect(load, [load]);

  const columns: Column<Recovery>[] = [
    {
      key: "passenger",
      header: "Passageiro",
      render: (row) => (
        <span className="bz-cell-primary">
          <span className="bz-cell-id">{row.passenger_phone || "—"}</span>
          <span className="bz-cell-name">{row.passenger_name || "—"}</span>
        </span>
      ),
    },
    {
      key: "card",
      header: "Cartão novo",
      render: (row) => (
        <span className="bz-cell-primary">
          <span className="bz-cell-id">{row.new_card_number || "—"}</span>
          <span className="bz-cell-sub">{row.new_card_uid || "sem UID"}</span>
        </span>
      ),
    },
    {
      key: "blocked",
      header: "Bloqueados",
      numeric: true,
      render: (row) => <span>{row.blocked_cards}</span>,
    },
    { key: "reason", header: "Motivo", render: (row) => <span className="bz-cell-sub">{row.reason || "—"}</span> },
    {
      key: "fee",
      header: "Taxa",
      numeric: true,
      render: (row) => <span>{formatCurrency(row.amount, row.currency || "MZN")}</span>,
    },
    { key: "status", header: "Pagamento", render: (row) => <EnumPill group="pay" value={row.status} /> },
    {
      key: "when",
      header: "Quando",
      render: (row) => (
        <span className="bz-cell-primary">
          <span className="bz-cell-name">{formatDateTime(row.created_at)}</span>
          <span className="bz-cell-sub">
            {row.finalised_at ? <Pill tone="ok">Concluída</Pill> : <Pill tone="warn">Por concluir</Pill>}
          </span>
        </span>
      ),
    },
  ];

  return (
    <PageFrame
      description="A taxa de recuperação já estava nas taxas administrativas; o processo que a gera passa a ter histórico."
      kicker="Passageiros"
      title="Recuperações de cartão"
    >
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="bz-toolbar">
        {STATES.map(([key, label]) => (
          <FilterPill active={state === key} key={key} onClick={() => setState(key)}>
            {label}
          </FilterPill>
        ))}
      </div>

      <DataTable
        columns={columns}
        empty={{
          title: "Sem recuperações",
          text: "Quando um agente recuperar um cartão perdido, a operação fica registada aqui com a taxa cobrada.",
        }}
        error={error}
        loading={loading}
        onRetry={load}
        rowKey={(row) => String(row.id)}
        rows={items}
      />
    </div>
    </PageFrame>
  );
}
