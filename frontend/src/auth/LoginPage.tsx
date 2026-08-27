import { useEffect, useMemo, useRef, useState, type ClipboardEvent, type CSSProperties, type FormEvent, type KeyboardEvent } from "react";
import { AlertCircle, ArrowRight, Bus, CreditCard, Eye, EyeOff, Lock, MapPin, Moon, Phone, QrCode, Route, Shield, Smartphone, Sun, Ticket, User, UserPlus, Wallet, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { apiLogin, apiOtpRequest, apiOtpVerify, apiPublic, apiTwoFactorVerify, isTwoFactor } from "../lib/api";
import { t, type Locale } from "../lib/i18n";
import { mensagemDeErro } from "../lib/errors";
import { showToast } from "../lib/toast";
import { useAuth } from "./AuthContext";
import { useUi } from "../ui/UiPreferences";
import { useBranding, pickLogo } from "../lib/branding";
import "./login.css";

type Mode = "staff" | "otp" | "register";
type OtpStep = "phone" | "code";

/* Microcopy que não existe no dicionário global. Mantém-se aqui porque só esta
   página a usa. */
const COPY: Record<Locale, {
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

/* Ícones esbatidos do fundo — mesmas âncoras, tamanhos e rotações do CondVisit,
   com o vocabulário BusUp (bilhete, QR, carteira, frota). */
const BACKGROUND_ICONS: { Icon: typeof Bus; large: boolean; style: CSSProperties }[] = [
  { Icon: Bus, large: true, style: { left: "8%", top: "12%", "--rot": "-6deg" } as CSSProperties },
  { Icon: Ticket, large: false, style: { left: "22%", top: "30%", "--rot": "6deg" } as CSSProperties },
  { Icon: QrCode, large: true, style: { left: "12%", bottom: "16%", "--rot": "-12deg" } as CSSProperties },
  { Icon: Route, large: false, style: { left: "38%", top: "14%", "--rot": "3deg" } as CSSProperties },
  { Icon: Wallet, large: true, style: { right: "34%", top: "18%", "--rot": "-3deg" } as CSSProperties },
  { Icon: MapPin, large: false, style: { right: "16%", top: "34%", "--rot": "12deg" } as CSSProperties },
  { Icon: CreditCard, large: true, style: { right: "9%", bottom: "14%", "--rot": "-6deg" } as CSSProperties },
  { Icon: Smartphone, large: false, style: { right: "28%", bottom: "20%", "--rot": "6deg" } as CSSProperties },
];

export default function LoginPage() {
  const { locale, setLocale, theme, toggleTheme } = useUi();
  const { login } = useAuth();
  const { branding } = useBranding();
  const navigate = useNavigate();
  const copy = COPY[locale] ?? COPY.pt;

  /* O tema do portal manda, e em tempo real: este ecrã tem o seu próprio
     botão, e ler o armazenamento uma só vez fazia o botão não mudar nada. */

  const [mode, setMode] = useState<Mode>("staff");

  // Staff login state
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  // Desafio do segundo factor. Enquanto existir, o formulário mostra o campo
  // do código em vez do da senha.
  const [desafio, setDesafio] = useState<{ id: string; pista: string } | null>(null);
  const [codigo2fa, setCodigo2fa] = useState("");
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
      showToast("danger", mensagemDeErro(err, locale));
    } finally {
      setResetBusy(false);
    }
  }

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setInterval(() => setCountdown((c) => c - 1), 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  /** Depois de autenticado, encaminha para o painel certo. */
  async function entrar(access: string, refresh: string) {
    login(access, refresh);
    const driverRes = await fetch("/api/driver/trips/", {
      headers: { Authorization: `Bearer ${access}` },
    }).catch(() => null);
    navigate(driverRes?.ok ? "/driver" : "/app", { replace: true });
  }

  async function handleStaffLogin(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const r = await apiLogin(username, password);
      if (isTwoFactor(r)) {
        // Com verificação em dois passos, a senha certa só abre o passo do
        // código — quem só tem a senha não entra.
        setDesafio({ id: r.challenge_id, pista: r.phone_hint });
        setCodigo2fa("");
        return;
      }
      await entrar(r.access, r.refresh);
    } catch (err) {
      setError(err instanceof Error && err.message && !/credenciais/i.test(err.message)
        ? err.message : t(locale, "invalidCredentials"));
    } finally {
      setLoading(false);
    }
  }

  async function handleTwoFactor(e: FormEvent) {
    e.preventDefault();
    if (!desafio) return;
    setError("");
    setLoading(true);
    try {
      const tokens = await apiTwoFactorVerify(desafio.id, codigo2fa.trim());
      await entrar(tokens.access, tokens.refresh);
    } catch (err) {
      setError(mensagemDeErro(err, locale));
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
      setError(mensagemDeErro(err, locale));
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
      setError(mensagemDeErro(err, locale));
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
      setError(mensagemDeErro(err, locale));
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

  const customLogo = pickLogo(branding.auth_logo_url, branding.primary_logo_url);

  const errorBlock = error ? (
    <p className="bzau-error" role="alert">
      <AlertCircle size={16} aria-hidden="true" />
      <span>{error}</span>
    </p>
  ) : null;

  return (
    <main className="bzau" data-theme={theme}>
      {/* ── Fundo: brilho diagonal + ícones esbatidos ── */}
      <div className="bzau-bg" aria-hidden="true">
        <div className="bzau-sheen" />
        {BACKGROUND_ICONS.map(({ Icon, large, style }, i) => (
          <Icon key={i} className={`bzau-bg-ico${large ? " is-lg" : ""}`} style={style} />
        ))}
      </div>

      <div className="bzau-shell">
        <div className="bzau-main">
          <div className="bzau-col">
            {/* ── Cabeçalho centrado ── */}
            <div className="bzau-head">
              {customLogo ? (
                <img alt="" className="bzau-hero-logo" src={customLogo} />
              ) : (
                <>
                  <img alt="" className="bzau-hero-logo bzau-on-light" src="/assets/busup/logo-light.png" />
                  <img alt="" className="bzau-hero-logo bzau-on-dark" src="/assets/busup/logo-dark.png" />
                </>
              )}
              <h1>{heading}</h1>
              <p className="bzau-sub">{subheading}</p>
            </div>

            {/* Idioma e tema por cima dos separadores: e onde a mao ja esta,
                e liberta o topo da pagina para o logotipo respirar. */}
            <div className="bzau-top-controls">
              <div className="bzau-lang" role="group" aria-label="PT / EN">
                <button type="button" aria-pressed={locale === "pt"} onClick={() => setLocale("pt")}>PT</button>
                <button type="button" aria-pressed={locale === "en"} onClick={() => setLocale("en")}>EN</button>
              </div>
              <button
                type="button"
                className="bzau-theme"
                onClick={toggleTheme}
                aria-label={theme === "dark" ? "Mudar para tema claro" : "Mudar para tema escuro"}
                title={theme === "dark" ? "Tema claro" : "Tema escuro"}
              >
                {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
              </button>
            </div>

            {/* ── Cartão do formulário ── */}
            <section className="bzau-card">
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
                      <Icon size={16} aria-hidden="true" />
                      {tab.label}
                    </button>
                  );
                })}
              </div>

              <div id="bzau-panel" role="tabpanel" aria-labelledby={`bzau-tab-${mode}`}>
                <p className="bzau-eyebrow">{copy.eyebrow[mode]}</p>

                {mode === "staff" ? (
                  desafio ? (
                  <form className="bzau-form" onSubmit={handleTwoFactor}>
                    {errorBlock}
                    <p className="bzau-2fa-hint">
                      {t(locale, "otpSentTo")} <strong>{desafio.pista}</strong>.
                    </p>
                    <div className="bzau-field">
                      <label className="bzau-label" htmlFor="bzau-2fa">{t(locale, "verificationCode")}</label>
                      <span className="bzau-input">
                        <input
                          id="bzau-2fa"
                          type="text"
                          inputMode="numeric"
                          autoComplete="one-time-code"
                          maxLength={6}
                          value={codigo2fa}
                          onChange={(e) => setCodigo2fa(e.target.value.replace(/\D/g, ""))}
                          autoFocus
                          required
                        />
                        <Lock size={16} className="bzau-input-ico" aria-hidden="true" />
                      </span>
                    </div>
                    <button type="submit" className="bzau-btn"
                      disabled={loading || codigo2fa.length < 6} aria-busy={loading}>
                      {loading && <span className="bzau-spin" aria-hidden="true" />}
                      {loading ? t(locale, "entering") : t(locale, "enter")}
                      {!loading && <ArrowRight size={16} aria-hidden="true" />}
                    </button>
                    <div className="bzau-actions">
                      <button type="button" className="bzau-btn bzau-btn-ghost"
                        onClick={() => { setDesafio(null); setCodigo2fa(""); setError(""); }}>
                        {t(locale, "back")}
                      </button>
                    </div>
                  </form>
                  ) : (
                  <form className="bzau-form" onSubmit={handleStaffLogin}>
                    {errorBlock}
                    <div className="bzau-field">
                      <label className="bzau-label" htmlFor="bzau-username">{t(locale, "username")}</label>
                      <span className="bzau-input">
                        <input
                          id="bzau-username"
                          type="text"
                          value={username}
                          onChange={(e) => setUsername(e.target.value)}
                          autoComplete="username"
                          required
                        />
                        <User size={16} className="bzau-input-ico" aria-hidden="true" />
                      </span>
                    </div>
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
                        <Lock size={16} className="bzau-input-ico" aria-hidden="true" />
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
                      {!loading && <ArrowRight size={16} aria-hidden="true" />}
                    </button>
                    <div className="bzau-actions">
                      <button
                        type="button"
                        className="bzau-btn bzau-btn-ghost"
                        onClick={() => { setResetOpen(true); setResetPhone(""); }}
                      >
                        {copy.forgot}
                      </button>
                    </div>
                  </form>
                  )
                ) : otpStep === "phone" ? (
                  <form className="bzau-form" onSubmit={handleOtpRequest}>
                    {errorBlock}
                    {mode === "register" && (
                      <div className="bzau-field">
                        <label className="bzau-label" htmlFor="bzau-fullname">{t(locale, "fullName")}</label>
                        <span className="bzau-input">
                          <input
                            id="bzau-fullname"
                            type="text"
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                            autoComplete="name"
                            required
                          />
                          <User size={16} className="bzau-input-ico" aria-hidden="true" />
                        </span>
                      </div>
                    )}
                    <div className="bzau-field">
                      <label className="bzau-label" htmlFor="bzau-phone">{t(locale, "phoneNumber")}</label>
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
                        <Phone size={16} className="bzau-input-ico" aria-hidden="true" />
                      </span>
                    </div>
                    <button
                      type="submit"
                      className="bzau-btn"
                      disabled={loading || !phone.trim() || (mode === "register" && !fullName.trim())}
                      aria-busy={loading}
                    >
                      {loading && <span className="bzau-spin" aria-hidden="true" />}
                      {loading ? t(locale, "sending") : t(locale, "sendCode")}
                      {!loading && <ArrowRight size={16} aria-hidden="true" />}
                    </button>
                  </form>
                ) : (
                  <div className="bzau-form">
                    {errorBlock}
                    <div className="bzau-notice">
                      <p>
                        {t(locale, "otpSent")} <strong>{phone}</strong>
                      </p>
                      {countdown > 0 && (
                        <p>
                          {t(locale, "otpExpires")} {Math.floor(countdown / 60)}:{String(countdown % 60).padStart(2, "0")}
                        </p>
                      )}
                    </div>
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
                    <button
                      type="button"
                      className="bzau-btn"
                      disabled={loading || otpDigits.some((d) => !d)}
                      aria-busy={loading}
                      onClick={() => void handleOtpVerify()}
                    >
                      {loading && <span className="bzau-spin" aria-hidden="true" />}
                      {loading ? t(locale, "verifying") : t(locale, "verifyCode")}
                      {!loading && <ArrowRight size={16} aria-hidden="true" />}
                    </button>
                    <div className="bzau-actions-row">
                      <button
                        type="button"
                        className="bzau-btn bzau-btn-ghost"
                        onClick={() => { setOtpStep("phone"); setError(""); }}
                      >
                        {t(locale, "changePhone")}
                      </button>
                      <button
                        type="button"
                        className="bzau-btn bzau-btn-ghost"
                        onClick={handleResend}
                        disabled={loading}
                      >
                        {t(locale, "otpResend")}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </section>

            {/* ── Rodapé: powered by UpDigital ── */}
            <div className="bzau-foot">
              <p className="bzau-powered">
                <span>{t(locale, "poweredBy")}</span>
                {branding.powered_by_logo_url ? (
                  <img alt="UpDigital" src={branding.powered_by_logo_url} />
                ) : (
                  <>
                    <img alt="UpDigital" className="bzau-on-light" src="/assets/up-digital-logo/up_digital_dark.png" />
                    <img alt="UpDigital" className="bzau-on-dark" src="/assets/up-digital-logo/up_digital_light.png" />
                  </>
                )}
              </p>
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
                <div className="bzau-field">
                  <label className="bzau-label" htmlFor="bzau-reset-phone">{t(locale, "phoneNumber")}</label>
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
                    <Phone size={16} className="bzau-input-ico" aria-hidden="true" />
                  </span>
                </div>
                <div className="bzau-actions-row">
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
