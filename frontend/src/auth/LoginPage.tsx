import { useEffect, useRef, useState, type ClipboardEvent, type FormEvent, type KeyboardEvent } from "react";
import { Lock, Phone, Shield, Smartphone, User, UserPlus, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { apiLogin, apiOtpRequest, apiOtpVerify, apiPublic } from "../lib/api";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "./AuthContext";
import { useUi } from "../ui/UiPreferences";

type Mode = "staff" | "otp" | "register";
type OtpStep = "phone" | "code";

export default function LoginPage() {
  const { locale, setLocale } = useUi();
  const { login } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState<Mode>("staff");

  // Staff login state
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
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
      showToast("success", "Se o telefone estiver associado, receberá uma SMS com a nova senha.");
      setResetOpen(false);
      setResetPhone("");
    } catch (err) {
      showToast("danger", err instanceof Error ? err.message : "Erro ao solicitar reposição.");
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
      setError(err instanceof Error ? err.message : "Código inválido.");
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

  return (
    <main className="login-page">
      <div className="login-left">
        <div className="login-left-content">
          <img alt="BuzUp" className="login-hero-logo" src="/assets/buzup-logo/buzup-logo.png" />
          <h1>BuzUp</h1>
          <p>{t(locale, "cashlessTransport")}</p>
        </div>
      </div>
      <div className="login-right">
        <div className="login-form-wrap">
          {/* Mode Toggle */}
          <div className="login-mode-toggle">
            <button
              type="button"
              className={`login-mode-btn${mode === "staff" ? " login-mode-btn-active" : ""}`}
              onClick={() => switchMode("staff")}
            >
              <Shield size={16} />
              {t(locale, "staffLogin")}
            </button>
            <button
              type="button"
              className={`login-mode-btn${mode === "otp" ? " login-mode-btn-active" : ""}`}
              onClick={() => switchMode("otp")}
            >
              <Smartphone size={16} />
              {t(locale, "otpLogin")}
            </button>
            <button
              type="button"
              className={`login-mode-btn${mode === "register" ? " login-mode-btn-active" : ""}`}
              onClick={() => switchMode("register")}
            >
              <UserPlus size={16} />
              {t(locale, "registerPassenger")}
            </button>
          </div>

          {mode === "staff" ? (
            <>
              <div className="login-form-header">
                <h2>{t(locale, "login")}</h2>
                <p>{t(locale, "loginSubtitle")}</p>
              </div>
              <form className="login-form" onSubmit={handleStaffLogin}>
                {error && <div className="login-error" role="alert">{error}</div>}
                <label className="login-field">
                  <User size={18} className="login-field-icon" />
                  <input type="text" aria-label={t(locale, "username")} placeholder={t(locale, "username")} value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
                </label>
                <label className="login-field">
                  <Lock size={18} className="login-field-icon" />
                  <input type="password" aria-label={t(locale, "password")} placeholder={t(locale, "password")} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
                </label>
                <button type="submit" className="login-submit" disabled={loading}>
                  {loading ? t(locale, "entering") : t(locale, "enter")}
                </button>
                <div style={{ textAlign: "center", marginTop: 8 }}>
                  <button
                    type="button"
                    className="otp-link-btn"
                    onClick={() => { setResetOpen(true); setResetPhone(""); }}
                  >
                    Esqueci a senha
                  </button>
                </div>
              </form>
            </>
          ) : (
            <>
              <div className="login-form-header">
                <h2>{mode === "register" ? t(locale, "createPassengerAccount") : t(locale, "welcomePassenger")}</h2>
                <p>{mode === "register" ? t(locale, "passengerRegisterSubtitle") : t(locale, "otpSubtitle")}</p>
              </div>

              {otpStep === "phone" ? (
                <form className="login-form" onSubmit={handleOtpRequest}>
                  {error && <div className="login-error" role="alert">{error}</div>}
                  {mode === "register" && (
                    <label className="login-field">
                      <User size={18} className="login-field-icon" />
                      <input
                        type="text"
                        aria-label={t(locale, "fullName")}
                        placeholder={t(locale, "fullName")}
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        autoComplete="name"
                        required
                      />
                    </label>
                  )}
                  <label className="login-field">
                    <Phone size={18} className="login-field-icon" />
                    <input
                      type="tel"
                      aria-label={t(locale, "phoneNumber")}
                      placeholder={t(locale, "phoneNumber") + " (84/85/86/87...)"}
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      autoComplete="tel"
                      required
                    />
                  </label>
                  <button type="submit" className="login-submit" disabled={loading || !phone.trim() || (mode === "register" && !fullName.trim())}>
                    {loading ? t(locale, "sending") : t(locale, "sendCode")}
                  </button>
                </form>
              ) : (
                <div className="login-form">
                  {error && <div className="login-error" role="alert">{error}</div>}
                  <p className="otp-sent-label">
                    {t(locale, "otpSent")} <strong>{phone}</strong>
                  </p>
                  <div className="otp-code-grid">
                    {otpDigits.map((digit, i) => (
                      <input
                        key={i}
                        ref={(el) => { inputRefs.current[i] = el; }}
                        type="text"
                        inputMode="numeric"
                        maxLength={1}
                        className="otp-digit"
                        value={digit}
                        onChange={(e) => handleDigitChange(i, e.target.value)}
                        onKeyDown={(e) => handleDigitKeyDown(i, e)}
                        onPaste={handleDigitPaste}
                        autoComplete={i === 0 ? "one-time-code" : "off"}
                        pattern="[0-9]*"
                        aria-label={`${t(locale, "otpCode")} ${i + 1}`}
                        autoFocus={i === 0}
                      />
                    ))}
                  </div>
                  {countdown > 0 && (
                    <p className="otp-timer">
                      {t(locale, "otpExpires")} {Math.floor(countdown / 60)}:{String(countdown % 60).padStart(2, "0")}
                    </p>
                  )}
                  <button
                    type="button"
                    className="login-submit"
                    disabled={loading || otpDigits.some((d) => !d)}
                    onClick={() => void handleOtpVerify()}
                  >
                    {loading ? t(locale, "verifying") : t(locale, "verifyCode")}
                  </button>
                  <div className="otp-actions">
                    <button
                      type="button"
                      className="otp-link-btn"
                      onClick={() => { setOtpStep("phone"); setError(""); }}
                    >
                      {t(locale, "changePhone")}
                    </button>
                    <button
                      type="button"
                      className="otp-link-btn"
                      onClick={handleResend}
                      disabled={loading}
                    >
                      {t(locale, "otpResend")}
                    </button>
                  </div>
                </div>
              )}
            </>
          )}

          <div className="login-footer">
            <div className="locale-flag-toggle" role="group">
              <button className={`locale-flag-button${locale === "pt" ? " locale-flag-button-active" : ""}`} onClick={() => setLocale("pt")} type="button">PT</button>
              <button className={`locale-flag-button${locale === "en" ? " locale-flag-button-active" : ""}`} onClick={() => setLocale("en")} type="button">EN</button>
            </div>
            <div className="login-powered">
              <span>{t(locale, "poweredBy")}</span>
              <img alt="UpDigital" src="/assets/up-digital-logo/up_digital_dark.png" className="login-powered-logo login-powered-logo-light" />
              <img alt="UpDigital" src="/assets/up-digital-logo/up_digital_light.png" className="login-powered-logo login-powered-logo-dark" />
            </div>
          </div>
        </div>
      </div>

      {resetOpen && (
        <>
          <div className="admin-modal-overlay" onClick={() => !resetBusy && setResetOpen(false)} />
          <div className="admin-modal-shell" role="dialog" aria-modal="true" aria-label="Reposição de senha">
            <div className="admin-modal-card">
              <div className="admin-modal-head">
                <div>
                  <h3>Reposição de senha</h3>
                  <p>Indique o telefone associado à sua conta.</p>
                </div>
                <button className="icon-button" disabled={resetBusy} onClick={() => setResetOpen(false)} type="button"><X size={18} /></button>
              </div>
              <div className="admin-modal-body">
                <form className="admin-form" onSubmit={handlePasswordReset}>
                  <label className="login-field">
                    <Phone size={18} className="login-field-icon" />
                    <input
                      type="tel"
                      aria-label={t(locale, "phoneNumber")}
                      placeholder={t(locale, "phoneNumber")}
                      value={resetPhone}
                      onChange={(e) => setResetPhone(e.target.value)}
                      autoComplete="tel"
                      required
                      autoFocus
                    />
                  </label>
                  <div className="admin-form-actions" style={{ marginTop: 16 }}>
                    <button className="primary-button" disabled={resetBusy || !resetPhone.trim()} type="submit">
                      {resetBusy ? "A enviar..." : "Enviar"}
                    </button>
                    <button className="secondary-button" disabled={resetBusy} onClick={() => setResetOpen(false)} type="button">
                      {t(locale, "cancel")}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </>
      )}
    </main>
  );
}
