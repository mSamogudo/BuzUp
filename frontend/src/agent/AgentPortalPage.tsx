import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle, CreditCard, LogOut, QrCode, ScanLine, Wallet, XCircle } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { showToast } from "../lib/toast";

type Tab = "validate" | "topup";

interface OperationLog {
  id: string;
  kind: "validate" | "topup";
  ok: boolean;
  label: string;
  detail: string;
  amount?: string;
  at: string;
}

export default function AgentPortalPage() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const [tab, setTab] = useState<Tab>("validate");

  const [validationInput, setValidationInput] = useState("");
  const [validating, setValidating] = useState(false);

  const [topupPhone, setTopupPhone] = useState("");
  const [topupAmount, setTopupAmount] = useState("");
  const [toppingUp, setToppingUp] = useState(false);

  const [log, setLog] = useState<OperationLog[]>([]);

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  function pushLog(entry: Omit<OperationLog, "id" | "at">) {
    setLog((prev) => [
      { ...entry, id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, at: new Date().toISOString() },
      ...prev,
    ].slice(0, 10));
  }

  async function handleValidate(e: FormEvent) {
    e.preventDefault();
    const code = validationInput.trim();
    if (!code) return;
    setValidating(true);
    try {
      // Em desenvolvimento: ligar a endpoint de validacao POS (ex: /api/pos/validate/).
      await new Promise((resolve) => setTimeout(resolve, 350));
      pushLog({
        kind: "validate",
        ok: true,
        label: "Validacao",
        detail: code,
      });
      showToast("neutral", "Funcionalidade em desenvolvimento.");
      setValidationInput("");
    } catch (err) {
      pushLog({
        kind: "validate",
        ok: false,
        label: "Validacao",
        detail: err instanceof Error ? err.message : String(err),
      });
      showToast("danger", err instanceof Error ? err.message : "Erro na validacao.");
    } finally {
      setValidating(false);
    }
  }

  async function handleTopup(e: FormEvent) {
    e.preventDefault();
    const phone = topupPhone.trim();
    const amount = topupAmount.trim();
    if (!phone || !amount) return;
    setToppingUp(true);
    try {
      // Em desenvolvimento: ligar a endpoint de recarga POS (ex: /api/pos/topup/).
      await new Promise((resolve) => setTimeout(resolve, 350));
      pushLog({
        kind: "topup",
        ok: true,
        label: "Recarga",
        detail: phone,
        amount,
      });
      showToast("neutral", "Funcionalidade em desenvolvimento.");
      setTopupPhone("");
      setTopupAmount("");
    } catch (err) {
      pushLog({
        kind: "topup",
        ok: false,
        label: "Recarga",
        detail: err instanceof Error ? err.message : String(err),
      });
      showToast("danger", err instanceof Error ? err.message : "Erro na recarga.");
    } finally {
      setToppingUp(false);
    }
  }

  return (
    <main className="driver-page">
      <header className="driver-topbar">
        <div>
          <span>Portal do Agente</span>
          <h1>Operacoes POS</h1>
        </div>
        <button className="driver-ghost-button" onClick={handleLogout} type="button"><LogOut size={18} /> Sair</button>
      </header>

      <section className="driver-layout">
        <aside className="driver-trip-list" style={{ minWidth: 260 }}>
          <div className="driver-section-head">
            <strong>POS</strong>
          </div>
          <button
            className={`driver-trip-card${tab === "validate" ? " driver-trip-card-active" : ""}`}
            onClick={() => setTab("validate")}
            type="button"
          >
            <span>Bilhetes</span>
            <strong style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
              <ScanLine size={16} /> Validar Bilhete
            </strong>
            <small>QR / UID de cartao</small>
          </button>
          <button
            className={`driver-trip-card${tab === "topup" ? " driver-trip-card-active" : ""}`}
            onClick={() => setTab("topup")}
            type="button"
          >
            <span>Carteira</span>
            <strong style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
              <Wallet size={16} /> Recarregar Carteira
            </strong>
            <small>Telefone + valor</small>
          </button>
        </aside>

        <section className="driver-workspace">
          {tab === "validate" ? (
            <>
              <div className="driver-trip-hero">
                <div>
                  <span>POS</span>
                  <h2>Validar Bilhete</h2>
                  <p>Leia o QR ou aproxime o cartao. Tambem pode introduzir o codigo manualmente.</p>
                </div>
                <QrCode size={42} />
              </div>
              <form className="admin-form" onSubmit={handleValidate} style={{ marginTop: 16 }}>
                <label className="field">
                  <span>Codigo QR ou UID do cartao</span>
                  <input
                    value={validationInput}
                    onChange={(e) => setValidationInput(e.target.value)}
                    placeholder="Ex: 04A1B2C3D4 ou TOKEN..."
                    autoFocus
                  />
                </label>
                <div className="admin-form-actions">
                  <button className="primary-button" disabled={validating || !validationInput.trim()} type="submit">
                    {validating ? "A validar..." : "Validar"}
                  </button>
                </div>
              </form>
            </>
          ) : (
            <>
              <div className="driver-trip-hero">
                <div>
                  <span>POS</span>
                  <h2>Recarregar Carteira</h2>
                  <p>Indique o telefone do passageiro e o valor a creditar.</p>
                </div>
                <CreditCard size={42} />
              </div>
              <form className="admin-form" onSubmit={handleTopup} style={{ marginTop: 16 }}>
                <div className="admin-form-grid">
                  <label className="field">
                    <span>Telefone</span>
                    <input
                      type="tel"
                      value={topupPhone}
                      onChange={(e) => setTopupPhone(e.target.value)}
                      placeholder="84/85/86/87..."
                    />
                  </label>
                  <label className="field">
                    <span>Valor (MZN)</span>
                    <input
                      type="number"
                      min="0"
                      step="1"
                      value={topupAmount}
                      onChange={(e) => setTopupAmount(e.target.value)}
                      placeholder="100"
                    />
                  </label>
                </div>
                <div className="admin-form-actions">
                  <button className="primary-button" disabled={toppingUp || !topupPhone.trim() || !topupAmount.trim()} type="submit">
                    {toppingUp ? "A recarregar..." : "Recarregar"}
                  </button>
                </div>
              </form>
            </>
          )}

          <div className="driver-revenue-panel" style={{ marginTop: 24 }}>
            <h3>Ultimas Operacoes</h3>
            {log.length === 0 ? (
              <p className="driver-muted">Sem operacoes recentes.</p>
            ) : (
              <div className="driver-revenue-grid">
                {log.map((entry) => (
                  <div key={entry.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {entry.ok ? <CheckCircle size={16} color="#22c55e" /> : <XCircle size={16} color="#ef4444" />}
                    <span style={{ flex: 1 }}>
                      {entry.label} · {entry.detail}
                      {entry.amount ? ` · ${entry.amount} MZN` : ""}
                    </span>
                    <strong style={{ fontSize: 11, color: "var(--app-text-muted)" }}>
                      {new Date(entry.at).toLocaleTimeString("pt-MZ")}
                    </strong>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </section>
    </main>
  );
}
