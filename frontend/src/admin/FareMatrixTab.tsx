import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, Download, Sparkles, Upload } from "lucide-react";
import { apiFetch, apiPost } from "../lib/api";
import { t, type Locale } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { AdminModal, SectionCard } from "../ui/common";
import { useConfirm } from "../ui/ConfirmDialog";
import { mensagemDeErro } from "../lib/errors";
import { useUi } from "../ui/UiPreferences";

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

const metodos = (lc: Locale) => [
  { key: "origin_destination", label: t(lc, "stopToStop"), hint: t(lc, "stopToStopHint") },
  { key: "fixed", label: t(lc, "flatPrice"), hint: t(lc, "flatPriceHint") },
];

export default function FareMatrixTab({ routes }: { routes: RouteOption[] }) {
  const { locale: lc } = useUi();
  const { token } = useAuth();
  const { confirm, dialog: confirmDialog } = useConfirm();
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
      showToast("danger", mensagemDeErro(err, lc));
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
        ? t(lc, "okFareGridSaved", { c: s.created, u: s.updated, d: s.deleted })
        : t(lc, "okFareImported"));
    } catch (err) {
      showToast("danger", mensagemDeErro(err, lc));
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
      showToast("neutral", t(lc, "okFareGridFilled"));
    } catch (err) {
      showToast("danger", mensagemDeErro(err, lc));
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
      showToast("success", t(lc, "okFareReturnCreated"));
    } catch (err) {
      showToast("danger", mensagemDeErro(err, lc));
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
      showToast("danger", mensagemDeErro(err, lc));
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
        showToast("success", t(lc, "okFareImported"));
      } else {
        setPreview({ rows: d.rows, changes: d.changes });
      }
    } catch (err) {
      showToast("danger", mensagemDeErro(err, lc));
    } finally { setBusy(false); }
  };

  // Trocar de rota com a grelha por gravar deitava fora 132 precos escritos a
  // mao sem uma palavra.
  const trocarRota = async (novo: string) => {
    if (dirty && data) {
      const ok = await confirm({
        title: t(lc, "unsavedChanges"),
        message: t(lc, "unsavedGrid"),
        confirmLabel: "Mudar de rota",
        tone: "danger",
      });
      if (!ok) return;
    }
    setRouteId(novo);
  };

  const comPreco = useMemo(
    () => Object.values(prices).filter((v) => String(v).trim() !== "").length,
    [prices],
  );

  return (
    <SectionCard
      title={t(lc, "priceTable")}
      description={t(lc, "priceTableHint")}
    >
      <div className="admin-form-grid" style={{ marginBottom: 14 }}>
        <label className="field"><span>{t(lc, "route")}</span>
          <select value={routeId} onChange={(e) => trocarRota(e.target.value)}>
            <option value="">{t(lc, "chooseRoute")}</option>
            {routes.map((r) => <option key={r.id} value={r.id}>{r.code} · {r.name}</option>)}
          </select>
        </label>
        <label className="field"><span>{t(lc, "fallbackPrice")}</span>
          <input
            value={fallback}
            disabled={!data}
            placeholder="ex: 1000"
            onChange={(e) => { setFallback(e.target.value.replace(/[^\d.,]/g, "")); setDirty(true); }}
          />
        </label>
      </div>

      {!data && !loading ? (
        <p className="dash-kpi-note">{t(lc, "chooseRouteForPrices")}</p>
      ) : null}
      {loading ? <p className="dash-kpi-note">{t(lc, "loading")}</p> : null}

      {data ? (
        <>
          <div className="fare-matrix-stats">
            <span><strong>{comPreco}</strong> de {data.pairs_total} trajectos com preço próprio</span>
            {data.unsellable > 0 ? (
              <span className="fare-matrix-bad">
                <AlertTriangle size={14} /> {data.unsellable} {data.unsellable === 1 ? "trajecto não se vende" : "trajectos não se vendem"} hoje
              </span>
            ) : (
              <span className="fare-matrix-ok">{t(lc, "allLegsPriced")}</span>
            )}
          </div>

          {!data.has_return ? (
            <div className="fare-matrix-warn">
              <AlertTriangle size={16} />
              <div>
                <strong>{t(lc, "outboundOnly")}</strong>
                <p>O regresso não é sequer um trajecto válido: a compra é recusada antes de se olhar para o preço. Criar o sentido de volta espelha as paragens da ida pela ordem inversa.</p>
              </div>
              <button className="primary-button" disabled={busy} onClick={criarVolta} type="button">{t(lc, "createInbound")}</button>
            </div>
          ) : null}

          <div className="admin-toolbar">
            <div className="fare-matrix-tools">
              <select value={method} onChange={(e) => setMethod(e.target.value)} aria-label={t(lc, "templateMethod")}>
                {metodos(lc).map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
              </select>
              <button className="icon-text-button" onClick={descarregarModelo} type="button">
                <Download size={15} /><span>{t(lc, "excelTemplate")}</span>
              </button>
              <button className="icon-text-button" onClick={() => { setFile(null); setPreview(null); setImportModal(true); }} type="button">
                <Upload size={15} /><span>{t(lc, "importExcel")}</span>
              </button>
              <button className="icon-text-button" onClick={() => setFillModal(true)} type="button">
                <Sparkles size={15} /><span>{t(lc, "fillByStops")}</span>
              </button>
            </div>
            <div className="admin-toolbar-spacer" />
            <button className="primary-button" disabled={busy || !dirty} onClick={gravar} type="button">
              {busy ? "A gravar…" : "Gravar tabela"}
            </button>
          </div>
          <p className="dash-kpi-note">{metodos(lc).find((m) => m.key === method)?.hint}</p>

          {data.stops.length < 2 ? (
            <p className="dash-kpi-note">{t(lc, "notEnoughStops")}</p>
          ) : (
            <div className="fare-matrix-wrap">
              <table className="fare-matrix">
                <thead>
                  <tr>
                    <th className="fare-matrix-corner">{t(lc, "fromTo")}</th>
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

      <AdminModal open={fillModal} onClose={() => setFillModal(false)} title={t(lc, "fillByStops")}>
        <div className="admin-form">
          <p className="dash-kpi-note">
            Calcula um preço para cada trajecto a partir do número de paragens entre a origem e o destino. Preenche a grelha para rever — não grava nada.
          </p>
          <div className="admin-form-grid">
            <label className="field"><span>{t(lc, "basePrice")}</span>
              <input value={fill.base} inputMode="decimal" placeholder="ex: 100"
                     onChange={(e) => setFill((f) => ({ ...f, base: e.target.value }))} />
            </label>
            <label className="field"><span>{t(lc, "perExtraStop")}</span>
              <input value={fill.per_stop} inputMode="decimal" placeholder="ex: 50"
                     onChange={(e) => setFill((f) => ({ ...f, per_stop: e.target.value }))} />
            </label>
          </div>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy || !fill.base} onClick={preencher} type="button">{t(lc, "fillGrid")}</button>
            <button className="secondary-button" onClick={() => setFillModal(false)} type="button">{t(lc, "cancel")}</button>
          </div>
        </div>
      </AdminModal>

      <AdminModal open={importModal} onClose={() => setImportModal(false)} title={t(lc, "importPriceTable")}>
        <div className="admin-form">
          <p className="dash-kpi-note">
            Descarregue o modelo, preencha a coluna do preço e volte a enviá-lo. O ficheiro é primeiro pré-visualizado: nada muda até confirmar.
          </p>
          <label className="field"><span>{t(lc, "excelFile")}</span>
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
              <button className="primary-button" disabled={busy} onClick={() => enviarExcel(true)} type="button">{t(lc, "apply")}</button>
            ) : (
              <button className="primary-button" disabled={busy || !file} onClick={() => enviarExcel(false)} type="button">{t(lc, "preview")}</button>
            )}
            <button className="secondary-button" onClick={() => setImportModal(false)} type="button">{t(lc, "cancel")}</button>
          </div>
        </div>
      </AdminModal>
      {confirmDialog}
    </SectionCard>
  );
}
