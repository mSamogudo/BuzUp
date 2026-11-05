import { useEffect, useImperativeHandle, useMemo, useRef, useState, useSyncExternalStore, type ReactNode, type Ref } from "react";
import { createPortal } from "react-dom";
import { Check, MapPin, Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import "./StopCombo.css";

export interface ComboOpt { id: number; code: string; name: string }

/** O que quem usa o combo pode pedir-lhe de fora. O cartao de pesquisa abre
 *  o destino sozinho logo que a origem fica escolhida (`abrir`), e leva o
 *  foco ao campo em falta quando a pesquisa e submetida incompleta (`focar`). */
export type StopComboControlo = { abrir: () => void; focar: () => void };

const norm = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** O troco do nome que bate com o que se escreveu, a negrito.
 *  A comparacao ignora acentos ("matola" encontra "Mátola"), por isso as
 *  posicoes sao medidas no texto normalizado e trazidas de volta ao original. */
function realce(nome: string, q: string): ReactNode {
  const alvo = norm(q.trim());
  if (!alvo) return nome;
  let plano = "";
  const origem: number[] = [];
  for (let i = 0; i < nome.length; i++) {
    for (const c of norm(nome[i])) { plano += c; origem.push(i); }
  }
  const k = plano.indexOf(alvo);
  if (k < 0) return nome;
  const a = origem[k];
  const b = origem[k + alvo.length - 1] + 1;
  return <>{nome.slice(0, a)}<mark className="bzbk-combo-realce">{nome.slice(a, b)}</mark>{nome.slice(b)}</>;
}

/** Telemovel = ecra ate 640px, a mesma fronteira do CSS do combo. */
const consulta = "(max-width: 640px)";
function useTelemovel() {
  return useSyncExternalStore(
    (avisar) => {
      const m = window.matchMedia(consulta);
      m.addEventListener("change", avisar);
      return () => m.removeEventListener("change", avisar);
    },
    () => window.matchMedia(consulta).matches,
    () => false,
  );
}

/** Combobox de paragem: lista todas as opções e filtra à medida que o
 * utilizador escreve — substitui o <select> que obrigava a rolar a lista
 * inteira à procura do nome. Sem dependências externas.
 *
 * O código da paragem (ST-...) continua a contar para a pesquisa, mas já não
 * aparece: é um identificador interno, e no cartão estreito da TPM ocupava
 * metade da linha e saía cortado.
 *
 * Com `folha`, no telemóvel a lista abre em ecrã inteiro em vez de pendurada
 * no campo: o teclado tapava metade da lista e os nomes longos não cabiam. */
export default function StopCombo({
  id, value, onChange, onEscolha, stops, exclude, placeholder,
  emptyText = "Nenhuma paragem com esse nome.",
  folha = false, rotulo, fechar = "Fechar", invalido = false, ref,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  /** Chamado quando a pessoa escolhe uma paragem (e nao quando limpa o campo). */
  onEscolha?: (v: string) => void;
  stops: ComboOpt[];
  exclude?: string;
  placeholder: string;
  /** Texto quando a pesquisa não encontra nada; vem do dicionário do site. */
  emptyText?: string;
  /** Lista em ecrã inteiro no telemóvel. */
  folha?: boolean;
  /** Título da folha (o rótulo do campo). */
  rotulo?: string;
  fechar?: string;
  invalido?: boolean;
  ref?: Ref<StopComboControlo>;
}) {
  const chosen = stops.find((s) => String(s.id) === value) || null;
  const [text, setText] = useState(chosen?.name || "");
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const folhaRef = useRef<HTMLDivElement>(null);
  const telemovel = useTelemovel();
  const emFolha = folha && telemovel;

  // Valor escolhido fora do combo (ex.: link partilhável ?origem=66) tem de
  // aparecer no campo assim que a lista de paragens chega.
  useEffect(() => { setText(chosen?.name || ""); }, [chosen?.name]);

  useImperativeHandle(ref, () => ({
    abrir: () => {
      if (emFolha) { setOpen(true); return; }
      // O foco abre a lista (onFocus); se ja tinha foco, abre-se a mao.
      inputRef.current?.focus();
      setOpen(true);
    },
    focar: () => inputRef.current?.focus(),
  }), [emFolha]);

  /* Com uma opção já escolhida e o texto intacto, mostra-se a lista completa
     (a pessoa abriu para trocar, não para filtrar pelo nome actual). */
  const consultaActiva = !text.trim() || (chosen && text === chosen.name) ? "" : text;
  const filtered = useMemo(() => {
    const base = stops.filter((s) => String(s.id) !== exclude);
    if (!consultaActiva) return base;
    const q = norm(consultaActiva);
    return base.filter((s) => norm(`${s.name} ${s.code}`).includes(q));
  }, [stops, exclude, consultaActiva]);

  useEffect(() => { setHi(0); }, [text, open]);

  // Fechar ao clicar fora (blur não serve: o clique na opção dispara antes).
  // Na folha não há "fora": ela cobre o ecrã e tem botão de fechar.
  // O ouvinte entra no tique seguinte: quando outro combo abre este de dentro
  // do seu proprio pointerdown (origem escolhida -> abre o destino), esse
  // mesmo evento ainda esta a subir ate ao document, e um ouvinte posto ja
  // apanhava-o e fechava a lista no instante em que ela abria.
  useEffect(() => {
    if (!open || emFolha) return;
    const onDown = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
        setText(chosen?.name || "");
      }
    };
    const t = window.setTimeout(() => document.addEventListener("pointerdown", onDown));
    return () => { window.clearTimeout(t); document.removeEventListener("pointerdown", onDown); };
  }, [open, chosen, emFolha]);

  // A folha prende o scroll da página e recebe o foco ao abrir.
  useEffect(() => {
    if (!open || !emFolha) return;
    const antes = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    folhaRef.current?.focus();
    return () => { document.body.style.overflow = antes; };
  }, [open, emFolha]);

  const fecharFolha = () => {
    setOpen(false);
    setText(chosen?.name || "");
    inputRef.current?.focus();
  };

  const pick = (s: ComboOpt) => {
    onChange(String(s.id));
    setText(s.name);
    setOpen(false);
    onEscolha?.(String(s.id));
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (!open && (e.key === "ArrowDown" || e.key === "Enter")) { e.preventDefault(); setOpen(true); return; }
    if (e.key === "ArrowDown") { e.preventDefault(); setHi((h) => Math.min(h + 1, filtered.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHi((h) => Math.max(h - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); if (filtered[hi]) pick(filtered[hi]); }
    else if (e.key === "Escape") { if (emFolha) fecharFolha(); else { setOpen(false); setText(chosen?.name || ""); } }
  };

  useEffect(() => {
    listRef.current?.querySelector<HTMLElement>(`[data-i="${hi}"]`)?.scrollIntoView({ block: "nearest" });
  }, [hi]);

  const lista = (
    <ul className="bzbk-combo-list" id={`${id}-list`} ref={listRef} role="listbox">
      {filtered.length === 0 && <li className="bzbk-combo-empty" role="presentation">{emptyText}</li>}
      {filtered.map((s, i) => (
        <li
          aria-selected={String(s.id) === value}
          className={`bzbk-combo-opt${i === hi ? " is-hi" : ""}${String(s.id) === value ? " is-sel" : ""}`}
          data-i={i}
          id={`${id}-opt-${s.id}`}
          key={s.id}
          onPointerEnter={() => setHi(i)}
          onPointerDown={(e) => { e.preventDefault(); pick(s); }}
          role="option"
        >
          <MapPin aria-hidden className="bzbk-combo-opt-icone" size={16} />
          <span className="bzbk-combo-opt-nome">{realce(s.name, consultaActiva)}</span>
          {String(s.id) === value ? <Check aria-hidden className="bzbk-combo-opt-check" size={16} /> : null}
        </li>
      ))}
    </ul>
  );

  const activo = open && filtered[hi] ? `${id}-opt-${filtered[hi].id}` : undefined;

  if (emFolha) {
    /* A folha vai para dentro da caixa do site (`.bzlp`), e nao para o body:
       e ai que vivem os tokens de cor e o tema escuro. */
    const destinoFolha = rootRef.current?.closest<HTMLElement>(".bzlp") ?? document.body;
    return (
      <div className="bzbk-combo" ref={rootRef}>
        <Input
          aria-controls={`${id}-folha`}
          aria-expanded={open}
          aria-haspopup="dialog"
          aria-invalid={invalido || undefined}
          className="bzbk-input"
          id={id}
          onClick={() => setOpen(true)}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " " || e.key === "ArrowDown") { e.preventDefault(); setOpen(true); } }}
          placeholder={placeholder}
          readOnly
          ref={inputRef}
          // Um <input> so de leitura e uma caixa de texto, e caixa de texto nao
          // pode levar `aria-expanded`. O padrao ARIA 1.2 para "campo que abre
          // um dialogo de escolha" e o combobox com `aria-haspopup="dialog"`.
          role="combobox"
          title={chosen?.name}
          value={chosen?.name || ""}
        />
        {open && createPortal(
          <div
            aria-label={rotulo}
            aria-modal="true"
            className="bzbk-folha"
            id={`${id}-folha`}
            onKeyDown={(e) => { if (e.key === "Escape") fecharFolha(); }}
            ref={folhaRef}
            role="dialog"
            tabIndex={-1}
          >
            <div className="bzbk-folha-topo">
              <h2 className="bzbk-folha-titulo">{rotulo}</h2>
              <button aria-label={fechar} className="bzbk-folha-fechar" onClick={fecharFolha} type="button">
                <X aria-hidden size={20} />
              </button>
            </div>
            <div className="bzbk-folha-busca">
              <Search aria-hidden size={18} />
              <input
                aria-activedescendant={activo}
                aria-autocomplete="list"
                aria-controls={`${id}-list`}
                aria-expanded
                aria-label={rotulo}
                autoComplete="off"
                enterKeyHint="search"
                onChange={(e) => setText(e.target.value)}
                onKeyDown={onKey}
                placeholder={placeholder}
                role="combobox"
                type="search"
                value={consultaActiva ? text : ""}
              />
            </div>
            {lista}
          </div>,
          destinoFolha,
        )}
      </div>
    );
  }

  return (
    <div className="bzbk-combo" ref={rootRef}>
      <Input
        aria-activedescendant={activo}
        aria-autocomplete="list"
        aria-controls={`${id}-list`}
        aria-expanded={open}
        aria-invalid={invalido || undefined}
        autoComplete="off"
        className="bzbk-input"
        id={id}
        onChange={(e) => {
          setText(e.target.value);
          setOpen(true);
          if (!e.target.value.trim()) onChange("");
        }}
        // O clique tambem abre: depois de um Escape o foco fica no campo, e
        // clicar de novo nao volta a disparar o onFocus.
        onClick={() => setOpen(true)}
        onFocus={() => setOpen(true)}
        onKeyDown={onKey}
        placeholder={placeholder}
        ref={inputRef}
        role="combobox"
        title={chosen && text === chosen.name ? chosen.name : undefined}
        value={text}
      />
      {open && lista}
    </div>
  );
}
