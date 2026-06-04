import { useEffect, useState } from "react";
import { RefreshCw, TrendingUp, BarChart3 } from "lucide-react";
import {
  AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { apiFetch } from "../lib/api";
import { formatCount, formatCurrency } from "../lib/format";
import { t } from "../lib/i18n";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { MetricCard, PageFrame } from "../ui/common";
import { SkeletonCard } from "../ui/Skeleton";

interface DashboardData {
  passengers_total: number;
  wallets_total_balance: string;
  today: {
    validations_total: number;
    validations_approved: number;
    validation_revenue: string;
    topups_count: number;
    topups_total: string;
    guest_checkouts_total: number;
    guest_checkouts_issued: number;
  };
  pending_payments: number;
  devices_active: number;
  devices_pending: number;
}

interface ChartData {
  revenue_7d: { date: string; revenue: string; validations: number; topups: string; topups_count: number }[];
  payment_methods: { provider: string; count: number; total: string }[];
  top_routes: { route_code: string; route_name: string; count: number; revenue: string }[];
  hourly_today: { hour: string; total: number; approved: number; denied: number }[];
  validation_trend: { date: string; approved: number; denied: number }[];
}

function ChartCard({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="dashboard-chart-card">
      <div className="dashboard-chart-header">
        {icon}
        <h3>{title}</h3>
      </div>
      <div className="dashboard-chart-body">
        {children}
      </div>
    </div>
  );
}

function formatShortDate(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("pt-MZ", { day: "2-digit", month: "short" });
}

function formatNum(val: string | number) {
  const n = typeof val === "string" ? parseFloat(val) : val;
  if (isNaN(n) || n === 0) return "0";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString("pt-MZ", { maximumFractionDigits: 0 });
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="dashboard-tooltip">
      <p className="dashboard-tooltip-label">{label}</p>
      {payload.map((p: any, i: number) => (
        <p key={i} style={{ color: p.color }}>
          {p.name}: <strong>{typeof p.value === "number" ? formatCurrency(p.value) : p.value}</strong>
        </p>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const { token } = useAuth();
  const { locale, theme } = useUi();
  const [data, setData] = useState<DashboardData | null>(null);
  const [charts, setCharts] = useState<ChartData | null>(null);
  const [loading, setLoading] = useState(true);

  const isDark = theme === "dark";
  const gridColor = isDark ? "#2A2F38" : "#E7E1D4";
  const textColor = isDark ? "#8F94A0" : "#6B6356";

  const load = () => {
    if (!token) return;
    setLoading(true);
    Promise.all([
      apiFetch("/api/admin/dashboard/", token),
      apiFetch("/api/admin/dashboard/charts/", token),
    ]).then(([d, c]) => { setData(d); setCharts(c); })
      .catch(() => {})
      .finally(() => setLoading(false));
  };
  useEffect(load, [token]);

  const d = data;
  const c = charts;

  // Combine series into one for the area chart so we have a single dense
  // visual: receita validada + total recargas, dia a dia, ultimos 7d.
  const trendData = (c?.revenue_7d || []).map((r) => ({
    date: formatShortDate(r.date),
    receita: parseFloat(r.revenue || "0"),
    recargas: parseFloat(r.topups || "0"),
  }));

  // Top 3 rotas com barra horizontal compacta.
  const routeData = (c?.top_routes || []).slice(0, 3).map((r) => ({
    code: r.route_code,
    name: r.route_name,
    validacoes: r.count,
    receita: parseFloat(r.revenue || "0"),
  }));
  const maxValidacoes = Math.max(1, ...routeData.map((r) => r.validacoes));

  return (
    <PageFrame
      kicker={t(locale, "overview")}
      title={t(locale, "dashboard")}
      action={
        <button className="icon-text-button" onClick={load} type="button">
          <RefreshCw size={16} />
          <span>{t(locale, "refresh")}</span>
        </button>
      }
    >
      {loading ? (
        <>
          <SkeletonCard count={4} />
          <div className="dashboard-chart-grid dashboard-chart-grid-compact" style={{ marginTop: 16 }}>
            <div className="skeleton skeleton-card" style={{ height: 280 }} />
            <div className="skeleton skeleton-card" style={{ height: 280 }} />
          </div>
        </>
      ) : (
        <>
          {/* 4 KPI tiles — uma so linha, tudo no viewport. */}
          <div className="admin-metric-grid dashboard-kpi-strip">
            <MetricCard
              label="Receita hoje"
              value={formatCurrency(d?.today.validation_revenue || "0")}
              detail={`${d?.today.validations_total || 0} validacoes`}
            />
            <MetricCard
              label="Top-ups hoje"
              value={formatCurrency(d?.today.topups_total || "0")}
              detail={`${d?.today.topups_count || 0} recargas`}
            />
            <MetricCard
              label="Saldo em circulacao"
              value={formatCurrency(d?.wallets_total_balance || "0")}
              detail={`${d?.passengers_total || 0} passageiros`}
            />
            <MetricCard
              label="Pendencias"
              value={formatCount((d?.pending_payments || 0) + (d?.devices_pending || 0))}
              detail={`${d?.pending_payments || 0} pgs · ${d?.devices_pending || 0} POS`}
            />
          </div>

          {/* 2 gráficos lado a lado, sem mais nada por baixo. */}
          <div className="dashboard-chart-grid dashboard-chart-grid-compact" style={{ marginTop: 16 }}>
            <ChartCard title="Receita & recargas — 7 dias" icon={<TrendingUp size={18} />}>
              {trendData.length === 0 ? (
                <p className="dashboard-empty">Sem dados.</p>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart data={trendData} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                    <defs>
                      <linearGradient id="gradReceita" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#1D5FA7" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="#1D5FA7" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="gradRecargas" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#2A9D8F" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="#2A9D8F" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: textColor }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: textColor }} axisLine={false} tickLine={false} tickFormatter={formatNum} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Area type="monotone" dataKey="receita" name="Receita" stroke="#1D5FA7" strokeWidth={2.5} fill="url(#gradReceita)" />
                    <Area type="monotone" dataKey="recargas" name="Recargas" stroke="#2A9D8F" strokeWidth={2} fill="url(#gradRecargas)" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </ChartCard>

            <ChartCard title="Top rotas (hoje)" icon={<BarChart3 size={18} />}>
              {routeData.length === 0 ? (
                <p className="dashboard-empty">Sem validacoes registadas hoje.</p>
              ) : (
                <div className="dashboard-route-rank-list">
                  {routeData.map((r, i) => (
                    <div key={r.code} className="dashboard-route-rank-row">
                      <span className="dashboard-route-rank-num">{i + 1}</span>
                      <div className="dashboard-route-rank-info">
                        <strong>{r.code}</strong>
                        <span>{r.name}</span>
                      </div>
                      <div className="dashboard-route-rank-bar">
                        <div
                          className="dashboard-route-rank-fill"
                          style={{ width: `${Math.max(8, (r.validacoes / maxValidacoes) * 100)}%` }}
                        />
                      </div>
                      <div className="dashboard-route-rank-stats">
                        <strong>{formatCount(r.validacoes)}</strong>
                        <span>{formatCurrency(r.receita)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ChartCard>
          </div>
        </>
      )}
    </PageFrame>
  );
}
