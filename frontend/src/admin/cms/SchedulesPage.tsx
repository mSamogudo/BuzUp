/**
 * CMS 3.9 — Publicações agendadas.
 *
 * O que publica, o alvo, quando e o estado. Cancelar mantém o registo; as
 * falhas mostram o motivo.
 */
import { useCallback, useEffect, useState } from "react";
import { CalendarPlus, X } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { showToast } from "../../lib/toast";
import { formatDateTime } from "../../lib/format";
import {
  Button,
  ConfirmDestructive,
  DataTable,
  EnumPill,
  Field,
  FilterPill,
  IconButton,
  Input,
  Modal,
  PageHeader,
  Select,
  type Column,
} from "../../design/ui";
import { cmsPages, cmsSchedules, i18nGet, rows, type CmsPage, type CmsSchedule } from "./api";

const STATES: [string, string][] = [
  ["all", "Todos"],
  ["scheduled", "Agendadas"],
  ["done", "Publicadas"],
  ["failed", "Falhadas"],
  ["cancelled", "Canceladas"],
];

export default function CmsSchedulesPage() {
  const { token } = useAuth();
  const [items, setItems] = useState<CmsSchedule[]>([]);
  const [pages, setPages] = useState<CmsPage[]>([]);
  const [state, setState] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState({ pageId: "", runAt: "" });
  const [saving, setSaving] = useState(false);
  const [confirm, setConfirm] = useState<CmsSchedule | null>(null);

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    cmsSchedules
      .list(token, { status: state === "all" ? undefined : state })
      .then((data) => setItems(rows<CmsSchedule>(data)))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, state]);

  useEffect(load, [load]);

  useEffect(() => {
    if (!token) return;
    cmsPages.list(token).then((d) => setPages(rows<CmsPage>(d))).catch(() => undefined);
  }, [token]);

  const create = async () => {
    if (!token || !draft.pageId || !draft.runAt) return;
    setSaving(true);
    try {
      await cmsSchedules.create(token, {
        target_type: "page",
        target_id: Number(draft.pageId),
        run_at: new Date(draft.runAt).toISOString(),
      });
      showToast("success", "Publicação agendada.");
      setCreating(false);
      setDraft({ pageId: "", runAt: "" });
      load();
    } catch (e) {
      showToast("danger", (e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const cancel = async () => {
    if (!token || !confirm) return;
    try {
      await cmsSchedules.cancel(token, confirm.id);
      showToast("neutral", "Agendamento cancelado.");
      setConfirm(null);
      load();
    } catch (e) {
      showToast("danger", (e as Error).message);
    }
  };

  const columns: Column<CmsSchedule>[] = [
    {
      key: "target",
      header: "O que publica",
      render: (row) => (
        <span className="bz-cell-primary">
          <span className="bz-cell-id">{row.target_type}</span>
          <span className="bz-cell-name">{row.target_label}</span>
        </span>
      ),
    },
    { key: "when", header: "Quando", render: (row) => <span className="bz-table-mono">{formatDateTime(row.run_at)}</span> },
    { key: "status", header: "Estado", render: (row) => <EnumPill group="cmssched" value={row.status} /> },
    {
      key: "result",
      header: "Resultado",
      render: (row) => <span className="bz-cell-sub">{row.result || "—"}</span>,
    },
    {
      key: "actions",
      header: "Acções",
      actions: true,
      render: (row) =>
        row.status === "scheduled" ? (
          <IconButton icon={<X size={16} />} label="Cancelar" onClick={() => setConfirm(row)} tone="danger" />
        ) : null,
    },
  ];

  return (
    <div className="bz-page">
      <PageHeader
        actions={
          <Button icon={<CalendarPlus size={16} />} onClick={() => setCreating(true)}>
            Agendar publicação
          </Button>
        }
        crumbs={["Conteúdo", "Agendamento"]}
        description="A publicação corre sozinha à hora marcada. O que falhar fica aqui com o motivo."
        title="Publicações agendadas"
      />

      <div className="bz-toolbar">
        {STATES.map(([key, label]) => (
          <FilterPill active={state === key} key={key} onClick={() => setState(key)}>
            {label}
          </FilterPill>
        ))}
      </div>

      <DataTable
        columns={columns}
        empty={{ title: "Nada agendado", text: "Agende a publicação de uma página para uma data futura." }}
        error={error}
        loading={loading}
        onRetry={load}
        rowKey={(row) => String(row.id)}
        rows={items}
      />

      <Modal
        footer={
          <>
            <Button onClick={() => setCreating(false)} variant="ghost">
              Cancelar
            </Button>
            <Button disabled={!draft.pageId || !draft.runAt} loading={saving} onClick={create}>
              Agendar
            </Button>
          </>
        }
        onClose={() => setCreating(false)}
        open={creating}
        size="sm"
        title="Agendar publicação"
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Field label="Página" required>
            <Select onChange={(e) => setDraft({ ...draft, pageId: e.target.value })} value={draft.pageId}>
              <option value="">Escolher…</option>
              {pages.map((page) => (
                <option key={page.id} value={page.id}>
                  {page.slug ? `/${page.slug}` : "/"} — {i18nGet(page.title, "pt")}
                </option>
              ))}
            </Select>
          </Field>
          <Field hint="Tem de ser no futuro." label="Data e hora" required>
            <Input onChange={(e) => setDraft({ ...draft, runAt: e.target.value })} type="datetime-local" value={draft.runAt} />
          </Field>
        </div>
      </Modal>

      <ConfirmDestructive
        confirmLabel="Cancelar agendamento"
        message="A publicação não corre e a página volta a rascunho. O registo do agendamento fica na lista."
        onCancel={() => setConfirm(null)}
        onConfirm={cancel}
        open={Boolean(confirm)}
        title="Cancelar agendamento"
      />
    </div>
  );
}
