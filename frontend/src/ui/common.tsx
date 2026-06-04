import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { ChevronDown, ChevronUp, Loader2, Search, X } from "lucide-react";
import { t } from "../lib/i18n";
import { humanizeStatus } from "../lib/format";
import { showToast } from "../lib/toast";
import { useUi } from "./UiPreferences";

export type TableColumn<T> = {
  header: string;
  className?: string;
  sortKey?: string;
  render: (row: T) => ReactNode;
};

export function ButtonSpinner({ size = 16 }: { size?: number }) {
  return <Loader2 aria-hidden="true" className="button-spinner" size={size} />;
}

export function StatusBadge({ value }: { value: string }) {
  const success = new Set(["active", "confirmed", "paid", "issued", "approved", "completed", "published", "installed", "used"]);
  const danger = new Set(["blocked", "failed", "cancelled", "rejected", "denied", "lost", "retired", "expired"]);
  const tone = success.has(value) ? "success" : danger.has(value) ? "danger" : "neutral";
  return <span className={`admin-status admin-status-${tone}`}>{humanizeStatus(value)}</span>;
}

export function MetricCard({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <article className="admin-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </article>
  );
}

export function PageFrame({ kicker, title, description, action, children }: {
  kicker: string; title: string; description?: string; action?: ReactNode; children: ReactNode;
}) {
  return (
    <section className="admin-page">
      <header className="admin-page-head">
        <div>
          <p className="admin-kicker">{kicker}</p>
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        {action ? <div className="admin-page-actions">{action}</div> : null}
      </header>
      {children}
    </section>
  );
}

export function SectionCard({ title, description, children }: { title: string; description?: string; children: ReactNode }) {
  return (
    <section className="admin-section">
      <div className="admin-section-head">
        <div>
          <h3>{title}</h3>
          {description ? <p>{description}</p> : null}
        </div>
      </div>
      {children}
    </section>
  );
}

export function TablePrimaryCell({ title, subtitle, meta }: { title: ReactNode; subtitle?: ReactNode; meta?: ReactNode }) {
  return (
    <div className="admin-table-primary">
      <strong>{title}</strong>
      {subtitle ? <small>{subtitle}</small> : null}
      {meta ? <small>{meta}</small> : null}
    </div>
  );
}

export function TableActionButton({ icon, label, onClick, tone = "default", loading = false, disabled = false }: {
  icon: ReactNode; label: string; onClick: () => void; tone?: "default" | "danger"; loading?: boolean; disabled?: boolean;
}) {
  return (
    <button
      aria-label={label}
      className={`admin-inline-button admin-inline-button-icon${tone === "danger" ? " admin-inline-button-danger" : ""}`}
      disabled={disabled || loading}
      onClick={onClick}
      title={label}
      type="button"
    >
      {loading ? <ButtonSpinner size={15} /> : icon}
    </button>
  );
}

export function AdminModal({ open, onClose, title, description, children }: {
  open: boolean; onClose: () => void; title: string; description?: string; children: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <>
      <div className="admin-modal-overlay" onClick={onClose} />
      <div className="admin-modal-shell" role="dialog" aria-modal="true" aria-label={title}>
        <div className="admin-modal-card">
          <div className="admin-modal-head">
            <div><h3>{title}</h3>{description ? <p>{description}</p> : null}</div>
            <button className="icon-button" onClick={onClose} type="button"><X size={18} /></button>
          </div>
          <div className="admin-modal-body">{children}</div>
        </div>
      </div>
    </>
  );
}

function normalizeSearchText(value: string) {
  return String(value || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

export function DataTable<T>({ columns, rows, rowKey, loading, emptyMessage, filterable = true }: {
  columns: TableColumn<T>[]; rows: T[]; rowKey: (row: T) => string;
  loading: boolean; emptyMessage: string; filterable?: boolean;
}) {
  const { locale } = useUi();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [query, setQuery] = useState("");
  const [sortBy, setSortBy] = useState("");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const nq = normalizeSearchText(query);

  const toggleSort = (key: string) => {
    if (sortBy === key) setSortDir((d) => d === "asc" ? "desc" : "asc");
    else { setSortBy(key); setSortDir("asc"); }
  };

  const filtered = useMemo(() => {
    let result = rows;
    if (filterable && nq) result = result.filter((row) => normalizeSearchText(JSON.stringify(row)).includes(nq));
    if (sortBy) {
      result = [...result].sort((a, b) => {
        const va = String((a as Record<string, unknown>)[sortBy] ?? "");
        const vb = String((b as Record<string, unknown>)[sortBy] ?? "");
        const cmp = va.localeCompare(vb, undefined, { numeric: true });
        return sortDir === "asc" ? cmp : -cmp;
      });
    }
    return result;
  }, [filterable, nq, rows, sortBy, sortDir]);

  useEffect(() => { setPage(1); }, [nq, pageSize]);

  if (loading) {
    return (
      <div className="skeleton-table">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="skeleton-table-row">
            {Array.from({ length: Math.min(columns.length, 4) }).map((_, j) => (
              <div key={j} className="skeleton skeleton-text" />
            ))}
          </div>
        ))}
      </div>
    );
  }

  if (!rows.length) return <div className="admin-empty-state">{emptyMessage}</div>;

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const sp = Math.min(page, totalPages);
  const si = (sp - 1) * pageSize;
  const visible = filtered.slice(si, si + pageSize);

  return (
    <div className="admin-table-wrap">
      <div className="admin-table-meta">
        {filterable ? (
          <label className="field admin-table-filter">
            <span>{t(locale, "search")}</span>
            <div className="admin-table-filter-row">
              <Search aria-hidden="true" className="admin-table-filter-icon" size={15} />
              <input placeholder={t(locale, "searchPlaceholder")} type="search" value={query} onChange={(e) => setQuery(e.target.value)} />
              {query ? <button className="icon-button admin-table-filter-clear" onClick={() => setQuery("")} type="button"><X size={15} /></button> : null}
            </div>
          </label>
        ) : <span />}
        <span className="admin-table-result-count">
          {filtered.length > 0 ? `${si + 1}-${Math.min(si + visible.length, filtered.length)} ${t(locale, "of")} ${filtered.length}` : `0 ${t(locale, "of")} 0`}
        </span>
        <label className="admin-table-page-size">
          <span>{t(locale, "perPage")}</span>
          <select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}>
            {[10, 25, 50, 100].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
      </div>
      <table className="admin-table">
        <thead><tr>{columns.map((c) => (
          <th className={c.className} key={c.header}>
            {c.sortKey ? (
              <span className="sortable-header" onClick={() => toggleSort(c.sortKey!)}>
                {c.header}
                <span className={`sort-icon${sortBy === c.sortKey ? " sort-icon-active" : ""}`}>
                  {sortBy === c.sortKey && sortDir === "asc" ? <ChevronUp size={12} /> : sortBy === c.sortKey && sortDir === "desc" ? <ChevronDown size={12} /> : <ChevronUp size={10} />}
                </span>
              </span>
            ) : c.header}
          </th>
        ))}</tr></thead>
        <tbody>
          {visible.length > 0 ? visible.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((c) => <td className={c.className} data-label={c.header} key={c.header}>{c.render(row)}</td>)}
            </tr>
          )) : (
            <tr><td className="admin-empty-state" colSpan={columns.length}>{nq ? t(locale, "noResults") : emptyMessage}</td></tr>
          )}
        </tbody>
      </table>
      {totalPages > 1 && (
        <div className="admin-table-pagination">
          <button className="secondary-button" disabled={sp <= 1} onClick={() => setPage((c) => Math.max(1, c - 1))} type="button">{t(locale, "previous")}</button>
          <span>{t(locale, "page")} {sp} {t(locale, "of")} {totalPages}</span>
          <button className="secondary-button" disabled={sp >= totalPages} onClick={() => setPage((c) => Math.min(totalPages, c + 1))} type="button">{t(locale, "next")}</button>
        </div>
      )}
    </div>
  );
}

export function TabBar({ items, value, onChange }: { items: { key: string; label: string; count?: number }[]; value: string; onChange: (key: string) => void }) {
  return (
    <div className="admin-tabbar" role="tablist">
      {items.map((item) => (
        <button
          aria-selected={item.key === value}
          className={`admin-tab${item.key === value ? " admin-tab-active" : ""}`}
          key={item.key}
          onClick={() => onChange(item.key)}
          role="tab"
          type="button"
        >
          <span>{item.label}</span>
          {typeof item.count === "number" ? <strong>{item.count}</strong> : null}
        </button>
      ))}
    </div>
  );
}

export function SegmentedControl({ items, value, onChange }: { items: { key: string; label: string }[]; value: string; onChange: (key: string) => void }) {
  return (
    <div className="segmented-control">
      {items.map((item) => (
        <button key={item.key} className={`segmented-item${item.key === value ? " segmented-item-active" : ""}`} onClick={() => onChange(item.key)} type="button">
          {item.label}
        </button>
      ))}
    </div>
  );
}

export function useAsyncData<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadToken, setReloadToken] = useState(0);
  const memoizedLoader = useCallback(loader, deps);

  useEffect(() => {
    let active = true;
    setLoading(true);
    memoizedLoader()
      .then((result) => { if (active) setData(result); })
      .catch((err) => { if (active) showToast("danger", err instanceof Error ? err.message : "Erro ao carregar."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [memoizedLoader, reloadToken]);

  return { data, loading, reload: () => setReloadToken((c) => c + 1) };
}
