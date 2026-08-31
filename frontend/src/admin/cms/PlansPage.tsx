/**
 * CMS 3.6 — Preços e planos.
 *
 * Primeiro separador: lista de planos ordenável, com nome, preço, unidade,
 * itens incluídos, destaque e visibilidade. Segundo separador: a tabela
 * comparativa da página de preços, editável linha a linha.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { GripVertical, Plus, Save, Trash2 } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { showToast } from "../../lib/toast";
import {
  Button,
  Card,
  ConfirmDestructive,
  Field,
  IconButton,
  InlineError,
  Input,
  Modal,
  PageHeader,
  Segmented,
  Switch,
  Tabs,
  TableSkeleton,
  Textarea,
} from "../../design/ui";
import {
  cmsPlans,
  i18nGet,
  i18nList,
  i18nSet,
  rows,
  type CmsPlan,
  type CmsPlanFeature,
  type Locale,
} from "./api";
import "./cms.css";

type Tab = "plans" | "features";

export default function CmsPlansPage() {
  const { token } = useAuth();
  const [tab, setTab] = useState<Tab>("plans");
  const [locale, setLocale] = useState<Locale>("pt");
  const [plans, setPlans] = useState<CmsPlan[]>([]);
  const [features, setFeatures] = useState<CmsPlanFeature[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<CmsPlan | null>(null);
  const [confirm, setConfirm] = useState<CmsPlan | null>(null);
  const [saving, setSaving] = useState(false);
  const dragFrom = useRef<number | null>(null);

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    Promise.all([cmsPlans.list(token), cmsPlans.features(token)])
      .then(([planData, featureData]) => {
        setPlans(rows<CmsPlan>(planData));
        setFeatures(rows<CmsPlanFeature>(featureData));
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(load, [load]);

  const savePlan = async () => {
    if (!token || !editing) return;
    setSaving(true);
    try {
      const body = {
        name: editing.name,
        price_label: editing.price_label,
        unit: editing.unit,
        cta_label: editing.cta_label,
        items: editing.items,
        highlighted: editing.highlighted,
        visible: editing.visible,
      };
      if (editing.id) await cmsPlans.update(token, editing.id, body);
      else await cmsPlans.create(token, { ...body, position: plans.length });
      showToast("success", "Plano gravado.");
      setEditing(null);
      load();
    } catch (e) {
      showToast("danger", (e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const archivePlan = async () => {
    if (!token || !confirm) return;
    try {
      await cmsPlans.archive(token, confirm.id);
      showToast("neutral", "Plano arquivado.");
      setConfirm(null);
      load();
    } catch (e) {
      showToast("danger", (e as Error).message);
    }
  };

  const reorder = async (next: CmsPlan[]) => {
    setPlans(next);
    if (!token) return;
    try {
      await cmsPlans.order(token, next.map((p) => p.id));
    } catch (e) {
      showToast("danger", (e as Error).message);
      load();
    }
  };

  const saveFeatures = async () => {
    if (!token) return;
    setSaving(true);
    try {
      const saved = await cmsPlans.saveFeatures(
        token,
        features.map((f, index) => ({ ...f, position: index })),
      );
      setFeatures(rows<CmsPlanFeature>(saved));
      showToast("success", "Tabela comparativa gravada.");
    } catch (e) {
      showToast("danger", (e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="bz-page">
        <PageHeader crumbs={["Conteúdo", "Preços e planos"]} title="Preços e planos" />
        <TableSkeleton cols={4} rows={4} />
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
            {tab === "plans" ? (
              <Button
                icon={<Plus size={16} />}
                onClick={() =>
                  setEditing({
                    id: 0,
                    name: { pt: "", en: "" },
                    price_label: { pt: "", en: "" },
                    unit: { pt: "", en: "" },
                    cta_label: { pt: "", en: "" },
                    items: { pt: [], en: [] },
                    position: plans.length,
                    highlighted: false,
                    visible: true,
                    deleted_at: null,
                  })
                }
              >
                Novo plano
              </Button>
            ) : (
              <Button icon={<Save size={16} />} loading={saving} onClick={saveFeatures}>
                Guardar tabela
              </Button>
            )}
          </>
        }
        crumbs={["Conteúdo", "Preços e planos"]}
        description="Os planos alimentam a landing e a página de preços; a tabela comparativa é a da página de preços."
        title="Preços e planos"
      />

      {error ? <InlineError>{error}</InlineError> : null}

      <Tabs
        onChange={setTab}
        options={[
          ["plans", "Planos"],
          ["features", "Tabela comparativa"],
        ]}
        value={tab}
      />

      {tab === "plans" ? (
        <div className="bzc-sortable">
          {plans.map((plan, index) => (
            <div
              className="bzc-sortrow"
              draggable
              key={plan.id}
              onDragOver={(e) => e.preventDefault()}
              onDragStart={() => {
                dragFrom.current = index;
              }}
              onDrop={(e) => {
                e.preventDefault();
                const from = dragFrom.current;
                if (from !== null && from !== index) {
                  const next = [...plans];
                  const [moved] = next.splice(from, 1);
                  next.splice(index, 0, moved);
                  void reorder(next);
                }
                dragFrom.current = null;
              }}
              style={{ gridTemplateColumns: "26px minmax(0,1.2fr) minmax(0,1fr) minmax(0,1.4fr) auto" }}
            >
              <span className="bzc-handle">
                <GripVertical size={16} />
              </span>
              <span className="bz-cell-primary">
                <span className="bz-cell-name">{i18nGet(plan.name, locale) || "(sem nome)"}</span>
                <span className="bz-cell-sub">{i18nGet(plan.unit, locale)}</span>
              </span>
              <span style={{ font: "800 16px/1 var(--font-display)", color: "var(--navy-text)" }}>
                {i18nGet(plan.price_label, locale)}
              </span>
              <span className="bz-cell-sub">{i18nList(plan.items, locale).length} itens incluídos</span>
              <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
                {plan.highlighted ? <span className="bz-pill bz-pill-info">Destaque</span> : null}
                <span className="bz-pill bz-pill-mute">{plan.visible ? "Visível" : "Oculto"}</span>
                <Button onClick={() => setEditing(plan)} size="sm" variant="ghost">
                  Editar
                </Button>
                <IconButton
                  bare
                  icon={<Trash2 size={15} />}
                  label="Arquivar plano"
                  onClick={() => setConfirm(plan)}
                  tone="danger"
                />
              </span>
            </div>
          ))}
          {plans.length === 0 ? <span className="bz-field-hint">Sem planos.</span> : null}
        </div>
      ) : (
        <Card flush large>
          <div className="bz-tablescroll">
            <table className="bz-table">
              <thead>
                <tr>
                  <th style={{ width: 40 }} />
                  <th>Funcionalidade</th>
                  <th>Urbano</th>
                  <th>Interurbano</th>
                  <th>Institucional</th>
                  <th className="bz-table-actions">Acções</th>
                </tr>
              </thead>
              <tbody>
                {features.map((feature, index) => {
                  const setField = (key: keyof CmsPlanFeature, next: string) =>
                    setFeatures((list) =>
                      list.map((f, i) => (i === index ? { ...f, [key]: i18nSet(f[key], locale, next) } : f)),
                    );
                  return (
                    <tr key={index}>
                      <td className="bz-table-mono">{String(index + 1).padStart(2, "0")}</td>
                      <td>
                        <Input onChange={(e) => setField("label", e.target.value)} value={i18nGet(feature.label, locale)} />
                      </td>
                      <td>
                        <Input onChange={(e) => setField("urban", e.target.value)} value={i18nGet(feature.urban, locale)} />
                      </td>
                      <td>
                        <Input
                          onChange={(e) => setField("intercity", e.target.value)}
                          value={i18nGet(feature.intercity, locale)}
                        />
                      </td>
                      <td>
                        <Input
                          onChange={(e) => setField("institutional", e.target.value)}
                          value={i18nGet(feature.institutional, locale)}
                        />
                      </td>
                      <td className="bz-table-actions">
                        <IconButton
                          bare
                          icon={<Trash2 size={15} />}
                          label="Remover linha"
                          onClick={() => setFeatures((list) => list.filter((_, i) => i !== index))}
                          tone="danger"
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="bz-tablefoot">
            <span>{features.length} linhas</span>
            <Button
              icon={<Plus size={15} />}
              onClick={() =>
                setFeatures((list) => [
                  ...list,
                  {
                    label: { pt: "", en: "" },
                    urban: { pt: "", en: "" },
                    intercity: { pt: "", en: "" },
                    institutional: { pt: "", en: "" },
                    position: list.length,
                  },
                ])
              }
              size="sm"
              variant="ghost"
            >
              Acrescentar linha
            </Button>
          </div>
        </Card>
      )}

      <Modal
        footer={
          <>
            <Button onClick={() => setEditing(null)} variant="ghost">
              Cancelar
            </Button>
            <Button loading={saving} onClick={savePlan}>
              {editing?.id ? "Guardar alterações" : "Criar"}
            </Button>
          </>
        }
        onClose={() => setEditing(null)}
        open={Boolean(editing)}
        title={editing?.id ? "Editar plano" : "Novo plano"}
      >
        {editing ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Segmented
              ariaLabel="Idioma"
              onChange={setLocale}
              options={[
                ["pt", "PT"],
                ["en", "EN"],
              ]}
              value={locale}
            />
            <div className="bz-formgrid">
              <Field label={`Nome · ${locale.toUpperCase()}`} required>
                <Input
                  onChange={(e) => setEditing({ ...editing, name: i18nSet(editing.name, locale, e.target.value) })}
                  value={i18nGet(editing.name, locale)}
                />
              </Field>
              <Field label={`Preço · ${locale.toUpperCase()}`}>
                <Input
                  onChange={(e) =>
                    setEditing({ ...editing, price_label: i18nSet(editing.price_label, locale, e.target.value) })
                  }
                  value={i18nGet(editing.price_label, locale)}
                />
              </Field>
              <Field label={`Unidade · ${locale.toUpperCase()}`} span2>
                <Textarea
                  onChange={(e) => setEditing({ ...editing, unit: i18nSet(editing.unit, locale, e.target.value) })}
                  value={i18nGet(editing.unit, locale)}
                />
              </Field>
              <Field label={`Botão · ${locale.toUpperCase()}`}>
                <Input
                  onChange={(e) =>
                    setEditing({ ...editing, cta_label: i18nSet(editing.cta_label, locale, e.target.value) })
                  }
                  value={i18nGet(editing.cta_label, locale)}
                />
              </Field>
              <Field label="Estado">
                <div style={{ display: "flex", gap: 18, alignItems: "center", height: 44 }}>
                  <Switch
                    checked={editing.highlighted}
                    label="Em destaque"
                    onChange={(v) => setEditing({ ...editing, highlighted: v })}
                  />
                  <Switch checked={editing.visible} label="Visível" onChange={(v) => setEditing({ ...editing, visible: v })} />
                </div>
              </Field>
              <Field hint="Um item por linha." label={`Itens incluídos · ${locale.toUpperCase()}`} span2>
                <Textarea
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      items: i18nSet(
                        editing.items,
                        locale,
                        e.target.value.split("\n").filter((line) => line.trim() !== ""),
                      ),
                    })
                  }
                  style={{ minHeight: 150 }}
                  value={i18nList(editing.items, locale).join("\n")}
                />
              </Field>
            </div>
          </div>
        ) : null}
      </Modal>

      <ConfirmDestructive
        message="O plano sai do site. Pode ser restaurado na vista de arquivados."
        onCancel={() => setConfirm(null)}
        onConfirm={archivePlan}
        open={Boolean(confirm)}
        title="Arquivar plano"
      />
    </div>
  );
}
