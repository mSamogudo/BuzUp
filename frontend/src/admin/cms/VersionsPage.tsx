/**
 * CMS 3.10 — Histórico de versões.
 *
 * Lista por página: versão, autor, data e nota. Comparar duas versões campo a
 * campo e restaurar (com confirmação). Restaurar cria versão nova; o histórico
 * não perde nada.
 */
import { useCallback, useEffect, useState } from "react";
import { GitCompare, Undo2 } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { showToast } from "../../lib/toast";
import { formatDateTime } from "../../lib/format";
import {
  Button,
  ConfirmDestructive,
  DataTable,
  IconButton,
  InlineError,
  Modal,
  PageHeader,
  Select,
  type Column,
} from "../../design/ui";
import { cmsPages, cmsVersions, i18nGet, rows, type CmsPage, type CmsVersion } from "./api";
import "./cms.css";

interface Change {
  field: string;
  a: unknown;
  b: unknown;
}

function show(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value || "—";
  return JSON.stringify(value);
}

export default function CmsVersionsPage() {
  const { token } = useAuth();
  const [pages, setPages] = useState<CmsPage[]>([]);
  const [pageId, setPageId] = useState<number | null>(null);
  const [versions, setVersions] = useState<CmsVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [changes, setChanges] = useState<Change[] | null>(null);
  const [comparing, setComparing] = useState(false);
  const [confirm, setConfirm] = useState<CmsVersion | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token) return;
    cmsPages
      .list(token)
      .then((data) => {
        const list = rows<CmsPage>(data);
        setPages(list);
        setPageId((current) => current ?? list[0]?.id ?? null);
      })
      .catch((e: Error) => setError(e.message));
  }, [token]);

  const load = useCallback(() => {
    if (!token || !pageId) return;
    setLoading(true);
    setError(null);
    cmsVersions
      .list(token, pageId)
      .then((data) => setVersions(rows<CmsVersion>(data)))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, pageId]);

  useEffect(load, [load]);

  const compare = async () => {
    if (!token) return;
    const [a, b] = Array.from(selected).map(Number);
    if (!a || !b) {
      showToast("neutral", "Escolha exactamente duas versões.");
      return;
    }
    setComparing(true);
    try {
      const result = await cmsVersions.compare(token, a, b);
      setChanges(result.changes || []);
    } catch (e) {
      showToast("danger", (e as Error).message);
    } finally {
      setComparing(false);
    }
  };

  const restore = async () => {
    if (!token || !confirm) return;
    setBusy(true);
    try {
      await cmsVersions.restore(token, confirm.id);
      showToast("success", "Versão restaurada como rascunho novo.");
      setConfirm(null);
      load();
    } catch (e) {
      showToast("danger", (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const columns: Column<CmsVersion>[] = [
    {
      key: "number",
      header: "Versão",
      render: (row) => (
        <span className="bz-cell-primary">
          <span className="bz-cell-id">v{row.number}</span>
          <span className="bz-cell-name">{row.note || "—"}</span>
        </span>
      ),
    },
    { key: "author", header: "Autor", render: (row) => <span>{row.author_name}</span> },
    { key: "when", header: "Data", render: (row) => <span className="bz-table-mono">{formatDateTime(row.created_at)}</span> },
    {
      key: "from",
      header: "Origem",
      render: (row) => <span className="bz-cell-sub">{row.restored_from ? `Restauro de v${row.restored_from}` : "—"}</span>,
    },
    {
      key: "actions",
      header: "Acções",
      actions: true,
      render: (row) => (
        <IconButton icon={<Undo2 size={16} />} label="Restaurar esta versão" onClick={() => setConfirm(row)} />
      ),
    },
  ];

  return (
    <div className="bz-page">
      <PageHeader
        actions={
          <Button
            disabled={selected.size !== 2}
            icon={<GitCompare size={16} />}
            loading={comparing}
            onClick={compare}
            variant="ghost"
          >
            Comparar seleccionadas
          </Button>
        }
        crumbs={["Conteúdo", "Versões"]}
        description="Cada gravação cria uma versão. Restaurar não apaga nada: cria uma versão nova com o conteúdo antigo."
        title="Histórico de versões"
      />

      {error ? <InlineError>{error}</InlineError> : null}

      <div className="bz-toolbar">
        <Select
          aria-label="Página"
          onChange={(e) => {
            setPageId(Number(e.target.value));
            setSelected(new Set());
          }}
          style={{ maxWidth: 380 }}
          value={String(pageId ?? "")}
        >
          {pages.map((page) => (
            <option key={page.id} value={page.id}>
              {page.slug ? `/${page.slug}` : "/"} — {i18nGet(page.title, "pt")}
            </option>
          ))}
        </Select>
        <span className="bz-field-hint">Escolha duas versões para comparar.</span>
      </div>

      <DataTable
        columns={columns}
        empty={{ title: "Sem versões", text: "A primeira gravação cria a primeira versão." }}
        error={error}
        loading={loading}
        onRetry={load}
        onToggleAll={(all) => setSelected(all ? new Set(versions.slice(0, 2).map((v) => String(v.id))) : new Set())}
        onToggleRow={(key) =>
          setSelected((current) => {
            const next = new Set(current);
            if (next.has(key)) next.delete(key);
            else next.add(key);
            return next;
          })
        }
        rowKey={(row) => String(row.id)}
        rows={versions}
        selected={selected}
      />

      <Modal onClose={() => setChanges(null)} open={changes !== null} size="lg" title="Diferenças entre versões">
        {changes && changes.length ? (
          <div className="bzc-diff">
            <div className="bzc-diffrow" style={{ background: "var(--surface2)" }}>
              <span className="bz-label">Campo</span>
              <span className="bz-label">Versão A</span>
              <span className="bz-label">Versão B</span>
            </div>
            {changes.map((change, i) => (
              <div className="bzc-diffrow" key={i}>
                <span className="bzc-difffield">{change.field}</span>
                <span className="bzc-diff-a">{show(change.a)}</span>
                <span className="bzc-diff-b">{show(change.b)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="bz-field-hint">As duas versões são iguais.</p>
        )}
      </Modal>

      <ConfirmDestructive
        confirmLabel="Restaurar"
        message={`A página volta ao conteúdo da versão ${confirm?.number ?? ""} e fica em rascunho. O histórico mantém-se completo.`}
        loading={busy}
        onCancel={() => setConfirm(null)}
        onConfirm={restore}
        open={Boolean(confirm)}
        title="Restaurar versão"
      />
    </div>
  );
}
