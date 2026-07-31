export interface Seat { label: string; occupied: boolean }
export interface SeatRow {
  row: number;
  /** Bancos à esquerda e à direita do corredor, como vêm do servidor. */
  left?: Seat[];
  right?: Seat[];
  /** Fila corrida do fundo: sem corredor a meio. */
  full_width?: boolean;
  /** Lista única, mantida para plantas antigas. */
  seats?: Seat[];
}

/** Planta do autocarro, com a disposição real dos bancos.
 *
 * O corredor não está numa posição fixa: há autocarros 2+2, 1+2 (banco
 * individual de um lado, comum nos interprovinciais) e 3+2. Quem sabe a
 * disposição é o servidor — manda cada fila já dividida em `left` e `right`, e
 * aqui só se põe o corredor entre as duas. Desenhar sempre 2+2 mostrava
 * lugares que não existem no autocarro.
 */
export default function SeatMap({
  rows, picked, maxPick, onToggle,
}: {
  rows: SeatRow[];
  picked: string[];
  maxPick: number;
  onToggle: (label: string) => void;
}) {
  // Colunas suficientes para a fila mais larga, para as filas incompletas não
  // desalinharem as outras.
  const widest = rows.reduce((max, r) => {
    const n = (r.left?.length ?? 0) + (r.right?.length ?? 0) || (r.seats?.length ?? 0);
    return Math.max(max, n);
  }, 0);

  return (
    <div>
      <div className="bzbk-bus">
        <div className="bzbk-bus-head">
          <span>FRENTE DO AUTOCARRO</span>
          <span aria-hidden>🚍</span>
        </div>
        <div className="bzbk-bus-scroll">
          {rows.map((r) => {
            const left = r.left ?? r.seats?.slice(0, 2) ?? [];
            const right = r.right ?? r.seats?.slice(2) ?? [];
            const seatProps = { picked, maxPick, onToggle };

            if (r.full_width) {
              return (
                <div
                  className="bzbk-row bzbk-row-full"
                  key={r.row}
                  style={{ gridTemplateColumns: `repeat(${widest}, minmax(0,1fr))` }}
                >
                  {left.map((s) => <SeatButton key={s.label} seat={s} {...seatProps} />)}
                </div>
              );
            }

            return (
              <div
                className="bzbk-row"
                key={r.row}
                style={{
                  gridTemplateColumns:
                    `repeat(${left.length}, minmax(0,1fr)) 22px repeat(${right.length}, minmax(0,1fr))`,
                }}
              >
                {left.map((s) => <SeatButton key={s.label} seat={s} {...seatProps} />)}
                <span className="bzbk-aisle">{r.row}</span>
                {right.map((s) => <SeatButton key={s.label} seat={s} {...seatProps} />)}
              </div>
            );
          })}
        </div>
      </div>
      <div className="bzbk-legend">
        <span><i /> Livre</span>
        <span><i className="picked" /> Seleccionado</span>
        <span><i className="taken" /> Ocupado</span>
      </div>
    </div>
  );
}

function SeatButton({ seat, picked, maxPick, onToggle }: {
  seat: Seat; picked: string[]; maxPick: number; onToggle: (label: string) => void;
}) {
  const isPicked = picked.includes(seat.label);
  // Bloqueia lugares novos quando já se escolheram todos os necessários —
  // evita o utilizador seleccionar 3 lugares para 2 passageiros.
  const full = !isPicked && picked.length >= maxPick;
  return (
    <button
      type="button"
      className={`bzbk-seat${seat.occupied ? " is-taken" : ""}${isPicked ? " is-picked" : ""}`}
      disabled={seat.occupied || full}
      aria-pressed={isPicked}
      aria-label={`Lugar ${seat.label}${seat.occupied ? " (ocupado)" : ""}`}
      title={seat.occupied ? "Ocupado" : `Lugar ${seat.label}`}
      onClick={() => onToggle(seat.label)}
    >
      {seat.label}
    </button>
  );
}
