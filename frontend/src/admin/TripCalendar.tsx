import { useMemo, useState } from "react";
import { t } from "../lib/i18n";
import { useUi } from "../ui/UiPreferences";
import { ChevronLeft, ChevronRight } from "lucide-react";

const WEEKDAYS = ["S", "T", "Q", "Q", "S", "S", "D"];
const WEEKDAY_TITLES = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];
const MONTHS = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

function iso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Segunda-feira = 0, para a grelha bater certo com os rótulos. */
function mondayIndex(d: Date): number {
  return (d.getDay() + 6) % 7;
}

function daysOfMonth(year: number, month: number): (Date | null)[] {
  const first = new Date(year, month, 1);
  const count = new Date(year, month + 1, 0).getDate();
  const cells: (Date | null)[] = Array(mondayIndex(first)).fill(null);
  for (let d = 1; d <= count; d += 1) cells.push(new Date(year, month, d));
  return cells;
}

/**
 * Calendário de marcação de dias.
 *
 * Dois meses lado a lado: programar uma carreira atravessa quase sempre a
 * fronteira do mês, e paginar para trás e para a frente fazia perder de vista o
 * que já estava marcado.
 *
 * As células são pequenas de propósito. Uma grelha de sete colunas com
 * `aspect-ratio: 1` num contentor largo dá quadrados de cem pixéis — meia
 * página de espaço para mostrar trinta números.
 */
export default function TripCalendar({
  selected, onChange, alreadyScheduled, months = 2,
}: {
  selected: string[];
  onChange: (dates: string[]) => void;
  /** Dias que já têm partida — marcados com um ponto, para não se repetir sem saber. */
  alreadyScheduled?: Set<string>;
  months?: number;
}) {
  const { locale: lc } = useUi();
  const hoje = useMemo(() => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; }, []);
  const [cursor, setCursor] = useState(() => new Date(hoje.getFullYear(), hoje.getMonth(), 1));
  const [arrastando, setArrastando] = useState<null | "marcar" | "desmarcar">(null);

  const marcados = useMemo(() => new Set(selected), [selected]);

  const paineis = useMemo(() => Array.from({ length: months }, (_, i) => {
    const m = new Date(cursor.getFullYear(), cursor.getMonth() + i, 1);
    return { data: m, celulas: daysOfMonth(m.getFullYear(), m.getMonth()) };
  }), [cursor, months]);

  const alternar = (dia: Date, forcar?: "marcar" | "desmarcar") => {
    if (dia < hoje) return;
    const chave = iso(dia);
    const accao = forcar ?? (marcados.has(chave) ? "desmarcar" : "marcar");
    if (accao === "marcar" && marcados.has(chave)) return;
    if (accao === "desmarcar" && !marcados.has(chave)) return;
    onChange(accao === "marcar"
      ? [...selected, chave].sort()
      : selected.filter((x) => x !== chave));
  };

  /** Todos os dias visíveis que satisfazem `criterio`, de hoje para a frente. */
  const diasVisiveis = (criterio: (d: Date) => boolean) =>
    paineis.flatMap((p) => p.celulas)
      .filter((d): d is Date => d !== null && d >= hoje && criterio(d))
      .map(iso);

  /** Alterna em bloco: se já estavam todos marcados, desmarca-os. */
  const alternarBloco = (criterio: (d: Date) => boolean) => {
    const dias = diasVisiveis(criterio);
    if (dias.length === 0) return;
    const todos = dias.every((d) => marcados.has(d));
    onChange(todos
      ? selected.filter((d) => !dias.includes(d))
      : [...new Set([...selected, ...dias])].sort());
  };

  const atalhos = [
    { rotulo: "Dias úteis", criterio: (d: Date) => mondayIndex(d) < 5 },
    { rotulo: "Fins-de-semana", criterio: (d: Date) => mondayIndex(d) >= 5 },
    { rotulo: "Tudo", criterio: () => true },
  ];

  const podeRecuar = cursor > new Date(hoje.getFullYear(), hoje.getMonth(), 1);

  return (
    <div className="bzcal" onMouseLeave={() => setArrastando(null)} onMouseUp={() => setArrastando(null)}>
      <div className="bzcal-bar">
        <div className="bzcal-nav-group">
          <button type="button" className="bzcal-nav" disabled={!podeRecuar} aria-label={t(lc, "prevMonth")}
            onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))}>
            <ChevronLeft size={15} />
          </button>
          <button type="button" className="bzcal-nav" aria-label={t(lc, "nextMonth")}
            onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))}>
            <ChevronRight size={15} />
          </button>
        </div>
        <div className="bzcal-shortcuts">
          {atalhos.map((a) => (
            <button key={a.rotulo} type="button" className="bzcal-shortcut"
              onClick={() => alternarBloco(a.criterio)}>{a.rotulo}</button>
          ))}
          <button type="button" className="bzcal-shortcut is-quiet"
            disabled={selected.length === 0} onClick={() => onChange([])}>{t(lc, "clear")}</button>
        </div>
      </div>

      <div className="bzcal-months">
        {paineis.map(({ data, celulas }) => (
          <div className="bzcal-month" key={`${data.getFullYear()}-${data.getMonth()}`}>
            <div className="bzcal-month-name">
              {MONTHS[data.getMonth()]} <span>{data.getFullYear()}</span>
            </div>
            <div className="bzcal-grid">
              {WEEKDAYS.map((rotulo, i) => (
                <button key={`${rotulo}${i}`} type="button" className="bzcal-weekday"
                  title={`Marcar todas as ${WEEKDAY_TITLES[i].toLowerCase()}s visíveis`}
                  onClick={() => alternarBloco((d) => mondayIndex(d) === i)}>
                  {rotulo}
                </button>
              ))}
              {celulas.map((dia, i) => {
                if (!dia) return <span key={`v${i}`} className="bzcal-empty" />;
                const chave = iso(dia);
                const passado = dia < hoje;
                const on = marcados.has(chave);
                const jaTem = alreadyScheduled?.has(chave);
                return (
                  <button
                    key={chave}
                    type="button"
                    disabled={passado}
                    aria-pressed={on}
                    title={jaTem ? "Já tem partida programada" : undefined}
                    className={`bzcal-day${on ? " is-on" : ""}${passado ? " is-past" : ""}${jaTem ? " has-trip" : ""}`}
                    onMouseDown={() => {
                      if (passado) return;
                      const accao = on ? "desmarcar" : "marcar";
                      setArrastando(accao);
                      alternar(dia, accao);
                    }}
                    onMouseEnter={() => { if (arrastando) alternar(dia, arrastando); }}
                  >
                    {dia.getDate()}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <p className="bzcal-hint">
        {t(lc, "calendarHint")}
      </p>
    </div>
  );
}
