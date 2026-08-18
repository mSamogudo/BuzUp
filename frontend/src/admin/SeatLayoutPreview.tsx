import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { apiFetch } from "../lib/api";

interface Fila { row: number; left: string[]; right: string[]; full_width: boolean }

/**
 * Como fica a planta com esta lotação e esta disposição.
 *
 * O operador escolhia «2+2» numa lista e nunca via o resultado — tinha de o
 * imaginar. Num autocarro de 50 lugares engana-se pouco; num minibus de 15, a
 * diferença entre 2+2 e 1+2 é a diferença entre uma planta que existe e uma
 * que o passageiro não vai encontrar a bordo.
 *
 * As filas vêm do servidor: a regra da planta é uma só, e escrevê-la outra vez
 * aqui era garantir que um dia deixavam de concordar.
 */
export default function SeatLayoutPreview({
  capacity, layout, lastRow,
}: {
  capacity: number;
  layout: string;
  lastRow: number;
}) {
  const { token } = useAuth();
  const [filas, setFilas] = useState<Fila[] | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (!token || !capacity || capacity <= 0) { setFilas(null); return; }
    let cancelado = false;
    const id = window.setTimeout(() => {
      const q = new URLSearchParams({
        capacity: String(capacity), layout, last_row: String(lastRow || 0),
      });
      apiFetch(`/api/vehicles/seat-preview/?${q}`, token)
        .then((d) => { if (!cancelado) { setFilas(d.rows || []); setErro(""); } })
        .catch((e) => { if (!cancelado) { setFilas(null); setErro(e instanceof Error ? e.message : "Erro"); } });
    }, 200);
    return () => { cancelado = true; window.clearTimeout(id); };
  }, [token, capacity, layout, lastRow]);

  if (erro) return <p className="bzsl-note">{erro}</p>;
  if (!filas) {
    return <p className="bzsl-note">Indique a lotação para ver como fica a planta.</p>;
  }
  if (filas.length === 0) return null;

  // A grelha é a da fila mais completa de cada lado: as filas incompletas
  // deixam a coluna vazia em vez de encolher e desalinhar as outras.
  const esqMax = filas.reduce((m, f) => Math.max(m, f.left.length), 0);
  const dirMax = filas.reduce((m, f) => Math.max(m, f.right.length), 0);
  const colunas = Math.max(1, esqMax + dirMax);
  const grelha = dirMax > 0
    ? `repeat(${esqMax}, 1fr) 14px repeat(${dirMax}, 1fr)`
    : `repeat(${esqMax}, 1fr) 14px`;

  const vazios = (n: number, chave: string) =>
    Array.from({ length: n }, (_, i) => <span className="bzsl-void" key={`${chave}${i}`} aria-hidden />);

  const total = filas.reduce((n, f) => n + f.left.length + f.right.length, 0);

  return (
    <div className="bzsl">
      <div className="bzsl-head">
        <span>FRENTE</span>
        <span>{filas.length} fila(s) · {total} lugares</span>
      </div>
      <div className="bzsl-rows">
        {filas.map((f) => (
          f.full_width ? (
            <div className="bzsl-row" key={f.row}
              style={{ gridTemplateColumns: `repeat(${colunas}, 1fr)` }}>
              {f.left.map((s) => <span className="bzsl-seat" key={s}>{s}</span>)}
              {vazios(colunas - f.left.length, `f${f.row}`)}
            </div>
          ) : (
            <div className="bzsl-row" key={f.row} style={{ gridTemplateColumns: grelha }}>
              {f.left.map((s) => <span className="bzsl-seat" key={s}>{s}</span>)}
              {vazios(esqMax - f.left.length, `e${f.row}`)}
              <span className="bzsl-aisle" aria-hidden />
              {f.right.map((s) => <span className="bzsl-seat" key={s}>{s}</span>)}
              {vazios(dirMax - f.right.length, `d${f.row}`)}
            </div>
          )
        ))}
      </div>
    </div>
  );
}
