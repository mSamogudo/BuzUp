import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Clock, RefreshCw, Wallet, XCircle } from "lucide-react";
import { apiFetch } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { DataTable, MetricCard, PageFrame, SectionCard, StatusBadge, TabBar, TablePrimaryCell } from "../ui/common";

interface RevenueSummary {
  guest_checkout: { revenue: string; count: number; tickets: number };
  app_passes: { revenue: string; count: number };
  wallet_validations: { revenue: string; count: number };
  direct_payments: { revenue: string; count: number };
  validations: { approved: number; denied: number };
  total_revenue: string;
}

interface TripPurchase { reference: string; payer_phone: string; quantity: number; total_amount: string; status: string; created_at: string; }
interface TripValidation { id: number; validation_type: string; status: string; failure_reason: string; amount_debited: string; device_serial: string; created_at: string; }
interface TripPass { uuid: string; payer_phone: string; fare_amount: string; status: string; origin_stop: string; destination_stop: string; created_at: string; used_at: string | null; }
interface TripActivityEvent { event_type: string; occurred_at: string; driver_name: string; metadata: Record<string, unknown>; }

interface TripDetail {
  id: number;
  uuid: string;
  route_code: string;
  route_name: string;
  vehicle_registration: string;
  driver_name: string;
  planned_departure_at: string | null;
  planned_arrival_at?: string | null;
  activity_started_at?: string | null;
  activity_paused_at?: string | null;
  activity_closed_at?: string | null;
  pause_seconds?: number;
  status: string;
  revenue_summary?: RevenueSummary;
  closure_summary?: RevenueSummary;
  purchases?: TripPurchase[];
  validations?: TripValidation[];
  travel_passes?: TripPass[];
  activity_events?: TripActivityEvent[];
}

const LIVE_STATUSES = new Set(["boarding", "departed", "paused"]);

export default function TripDetailPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const navigate = useNavigate();
  const [trip, setTrip] = useState<TripDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [tab, setTab] = useState("validations");

  const load = useCallback(async () => {
    if (!token || !tripId) return;
    try {
      const data = await apiFetch(`/api/trips/${tripId}/`, token);
      setTrip(data);
      setLastUpdate(new Date());
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro ao carregar viagem.");
    } finally {
      setLoading(false);
    }
  }, [token, tripId]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    const id = window.setInterval(() => {
      void load();
    }, 5000);
    return () => window.clearInterval(id);
  }, [load]);

  if (loading && !trip) {
    return (
      <PageFrame kicker={t(lc, "operation")} title={t(lc, "trips")}>
        <p style={{ textAlign: "center", color: "var(--app-text-muted)", padding: 32 }}>{t(lc, "loading")}</p>
      </PageFrame>
    );
  }

  if (!trip) {
    return (
      <PageFrame kicker={t(lc, "operation")} title={t(lc, "trips")}>
        <p style={{ textAlign: "center", color: "var(--app-text-muted)", padding: 32 }}>{t(lc, "noData")}</p>
      </PageFrame>
    );
  }

  const revenue = trip.revenue_summary || trip.closure_summary;
  const isLive = LIVE_STATUSES.has(trip.status);
  const validations = trip.validations || [];
  const purchases = trip.purchases || [];
  const passes = trip.travel_passes || [];
  const events = trip.activity_events || [];

  return (
    <PageFrame
      kicker={t(lc, "operation")}
      title={`${trip.route_code} · ${trip.route_name}`}
      action={
        <>
          <button className="icon-text-button" onClick={() => navigate("/app/trips")} type="button">
            <ArrowLeft size={16} /><span>Voltar</span>
          </button>
          <button className="icon-text-button" onClick={() => void load()} type="button">
            <RefreshCw size={16} /><span>{t(lc, "refresh")}</span>
          </button>
        </>
      }
    >
      <SectionCard title="Resumo">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "center", marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {isLive ? (
              <span
                aria-label="Em directo"
                style={{
                  display: "inline-block", width: 10, height: 10, borderRadius: "50%",
                  background: "#22c55e", boxShadow: "0 0 0 0 rgba(34,197,94,0.7)",
                  animation: "pulse 1.4s infinite",
                }}
              />
            ) : null}
            <StatusBadge value={trip.status} />
          </div>
          <div style={{ fontSize: 12, color: "var(--app-text-muted)", display: "flex", alignItems: "center", gap: 6 }}>
            <Clock size={12} />
            <span>Ultima actualizacao: {lastUpdate ? lastUpdate.toLocaleTimeString("pt-MZ") : "-"}</span>
          </div>
        </div>
        <div className="detail-fields" style={{ fontSize: 13 }}>
          <div className="detail-field"><dt>{t(lc, "route")}</dt><dd>{trip.route_code} - {trip.route_name}</dd></div>
          <div className="detail-field"><dt>{t(lc, "vehicles")}</dt><dd>{trip.vehicle_registration || "-"}</dd></div>
          <div className="detail-field"><dt>{t(lc, "drivers")}</dt><dd>{trip.driver_name || "-"}</dd></div>
          <div className="detail-field"><dt>{t(lc, "plannedDeparture")}</dt><dd>{formatDateTime(trip.planned_departure_at)}</dd></div>
          <div className="detail-field"><dt>Inicio actividade</dt><dd>{formatDateTime(trip.activity_started_at || null)}</dd></div>
          <div className="detail-field"><dt>Fecho actividade</dt><dd>{formatDateTime(trip.activity_closed_at || null)}</dd></div>
        </div>
      </SectionCard>

      <div className="admin-metric-grid">
        <MetricCard
          label="Receita Total"
          value={formatCurrency(revenue?.total_revenue || "0")}
        />
        <MetricCard
          label="Validacoes Aprovadas"
          value={String(revenue?.validations?.approved ?? 0)}
        />
        <MetricCard
          label="Validacoes Negadas"
          value={String(revenue?.validations?.denied ?? 0)}
        />
        <MetricCard
          label="Bilhetes Vendidos"
          value={String((revenue?.guest_checkout?.tickets ?? 0) + (revenue?.app_passes?.count ?? 0))}
        />
      </div>

      {revenue ? (
        <SectionCard title="Detalhe da Receita">
          <div className="driver-revenue-grid">
            <div><span>Carteira movel ({revenue.guest_checkout.count})</span><strong>{formatCurrency(revenue.guest_checkout.revenue)}</strong></div>
            <div><span>Passes app ({revenue.app_passes.count})</span><strong>{formatCurrency(revenue.app_passes.revenue)}</strong></div>
            <div><span>Validacoes carteira ({revenue.wallet_validations.count})</span><strong>{formatCurrency(revenue.wallet_validations.revenue)}</strong></div>
            <div><span>Pagamentos directos ({revenue.direct_payments.count})</span><strong>{formatCurrency(revenue.direct_payments.revenue)}</strong></div>
            <div style={{ gridColumn: "1 / -1", borderTop: "1px solid var(--app-border)", paddingTop: 8 }}>
              <span><Wallet size={14} style={{ verticalAlign: "middle", marginRight: 6 }} />Total</span>
              <strong>{formatCurrency(revenue.total_revenue)}</strong>
            </div>
          </div>
        </SectionCard>
      ) : null}

      <SectionCard title="Actividade">
        <TabBar
          items={[
            { key: "validations", label: t(lc, "validations"), count: validations.length },
            { key: "purchases", label: t(lc, "guestCheckouts"), count: purchases.length },
            { key: "passes", label: t(lc, "passesIssued"), count: passes.length },
            { key: "events", label: "Eventos", count: events.length },
          ]}
          value={tab}
          onChange={setTab}
        />

        {tab === "validations" && (
          <DataTable
            columns={[
              { header: t(lc, "type"), render: (r: TripValidation) => <TablePrimaryCell title={r.validation_type.replace(/_/g, " ")} subtitle={r.device_serial || "-"} /> },
              { header: t(lc, "status"), render: (r: TripValidation) => (
                <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  {r.status === "approved" ? <CheckCircle2 size={14} color="#22c55e" /> : <XCircle size={14} color="#ef4444" />}
                  <StatusBadge value={r.status} />
                </span>
              ) },
              { header: t(lc, "amount"), render: (r: TripValidation) => formatCurrency(r.amount_debited) },
              { header: t(lc, "failure"), render: (r: TripValidation) => r.failure_reason || "-" },
              { header: t(lc, "date"), render: (r: TripValidation) => formatDateTime(r.created_at) },
            ]}
            rows={validations}
            rowKey={(r) => String(r.id)}
            loading={false}
            emptyMessage={t(lc, "noValidations")}
            filterable={false}
          />
        )}

        {tab === "purchases" && (
          <DataTable
            columns={[
              { header: t(lc, "reference"), render: (r: TripPurchase) => <TablePrimaryCell title={r.reference} subtitle={r.payer_phone || "-"} /> },
              { header: "Quantidade", render: (r: TripPurchase) => String(r.quantity) },
              { header: t(lc, "amount"), render: (r: TripPurchase) => formatCurrency(r.total_amount) },
              { header: t(lc, "status"), render: (r: TripPurchase) => <StatusBadge value={r.status} /> },
              { header: t(lc, "date"), render: (r: TripPurchase) => formatDateTime(r.created_at) },
            ]}
            rows={purchases}
            rowKey={(r) => r.reference}
            loading={false}
            emptyMessage="Sem compras."
            filterable={false}
          />
        )}

        {tab === "passes" && (
          <DataTable
            columns={[
              { header: t(lc, "origin") + " / " + t(lc, "destination"), render: (r: TripPass) => <TablePrimaryCell title={`${r.origin_stop || "-"} → ${r.destination_stop || "-"}`} subtitle={r.payer_phone || "-"} /> },
              { header: t(lc, "amount"), render: (r: TripPass) => formatCurrency(r.fare_amount) },
              { header: t(lc, "status"), render: (r: TripPass) => <StatusBadge value={r.status} /> },
              { header: "Usado em", render: (r: TripPass) => formatDateTime(r.used_at) },
              { header: t(lc, "created"), render: (r: TripPass) => formatDateTime(r.created_at) },
            ]}
            rows={passes}
            rowKey={(r) => r.uuid}
            loading={false}
            emptyMessage="Sem passes."
            filterable={false}
          />
        )}

        {tab === "events" && (
          <div className="detail-list">
            {events.length === 0 ? (
              <p style={{ color: "var(--app-text-muted)", textAlign: "center", padding: 20 }}>Sem eventos.</p>
            ) : (
              events.map((item, idx) => (
                <div className="detail-list-row" key={`${item.event_type}-${item.occurred_at}-${idx}`}>
                  <strong>{item.event_type.replace(/_/g, " ")}</strong>
                  <span>{formatDateTime(item.occurred_at)} · {item.driver_name || "-"}</span>
                </div>
              ))
            )}
          </div>
        )}
      </SectionCard>

      <style>{`
        @keyframes pulse {
          0% { box-shadow: 0 0 0 0 rgba(34,197,94,0.6); }
          70% { box-shadow: 0 0 0 8px rgba(34,197,94,0); }
          100% { box-shadow: 0 0 0 0 rgba(34,197,94,0); }
        }
      `}</style>
    </PageFrame>
  );
}
