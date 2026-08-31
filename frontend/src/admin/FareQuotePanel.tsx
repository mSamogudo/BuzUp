/**
 * Simulador de tarifa (04-lacunas-backend.md, secção Tarifação).
 *
 * `POST /api/fares/quote/` já existia sem ecrã. Permite testar que regra ganha
 * — prioridade, classe, zona — antes de publicar uma alteração de preços, em
 * vez de descobrir a regra errada com o autocarro cheio.
 */
import { useCallback, useEffect, useState } from "react";
import { Calculator } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { apiFetch, apiPost } from "../lib/api";
import { formatCurrency } from "../lib/format";
import { enumEntry } from "../design/portal/enums";
import { Button, Card, Field, InlineError, Metric, Pill, Select } from "../design/ui";

interface RouteOption {
  id: number;
  code: string;
  name: string;
}

interface RouteStop {
  stop_id: number;
  stop_name: string;
  sequence: number;
  direction: string;
}

interface QuoteResult {
  amount: string;
  currency: string;
  method: string;
  route_code: string;
  origin: string | null;
  destination: string | null;
}

const CLASSES: [string, string][] = [
  ["standard", "Normal"],
  ["student", "Estudante"],
  ["senior", "Sénior"],
  ["child", "Criança"],
];

export default function FareQuotePanel() {
  const { token } = useAuth();
  const [routes, setRoutes] = useState<RouteOption[]>([]);
  const [stops, setStops] = useState<RouteStop[]>([]);
  const [routeId, setRouteId] = useState("");
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [klass, setKlass] = useState("standard");
  const [result, setResult] = useState<QuoteResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token) return;
    apiFetch("/api/routes/", token)
      .then((d) => setRoutes(d.results || d))
      .catch((e: Error) => setError(e.message));
  }, [token]);

  const loadStops = useCallback(() => {
    if (!token || !routeId) {
      setStops([]);
      return;
    }
    apiFetch(`/api/routes/${routeId}/stops/`, token)
      .then((d) => setStops(d.results || d))
      .catch(() => setStops([]));
  }, [token, routeId]);

  useEffect(loadStops, [loadStops]);

  const simulate = async () => {
    if (!token || !routeId) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const body: Record<string, unknown> = { route_id: Number(routeId), passenger_class: klass };
      if (origin) body.origin_stop_id = Number(origin);
      if (destination) body.destination_stop_id = Number(destination);
      setResult(await apiPost("/api/fares/quote/", token, body));
    } catch (e) {
      // Um 404 aqui é informação, não avaria: quer dizer que nenhuma regra
      // cobre este percurso — que é exactamente o que se veio testar.
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const outbound = stops.filter((s) => s.direction === "outbound").sort((a, b) => a.sequence - b.sequence);
  const list = outbound.length ? outbound : stops;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(280px, 380px)", gap: 16, alignItems: "start" }}>
      <Card large>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <p className="bz-page-desc" style={{ margin: 0 }}>
            Escolha o percurso e a classe do passageiro para ver que tarifa o sistema aplicaria neste momento.
          </p>

          <div className="bz-formgrid">
            <Field label="Rota" required span2>
              <Select
                onChange={(e) => {
                  setRouteId(e.target.value);
                  setOrigin("");
                  setDestination("");
                  setResult(null);
                }}
                value={routeId}
              >
                <option value="">Escolher…</option>
                {routes.map((route) => (
                  <option key={route.id} value={route.id}>
                    {route.code} — {route.name}
                  </option>
                ))}
              </Select>
            </Field>

            <Field hint="Vazio usa a tarifa da rota inteira." label="Origem">
              <Select disabled={!list.length} onChange={(e) => setOrigin(e.target.value)} value={origin}>
                <option value="">—</option>
                {list.map((stop) => (
                  <option key={`o-${stop.stop_id}`} value={stop.stop_id}>
                    {stop.sequence}. {stop.stop_name}
                  </option>
                ))}
              </Select>
            </Field>

            <Field label="Destino">
              <Select disabled={!list.length} onChange={(e) => setDestination(e.target.value)} value={destination}>
                <option value="">—</option>
                {list.map((stop) => (
                  <option key={`d-${stop.stop_id}`} value={stop.stop_id}>
                    {stop.sequence}. {stop.stop_name}
                  </option>
                ))}
              </Select>
            </Field>

            <Field label="Classe do passageiro">
              <Select onChange={(e) => setKlass(e.target.value)} value={klass}>
                {CLASSES.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <div>
            <Button disabled={!routeId} icon={<Calculator size={16} />} loading={busy} onClick={simulate}>
              Simular tarifa
            </Button>
          </div>

          {error ? <InlineError>{error}</InlineError> : null}
        </div>
      </Card>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <Metric
          detail={result ? `Rota ${result.route_code}` : "Ainda por simular"}
          label="Tarifa aplicada"
          value={result ? formatCurrency(result.amount, result.currency || "MZN") : "—"}
        />
        {result ? (
          <Card>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div className="bz-field">
                <span className="bz-field-label">Método de cálculo</span>
                <span>
                  <Pill tone={enumEntry("calc", result.method)[1]}>{enumEntry("calc", result.method)[0]}</Pill>
                </span>
              </div>
              <div className="bz-field">
                <span className="bz-field-label">Percurso</span>
                <span>
                  {result.origin || "início da rota"} → {result.destination || "fim da rota"}
                </span>
              </div>
            </div>
          </Card>
        ) : null}
      </div>
    </div>
  );
}
