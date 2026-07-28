export interface Seat { label: string; occupied: boolean }
export interface SeatRow { row: number; seats: Seat[] }

/** Planta do autocarro: 2 + corredor + 2, com o lugar do condutor à frente. */
export default function SeatMap({
  rows, picked, maxPick, onToggle,
}: {
  rows: SeatRow[];
  picked: string[];
  maxPick: number;
  onToggle: (label: string) => void;
}) {
  return (
    <div>
      <div className="bzbk-bus">
        <div className="bzbk-bus-head">
          <span>FRENTE DO AUTOCARRO</span>
          <span aria-hidden>🚍</span>
        </div>
        {rows.map((r) => (
          <div className="bzbk-row" key={r.row}>
            {r.seats.slice(0, 2).map((s) => (
              <SeatButton key={s.label} seat={s} picked={picked} maxPick={maxPick} onToggle={onToggle} />
            ))}
            {r.seats.length > 2 ? <span className="bzbk-aisle">{r.row}</span> : <span />}
            {r.seats.slice(2).map((s) => (
              <SeatButton key={s.label} seat={s} picked={picked} maxPick={maxPick} onToggle={onToggle} />
            ))}
          </div>
        ))}
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
