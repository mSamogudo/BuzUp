/**
 * Kit base do desenho (05-plano-implementacao.md, fase 0, ponto 5).
 *
 * Todos os componentes têm estado normal/hover/foco/desactivado, definidos em
 * `ui.css`. Nada aqui inventa medidas: vêm de `02-tokens-e-padroes.md`.
 */
import {
  forwardRef,
  type AnchorHTMLAttributes,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import { Link } from "react-router-dom";
import { Loader2, Search } from "lucide-react";
import logoLight from "../../assets/busup/busup-logo-light.png";
import logoDark from "../../assets/busup/busup-logo-dark.png";
import logoMark from "../../assets/busup/busup-mark.png";
import { enumEntry, type Tone } from "../portal/enums";

/* -------------------------------------------------------------------------- */
/* Botões                                                                      */
/* -------------------------------------------------------------------------- */

export type ButtonVariant = "primary" | "navy" | "ghost" | "quiet" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

function btnClass(variant: ButtonVariant, size: ButtonSize, block?: boolean, extra?: string) {
  return [
    "bz-btn",
    `bz-btn-${variant}`,
    size === "sm" ? "bz-btn-sm" : size === "lg" ? "bz-btn-lg" : "",
    block ? "bz-btn-block" : "",
    extra || "",
  ]
    .filter(Boolean)
    .join(" ");
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  block?: boolean;
  loading?: boolean;
  icon?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", block, loading, icon, children, className, disabled, type, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      className={btnClass(variant, size, block, className)}
      disabled={disabled || loading}
      type={type || "button"}
      {...rest}
    >
      {loading ? <Loader2 aria-hidden="true" className="bz-spin" size={16} /> : icon}
      {children}
    </button>
  );
});

export interface ButtonLinkProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  block?: boolean;
  icon?: ReactNode;
  /** Rota interna: usa o router em vez de recarregar a página. */
  to?: string;
}

export function ButtonLink({
  variant = "primary",
  size = "md",
  block,
  icon,
  children,
  className,
  to,
  ...rest
}: ButtonLinkProps) {
  const cls = btnClass(variant, size, block, className);
  if (to) {
    return (
      <Link className={cls} to={to} {...(rest as Record<string, unknown>)}>
        {icon}
        {children}
      </Link>
    );
  }
  return (
    <a className={cls} {...rest}>
      {icon}
      {children}
    </a>
  );
}

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Obrigatório: botão só de ícone precisa sempre de nome acessível. */
  label: string;
  icon: ReactNode;
  tone?: "default" | "danger";
  bare?: boolean;
  large?: boolean;
  loading?: boolean;
}

export function IconButton({
  label,
  icon,
  tone = "default",
  bare,
  large,
  loading,
  className,
  disabled,
  ...rest
}: IconButtonProps) {
  return (
    <button
      aria-label={label}
      className={[
        "bz-iconbtn",
        large ? "bz-iconbtn-lg" : "",
        bare ? "bz-iconbtn-bare" : "",
        tone === "danger" ? "bz-iconbtn-danger" : "",
        className || "",
      ]
        .filter(Boolean)
        .join(" ")}
      disabled={disabled || loading}
      title={label}
      type="button"
      {...rest}
    >
      {loading ? <Loader2 aria-hidden="true" className="bz-spin" size={15} /> : icon}
    </button>
  );
}

/* -------------------------------------------------------------------------- */
/* Pílulas                                                                     */
/* -------------------------------------------------------------------------- */

export function Pill({ tone = "mute", dot, children }: { tone?: Tone; dot?: boolean; children: ReactNode }) {
  return (
    <span className={`bz-pill bz-pill-${tone}`}>
      {dot ? <i aria-hidden="true" className="bz-pill-dot" /> : null}
      {children}
    </span>
  );
}

export function FilterPill({
  active,
  count,
  onClick,
  children,
}: {
  active: boolean;
  count?: number;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button aria-pressed={active} className="bz-filter" onClick={onClick} type="button">
      {children}
      {count === undefined ? null : <span className="bz-filter-count">{count}</span>}
    </button>
  );
}

/* -------------------------------------------------------------------------- */
/* Campos                                                                      */
/* -------------------------------------------------------------------------- */

export interface FieldProps {
  label?: string;
  required?: boolean;
  hint?: string;
  /** Erro 422 do backend, mapeado por campo. */
  error?: string;
  /** Contador de caracteres do editor do CMS: `[usado, limite]`. */
  count?: [number, number];
  span2?: boolean;
  htmlFor?: string;
  children: ReactNode;
}

export function Field({ label, required, hint, error, count, span2, htmlFor, children }: FieldProps) {
  const over = count ? count[0] > count[1] : false;
  return (
    <div className={`bz-field${span2 ? " bz-span2" : ""}`}>
      {label || count ? (
        <div className="bz-field-head">
          {label ? (
            <label className="bz-field-label" htmlFor={htmlFor}>
              {label}
              {required ? <span className="bz-field-req">*</span> : null}
            </label>
          ) : (
            <span />
          )}
          {count ? (
            <span className={`bz-field-count${over ? " bz-field-count-over" : ""}`}>
              {count[0]}/{count[1]}
            </span>
          ) : null}
        </div>
      ) : null}
      {children}
      {error ? <span className="bz-field-error">{error}</span> : hint ? <span className="bz-field-hint">{hint}</span> : null}
    </div>
  );
}

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
  mono?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { invalid, mono, className, ...rest },
  ref,
) {
  return (
    <input
      ref={ref}
      className={["bz-input", invalid ? "bz-input-invalid" : "", mono ? "bz-input-mono" : "", className || ""]
        .filter(Boolean)
        .join(" ")}
      {...rest}
    />
  );
});

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { invalid, className, children, ...rest },
  ref,
) {
  return (
    <span className="bz-selectwrap">
      <select
        ref={ref}
        className={["bz-select", invalid ? "bz-select-invalid" : "", className || ""].filter(Boolean).join(" ")}
        {...rest}
      >
        {children}
      </select>
    </span>
  );
});

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { invalid, className, ...rest },
  ref,
) {
  return (
    <textarea
      ref={ref}
      className={["bz-textarea", invalid ? "bz-textarea-invalid" : "", className || ""].filter(Boolean).join(" ")}
      {...rest}
    />
  );
});

export function SearchInput({
  value,
  onChange,
  placeholder = "Pesquisar",
  ariaLabel,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  ariaLabel?: string;
}) {
  return (
    <span className="bz-search">
      <Search aria-hidden="true" size={15} />
      <Input
        aria-label={ariaLabel || placeholder}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        type="search"
        value={value}
      />
    </span>
  );
}

export function Checkbox({
  checked,
  onChange,
  label,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label?: ReactNode;
  disabled?: boolean;
}) {
  return (
    <label className="bz-check">
      <input checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} type="checkbox" />
      {label}
    </label>
  );
}

export function Switch({
  checked,
  onChange,
  label,
  disabled,
  ariaLabel,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label?: ReactNode;
  disabled?: boolean;
  ariaLabel?: string;
}) {
  return (
    <label className="bz-switch">
      <input
        aria-label={ariaLabel || (typeof label === "string" ? label : undefined)}
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        role="switch"
        type="checkbox"
      />
      <span className="bz-switch-track" />
      {label}
    </label>
  );
}

/** Selector segmentado — PT/EN, desktop/mobile, claro/escuro. */
export function Segmented<T extends string>({
  value,
  options,
  onChange,
  ariaLabel,
}: {
  value: T;
  options: [T, string][];
  onChange: (v: T) => void;
  ariaLabel?: string;
}) {
  return (
    <div aria-label={ariaLabel} className="bz-seg" role="group">
      {options.map(([key, label]) => (
        <button aria-pressed={key === value} key={key} onClick={() => onChange(key)} type="button">
          {label}
        </button>
      ))}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Separadores, migalhas, cabeçalho de ecrã                                    */
/* -------------------------------------------------------------------------- */

export function Tabs<T extends string>({
  value,
  options,
  onChange,
  counts,
}: {
  value: T;
  options: [T, string][];
  onChange: (v: T) => void;
  counts?: Partial<Record<T, number>>;
}) {
  return (
    <div className="bz-tabs" role="tablist">
      {options.map(([key, label]) => (
        <button
          aria-selected={key === value}
          className="bz-tab"
          key={key}
          onClick={() => onChange(key)}
          role="tab"
          type="button"
        >
          {label}
          {counts && counts[key] !== undefined ? <span className="bz-tab-count">{counts[key]}</span> : null}
        </button>
      ))}
    </div>
  );
}

export function Breadcrumb({ items }: { items: (string | { label: string; to: string })[] }) {
  return (
    <nav aria-label="Migalhas" className="bz-crumbs">
      {items.map((item, i) => (
        <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
          {i > 0 ? <span aria-hidden="true">·</span> : null}
          {typeof item === "string" ? item : <Link to={item.to}>{item.label}</Link>}
        </span>
      ))}
    </nav>
  );
}

export function PageHeader({
  crumbs,
  title,
  description,
  actions,
}: {
  crumbs: (string | { label: string; to: string })[];
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="bz-page-head">
      <div style={{ minWidth: 0 }}>
        <Breadcrumb items={crumbs} />
        <h1 className="bz-page-title">{title}</h1>
        {description ? <p className="bz-page-desc">{description}</p> : null}
      </div>
      {actions ? <div className="bz-page-actions">{actions}</div> : null}
    </header>
  );
}

/* -------------------------------------------------------------------------- */
/* Cartões, métricas, estados                                                  */
/* -------------------------------------------------------------------------- */

export function Card({
  children,
  large,
  flush,
  className,
  style,
}: {
  children: ReactNode;
  large?: boolean;
  flush?: boolean;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <section
      className={["bz-card", large ? "bz-card-lg" : "", flush ? "bz-card-flush" : "", className || ""]
        .filter(Boolean)
        .join(" ")}
      style={style}
    >
      {children}
    </section>
  );
}

export function Metric({ label, value, detail }: { label: string; value: ReactNode; detail?: ReactNode }) {
  return (
    <Card>
      <div className="bz-metric">
        <span className="bz-metric-label">{label}</span>
        <strong className="bz-metric-value">{value}</strong>
        {detail ? <span className="bz-metric-detail">{detail}</span> : null}
      </div>
    </Card>
  );
}

export function EmptyState({
  icon,
  title,
  text,
  action,
}: {
  icon?: ReactNode;
  title: string;
  text?: string;
  action?: ReactNode;
}) {
  return (
    <div className="bz-empty">
      {icon ? <span className="bz-empty-icon">{icon}</span> : null}
      <strong className="bz-empty-title">{title}</strong>
      {text ? <p className="bz-empty-text">{text}</p> : null}
      {action}
    </div>
  );
}

export function Skeleton({ width, height = 12, radius }: { width?: number | string; height?: number; radius?: number }) {
  return <span aria-hidden="true" className="bz-skel" style={{ display: "block", width, height, borderRadius: radius }} />;
}

/** Esqueletos com a altura real das linhas (§7). */
export function TableSkeleton({ rows = 6, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div aria-busy="true" aria-label="A carregar">
      {Array.from({ length: rows }, (_, r) => (
        <div className="bz-skel-row" key={r}>
          {Array.from({ length: cols }, (_, c) => (
            <Skeleton height={12} key={c} width={c === 0 ? 180 : c === cols - 1 ? 70 : 110} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function InlineError({ children }: { children: ReactNode }) {
  return (
    <div className="bz-error-inline" role="alert">
      {children}
    </div>
  );
}

/** Aviso obrigatório nos módulos do bloco Propostas (inventário A.2). */
export function ProposalNotice({ children }: { children?: ReactNode }) {
  return (
    <div className="bz-proposal" role="note">
      <strong>Proposta.</strong>
      <span>
        {children ||
          "Este módulo não existe no sistema. Está desenhado como proposta — não há endpoints nem ecrãs correspondentes no repositório."}
      </span>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Logótipo                                                                    */
/* -------------------------------------------------------------------------- */

/**
 * O par claro/escuro do handoff. Ambas as imagens são renderizadas e o CSS
 * (`img[data-logo]` em tokens.css) mostra a certa conforme `html[data-theme]`
 * — assim a troca de tema não espera por JavaScript.
 */
export function Logo({ height = 26, className }: { height?: number; className?: string }) {
  return (
    <span className={className} style={{ display: "inline-flex", alignItems: "center" }}>
      <img alt="BusUp" data-logo="light" src={logoLight} style={{ height, width: "auto", display: "block" }} />
      <img alt="BusUp" data-logo="dark" src={logoDark} style={{ height, width: "auto", display: "block" }} />
    </span>
  );
}

export function LogoMark({ size = 34 }: { size?: number }) {
  return <img alt="BusUp" src={logoMark} style={{ width: size, height: size, objectFit: "contain", display: "block" }} />;
}

/**
 * Pilula de um valor de enum da API. O valor vem do backend; o rotulo e o tom
 * vem da tabela do desenho (02-tokens-e-padroes.md, secao 10). Um valor sem
 * traducao mostra-se cru com tom `mute` -- nunca rebenta.
 */
export function EnumPill({ group, value }: { group: string | null; value: string | null | undefined }) {
  const [label, tone] = enumEntry(group, value);
  return <Pill tone={tone}>{label}</Pill>;
}
