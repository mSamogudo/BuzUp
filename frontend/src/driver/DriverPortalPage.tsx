import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bus, Clock, LogOut, Pause, Play, Square, Wallet, RotateCcw, X } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { apiFetch, apiPost } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import { showToast } from "../lib/toast";
import { StatusBadge } from "../ui/common";

const LIVE_STATUSES = new Set(["boarding", "departed", "paused"]);

interface RevenueSummary {
  guest_checkout: { count: number; tickets: number; revenue: string };
  app_passes: { count: number; revenue: string };
  wallet_validations: { count: number; revenue: string };
  direct_payments: { count: number; revenue: string };
  validations: { approved: number; denied: number };
  total_revenue: string;
}

interface DriverTrip {
  id: number;
  uuid: string;
  route_code: string;
  route_name: string;
  vehicle_registration: string;
  planned_departure_at: string | null;
  activity_started_at: string | null;
  activity_paused_at: string | null;
  activity_closed_at: string | null;
  pause_seconds: number;
  closure_summary?: RevenueSummary;
  status: string;
  revenue_summary?: RevenueSummary;
}

export default function DriverPortalPage() {
  const { token, logout } = useAuth();
  const navigate = useNavigate();
  const [trips, setTrips] = useState<DriverTrip[]>([]);
  const [selected, setSelected] = useState<DriverTrip | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState("");
  const [closureModal, setClosureModal] = useState<DriverTrip | null>(null);
  const [liveRevenue, setLiveRevenue] = useState<Record<number, RevenueSummary>>({});
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const loadTrips = useCallback(async (opts?: { silent?: boolean }) => {
    if (!token) return;
    if (!opts?.silent) setLoading(true);
    try {
      const data = await apiFetch("/api/driver/trips/", token);
      const list: DriverTrip[] = data || [];
      setTrips(list);
      setSelected((current) => {
        if (current) return list.find((trip) => trip.id === current.id) || current;
        return list[0] || null;
      });

      const liveTrips = list.filter((trip) => LIVE_STATUSES.has(trip.status));
      if (liveTrips.length) {
        const results = await Promise.all(
          liveTrips.map((trip) =>
            apiFetch(`/api/trips/${trip.id}/`, token)
              .then((d) => [trip.id, d?.revenue_summary as RevenueSummary | undefined] as const)
              .catch(() => [trip.id, undefined] as const),
          ),
        );
        setLiveRevenue((prev) => {
          const next = { ...prev };
          for (const [id, summary] of results) {
            if (summary) next[id] = summary;
          }
          return next;
        });
      }
      setLastUpdate(new Date());
    } catch (err) {
      if (!opts?.silent) {
        showToast("danger", err instanceof Error ? err.message : "Erro ao carregar viagens.");
      }
    } finally {
      if (!opts?.silent) setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadTrips();
  }, [loadTrips]);

  useEffect(() => {
    const id = window.setInterval(() => {
      void loadTrips({ silent: true });
    }, 5000);
    return () => window.clearInterval(id);
  }, [loadTrips]);

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  async function runAction(action: "start" | "pause" | "resume" | "close") {
    if (!token || !selected) return;
    setBusyAction(action);
    try {
      const updated = await apiPost(`/api/driver/trips/${selected.id}/${action}/`, token, {});
      setSelected(updated);
      setTrips((items) => items.map((item) => item.id === updated.id ? updated : item));
      showToast("success", "Estado actualizado.");
      if (action === "close") {
        setClosureModal(updated);
      }
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro ao actualizar.");
    } finally {
      setBusyAction("");
    }
  }

  const visibleTrips = trips.filter((trip) => trip.status !== "completed" && trip.status !== "cancelled");

  const isClosed = selected && (selected.status === "completed" || selected.status === "cancelled");
  const canStart = selected && (
    selected.status === "scheduled" ||
    (selected.status === "boarding" && !selected.activity_started_at)
  );
  const canPauseClose = selected && !isClosed && !canStart && selected.status !== "paused";
  const canResumeClose = selected && selected.status === "paused";

  return (
    <main className="driver-page">
      <header className="driver-topbar">
        <div>
          <span>Portal do Motorista</span>
          <h1>Actividade do Autocarro</h1>
        </div>
        <button className="driver-ghost-button" onClick={handleLogout} type="button"><LogOut size={18} /> Sair</button>
      </header>

      <section className="driver-layout">
        <aside className="driver-trip-list">
          <div className="driver-section-head">
            <strong>Viagens alocadas</strong>
            <button className="driver-icon-button" onClick={() => void loadTrips()} type="button"><RotateCcw size={16} /></button>
          </div>
          {lastUpdate ? (
            <p className="driver-muted" style={{ fontSize: 11, display: "flex", alignItems: "center", gap: 4 }}>
              <Clock size={11} /> {lastUpdate.toLocaleTimeString("pt-MZ")}
            </p>
          ) : null}
          {loading ? <p className="driver-muted">A carregar...</p> : null}
          {!loading && visibleTrips.length === 0 ? <p className="driver-muted">Sem viagens pendentes.</p> : null}
          {visibleTrips.map((trip) => {
            const isLive = LIVE_STATUSES.has(trip.status);
            const liveSummary = liveRevenue[trip.id];
            return (
              <button
                className={`driver-trip-card${selected?.id === trip.id ? " driver-trip-card-active" : ""}`}
                key={trip.uuid}
                onClick={() => setSelected(trip)}
                type="button"
              >
                <span>{trip.route_code}</span>
                <strong>{trip.vehicle_registration || trip.route_name}</strong>
                <small>{trip.route_name}</small>
                <StatusBadge value={trip.status} />
                {isLive && liveSummary ? (
                  <span style={{
                    display: "inline-flex", alignItems: "center", gap: 4,
                    marginTop: 6, fontSize: 11, fontWeight: 600,
                    color: "#22c55e",
                  }}>
                    <span style={{
                      display: "inline-block", width: 6, height: 6, borderRadius: "50%",
                      background: "#22c55e",
                    }} />
                    Receita actual: {formatCurrency(liveSummary.total_revenue)}
                  </span>
                ) : null}
              </button>
            );
          })}
        </aside>

        <section className="driver-workspace">
          {!selected ? (
            <div className="driver-empty"><Bus size={42} /><p>Seleccione uma viagem alocada.</p></div>
          ) : (
            <>
              <div className="driver-trip-hero">
                <div>
                  <span>{selected.route_code}</span>
                  <h2>{selected.vehicle_registration || selected.route_name}</h2>
                  <p>{selected.route_name}</p>
                </div>
                <StatusBadge value={selected.status} />
              </div>

              <div className="driver-metrics">
                <article><Clock size={18} /><span>Planeado</span><strong>{formatDateTime(selected.planned_departure_at)}</strong></article>
                <article><Play size={18} /><span>Inicio</span><strong>{formatDateTime(selected.activity_started_at)}</strong></article>
                <article><Pause size={18} /><span>Repouso</span><strong>{formatPause(selected.pause_seconds, selected.activity_paused_at)}</strong></article>
                <article><Wallet size={18} /><span>Receita</span><strong>{formatCurrency(liveRevenue[selected.id]?.total_revenue || selected.revenue_summary?.total_revenue || selected.closure_summary?.total_revenue || "0")}</strong></article>
              </div>

              {!isClosed && (
                <div className="driver-actions">
                  {canStart && (
                    <button className="driver-primary-button" disabled={!!busyAction} onClick={() => void runAction("start")} type="button"><Play size={18} /> Iniciar Actividade</button>
                  )}
                  {canPauseClose && (
                    <>
                      <button className="driver-secondary-button" disabled={!!busyAction} onClick={() => void runAction("pause")} type="button"><Pause size={18} /> Pausar</button>
                      <button className="driver-danger-button" disabled={!!busyAction} onClick={() => void runAction("close")} type="button"><Square size={18} /> Encerrar</button>
                    </>
                  )}
                  {canResumeClose && (
                    <>
                      <button className="driver-primary-button" disabled={!!busyAction} onClick={() => void runAction("resume")} type="button"><Play size={18} /> Retomar</button>
                      <button className="driver-danger-button" disabled={!!busyAction} onClick={() => void runAction("close")} type="button"><Square size={18} /> Encerrar</button>
                    </>
                  )}
                </div>
              )}

              {(isClosed || selected.revenue_summary) && (
                <ClosureSummary summary={selected.revenue_summary || selected.closure_summary} title={isClosed ? "Resumo de Encerramento" : "Fecho do autocarro"} />
              )}
            </>
          )}
        </section>
      </section>

      {closureModal && closureModal.closure_summary && (
        <>
          <div className="admin-modal-overlay" onClick={() => setClosureModal(null)} />
          <div className="admin-modal-shell" role="dialog" aria-modal="true" aria-label="Resumo de Encerramento">
            <div className="admin-modal-card">
              <div className="admin-modal-head">
                <div>
                  <h3>Viagem Encerrada</h3>
                  <p>{closureModal.route_code} - {closureModal.route_name}</p>
                </div>
                <button className="icon-button" onClick={() => setClosureModal(null)} type="button"><X size={18} /></button>
              </div>
              <div className="admin-modal-body">
                <ClosureSummary summary={closureModal.closure_summary} title="Resumo Financeiro" />
              </div>
            </div>
          </div>
        </>
      )}
    </main>
  );
}

function ClosureSummary({ summary, title }: { summary?: RevenueSummary; title: string }) {
  if (!summary) return null;
  return (
    <div className="driver-revenue-panel">
      <h3>{title}</h3>
      <div className="driver-revenue-grid">
        <div><span>Bilhetes guest ({summary.guest_checkout.count})</span><strong>{formatCurrency(summary.guest_checkout.revenue)}</strong></div>
        <div><span>Passes app ({summary.app_passes.count})</span><strong>{formatCurrency(summary.app_passes.revenue)}</strong></div>
        <div><span>Validacoes carteira ({summary.wallet_validations.count})</span><strong>{formatCurrency(summary.wallet_validations.revenue)}</strong></div>
        <div><span>Pagamentos directos ({summary.direct_payments.count})</span><strong>{formatCurrency(summary.direct_payments.revenue)}</strong></div>
        <div><span>Total</span><strong>{formatCurrency(summary.total_revenue)}</strong></div>
      </div>
    </div>
  );
}

function formatPause(seconds: number, pausedAt: string | null) {
  let total = seconds || 0;
  if (pausedAt) {
    total += Math.max(0, Math.floor((Date.now() - new Date(pausedAt).getTime()) / 1000));
  }
  const minutes = Math.floor(total / 60);
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;
  if (hours) return `${hours}h ${remaining}min`;
  return `${remaining}min`;
}
