import { useEffect, useMemo, useRef, useState, type ClipboardEvent, type FormEvent, type KeyboardEvent } from "react";
import { AlertCircle, CreditCard, Eye, EyeOff, Lock, Phone, QrCode, Route, Shield, Smartphone, User, UserPlus, Wallet, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { apiLogin, apiOtpRequest, apiOtpVerify, apiPublic } from "../lib/api";
import { t, type Locale } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "./AuthContext";
import { useUi } from "../ui/UiPreferences";
import { useBranding, pickLogo } from "../lib/branding";
import "./login.css";

type Mode = "staff" | "otp" | "register";
type OtpStep = "phone" | "code";

/* Copy de marca do painel esquerdo + microcopy que não existe no dicionário
   global. Mantém-se aqui porque só esta página a usa. */
const COPY: Record<Locale, {
  headline: [string, string, string];
  lead: string;
  tag: string;
  proof: { title: string; text: string }[];
  chips: string[];
  eyebrow: Record<Mode, string>;
  showPassword: string;
  hidePassword: string;
  forgot: string;
  resetTitle: string;
  resetLead: string;
  resetSubmit: string;
  resetBusy: string;
  resetOk: string;
  resetFail: string;
}> = {
  pt: {
    headline: ["Bilhete, carteira e frota", " numa só ", "plataforma."],
    lead: "Entre no portal BusUp para gerir viagens, vendas e validações — ou entre como passageiro com o seu número de telefone.",
    tag: "Transporte cashless",
    proof: [
      { title: "3 canais de venda e validação", text: "App do passageiro, POS a bordo e agente de bilheteira." },
      { title: "2 carteiras móveis integradas", text: "M-Pesa e e-Mola, sem guardar dados de cartão." },
      { title: "Frota e viagens em tempo real", text: "Partidas, lugares e localização no mesmo painel." },
    ],
    chips: ["QR no telemóvel", "Cartão NFC", "M-Pesa", "e-Mola"],
    eyebrow: { staff: "Acesso seguro", otp: "Acesso por SMS", register: "Nova conta" },
    showPassword: "Mostrar senha",
    hidePassword: "Ocultar senha",
    forgot: "Esqueci a senha",
    resetTitle: "Reposição de senha",
    resetLead: "Indique o telefone associado à sua conta.",
    resetSubmit: "Enviar",
    resetBusy: "A enviar...",
    resetOk: "Se o telefone estiver associado, receberá uma SMS com a nova senha.",
    resetFail: "Erro ao solicitar reposição.",
  },
  en: {
    headline: ["Ticketing, wallet and fleet", " on a single ", "platform."],
    lead: "Sign in to the BusUp portal to manage trips, sales and validations — or sign in as a passenger with your phone number.",
    tag: "Cashless transport",
    proof: [
      { title: "3 sales and validation channels", text: "Passenger app, on-board POS and ticketing agent." },
      { title: "2 mobile wallets integrated", text: "M-Pesa and e-Mola, with no card data stored." },
      { title: "Fleet and trips in real time", text: "Departures, seats and location in one dashboard." },
    ],
    chips: ["QR on the phone", "NFC card", "M-Pesa", "e-Mola"],
    eyebrow: { staff: "Secure sign in", otp: "SMS access", register: "New account" },
    showPassword: "Show password",
    hidePassword: "Hide password",
    forgot: "Forgot password",
    resetTitle: "Password reset",
    resetLead: "Enter the phone number linked to your account.",
    resetSubmit: "Send",
    resetBusy: "Sending...",
    resetOk: "If the phone is linked to an account, you will receive an SMS with the new password.",
    resetFail: "Could not request the reset.",
  },
};

const PROOF_ICONS = [Route, Wallet, Smartphone];

export default function LoginPage() {
  const { locale, setLocale } = useUi();
  const { login } = useAuth();
  const { branding } = useBranding();
  const navigate = useNavigate();
  const copy = COPY[locale] ?? COPY.pt;

  /* O tema explícito do portal manda; sem escolha guardada seguimos o sistema
     (prefers-color-scheme), tal como a landing pública. */
  const explicitTheme = useMemo(() => {
    try {
      const stored = localStorage.getItem("buzup_theme");
      return stored === "dark" || stored === "light" ? stored : undefined;
    } catch {
      return undefined;
    }
  }, []);

  const [mode, setMode] = useState<Mode>("staff");

  // Staff login state
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // OTP state
  const [phone, setPhone] = useState("");
  const [fullName, setFullName] = useState("");
  const [otpStep, setOtpStep] = useState<OtpStep>("phone");
  const [challengeId, setChallengeId] = useState("");
  const [otpDigits, setOtpDigits] = useState(["", "", "", "", "", ""]);
  const [countdown, setCountdown] = useState(0);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Password reset
  const [resetOpen, setResetOpen] = useState(false);
  const [resetPhone, setResetPhone] = useState("");
  const [resetBusy, setResetBusy] = useState(false);

  async function handlePasswordReset(e: FormEvent) {
    e.preventDefault();
    setResetBusy(true);
    try {
      await apiPublic("/api/auth/password-reset/", {
        method: "POST",
        body: JSON.stringify({ phone: resetPhone }),
      });
      showToast("success", copy.resetOk);
      setResetOpen(false);
      setResetPhone("");
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : copy.resetFail);
    } finally {
      setResetBusy(false);
    }
  }

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setInterval(() => setCountdown((c) => c - 1), 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  async function handleStaffLogin(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const tokens = await apiLogin(username, password);
      login(tokens.access, tokens.refresh);
      const driverRes = await fetch("/api/driver/trips/", {
        headers: { Authorization: `Bearer ${tokens.access}` },
      }).catch(() => null);
      navigate(driverRes?.ok ? "/driver" : "/app", { replace: true });
    } catch {
      setError(t(locale, "invalidCredentials"));
    } finally {
      setLoading(false);
    }
  }

  async function handleOtpRequest(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (mode === "register" && !fullName.trim()) {
      setError(t(locale, "requiredFullName"));
      return;
    }
    setLoading(true);
    try {
      const res = await apiOtpRequest(phone);
      setPhone(res.phone || phone);
      setChallengeId(res.challenge_id);
      setCountdown(Math.floor(res.expires_in));
      setOtpStep("code");
      setOtpDigits(["", "", "", "", "", ""]);
      setTimeout(() => inputRefs.current[0]?.focus(), 100);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro.");
    } finally {
      setLoading(false);
    }
  }

  async function handleOtpVerify(codeOverride?: string) {
    const code = (codeOverride ?? otpDigits.join("")).replace(/\D/g, "").slice(0, 6);
    if (code.length < 6) return;
    setError("");
    setLoading(true);
    try {
      const res = await apiOtpVerify(phone, challengeId, code, mode === "register" ? fullName.trim() : undefined);
      login(res.access, res.refresh);
      if (res.agent_id) {
        navigate("/agent", { replace: true });
      } else if (res.driver_id) {
        navigate("/driver", { replace: true });
      } else if (res.passenger_id) {
        navigate("/portal", { replace: true });
      } else {
        navigate("/portal", { replace: true });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Codigo invalido.");
      setOtpDigits(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  }

  function handleDigitChange(index: number, value: string) {
    if (!/^\d*$/.test(value)) return;
    const newDigits = [...otpDigits];
    if (value.length > 1) {
      const chars = value.slice(0, 6).split("");
      chars.forEach((ch, i) => {
        if (index + i < 6) newDigits[index + i] = ch;
      });
      setOtpDigits(newDigits);
      const nextIdx = Math.min(index + chars.length, 5);
      inputRefs.current[nextIdx]?.focus();
      const nextCode = newDigits.join("");
      if (nextCode.length === 6) {
        setTimeout(() => void handleOtpVerify(nextCode), 50);
      }
      return;
    }
    newDigits[index] = value;
    setOtpDigits(newDigits);
    if (value && index < 5) inputRefs.current[index + 1]?.focus();
    const nextCode = newDigits.join("");
    if (nextCode.length === 6) {
      setTimeout(() => void handleOtpVerify(nextCode), 50);
    }
  }

  function handleDigitKeyDown(index: number, e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Backspace" && !otpDigits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  }

  function handleDigitPaste(e: ClipboardEvent<HTMLInputElement>) {
    const pastedCode = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (!pastedCode) return;
    e.preventDefault();
    const newDigits = Array.from({ length: 6 }, (_, i) => pastedCode[i] || "");
    setOtpDigits(newDigits);
    inputRefs.current[Math.min(pastedCode.length, 5)]?.focus();
    if (pastedCode.length === 6) {
      setTimeout(() => void handleOtpVerify(pastedCode), 50);
    }
  }

  async function handleResend() {
    setError("");
    setLoading(true);
    try {
      const res = await apiOtpRequest(phone);
      setPhone(res.phone || phone);
      setChallengeId(res.challenge_id);
      setCountdown(Math.floor(res.expires_in));
      setOtpDigits(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro.");
    } finally {
      setLoading(false);
    }
  }

  function switchMode(m: Mode) {
    setMode(m);
    setError("");
    setOtpStep("phone");
    setOtpDigits(["", "", "", "", "", ""]);
  }

  /* Navegação por setas no tablist (WAI-ARIA), já que só o separador activo
     fica na ordem de tabulação. */
  function handleTabKeys(e: KeyboardEvent<HTMLButtonElement>, index: number) {
    const order: Mode[] = ["staff", "otp", "register"];
    let next = -1;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = (index + 1) % order.length;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = (index - 1 + order.length) % order.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = order.length - 1;
    if (next < 0) return;
    e.preventDefault();
    switchMode(order[next]);
    document.getElementById(`bzau-tab-${order[next]}`)?.focus();
  }

  const tabs: { id: Mode; label: string; icon: typeof Shield }[] = [
    { id: "staff", label: t(locale, "staffLogin"), icon: Shield },
    { id: "otp", label: t(locale, "otpLogin"), icon: Smartphone },
    { id: "register", label: t(locale, "registerPassenger"), icon: UserPlus },
  ];

  const heading = mode === "staff"
    ? t(locale, "login")
    : mode === "register"
      ? t(locale, "createPassengerAccount")
      : t(locale, "welcomePassenger");
  const subheading = mode === "staff"
    ? t(locale, "loginSubtitle")
    : mode === "register"
      ? t(locale, "passengerRegisterSubtitle")
      : t(locale, "otpSubtitle");

  const errorBlock = error ? (
    <div className="bzau-error" role="alert">
      <AlertCircle size={17} />
      <span>{error}</span>
    </div>
  ) : null;

  return (
    <main className="bzau" data-theme={explicitTheme}>
      {/* ── Painel de marca ── */}
      <aside className="bzau-brand">
        <div className="bzau-brand-in">
          <img
            alt="BusUp"
            className="bzau-logo"
            src={pickLogo(branding.auth_logo_url, branding.primary_logo_url, "/assets/busup/logo-dark.png")}
          />
          <span className="bzau-mobile-tag">{copy.tag}</span>

          <span className="bzau-badge">{t(locale, "cashlessTransport")}</span>
          <h1>
            {copy.headline[0]}
            {copy.headline[1]}
            <span>{copy.headline[2]}</span>
          </h1>
          <p className="bzau-lead">{copy.lead}</p>

          <ul className="bzau-proof">
            {copy.proof.map((item, i) => {
              const Icon = PROOF_ICONS[i] ?? Route;
              return (
                <li key={item.title}>
                  <span className="bzau-proof-ico" aria-hidden="true">
                    <Icon size={18} />
                  </span>
                  <span>
                    <b>{item.title}</b>
                    <span>{item.text}</span>
                  </span>
                </li>
              );
            })}
          </ul>

          <div className="bzau-chips" aria-hidden="true">
            <span><QrCode size={13} style={{ verticalAlign: "-2px", marginRight: 6 }} />{copy.chips[0]}</span>
            <span><CreditCard size={13} style={{ verticalAlign: "-2px", marginRight: 6 }} />{copy.chips[1]}</span>
            <span>{copy.chips[2]}</span>
            <span>{copy.chips[3]}</span>
          </div>
        </div>
      </aside>

      {/* ── Painel do formulário ── */}
      <div className="bzau-panel">
        <div className="bzau-card">
          <div className="bzau-tabs" role="tablist" aria-label={t(locale, "login")}>
            {tabs.map((tab, i) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  id={`bzau-tab-${tab.id}`}
                  aria-selected={mode === tab.id}
                  aria-controls="bzau-panel"
                  tabIndex={mode === tab.id ? 0 : -1}
                  className="bzau-tab"
                  onClick={() => switchMode(tab.id)}
                  onKeyDown={(e) => handleTabKeys(e, i)}
                >
                  <Icon size={17} aria-hidden="true" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          <div id="bzau-panel" role="tabpanel" aria-labelledby={`bzau-tab-${mode}`}>
            <div className="bzau-head">
              <span className="bzau-eyebrow">{copy.eyebrow[mode]}</span>
              <h2>{heading}</h2>
              <p>{subheading}</p>
            </div>

            {mode === "staff" ? (
              <form className="bzau-form" onSubmit={handleStaffLogin}>
                {errorBlock}
                <label className="bzau-field" htmlFor="bzau-username">
                  <span className="bzau-label">{t(locale, "username")}</span>
                  <span className="bzau-input">
                    <input
                      id="bzau-username"
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      autoComplete="username"
                      required
                    />
                    <User size={18} className="bzau-input-ico" aria-hidden="true" />
                  </span>
                </label>
                <div className="bzau-field">
                  <label className="bzau-label" htmlFor="bzau-password">{t(locale, "password")}</label>
                  <span className="bzau-input has-reveal">
                    <input
                      id="bzau-password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      autoComplete="current-password"
                      required
                    />
                    <Lock size={18} className="bzau-input-ico" aria-hidden="true" />
                    <button
                      type="button"
                      className="bzau-reveal"
                      onClick={() => setShowPassword((v) => !v)}
                      aria-label={showPassword ? copy.hidePassword : copy.showPassword}
                      aria-pressed={showPassword}
                    >
                      {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                    </button>
                  </span>
                </div>
                <button type="submit" className="bzau-btn" disabled={loading} aria-busy={loading}>
                  {loading && <span className="bzau-spin" aria-hidden="true" />}
                  {loading ? t(locale, "entering") : t(locale, "enter")}
                </button>
                <div className="bzau-form-aside">
                  <button
                    type="button"
                    className="bzau-link"
                    onClick={() => { setResetOpen(true); setResetPhone(""); }}
                  >
                    {copy.forgot}
                  </button>
                </div>
              </form>
            ) : otpStep === "phone" ? (
              <form className="bzau-form" onSubmit={handleOtpRequest}>
                {errorBlock}
                {mode === "register" && (
                  <label className="bzau-field" htmlFor="bzau-fullname">
                    <span className="bzau-label">{t(locale, "fullName")}</span>
                    <span className="bzau-input">
                      <input
                        id="bzau-fullname"
                        type="text"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        autoComplete="name"
                        required
                      />
                      <User size={18} className="bzau-input-ico" aria-hidden="true" />
                    </span>
                  </label>
                )}
                <label className="bzau-field" htmlFor="bzau-phone">
                  <span className="bzau-label">{t(locale, "phoneNumber")}</span>
                  <span className="bzau-input">
                    <input
                      id="bzau-phone"
                      type="tel"
                      placeholder="84 / 85 / 86 / 87..."
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      autoComplete="tel"
                      required
                    />
                    <Phone size={18} className="bzau-input-ico" aria-hidden="true" />
                  </span>
                </label>
                <button
                  type="submit"
                  className="bzau-btn"
                  disabled={loading || !phone.trim() || (mode === "register" && !fullName.trim())}
                  aria-busy={loading}
                >
                  {loading && <span className="bzau-spin" aria-hidden="true" />}
                  {loading ? t(locale, "sending") : t(locale, "sendCode")}
                </button>
              </form>
            ) : (
              <div className="bzau-form">
                {errorBlock}
                <p className="bzau-otp-sent">
                  {t(locale, "otpSent")} <strong>{phone}</strong>
                </p>
                <div className="bzau-otp-grid">
                  {otpDigits.map((digit, i) => (
                    <input
                      key={i}
                      ref={(el) => { inputRefs.current[i] = el; }}
                      type="text"
                      inputMode="numeric"
                      maxLength={1}
                      value={digit}
                      onChange={(e) => handleDigitChange(i, e.target.value)}
                      onKeyDown={(e) => handleDigitKeyDown(i, e)}
                      onPaste={handleDigitPaste}
                      autoComplete={i === 0 ? "one-time-code" : "off"}
                      pattern="[0-9]*"
                      aria-label={`${t(locale, "otpCode")} — ${i + 1}`}
                      autoFocus={i === 0}
                    />
                  ))}
                </div>
                {countdown > 0 && (
                  <p className="bzau-otp-timer">
                    {t(locale, "otpExpires")} {Math.floor(countdown / 60)}:{String(countdown % 60).padStart(2, "0")}
                  </p>
                )}
                <button
                  type="button"
                  className="bzau-btn"
                  disabled={loading || otpDigits.some((d) => !d)}
                  aria-busy={loading}
                  onClick={() => void handleOtpVerify()}
                >
                  {loading && <span className="bzau-spin" aria-hidden="true" />}
                  {loading ? t(locale, "verifying") : t(locale, "verifyCode")}
                </button>
                <div className="bzau-otp-actions">
                  <button
                    type="button"
                    className="bzau-link"
                    onClick={() => { setOtpStep("phone"); setError(""); }}
                  >
                    {t(locale, "changePhone")}
                  </button>
                  <button
                    type="button"
                    className="bzau-link"
                    onClick={handleResend}
                    disabled={loading}
                  >
                    {t(locale, "otpResend")}
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="bzau-foot">
            <div className="bzau-lang" role="group" aria-label="PT / EN">
              <button type="button" aria-pressed={locale === "pt"} onClick={() => setLocale("pt")}>PT</button>
              <button type="button" aria-pressed={locale === "en"} onClick={() => setLocale("en")}>EN</button>
            </div>
            <div className="bzau-powered">
              <span>{t(locale, "poweredBy")}</span>
              {branding.powered_by_logo_url ? (
                <img alt="UpDigital" src={branding.powered_by_logo_url} />
              ) : (
                <>
                  <img alt="UpDigital" className="bzau-on-light" src="/assets/up-digital-logo/up_digital_dark.png" />
                  <img alt="UpDigital" className="bzau-on-dark" src="/assets/up-digital-logo/up_digital_light.png" />
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {resetOpen && (
        <>
          <div className="bzau-modal-overlay" onClick={() => !resetBusy && setResetOpen(false)} />
          <div className="bzau-modal">
            <div className="bzau-modal-card" role="dialog" aria-modal="true" aria-labelledby="bzau-reset-title">
              <div className="bzau-modal-head">
                <div>
                  <h3 id="bzau-reset-title">{copy.resetTitle}</h3>
                  <p>{copy.resetLead}</p>
                </div>
                <button
                  type="button"
                  className="bzau-modal-close"
                  disabled={resetBusy}
                  onClick={() => setResetOpen(false)}
                  aria-label={t(locale, "cancel")}
                >
                  <X size={18} />
                </button>
              </div>
              <form className="bzau-form" onSubmit={handlePasswordReset}>
                <label className="bzau-field" htmlFor="bzau-reset-phone">
                  <span className="bzau-label">{t(locale, "phoneNumber")}</span>
                  <span className="bzau-input">
                    <input
                      id="bzau-reset-phone"
                      type="tel"
                      value={resetPhone}
                      onChange={(e) => setResetPhone(e.target.value)}
                      autoComplete="tel"
                      required
                      autoFocus
                    />
                    <Phone size={18} className="bzau-input-ico" aria-hidden="true" />
                  </span>
                </label>
                <div className="bzau-modal-actions">
                  <button className="bzau-btn" disabled={resetBusy || !resetPhone.trim()} type="submit" aria-busy={resetBusy}>
                    {resetBusy && <span className="bzau-spin" aria-hidden="true" />}
                    {resetBusy ? copy.resetBusy : copy.resetSubmit}
                  </button>
                  <button
                    className="bzau-btn bzau-btn-ghost"
                    disabled={resetBusy}
                    onClick={() => setResetOpen(false)}
                    type="button"
                  >
                    {t(locale, "cancel")}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </>
      )}
    </main>
  );
}
