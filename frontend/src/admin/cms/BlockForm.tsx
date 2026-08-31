/**
 * Formulário de um bloco, gerado a partir do esquema em `blocks.ts`.
 *
 * Edita sempre o idioma escolhido no editor; o outro idioma fica intacto.
 * Cada campo com limite mostra o contador (03-cms-especificacao.md §3.2).
 */
import { useState } from "react";
import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import { Button, Field, IconButton, Input, Textarea } from "../../design/ui";
import { blockDef, type BlockField } from "./blocks";
import { MediaPicker } from "./MediaPicker";
import { i18nGet, i18nList, i18nSet, type CmsBlock, type CmsEcoSystem, type CmsPlan, type Locale } from "./api";

interface Props {
  block: CmsBlock;
  locale: Locale;
  plans: CmsPlan[];
  systems: CmsEcoSystem[];
  onChange: (content: Record<string, unknown>) => void;
}

export function BlockForm({ block, locale, plans, systems, onChange }: Props) {
  const def = blockDef(block.type);
  const content = block.content || {};

  const set = (key: string, value: unknown) => onChange({ ...content, [key]: value });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <p style={{ margin: 0, font: "400 13px/1.55 var(--font-ui)", color: "var(--muted)" }}>{def.hint}</p>
      {def.fields.map((field) => (
        <FieldEditor
          content={content}
          field={field}
          key={field.key}
          locale={locale}
          onChange={(value) => set(field.key, value)}
          plans={plans}
          systems={systems}
        />
      ))}
    </div>
  );
}

function FieldEditor({
  field,
  content,
  locale,
  plans,
  systems,
  onChange,
}: {
  field: BlockField;
  content: Record<string, unknown>;
  locale: Locale;
  plans: CmsPlan[];
  systems: CmsEcoSystem[];
  onChange: (value: unknown) => void;
}) {
  const value = content[field.key];

  if (field.kind === "text" || field.kind === "textarea") {
    const current = i18nGet(value, locale);
    const count: [number, number] | undefined = field.limit ? [current.length, field.limit] : undefined;
    return (
      <Field count={count} label={`${field.label} · ${locale.toUpperCase()}`}>
        {field.kind === "textarea" ? (
          <Textarea
            invalid={Boolean(field.limit && current.length > field.limit)}
            onChange={(e) => onChange(i18nSet(value, locale, e.target.value))}
            value={current}
          />
        ) : (
          <Input
            invalid={Boolean(field.limit && current.length > field.limit)}
            onChange={(e) => onChange(i18nSet(value, locale, e.target.value))}
            value={current}
          />
        )}
      </Field>
    );
  }

  if (field.kind === "list") {
    const items = i18nList(value, locale);
    return (
      <Field
        hint="Uma frase por linha."
        label={`${field.label} · ${locale.toUpperCase()}`}
      >
        <Textarea
          onChange={(e) =>
            onChange(i18nSet(value, locale, e.target.value.split("\n").filter((line) => line.trim() !== "")))
          }
          value={items.join("\n")}
        />
      </Field>
    );
  }

  if (field.kind === "richtext") {
    const current = i18nGet(value, locale);
    return (
      <Field
        hint="HTML restrito: h2, h3, p, ul, ol, a, strong, em. O resto é removido ao gravar."
        label={`${field.label} · ${locale.toUpperCase()}`}
      >
        <Textarea
          onChange={(e) => onChange(i18nSet(value, locale, e.target.value))}
          style={{ minHeight: 200, fontFamily: "var(--font-mono)", fontSize: 12.5 }}
          value={current}
        />
      </Field>
    );
  }

  if (field.kind === "media") {
    return <MediaField label={field.label} onChange={onChange} value={typeof value === "number" ? value : null} />;
  }

  if (field.kind === "plans" || field.kind === "systems") {
    const options: { id: number; label: string }[] =
      field.kind === "plans"
        ? plans.map((p) => ({ id: p.id, label: i18nGet(p.name, locale) }))
        : systems.map((s) => ({ id: s.id, label: s.name }));
    const selected = Array.isArray(value) ? (value as number[]) : [];
    return (
      <Field
        hint={
          field.kind === "plans"
            ? "Os planos editam-se em Preços e planos."
            : "Os sistemas editam-se em Ecossistema."
        }
        label={field.label}
      >
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {options.map((option) => {
            const on = selected.includes(option.id);
            return (
              <button
                aria-pressed={on}
                className="bz-filter"
                key={option.id}
                onClick={() =>
                  onChange(on ? selected.filter((id) => id !== option.id) : [...selected, option.id])
                }
                type="button"
              >
                {option.label}
              </button>
            );
          })}
          {options.length === 0 ? <span className="bz-field-hint">Nada para escolher ainda.</span> : null}
        </div>
      </Field>
    );
  }

  // Lista de objectos: itens repetíveis com sub-campos.
  const items = Array.isArray(value) ? (value as Record<string, unknown>[]) : [];
  const setItems = (next: Record<string, unknown>[]) => onChange(next);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div className="bz-field-head">
        <span className="bz-field-label">{field.label}</span>
        <Button
          icon={<Plus size={14} />}
          onClick={() => setItems([...items, {}])}
          size="sm"
          variant="ghost"
        >
          Acrescentar
        </Button>
      </div>

      {items.map((item, index) => (
        <div className="bzc-item" key={index}>
          <div className="bzc-item-head">
            <span className="bzc-item-title">
              {field.label} {String(index + 1).padStart(2, "0")}
            </span>
            <span>
              <IconButton
                bare
                disabled={index === 0}
                icon={<ArrowUp size={15} />}
                label="Subir"
                onClick={() => {
                  const next = [...items];
                  [next[index - 1], next[index]] = [next[index], next[index - 1]];
                  setItems(next);
                }}
              />
              <IconButton
                bare
                disabled={index === items.length - 1}
                icon={<ArrowDown size={15} />}
                label="Descer"
                onClick={() => {
                  const next = [...items];
                  [next[index + 1], next[index]] = [next[index], next[index + 1]];
                  setItems(next);
                }}
              />
              <IconButton
                bare
                icon={<Trash2 size={15} />}
                label="Remover"
                onClick={() => setItems(items.filter((_, i) => i !== index))}
                tone="danger"
              />
            </span>
          </div>

          {(field.itemFields || []).map((sub) => {
            if (sub.kind === "media") {
              return (
                <MediaField
                  key={sub.key}
                  label={sub.label}
                  onChange={(mediaId) => {
                    const next = [...items];
                    next[index] = { ...next[index], [sub.key]: mediaId };
                    setItems(next);
                  }}
                  value={typeof item[sub.key] === "number" ? (item[sub.key] as number) : null}
                />
              );
            }

            const raw = item[sub.key];
            const update = (nextValue: unknown) => {
              const next = [...items];
              next[index] = { ...next[index], [sub.key]: nextValue };
              setItems(next);
            };

            if (sub.kind === "list") {
              const lines = i18nList(raw, locale);
              return (
                <Field hint="Uma frase por linha." key={sub.key} label={`${sub.label} · ${locale.toUpperCase()}`}>
                  <Textarea
                    onChange={(e) =>
                      update(i18nSet(raw, locale, e.target.value.split("\n").filter((line) => line.trim() !== "")))
                    }
                    value={lines.join("\n")}
                  />
                </Field>
              );
            }

            const current = i18nGet(raw, locale);
            const count: [number, number] | undefined = sub.limit ? [current.length, sub.limit] : undefined;
            return (
              <Field count={count} key={sub.key} label={`${sub.label} · ${locale.toUpperCase()}`}>
                {sub.kind === "textarea" ? (
                  <Textarea
                    invalid={Boolean(sub.limit && current.length > sub.limit)}
                    onChange={(e) => update(i18nSet(raw, locale, e.target.value))}
                    value={current}
                  />
                ) : (
                  <Input
                    invalid={Boolean(sub.limit && current.length > sub.limit)}
                    onChange={(e) => update(i18nSet(raw, locale, e.target.value))}
                    value={current}
                  />
                )}
              </Field>
            );
          })}
        </div>
      ))}

      {items.length === 0 ? <span className="bz-field-hint">Sem itens.</span> : null}
    </div>
  );
}

function MediaField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number | null;
  onChange: (id: number | null) => void;
}) {
  const [picking, setPicking] = useState(false);
  return (
    <Field label={label}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <Button onClick={() => setPicking(true)} size="sm" variant="ghost">
          {value ? `Ficheiro #${value}` : "Escolher ficheiro"}
        </Button>
        {value ? (
          <IconButton bare icon={<Trash2 size={15} />} label="Remover ficheiro" onClick={() => onChange(null)} tone="danger" />
        ) : null}
      </div>
      <MediaPicker
        onClose={() => setPicking(false)}
        onPick={(asset) => {
          onChange(asset.id);
          setPicking(false);
        }}
        open={picking}
      />
    </Field>
  );
}
