/**
 * CMS 3.8 — Pedidos recebidos.
 *
 * Lista dos `service_requests` do formulário público, com filtro por estado,
 * detalhe com a mensagem e as acções do funil. Exporta CSV.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Download } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { showToast } from "../../lib/toast";
import { formatDateTime } from "../../lib/format";
import { apiDownload } from "../../lib/api";
import {
  Button,
  DataTable,
  EnumPill,
  FilterPill,
  Modal,
  PageHeader,
  SearchInput,
  TableFooter,
  type Column,
} from "../../design/ui";
import { cmsRequests, rows, type ServiceRequest } from "./api";

const STATES: [string, string][] = [
  ["all", "Todos"],
  ["new", "Novos"],
  ["contacted", "Contactados"],
  ["qualified", "Qualificados"],
  ["closed", "Fechados"],
];

const PAGE_SIZE = 20;

export default function CmsRequestsPage() {
  const { token } = useAuth();
  const [items, setItems] = useState<ServiceRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [state, setState] = useState("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [detail, setDetail] = useState<ServiceRequest | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    cmsRequests
      .list(token, { status: state === "all" ? undefined : state })
      .then((data) => setItems(rows<ServiceRequest>(data)))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, state]);

  useEffect(load, [load]);

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return items;
    return items.filter((item) =>
      [item.name, item.organization, item.phone, item.email].some((v) => (v || "").toLowerCase().includes(needle)),
    );
  }, [items, search]);

  const paged = useMemo(() => filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE), [filtered, page]);

  const setStatus = async (item: ServiceRequest, status: ServiceRequest["status"]) => {
    if (!token) return;
    setBusy(true);
    try {
      await cmsRequests.update(token, item.id, { status });
      showToast("success", "Estado actualizado.");
      setDetail(null);
      load();
    } catch (e) {
      showToast("danger", (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const exportCsv = async () => {
    if (!token) return;
    try {
      await apiDownload(cmsRequests.exportUrl, token, "pedidos-de-contacto.csv");
    } catch (e) {
      showToast("danger", (e as Error).message);
    }
  };

  const columns: Column<ServiceRequest>[] = [
    {
      key: "who",
      header: "Quem",
      render: (row) => (
        <span className="bz-cell-primary">
          <span className="bz-cell-name">{row.name}</span>
          <span className="bz-cell-sub">{row.organization || "—"}</span>
        </span>
      ),
    },
    {
      key: "contact",
      header: "Contacto",
      render: (row) => (
        <span className="bz-cell-primary">
          <span className="bz-cell-id">{row.phone}</span>
          <span className="bz-cell-sub">{row.email || "—"}</span>
        </span>
      ),
    },
    { key: "interest", header: "Interesse", render: (row) => <span>{row.interest_label}</span> },
    { key: "fleet", header: "Frota", render: (row) => <span className="bz-table-mono">{row.fleet_size || "—"}</span> },
    { key: "status", header: "Estado", render: (row) => <EnumPill group="srq" value={row.status} /> },
    {
      key: "when",
      header: "Recebido",
      render: (row) => <span className="bz-cell-sub">{formatDateTime(row.created_at)}</span>,
    },
  ];

  return (
    <div className="bz-page">
      <PageHeader
        actions={
          <Button icon={<Download size={16} />} onClick={exportCsv} variant="ghost">
            Exportar CSV
          </Button>
        }
        crumbs={["Conteúdo", "Pedidos"]}
        description="Os pedidos de contacto vindos da landing e da página de contactos."
        title="Pedidos recebidos"
      />

      <div className="bz-toolbar">
        {STATES.map(([key, label]) => (
          <FilterPill active={state === key} key={key} onClick={() => setState(key)}>
            {label}
          </FilterPill>
        ))}
        <span className="bz-toolbar-spacer" />
        <SearchInput onChange={setSearch} placeholder="Nome, empresa, telefone" value={search} />
      </div>

      <DataTable
        columns={columns}
        empty={{
          title: "Sem pedidos",
          text: "Os pedidos enviados pelo formulário do site aparecem aqui.",
        }}
        error={error}
        footer={<TableFooter onPage={setPage} page={page} pageSize={PAGE_SIZE} total={filtered.length} />}
        loading={loading}
        onRetry={load}
        onRowClick={setDetail}
        rowKey={(row) => String(row.id)}
        rows={paged}
      />

      <Modal
        footer={
          detail ? (
            <>
              <Button disabled={busy} onClick={() => setStatus(detail, "contacted")} variant="ghost">
                Marcar como contactado
              </Button>
              <Button disabled={busy} onClick={() => setStatus(detail, "qualified")} variant="ghost">
                Qualificar
              </Button>
              <Button disabled={busy} onClick={() => setStatus(detail, "closed")}>
                Fechar
              </Button>
            </>
          ) : null
        }
        onClose={() => setDetail(null)}
        open={Boolean(detail)}
        title={detail?.name || "Pedido"}
      >
        {detail ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div className="bz-formgrid">
              <div className="bz-field">
                <span className="bz-field-label">Empresa</span>
                <span>{detail.organization || "—"}</span>
              </div>
              <div className="bz-field">
                <span className="bz-field-label">Telefone</span>
                <span className="bz-mono">{detail.phone}</span>
              </div>
              <div className="bz-field">
                <span className="bz-field-label">Email</span>
                <span>{detail.email || "—"}</span>
              </div>
              <div className="bz-field">
                <span className="bz-field-label">Frota</span>
                <span>{detail.fleet_size || "—"}</span>
              </div>
              <div className="bz-field">
                <span className="bz-field-label">Interesse</span>
                <span>{detail.interest_label}</span>
              </div>
              <div className="bz-field">
                <span className="bz-field-label">Origem</span>
                <span className="bz-mono">{detail.source}</span>
              </div>
            </div>
            <div className="bz-field">
              <span className="bz-field-label">Mensagem</span>
              <p style={{ margin: 0, font: "400 14px/1.65 var(--font-ui)", color: "var(--muted)", whiteSpace: "pre-wrap" }}>
                {detail.message || "—"}
              </p>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
