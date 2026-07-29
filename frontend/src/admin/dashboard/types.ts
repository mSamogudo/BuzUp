/** Contrato de `GET /api/admin/analytics/` (apps/reports/analytics.py).
 *
 * Todos os montantes chegam como string decimal — o backend nunca envia float
 * para dinheiro. Converter com `num()` de `./theme` antes de desenhar. */

export interface AnalyticsFiltersEcho {
  date_from: string;
  date_to: string;
  route_id: number | null;
  driver_id: number | null;
  agent_id: number | null;
  provider: string | null;
}

export interface AnalyticsKpis {
  transport_revenue: string;
  ticket_revenue: string;
  validation_revenue: string;
  topups_total: string;
  payments_total: string;
  tickets_sold: number;
  validations: number;
  avg_ticket: string;
  trips_total: number;
  trips_completed: number;
}

export interface RevenuePoint {
  date: string;
  tickets: string;
  validations: string;
  topups: string;
}

export interface HourlyPoint {
  hour: string;
  count: number;
}

export interface PaymentMethodRow {
  provider: string;
  /** Nome legivel ja resolvido pelo backend (M-Pesa, e-Mola, Saldo BusUp...). */
  label?: string;
  /** mobile_money = dinheiro que entra; wallet = saldo ja carregado. */
  kind?: "mobile_money" | "wallet" | "cash" | "test" | "other";
  count: number;
  total: string;
}

export interface TopRouteRow {
  route_code: string;
  route_name: string;
  count: number;
  revenue: string;
}

export interface TopTripRow {
  trip_id: number;
  route: string;
  departure: string | null;
  vehicle: string;
  driver: string;
  passengers: number;
  revenue: string;
}

export interface TopDriverRow {
  driver_id: number;
  name: string;
  trips: number;
  completed: number;
  passengers: number;
  revenue: string;
}

export interface TopAgentRow {
  agent_id: number;
  name: string;
  sales: number;
  revenue: string;
}

export interface PackageRow {
  name: string;
  count: number;
  revenue: string;
}

export interface PackagesBlock {
  subscriptions: number;
  active_now: number;
  by_package: PackageRow[];
}

export interface RecentItem {
  kind: "validation" | "ticket";
  at: string;
  label: string;
  amount: string;
}

export interface Analytics {
  filters: AnalyticsFiltersEcho;
  kpis: AnalyticsKpis;
  revenue_series: RevenuePoint[];
  hourly: HourlyPoint[];
  payment_methods: PaymentMethodRow[];
  top_routes: TopRouteRow[];
  top_trips: TopTripRow[];
  top_drivers: TopDriverRow[];
  top_agents: TopAgentRow[];
  packages: PackagesBlock;
  recent: RecentItem[];
}

/** Estado dos filtros na UI — tudo string porque vem de `<input>`/`<select>`. */
export interface DashFilters {
  dateFrom: string;
  dateTo: string;
  routeId: string;
  driverId: string;
  agentId: string;
  provider: string;
}

/** Opção de dropdown vinda de /api/routes/, /api/drivers/, /api/agents/. */
export interface Lookup {
  id: number;
  code?: string;
  name?: string;
  full_name?: string;
  status?: string;
}
