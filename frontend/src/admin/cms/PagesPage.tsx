/**
 * CMS 3.1 — Páginas do site.
 *
 * Tabela: Página (nome + slug em mono) · Estado · Idiomas · Última edição ·
 * acções. Acção principal "+ Nova página"; por linha editar, pré-visualizar,
 * duplicar, agendar e arquivar.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Calendar, Copy, Eye, Pencil, Plus, Trash2, Undo2 } from "lucide-react";
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
  Pill,
  SearchInput,
  Select,
  TableFooter,
  useUndoWindow,
  type Column,
} from "../../design/ui";
import { cmsPages, i18nGet, rows, type CmsPage, type PageStatus } from "./api";

const STATUS_FILTERS: [PageStatus | "all", string][] = [
  ["all", "Todos"],
  ["published", "Publicados"],
  ["review", "Em revisão"],
  ["scheduled", "Agendados"],
  ["draft", "Rascunhos"],
];

const TEMPLATES: [string, string][] = [
  ["landing", "Landing"],
  ["pricing", "Preços"],
  ["contact", "Contactos"],
  ["apps", "Apps"],
  ["generic", "Genérica"],
];

const PAGE_SIZE = 20;

export default function CmsPagesPage() {
  const { token } = useAuth();
  const navigate = useNavigate();

  const [pages, setPages] = useState<CmsPage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<PageStatus | "all">("all");
  const [search, setSearch] = useState("");
  const [archived, setArchived] = useState(false);
  const [page, setPage] = useState(1);

  const [formOpen, setFormOpen] = useState(false);
  const [draft, setDraft] = useState({ slug: "", titlePt: "", titleEn: "", template: "generic" });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const [scheduleFor, setScheduleFor] = useState<CmsPage | null>(null);
  const [runAt, setRunAt] = useState("");
  const [confirm, setConfirm] = useState<CmsPage | null>(null);
  const [undoTarget, setUndoTarget] = useState<CmsPage | null>(null);
  const [busy, setBusy] = useState(false);
  const undo = useUndoWindow();

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    cmsPages
      .list(token, {
        status: status === "all" ? undefined : status,
        q: search || undefined,
        scope: archived ? "archived" : "active",
      })
      .then((data) => setPages(rows<CmsPage>(data)))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, status, search, archived]);

  useEffect(load, [load]);

  const paged = useMemo(() => pages.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE), [pages, page]);

  const openNew = () => {
    setDraft({ slug: "", titlePt: "", titleEn: "", template: "generic" });
    setFormErrors({});
    setFormOpen(true);
  };

  const create = async () => {
    if (!token) return;
    setSaving(true);
    setFormErrors({});
    try {
      const created: CmsPage = await cmsPages.create(token, {
        slug: draft.slug,
        title: { pt: draft.titlePt, en: draft.titleEn || draft.titlePt },
        template: draft.template,
        locales: ["pt", "en"],
      });
      showToast("success", "Página criada.");
      setFormOpen(false);
      navigate(`/app/cms/pages/${created.id}`);
    } catch (e) {
      const message = (e as Error).message;
      // Erro 422 do backend: mapeado por campo, debaixo do campo.
      setFormErrors({ slug: message });
      showToast("danger", message);
    } finally {
      setSaving(false);
    }
  };

  const preview = async (row: CmsPage) => {
    if (!token) return;
    try {
      const { token: previewToken } = await cmsPages.previewToken(token, row.id);
      const path = row.slug ? `/${row.slug}` : "/";
      window.open(`${path}?preview_token=${encodeURIComponent(previewToken)}`, "_blank", "noopener");
    } catch (e) {
      showToast("danger", (e as Error).message);
    }
  };

  const duplicate = async (row: CmsPage) => {
    if (!token) return;
    try {
      const copy: CmsPage = await cmsPages.duplicate(token, row.id);
      showToast("success", `Duplicada como "${copy.slug}".`);
      load();
    } catch (e) {
      showToast("danger", (e as Error).message);
    }
  };

  const schedule = async () => {
    if (!token || !scheduleFor || !runAt) return;
    setBusy(true);
    try {
      await cmsPages.schedule(token, scheduleFor.id, new Date(runAt).toISOString());
      showToast("success", "Publicação agendada.");
      setScheduleFor(null);
      setRunAt("");
      load();
    } catch (e) {
      showToast("danger", (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  // Arquivar é destrutivo mas reversível: 8 segundos para desfazer (A0.8).
  const archive = async () => {
    if (!token || !confirm) return;
    const target = confirm;
    setBusy(true);
    try {
      await cmsPages.archive(token, target.id);
      setConfirm(null);
      load();
      showToast("neutral", `"${target.slug || "(inicial)"}" arquivada.`);
      setUndoTarget(target);
      undo.start(() => setUndoTarget(null));
    } catch (e) {
      showToast("danger", (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const restore = async () => {
    if (!token || !undoTarget) return;
    try {
      await cmsPages.restore(token, undoTarget.id);
      setUndoTarget(null);
      load();
      showToast("success", "Arquivo desfeito.");
    } catch (e) {
      showToast("danger", (e as Error).message);
    }
  };

  const columns: Column<CmsPage>[] = [
    {
      key: "page",
      header: "Página",
      render: (row) => (
        <span className="bz-cell-primary">
          <span className="bz-cell-id">{row.slug ? `/${row.slug}` : "/"}</span>
          <span className="bz-cell-name">{i18nGet(row.title, "pt") || "(sem nome)"}</span>
        </span>
      ),
    },
    { key: "template", header: "Modelo", render: (row) => <Pill tone="mute">{row.template_label}</Pill> },
    { key: "status", header: "Estado", render: (row) => <EnumPill group="cms" value={row.status} /> },
    {
      key: "locales",
      header: "Idiomas",
      render: (row) => (
        <span className="bz-table-mono">{(row.locales || []).map((l) => l.toUpperCase()).join(" · ")}</span>
      ),
    },
    {
      key: "updated",
      header: "Última edição",
      render: (row) => (
        <span className="bz-cell-primary">
          <span className="bz-cell-name">{row.updated_by_name || "—"}</span>
          <span className="bz-cell-sub">
            {formatDateTime(row.updated_at)} · v{row.version_number}
          </span>
        </span>
      ),
    },
    {
      key: "actions",
      header: "Acções",
      actions: true,
      render: (row) =>
        archived ? (
          <IconButton
            icon={<Undo2 size={16} />}
            label="Restaurar"
            onClick={async () => {
              if (!token) return;
              await cmsPages.restore(token, row.id);
              load();
            }}
          />
        ) : (
          <>
            <IconButton icon={<Pencil size={16} />} label="Editar" onClick={() => navigate(`/app/cms/pages/${row.id}`)} />
            <IconButton icon={<Eye size={16} />} label="Pré-visualizar" onClick={() => preview(row)} />
            <IconButton icon={<Copy size={16} />} label="Duplicar" onClick={() => duplicate(row)} />
            <IconButton icon={<Calendar size={16} />} label="Agendar" onClick={() => setScheduleFor(row)} />
            <IconButton icon={<Trash2 size={16} />} label="Arquivar" onClick={() => setConfirm(row)} tone="danger" />
          </>
        ),
    },
  ];

  return (
    <div className="bz-page">
      <PageHeader
        actions={
          <Button icon={<Plus size={16} />} onClick={openNew}>
            Nova página
          </Button>
        }
        crumbs={["Conteúdo", "Páginas do site"]}
        description="As páginas do site público. O conteúdo vive aqui — nada de texto no código."
        title="Páginas do site"
      />

      {undoTarget ? (
        <div className="bz-proposal" role="status">
          <strong>Arquivada.</strong>
          <span>
            "{undoTarget.slug || "(inicial)"}" saiu da lista.{" "}
            <button
              onClick={restore}
              style={{
                border: 0,
                background: "none",
                padding: 0,
                cursor: "pointer",
                font: "800 13px/1 var(--font-ui)",
                color: "inherit",
                textDecoration: "underline",
              }}
              type="button"
            >
              Desfazer
            </button>
          </span>
        </div>
      ) : null}

      <div className="bz-toolbar">
        {STATUS_FILTERS.map(([key, label]) => (
          <FilterPill active={status === key} key={key} onClick={() => setStatus(key)}>
            {label}
          </FilterPill>
        ))}
        <span className="bz-toolbar-spacer" />
        <FilterPill active={archived} onClick={() => setArchived((v) => !v)}>
          Arquivadas
        </FilterPill>
        <SearchInput onChange={setSearch} placeholder="Procurar por nome ou endereço" value={search} />
      </div>

      <DataTable
        columns={columns}
        empty={{
          title: archived ? "Nada arquivado" : "Ainda não há páginas",
          text: archived
            ? "As páginas arquivadas aparecem aqui e podem ser restauradas."
            : "Crie a primeira página do site ou carregue o conteúdo dos protótipos com `manage.py seed_cms`.",
          action: archived ? undefined : <Button icon={<Plus size={16} />} onClick={openNew}>Nova página</Button>,
        }}
        error={error}
        footer={<TableFooter onPage={setPage} page={page} pageSize={PAGE_SIZE} total={pages.length} />}
        loading={loading}
        onRetry={load}
        onRowClick={(row) => navigate(`/app/cms/pages/${row.id}`)}
        rowKey={(row) => String(row.id)}
        rows={paged}
      />

      <Modal
        footer={
          <>
            <Button onClick={() => setFormOpen(false)} variant="ghost">
              Cancelar
            </Button>
            <Button disabled={!draft.titlePt} loading={saving} onClick={create}>
              Criar
            </Button>
          </>
        }
        onClose={() => setFormOpen(false)}
        open={formOpen}
        title="Nova página"
      >
        <div className="bz-formgrid">
          <Field error={formErrors.slug} hint="Vazio para a página inicial." label="Endereço" required>
            <Input
              mono
              onChange={(e) => setDraft({ ...draft, slug: e.target.value })}
              placeholder="precos"
              value={draft.slug}
            />
          </Field>
          <Field label="Modelo">
            <Select onChange={(e) => setDraft({ ...draft, template: e.target.value })} value={draft.template}>
              {TEMPLATES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Nome (PT)" required>
            <Input onChange={(e) => setDraft({ ...draft, titlePt: e.target.value })} value={draft.titlePt} />
          </Field>
          <Field label="Nome (EN)">
            <Input onChange={(e) => setDraft({ ...draft, titleEn: e.target.value })} value={draft.titleEn} />
          </Field>
        </div>
      </Modal>

      <Modal
        footer={
          <>
            <Button onClick={() => setScheduleFor(null)} variant="ghost">
              Cancelar
            </Button>
            <Button disabled={!runAt} loading={busy} onClick={schedule}>
              Agendar publicação
            </Button>
          </>
        }
        onClose={() => setScheduleFor(null)}
        open={Boolean(scheduleFor)}
        size="sm"
        title="Agendar publicação"
      >
        <Field
          hint="A publicação corre sozinha à hora marcada e o resultado fica em Agendamento."
          label="Data e hora"
          required
        >
          <Input onChange={(e) => setRunAt(e.target.value)} type="datetime-local" value={runAt} />
        </Field>
      </Modal>

      <ConfirmDestructive
        loading={busy}
        message={`"${confirm?.slug || "(inicial)"}" sai do site e da lista. Pode desfazer nos 8 segundos seguintes ou restaurar em Arquivadas.`}
        onCancel={() => setConfirm(null)}
        onConfirm={archive}
        open={Boolean(confirm)}
        title="Arquivar página"
      />
    </div>
  );
}
