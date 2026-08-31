/**
 * CMS 3.4 — Menus e rodapé.
 *
 * Quatro listas (cabeçalho, rodapé produto, rodapé contacto, rodapé
 * ecossistema) com itens arrastáveis, rótulo por idioma, destino (página
 * interna ou URL) e visibilidade. Grava-se um menu de cada vez, inteiro.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { GripVertical, Plus, Save, Trash2 } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { showToast } from "../../lib/toast";
import {
  Button,
  Card,
  IconButton,
  Input,
  InlineError,
  PageHeader,
  Segmented,
  Select,
  Switch,
  TableSkeleton,
} from "../../design/ui";
import { cmsMenus, cmsPages, i18nGet, i18nSet, rows, type CmsMenu, type CmsMenuItem, type CmsPage, type Locale } from "./api";
import "./cms.css";

const MENU_LABELS: Record<string, string> = {
  header: "Cabeçalho",
  footer_product: "Rodapé · Produto",
  footer_contact: "Rodapé · Contacto",
  footer_eco: "Rodapé · Ecossistema",
};

export default function CmsMenusPage() {
  const { token } = useAuth();
  const [menus, setMenus] = useState<CmsMenu[]>([]);
  const [pages, setPages] = useState<CmsPage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [locale, setLocale] = useState<Locale>("pt");
  const [drafts, setDrafts] = useState<Record<string, CmsMenuItem[]>>({});
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const dragFrom = useRef<{ menu: string; index: number } | null>(null);
  const [dragOver, setDragOver] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    Promise.all([cmsMenus.list(token), cmsPages.list(token)])
      .then(([menuData, pageData]) => {
        const list = rows<CmsMenu>(menuData);
        setMenus(list);
        setPages(rows<CmsPage>(pageData));
        setDrafts(Object.fromEntries(list.map((menu) => [menu.key, menu.items])));
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(load, [load]);

  const update = (key: string, items: CmsMenuItem[]) => setDrafts((d) => ({ ...d, [key]: items }));

  const save = async (key: string) => {
    if (!token) return;
    setSavingKey(key);
    try {
      const items = (drafts[key] || []).map((item, index) => ({ ...item, position: index }));
      await cmsMenus.saveItems(token, key, items);
      showToast("success", "Menu gravado.");
      load();
    } catch (e) {
      showToast("danger", (e as Error).message);
    } finally {
      setSavingKey(null);
    }
  };

  if (loading) {
    return (
      <div className="bz-page">
        <PageHeader crumbs={["Conteúdo", "Menus e rodapé"]} title="Menus e rodapé" />
        <TableSkeleton cols={4} rows={5} />
      </div>
    );
  }

  return (
    <div className="bz-page">
      <PageHeader
        actions={
          <Segmented
            ariaLabel="Idioma dos rótulos"
            onChange={setLocale}
            options={[
              ["pt", "PT"],
              ["en", "EN"],
            ]}
            value={locale}
          />
        }
        crumbs={["Conteúdo", "Menus e rodapé"]}
        description="Cada menu grava-se inteiro, com a ordem. O destino pode ser uma página do site ou um endereço externo."
        title="Menus e rodapé"
      />

      {error ? <InlineError>{error}</InlineError> : null}

      {menus.map((menu) => {
        const items = drafts[menu.key] || [];
        return (
          <Card key={menu.key} large>
            <div className="bz-toolbar" style={{ marginBottom: 14 }}>
              <strong style={{ font: "800 16px/1.2 var(--font-display)" }}>
                {MENU_LABELS[menu.key] || menu.key}
              </strong>
              <span className="bz-field-hint">{items.length} itens</span>
              <span className="bz-toolbar-spacer" />
              <Button
                icon={<Plus size={15} />}
                onClick={() =>
                  update(menu.key, [
                    ...items,
                    { label: { pt: "", en: "" }, page: null, href: "", position: items.length, target: "", visible: true },
                  ])
                }
                size="sm"
                variant="ghost"
              >
                Acrescentar
              </Button>
              <Button
                icon={<Save size={15} />}
                loading={savingKey === menu.key}
                onClick={() => save(menu.key)}
                size="sm"
              >
                Guardar menu
              </Button>
            </div>

            <div className="bzc-sortable">
              {items.map((item, index) => (
                <div
                  className={`bzc-sortrow${dragOver === `${menu.key}:${index}` ? " bzc-sortrow-over" : ""}`}
                  draggable
                  key={index}
                  onDragEnd={() => {
                    dragFrom.current = null;
                    setDragOver(null);
                  }}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(`${menu.key}:${index}`);
                  }}
                  onDragStart={() => {
                    dragFrom.current = { menu: menu.key, index };
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    const from = dragFrom.current;
                    if (from && from.menu === menu.key && from.index !== index) {
                      const next = [...items];
                      const [moved] = next.splice(from.index, 1);
                      next.splice(index, 0, moved);
                      update(menu.key, next);
                    }
                    dragFrom.current = null;
                    setDragOver(null);
                  }}
                >
                  <span className="bzc-handle">
                    <GripVertical size={16} />
                  </span>

                  <Input
                    aria-label={`Rótulo ${locale.toUpperCase()}`}
                    onChange={(e) => {
                      const next = [...items];
                      next[index] = { ...item, label: i18nSet(item.label, locale, e.target.value) };
                      update(menu.key, next);
                    }}
                    placeholder={`Rótulo ${locale.toUpperCase()}`}
                    value={i18nGet(item.label, locale)}
                  />

                  {item.page ? (
                    <Select
                      aria-label="Página de destino"
                      onChange={(e) => {
                        const next = [...items];
                        const value = e.target.value;
                        next[index] = value === "" ? { ...item, page: null } : { ...item, page: Number(value), href: "" };
                        update(menu.key, next);
                      }}
                      value={String(item.page)}
                    >
                      <option value="">Endereço livre…</option>
                      {pages.map((page) => (
                        <option key={page.id} value={page.id}>
                          {page.slug ? `/${page.slug}` : "/"} — {i18nGet(page.title, "pt")}
                        </option>
                      ))}
                    </Select>
                  ) : (
                    <Input
                      aria-label="Destino"
                      mono
                      onChange={(e) => {
                        const next = [...items];
                        next[index] = { ...item, href: e.target.value };
                        update(menu.key, next);
                      }}
                      placeholder="/precos, #recursos ou https://…"
                      value={item.href}
                    />
                  )}

                  <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <Switch
                      ariaLabel="Visível"
                      checked={item.visible}
                      onChange={(v) => {
                        const next = [...items];
                        next[index] = { ...item, visible: v };
                        update(menu.key, next);
                      }}
                    />
                    <IconButton
                      bare
                      icon={<span style={{ font: "600 11px/1 var(--font-mono)" }}>{item.page ? "URL" : "Pág" }</span>}
                      label={item.page ? "Passar a endereço livre" : "Passar a página interna"}
                      onClick={() => {
                        const next = [...items];
                        next[index] = item.page
                          ? { ...item, page: null }
                          : { ...item, page: pages[0]?.id ?? null, href: "" };
                        update(menu.key, next);
                      }}
                    />
                    <IconButton
                      bare
                      icon={<Trash2 size={15} />}
                      label="Remover item"
                      onClick={() => update(menu.key, items.filter((_, i) => i !== index))}
                      tone="danger"
                    />
                  </span>
                </div>
              ))}
              {items.length === 0 ? <span className="bz-field-hint">Menu vazio.</span> : null}
            </div>
          </Card>
        );
      })}
    </div>
  );
}
