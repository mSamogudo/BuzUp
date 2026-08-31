/**
 * CMS 3.7 — Ecossistema UpDigital.
 *
 * Lista ordenável de sistemas com logótipo, nome, URL e estado.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { GripVertical, Plus, Trash2 } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { showToast } from "../../lib/toast";
import {
  Button,
  ConfirmDestructive,
  EnumPill,
  Field,
  IconButton,
  InlineError,
  Input,
  Modal,
  PageHeader,
  Segmented,
  Switch,
  TableSkeleton,
  Textarea,
} from "../../design/ui";
import { MediaPicker } from "./MediaPicker";
import { cmsEco, i18nGet, i18nSet, rows, type CmsEcoSystem, type Locale } from "./api";
import "./cms.css";

export default function CmsEcoSystemsPage() {
  const { token } = useAuth();
  const [systems, setSystems] = useState<CmsEcoSystem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [locale, setLocale] = useState<Locale>("pt");
  const [editing, setEditing] = useState<CmsEcoSystem | null>(null);
  const [confirm, setConfirm] = useState<CmsEcoSystem | null>(null);
  const [saving, setSaving] = useState(false);
  const [picking, setPicking] = useState(false);
  const dragFrom = useRef<number | null>(null);

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    cmsEco
      .list(token)
      .then((data) => setSystems(rows<CmsEcoSystem>(data)))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(load, [load]);

  const save = async () => {
    if (!token || !editing) return;
    setSaving(true);
    try {
      const body = {
        name: editing.name,
        logo: editing.logo,
        url: editing.url,
        note: editing.note,
        status: editing.status,
      };
      if (editing.id) await cmsEco.update(token, editing.id, body);
      else await cmsEco.create(token, { ...body, position: systems.length });
      showToast("success", "Sistema gravado.");
      setEditing(null);
      load();
    } catch (e) {
      showToast("danger", (e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const archive = async () => {
    if (!token || !confirm) return;
    try {
      await cmsEco.archive(token, confirm.id);
      showToast("neutral", "Sistema arquivado.");
      setConfirm(null);
      load();
    } catch (e) {
      showToast("danger", (e as Error).message);
    }
  };

  const reorder = async (next: CmsEcoSystem[]) => {
    setSystems(next);
    if (!token) return;
    try {
      await cmsEco.order(token, next.map((s) => s.id));
    } catch (e) {
      showToast("danger", (e as Error).message);
      load();
    }
  };

  if (loading) {
    return (
      <div className="bz-page">
        <PageHeader crumbs={["Conteúdo", "Ecossistema"]} title="Ecossistema UpDigital" />
        <TableSkeleton cols={4} rows={5} />
      </div>
    );
  }

  return (
    <div className="bz-page">
      <PageHeader
        actions={
          <>
            <Segmented
              ariaLabel="Idioma"
              onChange={setLocale}
              options={[
                ["pt", "PT"],
                ["en", "EN"],
              ]}
              value={locale}
            />
            <Button
              icon={<Plus size={16} />}
              onClick={() =>
                setEditing({
                  id: 0,
                  name: "",
                  logo: null,
                  logo_url: "",
                  url: "",
                  note: { pt: "", en: "" },
                  status: "published",
                  status_label: "Publicado",
                  position: systems.length,
                  deleted_at: null,
                })
              }
            >
              Novo sistema
            </Button>
          </>
        }
        crumbs={["Conteúdo", "Ecossistema"]}
        description="Os sistemas do grupo mostrados na landing, nos preços e no rodapé."
        title="Ecossistema UpDigital"
      />

      {error ? <InlineError>{error}</InlineError> : null}

      <div className="bzc-sortable">
        {systems.map((system, index) => (
          <div
            className="bzc-sortrow"
            draggable
            key={system.id}
            onDragOver={(e) => e.preventDefault()}
            onDragStart={() => {
              dragFrom.current = index;
            }}
            onDrop={(e) => {
              e.preventDefault();
              const from = dragFrom.current;
              if (from !== null && from !== index) {
                const next = [...systems];
                const [moved] = next.splice(from, 1);
                next.splice(index, 0, moved);
                void reorder(next);
              }
              dragFrom.current = null;
            }}
            style={{ gridTemplateColumns: "26px 92px minmax(0,1fr) minmax(0,1.2fr) auto" }}
          >
            <span className="bzc-handle">
              <GripVertical size={16} />
            </span>
            <span
              style={{
                height: 44,
                display: "grid",
                placeItems: "center",
                background: "var(--surface2)",
                borderRadius: 10,
                padding: 6,
              }}
            >
              {system.logo_url ? (
                <img alt="" src={system.logo_url} style={{ maxWidth: "100%", maxHeight: 26, objectFit: "contain" }} />
              ) : (
                <span className="bz-label">—</span>
              )}
            </span>
            <span className="bz-cell-primary">
              <span className="bz-cell-name">{system.name}</span>
              <span className="bz-cell-sub">{i18nGet(system.note, locale)}</span>
            </span>
            <span className="bz-table-mono">{system.url || "—"}</span>
            <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <EnumPill group="cms" value={system.status} />
              <Button onClick={() => setEditing(system)} size="sm" variant="ghost">
                Editar
              </Button>
              <IconButton
                bare
                icon={<Trash2 size={15} />}
                label="Arquivar sistema"
                onClick={() => setConfirm(system)}
                tone="danger"
              />
            </span>
          </div>
        ))}
        {systems.length === 0 ? <span className="bz-field-hint">Sem sistemas.</span> : null}
      </div>

      <Modal
        footer={
          <>
            <Button onClick={() => setEditing(null)} variant="ghost">
              Cancelar
            </Button>
            <Button loading={saving} onClick={save}>
              {editing?.id ? "Guardar alterações" : "Criar"}
            </Button>
          </>
        }
        onClose={() => setEditing(null)}
        open={Boolean(editing)}
        title={editing?.id ? "Editar sistema" : "Novo sistema"}
      >
        {editing ? (
          <div className="bz-formgrid">
            <Field label="Nome" required>
              <Input onChange={(e) => setEditing({ ...editing, name: e.target.value })} value={editing.name} />
            </Field>
            <Field label="Endereço">
              <Input
                mono
                onChange={(e) => setEditing({ ...editing, url: e.target.value })}
                placeholder="https://payup.updigital.co.mz"
                value={editing.url}
              />
            </Field>
            <Field label="Logótipo">
              <Button onClick={() => setPicking(true)} size="sm" variant="ghost">
                {editing.logo ? `Ficheiro #${editing.logo}` : "Escolher ficheiro"}
              </Button>
            </Field>
            <Field label="Publicado">
              <div style={{ display: "flex", alignItems: "center", height: 44 }}>
                <Switch
                  checked={editing.status === "published"}
                  label={editing.status === "published" ? "No site" : "Rascunho"}
                  onChange={(v) => setEditing({ ...editing, status: v ? "published" : "draft" })}
                />
              </div>
            </Field>
            <Field label={`Nota · ${locale.toUpperCase()}`} span2>
              <Textarea
                onChange={(e) => setEditing({ ...editing, note: i18nSet(editing.note, locale, e.target.value) })}
                value={i18nGet(editing.note, locale)}
              />
            </Field>
          </div>
        ) : null}
      </Modal>

      <MediaPicker
        onClose={() => setPicking(false)}
        onPick={(asset) => {
          setEditing((current) => (current ? { ...current, logo: asset.id, logo_url: asset.url } : current));
          setPicking(false);
        }}
        open={picking}
      />

      <ConfirmDestructive
        message="O sistema sai da landing, dos preços e do rodapé."
        onCancel={() => setConfirm(null)}
        onConfirm={archive}
        open={Boolean(confirm)}
        title="Arquivar sistema"
      />
    </div>
  );
}
