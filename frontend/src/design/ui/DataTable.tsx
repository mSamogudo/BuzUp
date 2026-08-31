/**
 * Tabela do portal (02-tokens-e-padroes.md §7).
 *
 * Responde sempre aos quatro estados do handoff: a carregar (esqueletos com a
 * altura real das linhas), vazio, erro e cheia. O rodapé mostra a contagem
 * total, os arquivados e a paginação.
 */
import type { ReactNode } from "react";
import { ChevronLeft, ChevronRight, Inbox } from "lucide-react";
import { Button, EmptyState, IconButton, InlineError, TableSkeleton } from "./kit";

export type Column<T> = {
  key: string;
  header: string;
  /** Alinhada à direita e em mono — para valores e contagens. */
  numeric?: boolean;
  /** Coluna de acções: alinhada à direita, sem quebra. */
  actions?: boolean;
  width?: number | string;
  render: (row: T) => ReactNode;
};

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading,
  error,
  onRetry,
  empty,
  onRowClick,
  selected,
  onToggleRow,
  onToggleAll,
  footer,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  empty?: { title: string; text?: string; action?: ReactNode };
  onRowClick?: (row: T) => void;
  /** Selecção múltipla: chaves seleccionadas. Sem isto a coluna não aparece. */
  selected?: Set<string>;
  onToggleRow?: (key: string) => void;
  onToggleAll?: (all: boolean) => void;
  footer?: ReactNode;
}) {
  const selectable = Boolean(selected && onToggleRow);
  const allSelected = selectable && rows.length > 0 && rows.every((r) => selected!.has(rowKey(r)));

  return (
    <div className="bz-tablewrap">
      <div className="bz-tablescroll">
        <table className="bz-table bz-table-sticky1">
          <thead>
            <tr>
              {selectable ? (
                <th style={{ width: 44 }}>
                  <input
                    aria-label="Seleccionar tudo"
                    checked={allSelected}
                    onChange={(e) => onToggleAll?.(e.target.checked)}
                    type="checkbox"
                  />
                </th>
              ) : null}
              {columns.map((c) => (
                <th
                  className={c.numeric ? "bz-table-num" : c.actions ? "bz-table-actions" : undefined}
                  key={c.key}
                  style={c.width ? { width: c.width } : undefined}
                >
                  {c.header}
                </th>
              ))}
            </tr>
          </thead>
          {loading || error || rows.length === 0 ? null : (
            <tbody>
              {rows.map((row) => {
                const key = rowKey(row);
                return (
                  <tr
                    key={key}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    style={onRowClick ? { cursor: "pointer" } : undefined}
                  >
                    {selectable ? (
                      <td onClick={(e) => e.stopPropagation()}>
                        <input
                          aria-label="Seleccionar linha"
                          checked={selected!.has(key)}
                          onChange={() => onToggleRow!(key)}
                          type="checkbox"
                        />
                      </td>
                    ) : null}
                    {columns.map((c) => (
                      <td
                        className={c.numeric ? "bz-table-num" : c.actions ? "bz-table-actions" : undefined}
                        key={c.key}
                        onClick={c.actions ? (e) => e.stopPropagation() : undefined}
                      >
                        {c.render(row)}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          )}
        </table>
      </div>

      {loading ? <TableSkeleton cols={columns.length} rows={6} /> : null}

      {!loading && error ? (
        <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
          <InlineError>{error}</InlineError>
          {onRetry ? (
            <div>
              <Button onClick={onRetry} size="sm" variant="ghost">
                Tentar de novo
              </Button>
            </div>
          ) : null}
        </div>
      ) : null}

      {!loading && !error && rows.length === 0 ? (
        <EmptyState
          action={empty?.action}
          icon={<Inbox size={20} />}
          text={empty?.text}
          title={empty?.title || "Sem registos"}
        />
      ) : null}

      {footer}
    </div>
  );
}

export function TableFooter({
  total,
  archived,
  page,
  pageSize,
  onPage,
  extra,
}: {
  total: number;
  archived?: number;
  page: number;
  pageSize: number;
  onPage: (p: number) => void;
  extra?: ReactNode;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="bz-tablefoot">
      <span>
        {total} {total === 1 ? "registo" : "registos"}
        {archived !== undefined && archived > 0 ? ` · ${archived} arquivados` : ""}
      </span>
      {extra}
      <div className="bz-pager">
        <IconButton
          bare
          disabled={page <= 1}
          icon={<ChevronLeft size={17} />}
          label="Página anterior"
          onClick={() => onPage(page - 1)}
        />
        <span className="bz-pager-page">
          {page} / {pages}
        </span>
        <IconButton
          bare
          disabled={page >= pages}
          icon={<ChevronRight size={17} />}
          label="Página seguinte"
          onClick={() => onPage(page + 1)}
        />
      </div>
    </div>
  );
}
