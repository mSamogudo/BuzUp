import { useEffect, useRef, useState, type ClipboardEvent, type FormEvent, type KeyboardEvent } from "react";
import { Check, ChevronLeft, Eye, EyeOff, Moon, Phone, RefreshCw, Shield, ShieldCheck, Smartphone, Sun, User, UserPlus, X, Zap } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { apiLogin, apiOtpRequest, apiOtpVerify, apiPublic } from "../lib/api";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "./AuthContext";
import { useUi } from "../ui/UiPreferences";

type Mode = "staff" | "otp" | "register";
type OtpStep = "phone" | "code";

export default function LoginPage() {
  const { locale, setLocale, theme, toggleTheme } = useUi();
  const { login } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState<Mode>("staff");

  // Staff login state
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  // delight: a "tap" ripple keyed per press so the NFC motif echoes on the primary CTA
  const [tapKey, setTapKey] = useState(0);
  const [otpShake, setOtpShake] = useState(false);
  const [verified, setVerified] = useState(false);
  const fireTap = () => setTapKey((k) => k + 1);

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

  function handleResetKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === "Escape" && !resetBusy) {
      setResetOpen(false);
      return;
    }
    if (e.key !== "Tab") return;
    const focusables = e.currentTarget.querySelectorAll<HTMLElement>("button:not([disabled]), input:not([disabled])");
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
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
      const route = res.agent_id ? "/agent" : res.driver_id ? "/driver" : "/portal";
      // guaranteed success beat: let the "Confirmado" state land even on a fast connection
      setVerified(true);
      await new Promise((r) => setTimeout(r, 420));
      login(res.access, res.refresh);
      navigate(route, { replace: true });
      return;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Código inválido.");
      setOtpDigits(["", "", "", "", "", ""]);
      setOtpShake(true);
      setTimeout(() => setOtpShake(false), 420);
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
    setVerified(false);
  }

  const eyebrow =
    mode === "staff" ? t(locale, "loginEyebrowStaff") : mode === "register" ? t(locale, "loginEyebrowRegister") : t(locale, "loginEyebrow");
  const heading =
    mode === "staff" ? t(locale, "welcomeBack") : mode === "register" ? t(locale, "createPassengerAccount") : t(locale, "welcomePassenger");
  const subtitle =
    mode === "staff" ? t(locale, "loginSubtitle") : mode === "register" ? t(locale, "passengerRegisterSubtitle") : t(locale, "otpSubtitle");

  return (
    <main className="lgn">
      {/* top bar */}
      <div className="lgn-top">
        <a href="/" className="lgn-brand" aria-label="BusUp">
          <img className="lgn-brand-img lgn-brand-light" src="/assets/buzup-logo/buzup-logo-dark.png" alt="BusUp" />
          <img className="lgn-brand-img lgn-brand-dark" src="/assets/buzup-logo/buzup-logo.png" alt="BusUp" />
        </a>
        <div className="lgn-top-tools">
          <a href="/" className="lgn-backlink" aria-label={t(locale, "backToSite")}>
            <ChevronLeft size={16} />
            <span className="lgn-backlink-txt">{t(locale, "backToSite")}</span>
          </a>
          <button
            type="button"
            className="lgn-ttbtn"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Tema claro" : "Tema escuro"}
            title="Tema"
          >
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <div className="lgn-langtog" role="group" aria-label="Idioma / Language">
            <button className={locale === "pt" ? "lgn-lang-active" : ""} onClick={() => setLocale("pt")} type="button">PT</button>
            <button className={locale === "en" ? "lgn-lang-active" : ""} onClick={() => setLocale("en")} type="button">EN</button>
          </div>
        </div>
      </div>

      {/* LEFT: form */}
      <section className="lgn-auth">
        <div className="lgn-auth-inner">
          <div className="lgn-modes" role="group" aria-label="Tipo de acesso">
            <button type="button" className={`lgn-mode${mode === "staff" ? " lgn-mode-active" : ""}`} onClick={() => switchMode("staff")}>
              <Shield size={15} />{t(locale, "modeStaff")}
            </button>
            <button type="button" className={`lgn-mode${mode === "otp" ? " lgn-mode-active" : ""}`} onClick={() => switchMode("otp")}>
              <Smartphone size={15} />{t(locale, "modePassenger")}
            </button>
            <button type="button" className={`lgn-mode${mode === "register" ? " lgn-mode-active" : ""}`} onClick={() => switchMode("register")}>
              <UserPlus size={15} />{t(locale, "modeRegister")}
            </button>
          </div>

          <span className="lgn-eyebrow">{eyebrow}</span>
          <h1>{heading}</h1>
          <p className="lgn-sub">{subtitle}</p>

          {mode === "staff" ? (
            <form className="lgn-form" onSubmit={handleStaffLogin} noValidate>
              {error && <div className="lgn-error" role="alert">{error}</div>}
              <div className="lgn-field">
                <label htmlFor="lgn-username">{t(locale, "username")}</label>
                <input
                  id="lgn-username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  required
                />
              </div>
              <div className="lgn-field lgn-pass">
                <label htmlFor="lgn-password">{t(locale, "password")}</label>
                <div className="lgn-input-wrap">
                  <input
                    id="lgn-password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    autoComplete="current-password"
                    required
                  />
                  <button
                    type="button"
                    className="lgn-pass-toggle"
                    onClick={() => setShowPassword((s) => !s)}
                    aria-label={t(locale, showPassword ? "hidePassword" : "showPassword")}
                    aria-pressed={showPassword}
                  >
                    {showPassword ? <EyeOff size={19} /> : <Eye size={19} />}
                  </button>
                </div>
                <button type="button" className="lgn-inline-link lgn-forgot" onClick={() => { setResetOpen(true); setResetPhone(""); }}>
                  {t(locale, "forgotPassword")}
                </button>
              </div>
              <button type="submit" className={`lgn-btn lgn-submit${loading ? " lgn-loading" : ""}`} disabled={loading} onPointerDown={fireTap}>
                <span className="lgn-btn-label">{t(locale, "enter")}</span>
                <span className="lgn-spin" aria-hidden="true" />
                {tapKey > 0 && <span key={tapKey} className="lgn-tap-ripple" aria-hidden="true" />}
              </button>
              <p className="lgn-signup">
                {t(locale, "noAccountYet")}{" "}
                <button type="button" className="lgn-inline-link lgn-strong" onClick={() => switchMode("register")}>{t(locale, "createAccountLink")}</button>
              </p>
              <div className="lgn-assure">
                <ShieldCheck size={15} />
                {t(locale, "secureEncrypted")}
              </div>
            </form>
          ) : otpStep === "phone" ? (
            <form className="lgn-form" onSubmit={handleOtpRequest} noValidate>
              {error && <div className="lgn-error" role="alert">{error}</div>}
              {mode === "register" && (
                <div className="lgn-field">
                  <label htmlFor="lgn-fullname">{t(locale, "fullName")}</label>
                  <input
                    id="lgn-fullname"
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    autoComplete="name"
                    required
                  />
                </div>
              )}
              <div className="lgn-field">
                <label htmlFor="lgn-phone">{t(locale, "phoneNumber")}</label>
                <input
                  id="lgn-phone"
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="84 / 85 / 86 / 87..."
                  autoComplete="tel"
                  required
                />
              </div>
              <button
                type="submit"
                className={`lgn-btn lgn-submit${loading ? " lgn-loading" : ""}`}
                disabled={loading || !phone.trim() || (mode === "register" && !fullName.trim())}
                onPointerDown={fireTap}
              >
                <span className="lgn-btn-label">{t(locale, "sendCode")}</span>
                <span className="lgn-spin" aria-hidden="true" />
                {tapKey > 0 && <span key={tapKey} className="lgn-tap-ripple" aria-hidden="true" />}
              </button>
              <p className="lgn-signup">
                {mode === "register" ? t(locale, "haveAccountAlready") : t(locale, "noAccountYet")}{" "}
                <button
                  type="button"
                  className="lgn-inline-link lgn-strong"
                  onClick={() => switchMode(mode === "register" ? "otp" : "register")}
                >
                  {mode === "register" ? t(locale, "signInLink") : t(locale, "createAccountLink")}
                </button>
              </p>
              <div className="lgn-assure">
                <ShieldCheck size={15} />
                {t(locale, "secureEncrypted")}
              </div>
            </form>
          ) : (
            <div className="lgn-form">
              {error && <div className="lgn-error" role="alert">{error}</div>}
              <p className="lgn-otp-sent">
                {t(locale, "otpSent")} <strong>{phone}</strong>
              </p>
              <span className="lgn-sr-only" aria-live="polite">
                {verified ? t(locale, "otpVerified") : loading ? t(locale, "verifying") : ""}
              </span>
              <div className={`lgn-otp-grid${loading ? " lgn-otp-verifying" : ""}${verified ? " lgn-otp-done" : ""}${otpShake ? " lgn-otp-shake" : ""}`}>
                {otpDigits.map((digit, i) => (
                  <input
                    key={i}
                    ref={(el) => { inputRefs.current[i] = el; }}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    className={`lgn-otp-digit${digit ? " lgn-otp-filled" : ""}`}
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
              {verified ? (
                <p className="lgn-otp-confirmed"><Check size={16} />{t(locale, "otpVerified")}</p>
              ) : countdown > 0 ? (
                <p className="lgn-otp-timer">
                  {t(locale, "otpExpires")} {Math.floor(countdown / 60)}:{String(countdown % 60).padStart(2, "0")}
                </p>
              ) : null}
              <button
                type="button"
                className={`lgn-btn lgn-submit${loading ? " lgn-loading" : ""}`}
                disabled={loading || otpDigits.some((d) => !d)}
                onClick={() => void handleOtpVerify()}
                onPointerDown={fireTap}
              >
                <span className="lgn-btn-label">{t(locale, "verifyCode")}</span>
                <span className="lgn-spin" aria-hidden="true" />
                {tapKey > 0 && <span key={tapKey} className="lgn-tap-ripple" aria-hidden="true" />}
              </button>
              <div className="lgn-otp-actions">
                <button type="button" className="lgn-inline-link" onClick={() => { setOtpStep("phone"); setError(""); }}>
                  {t(locale, "changePhone")}
                </button>
                <button type="button" className="lgn-inline-link" onClick={handleResend} disabled={loading}>
                  {t(locale, "otpResend")}
                </button>
              </div>
            </div>
          )}

          <div className="lgn-powered">
            <span>{t(locale, "poweredBy")}</span>
            <img alt="UpDigital" src="/assets/up-digital-logo/up_digital_dark.png" className="lgn-powered-logo lgn-powered-light" />
            <img alt="UpDigital" src="/assets/up-digital-logo/up_digital_light.png" className="lgn-powered-logo lgn-powered-dark" />
          </div>
        </div>
      </section>

      {/* RIGHT: brand panel */}
      <aside className="lgn-brandside">
        <div className="lgn-rings" aria-hidden="true"><span /><span /><span /><span /></div>
        <div className="lgn-bs-inner">
          <span className="lgn-eyebrow lgn-eyebrow-blue">{t(locale, "brandsideEyebrow")}</span>
          <h2>{t(locale, "brandsideTitle")}</h2>
          <p className="lgn-lead">{t(locale, "brandsideLead")}</p>
          <ul className="lgn-tpoints">
            <li className="lgn-tpoint">
              <span className="lgn-tpoint-ic"><Zap size={20} /></span>
              <span className="lgn-tpoint-txt"><b>{t(locale, "tp1Title")}</b><span>{t(locale, "tp1Sub")}</span></span>
            </li>
            <li className="lgn-tpoint">
              <span className="lgn-tpoint-ic"><RefreshCw size={20} /></span>
              <span className="lgn-tpoint-txt"><b>{t(locale, "tp2Title")}</b><span>{t(locale, "tp2Sub")}</span></span>
            </li>
            <li className="lgn-tpoint">
              <span className="lgn-tpoint-ic"><ShieldCheck size={20} /></span>
              <span className="lgn-tpoint-txt"><b>{t(locale, "tp3Title")}</b><span>{t(locale, "tp3Sub")}</span></span>
            </li>
          </ul>
        </div>
      </aside>

      {resetOpen && (
        <>
          <div className="admin-modal-overlay" onClick={() => !resetBusy && setResetOpen(false)} />
          <div className="admin-modal-shell" role="dialog" aria-modal="true" aria-labelledby="lgn-reset-title" onKeyDown={handleResetKeyDown}>
            <div className="admin-modal-card">
              <div className="admin-modal-head">
                <div>
                  <h3 id="lgn-reset-title">Reposição de senha</h3>
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
