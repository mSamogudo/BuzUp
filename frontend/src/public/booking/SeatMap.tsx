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
 * aqui só se põe o corredor entre as duas.
 *
 * **Todas as filas partilham a mesma grelha.** Antes cada uma calculava as
 * suas colunas a partir dos bancos que tinha, e como estão centradas, uma fila
 * incompleta ficava mais estreita e empurrava os seus bancos para o meio: as
 * colunas deixavam de se alinhar e o corredor fazia um degrau. Num autocarro
 * grande a última fila é uma em vinte e quase não se nota; num minibus de 12
 * ou 15 lugares é metade da planta.
 *
 * Os lugares em falta ficam como espaço vazio — que é exactamente o que se vê
 * dentro do autocarro quando a última fila é mais curta.
 */
export default function SeatMap({
  rows, picked, maxPick, onToggle,
}: {
  rows: SeatRow[];
  picked: string[];
  maxPick: number;
  onToggle: (label: string) => void;
}) {
  const ladosDe = (r: SeatRow) => ({
    left: r.left ?? r.seats?.slice(0, 2) ?? [],
    right: r.right ?? r.seats?.slice(2) ?? [],
  });

  // A grelha vem das filas NORMAIS. A fila corrida do fundo traz todos os
  // bancos em `left` — contá-la aqui fazia `esqMax` saltar de 2 para 4 e
  // alargava TODAS as filas: um 2+2 passava a desenhar-se como 4+2, e no
  // telemóvel a planta transbordava o ecrã por causa da última linha.
  const normais = rows.filter((r) => !r.full_width);
  const base = normais.length > 0 ? normais : rows;
  const esqMax = base.reduce((m, r) => Math.max(m, ladosDe(r).left.length), 0);
  const dirMax = base.reduce((m, r) => Math.max(m, ladosDe(r).right.length), 0);

  // A fila do fundo pode ser mais larga do que as outras (5 bancos num 2+2).
  // Nesse caso é ela que manda na largura — mas só nesse caso.
  const larguraDoFundo = rows
    .filter((r) => r.full_width)
    .reduce((m, r) => Math.max(m, ladosDe(r).left.length), 0);
  const colunas = Math.max(1, esqMax + dirMax, larguraDoFundo);

  const grelha = dirMax > 0
    ? `repeat(${esqMax}, var(--seat)) var(--aisle) repeat(${dirMax}, var(--seat))`
    : `repeat(${esqMax}, var(--seat)) var(--aisle)`;

  const vazios = (n: number, chave: string) =>
    Array.from({ length: n }, (_, i) => <span className="bzbk-seat-void" key={`${chave}${i}`} aria-hidden />);

  return (
    <div>
      {/* O CSS dimensiona o banco a partir de DUAS restrições:
          `--rows` para a planta caber na altura (um autocarro de 15 filas ficava
          com 1000px numa caixa de 430 e obrigava a rolar tudo), e `--cols` para
          caber na largura — que é o que faltava. Sem o número de colunas, o
          CSS não tinha como saber se a fila mais larga transbordava o ecrã do
          telemóvel, e transbordava. */}
      <div className="bzbk-bus" style={{
        ["--rows" as string]: Math.max(1, rows.length),
        ["--cols" as string]: colunas,
      }}>
        <div className="bzbk-bus-head">
          <span>FRENTE DO AUTOCARRO</span>
          <span aria-hidden>🚍</span>
        </div>
        <div className="bzbk-bus-scroll">
          {rows.map((r) => {
            const { left, right } = ladosDe(r);
            const seatProps = { picked, maxPick, onToggle };

            // Fila corrida do fundo: ocupa a largura toda da MESMA grelha, para
            // a planta não mudar de largura na última linha.
            if (r.full_width) {
              return (
                <div className="bzbk-row bzbk-row-full" key={r.row}
                  style={{ gridTemplateColumns: `repeat(${colunas}, var(--seat))` }}>
                  {left.map((s) => <SeatButton key={s.label} seat={s} {...seatProps} />)}
                  {vazios(colunas - left.length, `f${r.row}`)}
                </div>
              );
            }

            return (
              <div className="bzbk-row" key={r.row} style={{ gridTemplateColumns: grelha }}>
                {left.map((s) => <SeatButton key={s.label} seat={s} {...seatProps} />)}
                {vazios(esqMax - left.length, `e${r.row}`)}
                <span className="bzbk-aisle">{r.row}</span>
                {right.map((s) => <SeatButton key={s.label} seat={s} {...seatProps} />)}
                {vazios(dirMax - right.length, `d${r.row}`)}
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
