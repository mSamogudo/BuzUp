import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, Download, Sparkles, Upload } from "lucide-react";
import { apiFetch, apiPost } from "../lib/api";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { AdminModal, SectionCard } from "../ui/common";

/** Tabela de preços de uma rota: uma grelha origem × destino.
 *
 * Porque existe: o motor de tarifas sempre soube cobrar preços diferentes de
 * paragem para paragem, mas configurá-los era uma regra de cada vez. Numa rota
 * de 12 paragens são 132 trajectos — e o que acontecia era ficar um configurado
 * e os outros a recusar a compra com "sem tarifa configurada".
 */

interface RouteOption { id: number; code: string; name: string; }
interface MatrixStop { id: number; code: string; name: string; }
interface MatrixData {
  route: { id: number; code: string; name: string; service_type: string };
  stops: MatrixStop[];
  prices: Record<string, string>;
  fallback_amount: string;
  pairs_total: number;
  pairs_priced: number;
  has_return: boolean;
  unsellable: number;
}

const METODOS = [
  { key: "origin_destination", label: "Paragem a paragem", hint: "Uma linha por trajecto — preço diferente em cada par." },
  { key: "fixed", label: "Preço único", hint: "Um só valor, igual em qualquer trajecto da rota." },
];

export default function FareMatrixTab({ routes }: { routes: RouteOption[] }) {
  const { token } = useAuth();
  const [routeId, setRouteId] = useState("");
  const [data, setData] = useState<MatrixData | null>(null);
  const [prices, setPrices] = useState<Record<string, string>>({});
  const [fallback, setFallback] = useState("");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);

  const [fillModal, setFillModal] = useState(false);
  const [fill, setFill] = useState({ base: "", per_stop: "" });
  const [method, setMethod] = useState("origin_destination");
  const [importModal, setImportModal] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<{ rows: number; changes: number } | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const aplicar = useCallback((d: MatrixData) => {
    setData(d);
    setPrices(d.prices || {});
    setFallback(d.fallback_amount || "");
    setDirty(false);
  }, []);

  const carregar = useCallback(async (id: string) => {
    if (!id) { setData(null); return; }
    setLoading(true);
    try {
      aplicar(await apiFetch(`/api/admin/routes/${id}/fare-matrix/`, token!));
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro");
      setData(null);
    } finally { setLoading(false); }
  }, [token, aplicar]);

  useEffect(() => { carregar(routeId); }, [routeId, carregar]);

  const definir = (chave: string, valor: string) => {
    // Só dígitos, ponto e vírgula: um preço com letras só se descobre na
    // gravação, e aí já se perdeu o trabalho todo da grelha.
    const limpo = valor.replace(/[^\d.,]/g, "");
    setPrices((p) => ({ ...p, [chave]: limpo }));
    setDirty(true);
  };

  const gravar = async () => {
    if (!data) return;
    setBusy(true);
    try {
      const d: MatrixData = await apiPost(
        `/api/admin/routes/${data.route.id}/fare-matrix/`, token!,
        { prices, fallback_amount: fallback },
      );
      aplicar(d);
      const s = (d as unknown as { saved?: { created: number; updated: number; deleted: number } }).saved;
      showToast("success", s
        ? `Tabela gravada: ${s.created} novos, ${s.updated} actualizados, ${s.deleted} removidos.`
        : "Tabela gravada.");
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro");
    } finally { setBusy(false); }
  };

  const preencher = async () => {
    if (!data) return;
    setBusy(true);
    try {
      const r = await apiPost(
        `/api/admin/routes/${data.route.id}/fare-matrix/fill/`, token!,
        { base: fill.base, per_stop: fill.per_stop },
      );
      // Só preenche a grelha — a gravação continua a ser um acto do operador.
      setPrices(r.prices || {});
      setDirty(true);
      setFillModal(false);
      showToast("neutral", "Grelha preenchida. Reveja os valores e grave.");
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro");
    } finally { setBusy(false); }
  };

  const criarVolta = async () => {
    if (!data) return;
    setBusy(true);
    try {
      const d: MatrixData = await apiPost(
        `/api/admin/routes/${data.route.id}/fare-matrix/return-direction/`, token!, {},
      );
      aplicar(d);
      showToast("success", "Sentido de volta criado a espelhar a ida. Confirme as distâncias em Rotas.");
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro");
    } finally { setBusy(false); }
  };

  const descarregarModelo = async () => {
    if (!data) return;
    try {
      const res = await fetch(
        `/api/admin/routes/${data.route.id}/fare-matrix/template/?method=${method}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!res.ok) throw new Error("Falha ao descarregar o modelo.");
      const url = URL.createObjectURL(await res.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = `precos-${data.route.code}-${method}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro");
    }
  };

  const enviarExcel = async (aplicarJa: boolean) => {
    if (!data || !file) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      if (aplicarJa) fd.append("apply", "true");
      const res = await fetch(`/api/admin/routes/${data.route.id}/fare-matrix/import/`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd,
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || "Erro ao importar.");
      if (aplicarJa) {
        aplicar(d);
        setImportModal(false);
        setPreview(null);
        setFile(null);
        if (fileRef.current) fileRef.current.value = "";
        showToast("success", "Tabela importada e aplicada.");
      } else {
        setPreview({ rows: d.rows, changes: d.changes });
      }
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro");
    } finally { setBusy(false); }
  };

  const comPreco = useMemo(
    () => Object.values(prices).filter((v) => String(v).trim() !== "").length,
    [prices],
  );

  return (
    <SectionCard
      title="Tabela de preços"
      description="O preço de cada trajecto da rota, de paragem a paragem e nos dois sentidos. Um trajecto sem preço próprio cai no preço de recurso; sem nenhum dos dois, o passageiro não consegue comprar."
    >
      <div className="admin-form-grid" style={{ marginBottom: 14 }}>
        <label className="field"><span>Rota</span>
          <select value={routeId} onChange={(e) => setRouteId(e.target.value)}>
            <option value="">Escolha a rota…</option>
            {routes.map((r) => <option key={r.id} value={r.id}>{r.code} · {r.name}</option>)}
          </select>
        </label>
        <label className="field"><span>Preço de recurso (MZN)</span>
          <input
            value={fallback}
            disabled={!data}
            placeholder="ex: 1000"
            onChange={(e) => { setFallback(e.target.value.replace(/[^\d.,]/g, "")); setDirty(true); }}
          />
        </label>
      </div>

      {!data && !loading ? (
        <p className="dash-kpi-note">Escolha uma rota para ver e editar a tabela de preços.</p>
      ) : null}
      {loading ? <p className="dash-kpi-note">A carregar…</p> : null}

      {data ? (
        <>
          <div className="fare-matrix-stats">
            <span><strong>{comPreco}</strong> de {data.pairs_total} trajectos com preço próprio</span>
            {data.unsellable > 0 ? (
              <span className="fare-matrix-bad">
                <AlertTriangle size={14} /> {data.unsellable} {data.unsellable === 1 ? "trajecto não se vende" : "trajectos não se vendem"} hoje
              </span>
            ) : (
              <span className="fare-matrix-ok">Todos os trajectos têm preço.</span>
            )}
          </div>

          {!data.has_return ? (
            <div className="fare-matrix-warn">
              <AlertTriangle size={16} />
              <div>
                <strong>Esta rota só tem sentido de ida.</strong>
                <p>O regresso não é sequer um trajecto válido: a compra é recusada antes de se olhar para o preço. Criar o sentido de volta espelha as paragens da ida pela ordem inversa.</p>
              </div>
              <button className="primary-button" disabled={busy} onClick={criarVolta} type="button">Criar sentido de volta</button>
            </div>
          ) : null}

          <div className="admin-toolbar">
            <div className="fare-matrix-tools">
              <select value={method} onChange={(e) => setMethod(e.target.value)} aria-label="Método do modelo">
                {METODOS.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
              </select>
              <button className="icon-text-button" onClick={descarregarModelo} type="button">
                <Download size={15} /><span>Modelo Excel</span>
              </button>
              <button className="icon-text-button" onClick={() => { setFile(null); setPreview(null); setImportModal(true); }} type="button">
                <Upload size={15} /><span>Importar Excel</span>
              </button>
              <button className="icon-text-button" onClick={() => setFillModal(true)} type="button">
                <Sparkles size={15} /><span>Preencher por paragens</span>
              </button>
            </div>
            <div className="admin-toolbar-spacer" />
            <button className="primary-button" disabled={busy || !dirty} onClick={gravar} type="button">
              {busy ? "A gravar…" : "Gravar tabela"}
            </button>
          </div>
          <p className="dash-kpi-note">{METODOS.find((m) => m.key === method)?.hint}</p>

          {data.stops.length < 2 ? (
            <p className="dash-kpi-note">Esta rota não tem paragens suficientes para ter tabela de preços.</p>
          ) : (
            <div className="fare-matrix-wrap">
              <table className="fare-matrix">
                <thead>
                  <tr>
                    <th className="fare-matrix-corner">De \ Para</th>
                    {data.stops.map((s) => <th key={s.id} title={s.name}>{s.name}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {data.stops.map((origem) => (
                    <tr key={origem.id}>
                      <th title={origem.name}>{origem.name}</th>
                      {data.stops.map((destino) => {
                        if (origem.id === destino.id) return <td key={destino.id} className="fare-matrix-self">—</td>;
                        const chave = `${origem.id}-${destino.id}`;
                        const valor = prices[chave] ?? "";
                        return (
                          <td key={destino.id}>
                            <input
                              value={valor}
                              inputMode="decimal"
                              placeholder={fallback ? fallback : "—"}
                              className={valor.trim() === "" && !fallback ? "fare-matrix-empty" : ""}
                              onChange={(e) => definir(chave, e.target.value)}
                            />
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="dash-kpi-note" style={{ marginTop: 8 }}>
            Uma célula vazia usa o preço de recurso. Sem preço de recurso, uma célula vazia é um trajecto que ninguém consegue comprar.
          </p>
        </>
      ) : null}

      <AdminModal open={fillModal} onClose={() => setFillModal(false)} title="Preencher por paragens">
        <div className="admin-form">
          <p className="dash-kpi-note">
            Calcula um preço para cada trajecto a partir do número de paragens entre a origem e o destino. Preenche a grelha para rever — não grava nada.
          </p>
          <div className="admin-form-grid">
            <label className="field"><span>Preço base (1 paragem)</span>
              <input value={fill.base} inputMode="decimal" placeholder="ex: 100"
                     onChange={(e) => setFill((f) => ({ ...f, base: e.target.value }))} />
            </label>
            <label className="field"><span>Acréscimo por paragem extra</span>
              <input value={fill.per_stop} inputMode="decimal" placeholder="ex: 50"
                     onChange={(e) => setFill((f) => ({ ...f, per_stop: e.target.value }))} />
            </label>
          </div>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy || !fill.base} onClick={preencher} type="button">Preencher grelha</button>
            <button className="secondary-button" onClick={() => setFillModal(false)} type="button">Cancelar</button>
          </div>
        </div>
      </AdminModal>

      <AdminModal open={importModal} onClose={() => setImportModal(false)} title="Importar tabela de preços">
        <div className="admin-form">
          <p className="dash-kpi-note">
            Descarregue o modelo, preencha a coluna do preço e volte a enviá-lo. O ficheiro é primeiro pré-visualizado: nada muda até confirmar.
          </p>
          <label className="field"><span>Ficheiro Excel (.xlsx)</span>
            <input ref={fileRef} type="file" accept=".xlsx"
                   onChange={(e) => { setFile(e.target.files?.[0] || null); setPreview(null); }} />
          </label>
          {preview ? (
            <p className="fare-matrix-preview">
              {preview.rows} {preview.rows === 1 ? "linha lida" : "linhas lidas"} · <strong>{preview.changes}</strong> {preview.changes === 1 ? "preço muda" : "preços mudam"}.
              {preview.changes === 0 ? " A tabela fica igual." : ""}
            </p>
          ) : null}
          <div className="admin-form-actions">
            {preview ? (
              <button className="primary-button" disabled={busy} onClick={() => enviarExcel(true)} type="button">Aplicar</button>
            ) : (
              <button className="primary-button" disabled={busy || !file} onClick={() => enviarExcel(false)} type="button">Pré-visualizar</button>
            )}
            <button className="secondary-button" onClick={() => setImportModal(false)} type="button">Cancelar</button>
          </div>
        </div>
      </AdminModal>
    </SectionCard>
  );
}
