import { useEffect, useMemo, useRef, useState } from "react";

export interface ComboOpt { id: number; code: string; name: string }

/** Combobox de paragem: lista todas as opções e filtra à medida que o
 * utilizador escreve — substitui o <select> que obrigava a rolar a lista
 * inteira à procura do nome. Sem dependências externas. */
export default function StopCombo({ id, value, onChange, stops, exclude, placeholder }: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  stops: ComboOpt[];
  exclude?: string;
  placeholder: string;
}) {
  const chosen = stops.find((s) => String(s.id) === value) || null;
  const [text, setText] = useState(chosen?.name || "");
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // Valor escolhido fora do combo (ex.: link partilhável ?origem=66) tem de
  // aparecer no campo assim que a lista de paragens chega.
  useEffect(() => { setText(chosen?.name || ""); }, [chosen?.name]);

  const norm = (s: string) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const filtered = useMemo(() => {
    const base = stops.filter((s) => String(s.id) !== exclude);
    // Com uma opção já escolhida e o texto intacto, mostrar a lista completa
    // (o utilizador abriu para trocar, não para filtrar pelo nome actual).
    if (!text.trim() || (chosen && text === chosen.name)) return base;
    const q = norm(text);
    return base.filter((s) => norm(`${s.name} ${s.code}`).includes(q));
  }, [stops, exclude, text, chosen]);

  useEffect(() => { setHi(0); }, [text, open]);

  // Fechar ao clicar fora (blur não serve: o clique na opção dispara antes).
  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
        setText(chosen?.name || "");
      }
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [open, chosen]);

  const pick = (s: ComboOpt) => {
    onChange(String(s.id));
    setText(s.name);
    setOpen(false);
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (!open && (e.key === "ArrowDown" || e.key === "Enter")) { setOpen(true); return; }
    if (e.key === "ArrowDown") { e.preventDefault(); setHi((h) => Math.min(h + 1, filtered.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHi((h) => Math.max(h - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); if (filtered[hi]) pick(filtered[hi]); }
    else if (e.key === "Escape") { setOpen(false); setText(chosen?.name || ""); }
  };

  useEffect(() => {
    listRef.current?.querySelector<HTMLElement>(`[data-i="${hi}"]`)?.scrollIntoView({ block: "nearest" });
  }, [hi]);

  return (
    <div className="bzbk-combo" ref={rootRef}>
      <input
        aria-autocomplete="list"
        aria-controls={`${id}-list`}
        aria-expanded={open}
        autoComplete="off"
        className="bzbk-input"
        id={id}
        onChange={(e) => {
          setText(e.target.value);
          setOpen(true);
          if (!e.target.value.trim()) onChange("");
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKey}
        placeholder={placeholder}
        role="combobox"
        value={text}
      />
      {open && (
        <ul className="bzbk-combo-list" id={`${id}-list`} ref={listRef} role="listbox">
          {filtered.length === 0 && <li className="bzbk-combo-empty">Nenhuma paragem com esse nome.</li>}
          {filtered.map((s, i) => (
            <li
              aria-selected={String(s.id) === value}
              className={`bzbk-combo-opt${i === hi ? " is-hi" : ""}${String(s.id) === value ? " is-sel" : ""}`}
              data-i={i}
              key={s.id}
              onPointerDown={(e) => { e.preventDefault(); pick(s); }}
              role="option"
            >
              {s.name}
              {s.code ? <small>{s.code}</small> : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
