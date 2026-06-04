import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Bus,
  CheckCircle,
  CreditCard,
  Download,
  Gift,
  LogOut,
  MapPin,
  ReceiptText,
  RefreshCw,
  Search,
  Ticket,
  Wallet,
  X,
} from "lucide-react";
import { apiFetch, apiPost, apiPublic } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { StatusBadge } from "../ui/common";
import { showToast } from "../lib/toast";

interface ActivePackage {
  id: number;
  package_id: number;
  package_name: string;
  discount_type: string;
  special_balance: string;
  trips_remaining: number | null;
  expires_at: string | null;
  status: string;
}

interface AvailablePackage {
  id: number;
  uuid: string;
  name: string;
  description: string;
  discount_type: string;
  discount_value: string;
  price: string;
  validity_days: number;
  max_trips: number;
  routes: { route_id: number; route_code: string; route_name: string }[];
}

interface PortalData {
  id: number;
  full_name: string;
  phone: string;
  wallet_uuid: string;
  balance: string;
  card_number: string | null;
  qr_token: string | null;
  card_id: number | null;
  active_packages: ActivePackage[];
  available_packages: AvailablePackage[];
}

interface StopOption { id: number; code: string; name: string; }
interface RouteOption { id: number; code: string; name: string; }
interface TripResult {
  trip_id: number;
  route_id: number;
  route_code: string;
  route_name: string;
  vehicle: string | null;
  driver: string | null;
  departure: string | null;
  started_at: string | null;
  direction: string;
  status: string;
  fare_amount: string | null;
}
interface TicketPurchaseResult {
  id: number;
  route_code: string;
  route_name: string;
  origin_stop: string;
  destination_stop: string;
  fare_amount: string;
  status: string;
  pdf_url: string;
  token: string;
}
interface TopupResult {
  reference: string;
  status: string;
  amount: string;
  detail_message: string;
  balance: string;
}
interface WalletTransaction {
  id: number;
  type: string;
  direction: string;
  amount: string;
  signed_amount: string;
  balance_after: string;
  reference: string;
  status: string;
  created_at: string;
}

type Direction = "outbound" | "inbound";

export default function PassengerPortalPage() {
  const { locale } = useUi();
  const { token, logout } = useAuth();
  const navigate = useNavigate();

  const [data, setData] = useState<PortalData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // search form
  const [stops, setStops] = useState<StopOption[]>([]);
  const [, setRoutes] = useState<RouteOption[]>([]);
  const [originId, setOriginId] = useState("");
  const [destId, setDestId] = useState("");
  const [direction, setDirection] = useState<Direction>("outbound");
  const [searching, setSearching] = useState(false);
  const [trips, setTrips] = useState<TripResult[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

  // payment modal
  const [selectedTrip, setSelectedTrip] = useState<TripResult | null>(null);
  const [submittingPayment, setSubmittingPayment] = useState(false);
  const [paymentResult, setPaymentResult] = useState<TicketPurchaseResult | null>(null);
  const [usePackage, setUsePackage] = useState(true);
  const [selectedPackageId, setSelectedPackageId] = useState<number | null>(null);
  const [quote, setQuote] = useState<{ base_fare: string; wallet_amount: string; package_id: number | null; package_name: string; discount_type: string } | null>(null);

  // wallet drawer
  const [walletOpen, setWalletOpen] = useState(false);
  const [transactions, setTransactions] = useState<WalletTransaction[]>([]);
  const [loadingTransactions, setLoadingTransactions] = useState(false);
  const [topupAmount, setTopupAmount] = useState("");
  const [topupPhone, setTopupPhone] = useState("");
  const [topupSubmitting, setTopupSubmitting] = useState(false);
  const [topupResult, setTopupResult] = useState<TopupResult | null>(null);
  const [packageBuyingId, setPackageBuyingId] = useState<number | null>(null);

  const loadPortal = useCallback(async () => {
    if (!token) return;
    try {
      const res = await apiFetch("/api/auth/me/passenger-portal/", token);
      setData(res as PortalData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar dados.");
    }
  }, [token]);

  const loadTransactions = useCallback(async () => {
    if (!token) return;
    setLoadingTransactions(true);
    try {
      const res = await apiFetch("/api/auth/me/passenger-portal/transactions/", token);
      setTransactions(res.results || []);
    } catch {
      setTransactions([]);
    } finally {
      setLoadingTransactions(false);
    }
  }, [token]);

  const loadCatalog = useCallback(async () => {
    try {
      const res = await apiPublic("/api/public/trips/");
      setRoutes(res.routes || []);
      setStops(res.stops || []);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([loadPortal(), loadCatalog(), loadTransactions()]).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [loadPortal, loadCatalog, loadTransactions]);

  useEffect(() => {
    if (topupPhone === "" && data?.phone) {
      setTopupPhone(data.phone);
    }
  }, [data?.phone, topupPhone]);

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (originId && destId && originId === destId) {
      showToast("danger", "O destino deve ser diferente da origem.");
      return;
    }
    setSearching(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (originId) params.set("origin", originId);
      if (destId) params.set("destination", destId);
      const res = await apiPublic(`/api/public/trips/?${params.toString()}`);
      const allTrips: TripResult[] = res.trips || [];
      const filtered = allTrips.filter((trip) => !trip.direction || trip.direction === direction);
      setTrips(filtered);
      setHasSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao pesquisar.");
    } finally {
      setSearching(false);
    }
  }

  function openPaymentModal(trip: TripResult) {
    setSelectedTrip(trip);
    setPaymentResult(null);
    setSelectedPackageId(null);
    setUsePackage(true);
    setQuote(null);
  }

  function closePaymentModal() {
    setSelectedTrip(null);
    setPaymentResult(null);
    setSelectedPackageId(null);
    setQuote(null);
  }

  useEffect(() => {
    if (!selectedTrip || !token) { setQuote(null); return; }
    let cancelled = false;
    const origin = stops.find((s) => String(s.id) === originId);
    const dest = stops.find((s) => String(s.id) === destId);
    const payload: Record<string, unknown> = {
      route_id: selectedTrip.route_id,
      origin_stop_id: origin?.id,
      destination_stop_id: dest?.id,
      trip_id: selectedTrip.trip_id,
    };
    if (usePackage) {
      if (selectedPackageId) payload.passenger_package_id = selectedPackageId;
    } else {
      payload.use_package = false;
    }
    apiPost("/api/travel-passes/quote/", token, payload)
      .then((res) => { if (!cancelled) setQuote(res); })
      .catch(() => { if (!cancelled) setQuote(null); });
    return () => { cancelled = true; };
  }, [selectedTrip, token, usePackage, selectedPackageId, originId, destId, stops]);

  async function handleBuyTicket(e: FormEvent) {
    e.preventDefault();
    if (!selectedTrip || !token) return;
    setSubmittingPayment(true);
    setError("");
    try {
      const origin = stops.find((s) => String(s.id) === originId);
      const dest = stops.find((s) => String(s.id) === destId);
      const payload: Record<string, unknown> = {
        route_id: selectedTrip.route_id,
        origin_stop_id: origin?.id,
        destination_stop_id: dest?.id,
        trip_id: selectedTrip.trip_id,
        use_package: usePackage,
      };
      if (usePackage && selectedPackageId) {
        payload.passenger_package_id = selectedPackageId;
      }
      const res = await apiPost("/api/travel-passes/purchase/", token, payload);
      setPaymentResult(res);
      const used = res.used_package;
      if (used) {
        showToast("success", `Bilhete emitido com pacote ${used.name}.`);
      } else {
        showToast("success", "Bilhete emitido com saldo da conta.");
      }
      await Promise.all([loadPortal(), loadTransactions()]);
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro ao comprar bilhete.");
    } finally {
      setSubmittingPayment(false);
    }
  }

  async function handleTopup(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setTopupSubmitting(true);
    setTopupResult(null);
    try {
      const res = await apiPost("/api/auth/me/passenger-portal/topup/", token, {
        amount: topupAmount,
        payer_phone: topupPhone,
      });
      setTopupResult(res);
      showToast(res.status === "confirmed" ? "success" : "neutral", res.detail_message || "Recarga iniciada.");
      await Promise.all([loadPortal(), loadTransactions()]);
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro ao iniciar recarga.");
    } finally {
      setTopupSubmitting(false);
    }
  }

  async function handleBuyPackage(packageId: number) {
    if (!token) return;
    setPackageBuyingId(packageId);
    try {
      const res = await apiPost("/api/auth/me/passenger-portal/packages/subscribe/", token, { package_id: packageId });
      showToast("success", `Pacote ${res.package_name || ""} activo.`);
      await Promise.all([loadPortal(), loadTransactions()]);
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro ao comprar pacote.");
    } finally {
      setPackageBuyingId(null);
    }
  }

  async function downloadExtract() {
    if (!token) return;
    try {
      const res = await fetch("/api/auth/me/passenger-portal/extract/", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Erro ao gerar extracto.");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "extracto-passageiro.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro ao gerar extracto.");
    }
  }

  if (loading) {
    return (
      <main className="portal-page">
        <div className="portal-container">
          <div className="skeleton-group">
            <div className="skeleton-card" />
            <div className="skeleton-card" />
            <div className="skeleton-card" />
          </div>
        </div>
      </main>
    );
  }

  if (error && !data) {
    return (
      <main className="portal-page">
        <div className="portal-container">
          <div className="portal-error">
            <p>{error}</p>
            <button className="secondary-button" onClick={handleLogout} type="button">
              <LogOut size={16} />
              {t(locale, "signOut")}
            </button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="portal-page">
      <div className="portal-container">
        <header className="portal-header">
          <div className="portal-header-info">
            <div className="portal-avatar">
              {(data?.full_name || "")
                .split(/\s+/)
                .filter(Boolean)
                .slice(0, 2)
                .map((w) => w[0]?.toUpperCase())
                .join("")}
            </div>
            <div>
              <h1 className="portal-name">{data?.full_name}</h1>
              <p className="portal-phone">{data?.phone}</p>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="secondary-button" onClick={() => setWalletOpen(true)} type="button" aria-label="Minha Carteira">
              <Wallet size={16} />
              <span>{formatCurrency(data?.balance || "0")}</span>
            </button>
            <button className="secondary-button" onClick={handleLogout} type="button" aria-label="Sair">
              <LogOut size={16} />
            </button>
          </div>
        </header>

        <section className="portal-wallet-grid">
          <article className="portal-wallet-card portal-wallet-card-strong">
            <span>Saldo da conta</span>
            <strong>{formatCurrency(data?.balance || "0")}</strong>
            <button className="primary-button" onClick={() => setWalletOpen(true)} type="button">
              <Wallet size={16} /> Recarregar
            </button>
          </article>
          <article className="portal-wallet-card">
            <span>Cartao</span>
            <strong>{data?.card_number || "Sem cartao associado"}</strong>
            <small>O validador desconta directamente deste saldo.</small>
          </article>
          <article className="portal-wallet-card">
            <span>Pacotes activos</span>
            <strong>{data?.active_packages?.length || 0}</strong>
            <small>Pacotes e bilhetes tambem usam o saldo da conta.</small>
          </article>
        </section>

        <section className="portal-section">
          <h2 className="portal-section-title">
            <Search size={18} />
            Pesquisar Autocarro
          </h2>

          <form className="co-form" onSubmit={handleSearch}>
            <select
              className="co-select"
              value={originId}
              onChange={(e) => { const v = e.target.value; setOriginId(v); if (v && v === destId) setDestId(""); }}
            >
              <option value="">Origem</option>
              {stops.filter((s) => String(s.id) !== destId).map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>

            <select
              className="co-select"
              value={destId}
              onChange={(e) => { const v = e.target.value; setDestId(v); if (v && v === originId) setOriginId(""); }}
            >
              <option value="">Destino</option>
              {stops.filter((s) => String(s.id) !== originId).map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>

            <div className="co-row">
              <label className={`co-btn-outline${direction === "outbound" ? " " : ""}`} style={direction === "outbound" ? { borderColor: "#1D5FA7", color: "#1D5FA7", fontWeight: 700 } : undefined}>
                <input
                  type="radio"
                  name="dir"
                  value="outbound"
                  checked={direction === "outbound"}
                  onChange={() => setDirection("outbound")}
                  style={{ display: "none" }}
                />
                <ArrowRight size={16} /> IDA
              </label>
              <label className={`co-btn-outline${direction === "inbound" ? " " : ""}`} style={direction === "inbound" ? { borderColor: "#1D5FA7", color: "#1D5FA7", fontWeight: 700 } : undefined}>
                <input
                  type="radio"
                  name="dir"
                  value="inbound"
                  checked={direction === "inbound"}
                  onChange={() => setDirection("inbound")}
                  style={{ display: "none" }}
                />
                <ArrowLeft size={16} /> VOLTA
              </label>
            </div>

            <button className="co-btn" type="submit" disabled={searching}>
              <Search size={18} />{searching ? "A pesquisar..." : "Pesquisar"}
            </button>
          </form>
        </section>

        {hasSearched && (
          <section className="portal-section">
            <h2 className="portal-section-title">
              <Bus size={18} />
              {trips.length} autocarro{trips.length === 1 ? "" : "s"} disponivel{trips.length === 1 ? "" : "s"}
            </h2>
            {trips.length === 0 ? (
              <p className="portal-empty">Nenhum autocarro disponivel para essa pesquisa.</p>
            ) : (
              <div className="co-trips">
                {trips.map((trip) => (
                  <button key={trip.trip_id} className="co-trip" onClick={() => openPaymentModal(trip)} type="button">
                    <div className="co-trip-left">
                      <span className="co-trip-code">{trip.route_code}</span>
                      <div className="co-trip-details">
                        <strong>{trip.vehicle || trip.route_name}</strong>
                        <span>{trip.route_name} - {trip.direction === "inbound" ? "VOLTA" : "IDA"}</span>
                        <span>
                          <MapPin size={12} /> {trip.started_at ? formatDateTime(trip.started_at) : trip.departure ? formatDateTime(trip.departure) : "-"}
                        </span>
                      </div>
                    </div>
                    <div className="co-trip-price">{trip.fare_amount ? formatCurrency(trip.fare_amount) : "-"}</div>
                  </button>
                ))}
              </div>
            )}
          </section>
        )}
      </div>

      {selectedTrip && (
        <>
          <div className="admin-modal-overlay" onClick={closePaymentModal} />
          <div className="admin-modal-shell" role="dialog" aria-modal="true" aria-label="Comprar Bilhete">
            <div className="admin-modal-card">
              <div className="admin-modal-head">
                <div>
                  <h3>Comprar Bilhete</h3>
                  <p>{selectedTrip.route_code} - {selectedTrip.route_name}</p>
                </div>
                <button className="icon-button" onClick={closePaymentModal} type="button"><X size={18} /></button>
              </div>
              <div className="admin-modal-body">
                {paymentResult ? (
                  <div className="co-success">
                    <CheckCircle size={48} className="co-success-icon" />
                    <h2>Bilhete Emitido</h2>
                    <p>O valor foi debitado do saldo da sua conta.</p>
                    <div className="co-receipt">
                      <div><span>Rota</span><strong>{paymentResult.route_code}</strong></div>
                      <div><span>Total</span><strong>{formatCurrency(paymentResult.fare_amount)}</strong></div>
                      <div><span>Estado</span><strong>{paymentResult.status}</strong></div>
                    </div>
                    {paymentResult.pdf_url && (
                      <a className="co-btn" href={paymentResult.pdf_url} target="_blank" rel="noreferrer">
                        <Ticket size={18} /> Ver Bilhete
                      </a>
                    )}
                  </div>
                ) : (
                  <form className="co-form" onSubmit={handleBuyTicket}>
                    <div className="co-pay-summary">
                      <div className="co-pay-route">
                        <span className="co-trip-code">{selectedTrip.route_code}</span>
                        <div>
                          <strong>{selectedTrip.vehicle || selectedTrip.route_name}</strong>
                          <span>{selectedTrip.direction === "inbound" ? "VOLTA" : "IDA"}</span>
                        </div>
                      </div>
                      <div className="co-pay-amount">
                        {quote && quote.package_id ? (
                          <>
                            <span style={{ textDecoration: "line-through", fontSize: 14, color: "var(--app-text-muted)" }}>{formatCurrency(quote.base_fare)}</span>
                            <br />
                            <strong style={{ color: "var(--app-accent)" }}>{formatCurrency(quote.wallet_amount)}</strong>
                          </>
                        ) : (
                          formatCurrency(selectedTrip.fare_amount)
                        )}
                      </div>
                    </div>

                    {(data?.active_packages || []).length > 0 && (
                      <div className="portal-package-picker">
                        <label className="portal-payment-toggle">
                          <input type="checkbox" checked={usePackage} onChange={(e) => setUsePackage(e.target.checked)} />
                          <span>Usar pacote especial se disponivel</span>
                        </label>
                        {usePackage && (
                          <select
                            className="portal-package-select"
                            value={selectedPackageId === null ? "" : String(selectedPackageId)}
                            onChange={(e) => setSelectedPackageId(e.target.value ? Number(e.target.value) : null)}
                          >
                            <option value="">Automatico (escolhe melhor)</option>
                            {(data?.active_packages || []).map((p) => (
                              <option key={p.id} value={p.id}>
                                {p.package_name} {(p.trips_remaining || 0) > 0 ? `· ${p.trips_remaining} viagens` : p.special_balance ? `· ${formatCurrency(p.special_balance)} saldo` : ""}
                              </option>
                            ))}
                          </select>
                        )}
                      </div>
                    )}

                    <div className="portal-payment-note">
                      <Wallet size={18} />
                      <div>
                        {quote && quote.package_id ? (
                          <>
                            <strong>Pacote {quote.package_name}</strong>
                            <span>Pagar do saldo: {formatCurrency(quote.wallet_amount)} (saldo: {formatCurrency(data?.balance || "0")})</span>
                          </>
                        ) : (
                          <>
                            <strong>Pagamento por saldo da conta</strong>
                            <span>Saldo actual: {formatCurrency(data?.balance || "0")}</span>
                          </>
                        )}
                      </div>
                    </div>
                    <button className="co-btn" type="submit" disabled={submittingPayment}>
                      <CreditCard size={18} />{submittingPayment ? "A processar..." : (quote && quote.package_id ? "Comprar com pacote" : "Comprar com saldo")}
                    </button>
                  </form>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {walletOpen && (
        <>
          <div className="admin-modal-overlay" onClick={() => setWalletOpen(false)} />
          <aside
            className="portal-wallet-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Minha Carteira"
            style={{
              position: "fixed",
              top: 0,
              right: 0,
              bottom: 0,
              width: "min(420px, 100%)",
              background: "var(--app-surface-strong, #fff)",
              boxShadow: "-12px 0 32px rgba(0,0,0,0.18)",
              zIndex: 60,
              overflowY: "auto",
              padding: 20,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
              <h2 style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 18, fontWeight: 700 }}>
                <Wallet size={20} /> Minha Carteira
              </h2>
              <button className="icon-button" onClick={() => setWalletOpen(false)} type="button"><X size={18} /></button>
            </div>

            <section className="admin-metric-grid" style={{ gridTemplateColumns: "1fr", marginBottom: 16 }}>
              <article className="admin-card admin-card-strong">
                <span>
                  <Wallet size={14} style={{ display: "inline", verticalAlign: "middle", marginRight: 6 }} />
                  {t(locale, "balance")}
                </span>
                <strong>{formatCurrency(data?.balance || "0")}</strong>
              </article>
            </section>

            <section className="portal-section">
              <h3 className="portal-section-title">
                <Wallet size={18} />
                Recarregar conta
              </h3>
              <form className="co-form" onSubmit={handleTopup}>
                <input
                  className="co-input"
                  inputMode="decimal"
                  placeholder="Valor da recarga"
                  required
                  type="number"
                  min={1}
                  step="0.01"
                  value={topupAmount}
                  onChange={(e) => setTopupAmount(e.target.value)}
                />
                <input
                  className="co-input"
                  required
                  type="tel"
                  placeholder="Telefone M-Pesa/E-Mola"
                  value={topupPhone}
                  onChange={(e) => setTopupPhone(e.target.value)}
                />
                <button className="co-btn" disabled={topupSubmitting || !topupAmount || !topupPhone} type="submit">
                  <CreditCard size={18} />{topupSubmitting ? "A processar..." : "Recarregar"}
                </button>
              </form>
              {topupResult && (
                <div className="co-receipt">
                  <div><span>Referencia</span><strong>{topupResult.reference}</strong></div>
                  <div><span>Estado</span><strong>{topupResult.status}</strong></div>
                  <div><span>Valor</span><strong>{formatCurrency(topupResult.amount)}</strong></div>
                </div>
              )}
            </section>

            <section className="portal-section">
              <div className="portal-section-head">
                <h3 className="portal-section-title">
                  <ReceiptText size={18} />
                  Transaccoes
                </h3>
                <div className="portal-section-actions">
                  <button className="icon-button" onClick={loadTransactions} title="Actualizar" type="button">
                    <RefreshCw size={16} />
                  </button>
                  <button className="icon-button" onClick={downloadExtract} title="Baixar extracto" type="button">
                    <Download size={16} />
                  </button>
                </div>
              </div>
              {loadingTransactions ? (
                <p className="portal-empty">A carregar transaccoes...</p>
              ) : transactions.length === 0 ? (
                <p className="portal-empty">Sem transaccoes recentes.</p>
              ) : (
                <div className="portal-transactions-list">
                  {transactions.map((tx) => {
                    const labels: Record<string, string> = {
                      topup: "Recarga",
                      fare_debit: "Viagem",
                      fee: "Taxa/Pacote",
                      refund: "Reembolso",
                      reversal: "Reversao",
                      adjustment: "Ajuste",
                    };
                    const label = labels[tx.type] || tx.type;
                    const meta = (tx as unknown as { metadata?: Record<string, unknown> }).metadata || {};
                    const pkgName = meta && typeof meta === "object" ? (meta.package_name as string | undefined) : undefined;
                    const fullyCovered = meta && (meta.fully_covered_by_package === true);
                    const isZero = Number(tx.amount) === 0;
                    return (
                      <article key={tx.id} className="portal-transaction-item">
                        <div>
                          <strong>{label}{pkgName ? ` (${pkgName})` : ""}</strong>
                          <span>{tx.reference}</span>
                          <small>{formatDateTime(tx.created_at)}</small>
                        </div>
                        <div className={tx.direction === "credit" ? "portal-tx-credit" : "portal-tx-debit"}>
                          {isZero && fullyCovered ? "GRATIS" : `${tx.direction === "credit" ? "+" : "-"}${formatCurrency(tx.amount)}`}
                        </div>
                      </article>
                    );
                  })}
                </div>
              )}
            </section>

            <section className="portal-section">
              <h3 className="portal-section-title">
                <CreditCard size={18} />
                {t(locale, "digitalCards")}
              </h3>
              <div className="portal-card-display">
                {data?.card_number ? (
                  <>
                    <div className="portal-card-row">
                      <span className="portal-card-label">{t(locale, "cardNumber")}</span>
                      <strong className="portal-card-value">{data.card_number}</strong>
                    </div>
                    {data.card_id && token && (
                      <div
                        style={{
                          display: "flex", flexDirection: "column",
                          alignItems: "center", gap: 10, marginTop: 12,
                          padding: 14, background: "#fff", borderRadius: 12,
                          border: "1px solid #E7E1D4",
                        }}
                      >
                        <img
                          src={`/api/cards/${data.card_id}/qr.png?token=${encodeURIComponent(token)}`}
                          alt="QR do meu cartao"
                          style={{ width: 220, height: 220 }}
                        />
                        <small style={{ color: "#6B6356", textAlign: "center" }}>
                          Mostre este QR ao agente para comprar bilhetes ou recarregar a sua carteira.
                        </small>
                        <a
                          className="primary-button"
                          href={`/api/cards/${data.card_id}/qr.png?token=${encodeURIComponent(token)}`}
                          download={`buzup-qr-${data.card_number}.png`}
                          style={{ textDecoration: "none" }}
                        >
                          Descarregar QR
                        </a>
                      </div>
                    )}
                  </>
                ) : (
                  <p className="portal-empty">{t(locale, "noCards")}</p>
                )}
              </div>
            </section>

            <section className="portal-section">
              <h3 className="portal-section-title">
                <Gift size={18} />
                {t(locale, "packages")}
              </h3>
              {data?.active_packages && data.active_packages.length > 0 ? (
                <div className="portal-packages-list">
                  {data.active_packages.map((pkg) => (
                    <div key={pkg.id} className="portal-package-item">
                      <div className="portal-package-header">
                        <strong>{pkg.package_name}</strong>
                        <StatusBadge value={pkg.status} />
                      </div>
                      <div className="portal-package-details">
                        {pkg.discount_type === "fixed_amount" && (
                          <span>
                            Saldo especial: <strong>{formatCurrency(pkg.special_balance)}</strong>
                          </span>
                        )}
                        {pkg.trips_remaining !== null && (
                          <span>
                            {t(locale, "tripsRemaining")}: <strong>{pkg.trips_remaining}</strong>
                          </span>
                        )}
                        {pkg.expires_at && (
                          <span>
                            {t(locale, "expiresAt")}: <strong>{formatDateTime(pkg.expires_at)}</strong>
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="portal-empty">{t(locale, "noPackages")}</p>
              )}
              <div className="portal-section-head portal-package-market-head">
                <h3 className="portal-section-title">
                  <Gift size={18} />
                  Comprar pacote
                </h3>
              </div>
              <div className="portal-packages-list">
                {(data?.available_packages || [])
                  .filter((pkg) => !(data?.active_packages || []).some((active) => active.package_id === pkg.id && active.status === "active"))
                  .map((pkg) => (
                    <article key={pkg.id} className="portal-package-item portal-package-buy">
                      <div className="portal-package-header">
                        <strong>{pkg.name}</strong>
                        <span className="portal-package-price">{formatCurrency(pkg.price)}</span>
                      </div>
                      <div className="portal-package-details">
                        <span>{packageBenefit(pkg)}</span>
                        <span>{pkg.validity_days} dias</span>
                        <span>{pkg.routes.length > 0 ? pkg.routes.map((route) => route.route_code).join(", ") : "Todas as rotas"}</span>
                      </div>
                      {pkg.description ? <p className="portal-package-description">{pkg.description}</p> : null}
                      <button
                        className="primary-button"
                        disabled={packageBuyingId === pkg.id}
                        onClick={() => handleBuyPackage(pkg.id)}
                        type="button"
                      >
                        <CreditCard size={16} />
                        {packageBuyingId === pkg.id ? "A processar..." : "Comprar com saldo"}
                      </button>
                    </article>
                  ))}
                {(data?.available_packages || []).filter((pkg) => !(data?.active_packages || []).some((active) => active.package_id === pkg.id && active.status === "active")).length === 0 ? (
                  <p className="portal-empty">Sem pacotes disponiveis para compra.</p>
                ) : null}
              </div>
            </section>
          </aside>
        </>
      )}
    </main>
  );
}

function packageBenefit(pkg: AvailablePackage) {
  if (pkg.discount_type === "percentage") return `${Number(pkg.discount_value).toFixed(0)}% desconto`;
  if (pkg.discount_type === "free_trips") return `${pkg.max_trips} viagens incluidas`;
  if (pkg.discount_type === "fixed_amount") return `${formatCurrency(pkg.discount_value)} de saldo especial`;
  return pkg.discount_type.replace(/_/g, " ");
}
