import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

const WEEKDAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
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

/**
 * Calendário de marcação de dias.
 *
 * Clicar num dia marca-o; arrastar sobre vários marca a fila toda, que é como
 * se marca uma semana de partidas sem sete cliques. Os dias já passados ficam
 * inertes: uma partida no passado não é uma partida, é um engano.
 */
export default function TripCalendar({
  selected, onChange, alreadyScheduled,
}: {
  selected: string[];
  onChange: (dates: string[]) => void;
  /** Dias que já têm partida — mostrados com um ponto, para não se repetir sem saber. */
  alreadyScheduled?: Set<string>;
}) {
  const hoje = useMemo(() => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; }, []);
  const [cursor, setCursor] = useState(() => new Date(hoje.getFullYear(), hoje.getMonth(), 1));
  const [arrastando, setArrastando] = useState<null | "marcar" | "desmarcar">(null);

  const marcados = useMemo(() => new Set(selected), [selected]);

  const celulas = useMemo(() => {
    const primeiro = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
    const dias = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0).getDate();
    const vazias = mondayIndex(primeiro);
    const saida: (Date | null)[] = Array(vazias).fill(null);
    for (let d = 1; d <= dias; d += 1) {
      saida.push(new Date(cursor.getFullYear(), cursor.getMonth(), d));
    }
    return saida;
  }, [cursor]);

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

  /** Marca todas as ocorrências deste dia da semana no mês visível. */
  const marcarColuna = (coluna: number) => {
    const dias = celulas
      .filter((d): d is Date => d !== null && d >= hoje && mondayIndex(d) === coluna)
      .map(iso);
    if (dias.length === 0) return;
    const todosMarcados = dias.every((d) => marcados.has(d));
    onChange(todosMarcados
      ? selected.filter((d) => !dias.includes(d))
      : [...new Set([...selected, ...dias])].sort());
  };

  const mesVisivel = `${MONTHS[cursor.getMonth()]} ${cursor.getFullYear()}`;
  const podeRecuar = cursor > new Date(hoje.getFullYear(), hoje.getMonth(), 1);

  return (
    <div className="bzcal" onMouseLeave={() => setArrastando(null)} onMouseUp={() => setArrastando(null)}>
      <div className="bzcal-head">
        <button type="button" className="bzcal-nav" disabled={!podeRecuar}
          aria-label="Mês anterior"
          onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))}>
          <ChevronLeft size={16} />
        </button>
        <strong>{mesVisivel}</strong>
        <button type="button" className="bzcal-nav" aria-label="Mês seguinte"
          onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))}>
          <ChevronRight size={16} />
        </button>
      </div>

      <div className="bzcal-grid">
        {WEEKDAYS.map((rotulo, i) => (
          <button key={rotulo} type="button" className="bzcal-weekday"
            title={`Marcar todas as ${rotulo.toLowerCase()}s deste mês`}
            onClick={() => marcarColuna(i)}>
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

      <div className="bzcal-foot">
        <span>{selected.length} dia(s) marcado(s)</span>
        {selected.length > 0 ? (
          <button type="button" className="bzcal-clear" onClick={() => onChange([])}>
            Limpar
          </button>
        ) : (
          <span className="bzcal-hint">Clique nos dias, ou no nome do dia da semana.</span>
        )}
      </div>
    </div>
  );
}
