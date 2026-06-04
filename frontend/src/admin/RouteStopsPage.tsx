import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, GripVertical, Plus, RefreshCw, Save, X } from "lucide-react";
import { apiFetch, apiPost } from "../lib/api";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { PageFrame, SectionCard, useAsyncData } from "../ui/common";

type RouteDirection = "outbound" | "inbound";

interface RouteRecord { id: number; uuid: string; code: string; name: string; description: string; status: string; stop_count: number; }
interface StopOption { id: number; code: string; name: string; }
interface RouteStopRecord { id?: number; uuid?: string; stop_id: number; stop_code?: string; stop_name: string; sequence: number; distance_from_start_km: string; direction: RouteDirection; }

const DIRECTIONS: RouteDirection[] = ["outbound", "inbound"];

function resequence(items: RouteStopRecord[]): RouteStopRecord[] {
  const grouped: Record<RouteDirection, RouteStopRecord[]> = { outbound: [], inbound: [] };
  for (const item of items) grouped[item.direction].push(item);
  const out: RouteStopRecord[] = [];
  for (const dir of DIRECTIONS) {
    grouped[dir].forEach((item, index) => out.push({ ...item, sequence: index + 1 }));
  }
  return out;
}

function stopKey(item: RouteStopRecord): string {
  return `${item.direction}-${item.stop_id}`;
}

export default function RouteStopsPage() {
  const { routeId } = useParams<{ routeId: string }>();
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const navigate = useNavigate();

  const stopLoader = useCallback(() => apiFetch("/api/stops/", token!).then((d) => d.results || d), [token]);
  const { data: stopOptions } = useAsyncData<StopOption[]>(stopLoader, [token]);

  const [route, setRoute] = useState<RouteRecord | null>(null);
  const [routeStops, setRouteStops] = useState<RouteStopRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [stopDraft, setStopDraft] = useState({ stop_id: "", distance_from_start_km: "0", direction: "outbound" as RouteDirection });
  const [draggedKey, setDraggedKey] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token || !routeId) return;
    setLoading(true);
    try {
      const [routeData, stopsData] = await Promise.all([
        apiFetch(`/api/routes/${routeId}/`, token),
        apiFetch(`/api/routes/${routeId}/stops/`, token),
      ]);
      setRoute(routeData);
      const items = (stopsData.results || stopsData || []).map((item: RouteStopRecord) => ({
        ...item,
        distance_from_start_km: String(item.distance_from_start_km || "0"),
      }));
      setRouteStops(resequence(items));
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro");
    } finally {
      setLoading(false);
    }
  }, [token, routeId]);

  useEffect(() => { void load(); }, [load]);

  const addRouteStop = () => {
    const stop = (stopOptions || []).find((s) => String(s.id) === stopDraft.stop_id);
    if (!stop) { showToast("danger", t(lc, "select")); return; }
    const direction = stopDraft.direction;
    if (routeStops.some((s) => s.direction === direction && Number(s.stop_id) === stop.id)) {
      showToast("danger", "Paragem duplicada na mesma direccao.");
      return;
    }
    setRouteStops(resequence([...routeStops, {
      stop_id: stop.id,
      stop_code: stop.code,
      stop_name: stop.name,
      sequence: 9999,
      distance_from_start_km: stopDraft.distance_from_start_km || "0",
      direction,
    }]));
    setStopDraft({ stop_id: "", distance_from_start_km: "0", direction });
  };

  const handleDragStart = (key: string) => setDraggedKey(key);
  const handleDragEnd = () => setDraggedKey(null);
  const handleDragOver = (e: React.DragEvent) => e.preventDefault();

  const handleDrop = (targetKey: string, targetDirection: RouteDirection) => {
    if (!draggedKey || draggedKey === targetKey) { setDraggedKey(null); return; }
    const dragged = routeStops.find((s) => stopKey(s) === draggedKey);
    if (!dragged) { setDraggedKey(null); return; }

    const filtered = routeStops.filter((s) => stopKey(s) !== draggedKey);
    const targetIndex = filtered.findIndex((s) => stopKey(s) === targetKey);
    if (targetIndex < 0) { setDraggedKey(null); return; }

    const next = [...filtered];
    next.splice(targetIndex, 0, { ...dragged, direction: targetDirection });
    setRouteStops(resequence(next));
    setDraggedKey(null);
  };

  const handleDropOnDirection = (direction: RouteDirection) => {
    if (!draggedKey) return;
    const dragged = routeStops.find((s) => stopKey(s) === draggedKey);
    if (!dragged) { setDraggedKey(null); return; }
    const filtered = routeStops.filter((s) => stopKey(s) !== draggedKey);
    const sameDirectionItems = filtered.filter((s) => s.direction === direction);
    const otherItems = filtered.filter((s) => s.direction !== direction);
    setRouteStops(resequence([...otherItems, ...sameDirectionItems, { ...dragged, direction }]));
    setDraggedKey(null);
  };

  const saveRouteStops = async () => {
    if (!routeId) return;
    setBusy(true);
    try {
      await apiPost(`/api/routes/${routeId}/set-stops/`, token!, routeStops.map((item) => ({
        stop_id: Number(item.stop_id),
        sequence: Number(item.sequence),
        distance_from_start_km: item.distance_from_start_km || "0",
        direction: item.direction,
      })));
      showToast("success", t(lc, "saveStops"));
      await load();
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro");
    } finally {
      setBusy(false);
    }
  };

  const stopsByDirection = (direction: RouteDirection) => routeStops.filter((s) => s.direction === direction).sort((a, b) => a.sequence - b.sequence);

  const title = route ? `${route.code} - ${route.name}` : t(lc, "routeStops");

  return (
    <PageFrame
      kicker={t(lc, "operation")}
      title={title}
      action={<>
        <button className="icon-text-button" onClick={() => navigate("/app/routes")} type="button">
          <ArrowLeft size={16} /><span>Voltar</span>
        </button>
        <button className="icon-text-button" onClick={() => void load()} type="button">
          <RefreshCw size={16} /><span>{t(lc, "refresh")}</span>
        </button>
      </>}
    >
      <SectionCard title={t(lc, "routeStops")}>
        <div className="route-stop-builder">
          <p className="route-stop-hint">Arraste as paragens para reordenar. A sequencia e recalculada automaticamente.</p>

          <div className="admin-form-grid admin-form-grid-wide">
            <label className="field">
              <span>{t(lc, "stops")}</span>
              <select value={stopDraft.stop_id} onChange={(e) => setStopDraft((p) => ({ ...p, stop_id: e.target.value }))}>
                <option value="">{t(lc, "select")}</option>
                {(stopOptions || []).map((stop) => <option key={stop.id} value={stop.id}>{stop.code} - {stop.name}</option>)}
              </select>
            </label>
            <label className="field">
              <span>{t(lc, "distanceKm")}</span>
              <input min="0" step="0.01" type="number" value={stopDraft.distance_from_start_km} onChange={(e) => setStopDraft((p) => ({ ...p, distance_from_start_km: e.target.value }))} />
            </label>
            <label className="field">
              <span>{t(lc, "direction")}</span>
              <select value={stopDraft.direction} onChange={(e) => setStopDraft((p) => ({ ...p, direction: e.target.value as RouteDirection }))}>
                <option value="outbound">{t(lc, "outbound")}</option>
                <option value="inbound">{t(lc, "inbound")}</option>
              </select>
            </label>
            <div className="route-stop-add-action">
              <button className="secondary-button" onClick={addRouteStop} type="button"><Plus size={15} /> {t(lc, "addStop")}</button>
            </div>
          </div>

          <div className="route-stop-directions">
            {DIRECTIONS.map((direction) => {
              const items = stopsByDirection(direction);
              return (
                <div
                  className="route-stop-direction-block"
                  key={direction}
                  onDragOver={handleDragOver}
                  onDrop={() => handleDropOnDirection(direction)}
                >
                  <div className="route-stop-direction-header">
                    <h5>{direction === "outbound" ? t(lc, "outbound") : t(lc, "inbound")}</h5>
                    <span>{items.length} paragens</span>
                  </div>
                  {items.length === 0 ? (
                    <div className="route-stop-empty">{loading ? t(lc, "loading") : "Sem paragens nesta direccao. Arraste aqui."}</div>
                  ) : (
                    <ul className="route-stop-list">
                      {items.map((item) => {
                        const key = stopKey(item);
                        return (
                          <li
                            className={`route-stop-row${draggedKey === key ? " route-stop-row-dragging" : ""}`}
                            key={key}
                            draggable
                            onDragStart={() => handleDragStart(key)}
                            onDragEnd={handleDragEnd}
                            onDragOver={handleDragOver}
                            onDrop={(e) => { e.stopPropagation(); handleDrop(key, direction); }}
                          >
                            <span className="route-stop-drag-handle" aria-hidden="true"><GripVertical size={16} /></span>
                            <div className="route-stop-sequence">{item.sequence}</div>
                            <div className="route-stop-main">
                              <strong>{item.stop_name}</strong>
                              <span>{item.stop_code || "-"} · {item.distance_from_start_km || "0"} km</span>
                            </div>
                            <button
                              className="icon-button"
                              onClick={() => setRouteStops(resequence(routeStops.filter((s) => stopKey(s) !== key)))}
                              title={t(lc, "delete")}
                              type="button"
                            >
                              <X size={15} />
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>
              );
            })}
          </div>

          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy} onClick={saveRouteStops} type="button"><Save size={15} /> {busy ? t(lc, "saving") : t(lc, "saveStops")}</button>
            <button className="secondary-button" onClick={() => navigate("/app/routes")} type="button">{t(lc, "cancel")}</button>
          </div>
        </div>
      </SectionCard>
    </PageFrame>
  );
}
