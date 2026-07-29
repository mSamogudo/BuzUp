import type { ReactNode } from "react";
import {
  Area, Bar, BarChart, CartesianGrid, Cell, ComposedChart, LabelList, Legend,
  Line, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { formatCount, formatCurrency } from "../../lib/format";
import type { ChartTheme } from "./theme";
import { compact, num, providerLabel, shortDate } from "./theme";
import type { HourlyPoint, PaymentMethodRow, RevenuePoint, TopRouteRow } from "./types";

/* ------------------------------------------------------------------ */
/* Casca comum                                                         */
/* ------------------------------------------------------------------ */

export function ChartCard({ title, subtitle, icon, action, children }: {
  title: string; subtitle?: string; icon: ReactNode; action?: ReactNode; children: ReactNode;
}) {
  return (
    <div className="dashboard-chart-card">
      <div className="dashboard-chart-header">
        {icon}
        <div style={{ minWidth: 0 }}>
          <h3>{title}</h3>
          {subtitle ? (
            <p style={{ margin: "2px 0 0", fontSize: 11.5, color: "var(--app-text-muted)", fontWeight: 500 }}>
              {subtitle}
            </p>
          ) : null}
        </div>
        {action ? <div style={{ marginLeft: "auto" }}>{action}</div> : null}
      </div>
      <div className="dashboard-chart-body" style={{ flexDirection: "column" }}>{children}</div>
    </div>
  );
}

function Empty({ message }: { message: string }) {
  return <p className="dashboard-empty">{message}</p>;
}

/** Tooltip partilhado. `money` decide se os valores são MZN ou contagens.
 * Num donut não há `label` nem `color` — a cor vive em `payload.fill` e o
 * cabeçalho é o nome da fatia. */
function TipBox({ active, payload, label, money }: any) {
  if (!active || !payload?.length) return null;
  const heading = label || payload[0]?.name || "";
  return (
    <div className="dashboard-tooltip">
      {heading ? <p className="dashboard-tooltip-label">{heading}</p> : null}
      {payload.map((p: any, i: number) => (
        <p key={i}>
          <span style={{
            display: "inline-block", width: 8, height: 8, borderRadius: 2,
            background: p.color || p.payload?.fill, marginRight: 6,
          }} />
          {p.name}: <strong>{money ? formatCurrency(p.value) : formatCount(p.value)}</strong>
        </p>
      ))}
    </div>
  );
}

const axisProps = (c: ChartTheme) => ({
  tick: { fontSize: 11, fill: c.axis },
  axisLine: false,
  tickLine: false,
});

/* ------------------------------------------------------------------ */
/* 1. Receita por dia                                                  */
/* ------------------------------------------------------------------ */

/** Bilhetes + validações empilham-se (são a mesma coisa: receita de
 * transporte). As recargas ficam como linha tracejada por cima: mesmo eixo,
 * mesma moeda, mas NÃO são receita — empilhá-las inflacionaria o total.
 * Um único eixo Y, sempre. */
export function RevenueChart({ data, c }: { data: RevenuePoint[]; c: ChartTheme }) {
  const rows = data.map((r) => ({
    date: shortDate(r.date),
    bilhetes: num(r.tickets),
    validacoes: num(r.validations),
    recargas: num(r.topups),
  }));
  const hasData = rows.some((r) => r.bilhetes || r.validacoes || r.recargas);
  if (!hasData) return <Empty message="Sem receita registada neste intervalo." />;

  return (
    <ResponsiveContainer height={290} width="100%">
      <ComposedChart data={rows} margin={{ top: 10, right: 12, left: -10, bottom: 0 }}>
        <defs>
          <linearGradient id="dashGradTickets" x1="0" x2="0" y1="0" y2="1">
            <stop offset="5%" stopColor={c.series[0]} stopOpacity={0.42} />
            <stop offset="95%" stopColor={c.series[0]} stopOpacity={0.04} />
          </linearGradient>
          <linearGradient id="dashGradValidations" x1="0" x2="0" y1="0" y2="1">
            <stop offset="5%" stopColor={c.series[1]} stopOpacity={0.42} />
            <stop offset="95%" stopColor={c.series[1]} stopOpacity={0.04} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={c.grid} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="date" interval="preserveStartEnd" minTickGap={18} {...axisProps(c)} />
        <YAxis tickFormatter={compact} width={54} {...axisProps(c)} />
        <Tooltip content={<TipBox money />} cursor={{ stroke: c.axis, strokeOpacity: 0.35 }} />
        <Legend iconSize={9} wrapperStyle={{ fontSize: 11.5, paddingTop: 6 }} />
        <Area
          dataKey="bilhetes" fill="url(#dashGradTickets)" name="Bilhetes"
          stackId="receita" stroke={c.series[0]} strokeWidth={2}
          // 2px de superfície entre as duas parcelas — a fronteira lê-se mesmo
          // quando as cores ficam próximas.
          activeDot={{ r: 4, stroke: c.surface, strokeWidth: 2 }} type="monotone"
        />
        <Area
          dataKey="validacoes" fill="url(#dashGradValidations)" name="Validações"
          stackId="receita" stroke={c.series[1]} strokeWidth={2}
          activeDot={{ r: 4, stroke: c.surface, strokeWidth: 2 }} type="monotone"
        />
        <Line
          activeDot={{ r: 4, stroke: c.surface, strokeWidth: 2 }} dataKey="recargas" dot={false}
          name="Recargas (não é receita)" stroke={c.series[2]} strokeDasharray="5 4"
          strokeWidth={2} type="monotone"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

/* ------------------------------------------------------------------ */
/* 2. Distribuição horária                                             */
/* ------------------------------------------------------------------ */

export function HourlyChart({ data, c }: { data: HourlyPoint[]; c: ChartTheme }) {
  const total = data.reduce((s, r) => s + r.count, 0);
  if (!total) return <Empty message="Sem validações neste intervalo." />;
  const peak = data.reduce((best, r) => (r.count > best.count ? r : best), data[0]);

  return (
    <ResponsiveContainer height={290} width="100%">
      <BarChart data={data} margin={{ top: 10, right: 8, left: -14, bottom: 0 }}>
        <CartesianGrid stroke={c.grid} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="hour" interval={1} {...axisProps(c)} />
        <YAxis allowDecimals={false} tickFormatter={compact} width={44} {...axisProps(c)} />
        <Tooltip content={<TipBox />} cursor={{ fill: c.axis, fillOpacity: 0.08 }} />
        <Bar dataKey="count" name="Validações" radius={[4, 4, 0, 0]}>
          {data.map((r) => (
            // A hora de pico ganha a cor cheia; as restantes recuam. Isto é
            // ênfase, não uma segunda categoria.
            <Cell fill={c.series[0]} fillOpacity={r.hour === peak.hour ? 1 : 0.45} key={r.hour} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ------------------------------------------------------------------ */
/* 3. Métodos de pagamento                                             */
/* ------------------------------------------------------------------ */

/** Donut com no máximo 4 fatias identificadas + "Outros": acima disso as cores
 * deixam de ser distinguíveis por quem tem daltonismo. Cada fatia leva rótulo
 * directo na legenda — nunca só cor. */
export function PaymentDonut({ data, c }: { data: PaymentMethodRow[]; c: ChartTheme }) {
  const sorted = [...data].sort((a, b) => num(b.total) - num(a.total));
  const head = sorted.slice(0, 4);
  const tail = sorted.slice(4);
  const slices = head.map((r, i) => ({
    name: r.label || providerLabel(r.provider),
    value: num(r.total),
    count: r.count,
    fill: c.series[i],
  }));
  if (tail.length) {
    slices.push({
      name: `Outros (${tail.length})`,
      value: tail.reduce((s, r) => s + num(r.total), 0),
      count: tail.reduce((s, r) => s + r.count, 0),
      fill: c.other,
    });
  }
  const total = slices.reduce((s, r) => s + r.value, 0);
  if (!slices.length || total <= 0) return <Empty message="Sem pagamentos confirmados neste intervalo." />;

  return (
    <>
      <ResponsiveContainer height={190} width="100%">
        <PieChart>
          <Tooltip content={<TipBox money />} />
          <Pie
            data={slices} dataKey="value" innerRadius={52} nameKey="name" outerRadius={82}
            paddingAngle={2} stroke={c.surface} strokeWidth={2}
          >
            {slices.map((s) => <Cell fill={s.fill} key={s.name} />)}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="dash-legend">
        {slices.map((s) => (
          <div className="dash-legend-row" key={s.name}>
            <span className="dash-legend-swatch" style={{ background: s.fill }} />
            <span className="dash-legend-name">{s.name}</span>
            <span className="dash-legend-value">
              <strong>{formatCurrency(s.value)}</strong> · {Math.round((s.value / total) * 100)}% · {formatCount(s.count)}
            </span>
          </div>
        ))}
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ */
/* 4. Top rotas                                                        */
/* ------------------------------------------------------------------ */

export function TopRoutesChart({ data, c }: { data: TopRouteRow[]; c: ChartTheme }) {
  if (!data.length) return <Empty message="Sem rotas com movimento neste intervalo." />;
  const rows = data.map((r) => ({
    code: r.route_code || "—",
    name: r.route_name || "",
    receita: num(r.revenue),
    viagens: r.count,
  }));

  return (
    <ResponsiveContainer height={Math.max(200, rows.length * 38 + 30)} width="100%">
      <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 62, left: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke={c.grid} strokeDasharray="3 3" />
        <XAxis tickFormatter={compact} type="number" {...axisProps(c)} />
        <YAxis dataKey="code" type="category" width={72} {...axisProps(c)} />
        <Tooltip content={<TipBox money />} cursor={{ fill: c.axis, fillOpacity: 0.08 }} />
        <Bar barSize={16} dataKey="receita" fill={c.series[0]} name="Receita" radius={[0, 4, 4, 0]}>
          <LabelList
            dataKey="receita" fill={c.axis} fontSize={11}
            formatter={(v: unknown) => compact(v as number)} position="right"
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
