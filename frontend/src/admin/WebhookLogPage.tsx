/**
 * Registo de webhooks por provedor (04-lacunas-backend.md, secção Financeiro).
 *
 * É o primeiro sítio onde se olha quando um pagamento fica pendente: o que o
 * gateway enviou, se a assinatura era válida e o que se fez com isso. Só de
 * leitura — um diário não se edita.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { PageFrame } from "../ui/common";
import { apiFetch } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import {
  DataTable,
  EnumPill,
  FilterPill,
  Modal,
  Pill,
  SearchInput,
  TableFooter,
  type Column,
} from "../design/ui";

interface CallbackLog {
  id: number;
  uuid: string;
  payment_intent: number;
  reference: string;
  provider: string;
  intent_status: string;
  amount: string;
  currency: string;
  provider_reference: string;
  signature_valid: boolean;
  processing_status: string;
  raw_payload: Record<string, unknown>;
  received_at: string;
}

const PROVIDERS: [string, string][] = [
  ["all", "Todos"],
  ["MPESA", "M-Pesa"],
  ["EMOLA", "e-Mola"],
];

const PAGE_SIZE = 20;

export default function WebhookLogPage() {
  const { token } = useAuth();
  const [items, setItems] = useState<CallbackLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [provider, setProvider] = useState("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [detail, setDetail] = useState<CallbackLog | null>(null);

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    const params = new URLSearchParams();
    if (provider !== "all") params.set("provider", provider);
    if (search.trim()) params.set("q", search.trim());
    apiFetch(`/api/payments/callback-log/${params.toString() ? `?${params}` : ""}`, token)
      .then((data) => setItems(data?.results || data || []))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, provider, search]);

  useEffect(load, [load]);

  const paged = useMemo(() => items.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE), [items, page]);

  const columns: Column<CallbackLog>[] = [
    {
      key: "ref",
      header: "Pagamento",
      render: (row) => (
        <span className="bz-cell-primary">
          <span className="bz-cell-id">{row.reference}</span>
          <span className="bz-cell-sub">{row.provider_reference || "sem referência do provedor"}</span>
        </span>
      ),
    },
    { key: "provider", header: "Provedor", render: (row) => <Pill tone="mute">{row.provider || "—"}</Pill> },
    {
      key: "amount",
      header: "Valor",
      numeric: true,
      render: (row) => <span>{formatCurrency(row.amount, row.currency || "MZN")}</span>,
    },
    { key: "intent", header: "Estado do pagamento", render: (row) => <EnumPill group="pay" value={row.intent_status} /> },
    {
      key: "signature",
      header: "Assinatura",
      render: (row) => (
        <Pill tone={row.signature_valid ? "ok" : "bad"}>{row.signature_valid ? "Válida" : "Inválida"}</Pill>
      ),
    },
    {
      key: "processing",
      header: "Processamento",
      render: (row) => <Pill tone={row.processing_status === "processed" ? "ok" : "warn"}>{row.processing_status}</Pill>,
    },
    {
      key: "when",
      header: "Recebido",
      render: (row) => <span className="bz-table-mono">{formatDateTime(row.received_at)}</span>,
    },
  ];

  return (
    <PageFrame
      description="O que cada gateway enviou, tal como chegou. É o primeiro sítio onde se olha quando um pagamento fica pendente."
      kicker="Financeiro"
      title="Registo de webhooks"
    >
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="bz-toolbar">
        {PROVIDERS.map(([key, label]) => (
          <FilterPill active={provider === key} key={key} onClick={() => setProvider(key)}>
            {label}
          </FilterPill>
        ))}
        <span className="bz-toolbar-spacer" />
        <SearchInput onChange={setSearch} placeholder="Referência do pagamento" value={search} />
      </div>

      <DataTable
        columns={columns}
        empty={{
          title: "Sem webhooks recebidos",
          text: "Quando o M-Pesa ou o e-Mola confirmarem um pagamento, o pedido que enviaram fica registado aqui.",
        }}
        error={error}
        footer={<TableFooter onPage={setPage} page={page} pageSize={PAGE_SIZE} total={items.length} />}
        loading={loading}
        onRetry={load}
        onRowClick={setDetail}
        rowKey={(row) => String(row.id)}
        rows={paged}
      />

      <Modal
        onClose={() => setDetail(null)}
        open={Boolean(detail)}
        size="lg"
        title={detail ? `Callback de ${detail.reference}` : "Callback"}
      >
        {detail ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div className="bz-formgrid">
              <div className="bz-field">
                <span className="bz-field-label">Provedor</span>
                <span>{detail.provider || "—"}</span>
              </div>
              <div className="bz-field">
                <span className="bz-field-label">Referência do provedor</span>
                <span className="bz-mono">{detail.provider_reference || "—"}</span>
              </div>
              <div className="bz-field">
                <span className="bz-field-label">Assinatura</span>
                <span>
                  <Pill tone={detail.signature_valid ? "ok" : "bad"}>
                    {detail.signature_valid ? "Válida" : "Inválida"}
                  </Pill>
                </span>
              </div>
              <div className="bz-field">
                <span className="bz-field-label">Recebido</span>
                <span className="bz-mono">{formatDateTime(detail.received_at)}</span>
              </div>
            </div>
            <div className="bz-field">
              <span className="bz-field-label">Corpo recebido</span>
              <pre
                style={{
                  margin: 0,
                  padding: 16,
                  borderRadius: "var(--r-field)",
                  background: "var(--surface2)",
                  border: "1px solid var(--border)",
                  font: "500 12px/1.6 var(--font-mono)",
                  color: "var(--text)",
                  overflowX: "auto",
                  maxHeight: 340,
                }}
              >
                {JSON.stringify(detail.raw_payload, null, 2)}
              </pre>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
    </PageFrame>
  );
}
