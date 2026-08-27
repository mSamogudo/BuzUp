import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, KeyRound, LogOut, Save, UserCircle2 } from "lucide-react";
import { apiFetch, apiPatch } from "../lib/api";
import { getInitials } from "../lib/format";
import { t } from "../lib/i18n";
import { mensagemDeErro } from "../lib/errors";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";

interface MeData {
  username: string;
  email: string;
  phone: string;
  first_name: string;
  last_name: string;
  is_superuser: boolean;
  roles: { name: string; code: string }[];
}

export default function ProfilePage() {
  const { token, logout } = useAuth();
  const { locale } = useUi();
  const navigate = useNavigate();
  const [me, setMe] = useState<MeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", phone: "" });
  const [pwd, setPwd] = useState({ current_password: "", new_password: "", confirm_password: "" });

  useEffect(() => {
    if (!token) return;
    let active = true;
    apiFetch("/api/auth/me/", token)
      .then((data) => {
        if (!active) return;
        setMe(data);
        setForm({
          first_name: data.first_name || "",
          last_name: data.last_name || "",
          email: data.email || "",
          phone: data.phone || "",
        });
      })
      .catch((err) => {
        if (active) showToast("danger", mensagemDeErro(err, locale));
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  async function submitProfile(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSavingProfile(true);
    try {
      const updated = await apiPatch("/api/auth/me/profile/", token, form);
      setMe((prev) => prev ? { ...prev, ...updated } : updated);
      showToast("success", t(locale, "okProfileSaved"));
    } catch (err) {
      showToast("danger", mensagemDeErro(err, locale));
    } finally {
      setSavingProfile(false);
    }
  }

  async function submitPassword(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    if (!pwd.current_password || !pwd.new_password) {
      showToast("danger", t(locale, "errPasswordFields"));
      return;
    }
    if (pwd.new_password !== pwd.confirm_password) {
      showToast("danger", t(locale, "errPasswordMismatch"));
      return;
    }
    if (pwd.new_password.length < 8) {
      showToast("danger", t(locale, "errPasswordShort"));
      return;
    }
    setSavingPassword(true);
    try {
      await apiPatch("/api/auth/me/profile/", token, {
        current_password: pwd.current_password,
        new_password: pwd.new_password,
      });
      showToast("success", t(locale, "okPasswordChanged"));
      setPwd({ current_password: "", new_password: "", confirm_password: "" });
    } catch (err) {
      showToast("danger", mensagemDeErro(err, locale));
    } finally {
      setSavingPassword(false);
    }
  }

  const displayName = me ? `${me.first_name} ${me.last_name}`.trim() || me.username : "";
  const roleLabel = me?.roles?.[0]?.name || (me?.is_superuser ? "Super Admin" : "");

  return (
    <main className="profile-page" style={{ minHeight: "100vh", background: "var(--app-bg)" }}>
      <header style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "16px 24px", borderBottom: "1px solid var(--app-border)",
        background: "var(--app-surface)",
      }}>
        <button className="icon-text-button" onClick={() => navigate(-1)} type="button">
          <ArrowLeft size={16} /><span>{t(locale, "back")}</span>
        </button>
        <h2 style={{ margin: 0, fontSize: 18 }}>{t(locale, "profile")}</h2>
        <button className="danger-button" onClick={handleLogout} type="button">
          <LogOut size={14} /> {t(locale, "signOut")}
        </button>
      </header>

      <div style={{ maxWidth: 720, margin: "0 auto", padding: "24px 16px", display: "flex", flexDirection: "column", gap: 16 }}>
        {loading ? (
          <p style={{ textAlign: "center", color: "var(--app-text-muted)" }}>{t(locale, "loading")}</p>
        ) : !me ? (
          <p style={{ textAlign: "center", color: "var(--app-text-muted)" }}>{t(locale, "noData")}</p>
        ) : (
          <>
            <section className="admin-section">
              <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "8px 4px 16px" }}>
                <div className="admin-avatar" style={{ width: 56, height: 56, fontSize: 20 }}>
                  {getInitials(displayName) || <UserCircle2 size={28} />}
                </div>
                <div>
                  <strong style={{ fontSize: 16 }}>{displayName}</strong>
                  <div style={{ fontSize: 13, color: "var(--app-text-muted)" }}>{me.email}</div>
                  {roleLabel ? <div style={{ fontSize: 12, color: "var(--app-text-muted)" }}>{roleLabel}</div> : null}
                </div>
              </div>

              <div className="admin-section-head">
                <div>
                  <h3>{t(locale, "personalDetails")}</h3>
                </div>
              </div>
              <form className="admin-form" onSubmit={submitProfile}>
                <div className="admin-form-grid">
                  <label className="field">
                    <span>{t(locale, "name")}</span>
                    <input value={form.first_name} onChange={(e) => setForm((p) => ({ ...p, first_name: e.target.value }))} />
                  </label>
                  <label className="field">
                    <span>{t(locale, "lastName")}</span>
                    <input value={form.last_name} onChange={(e) => setForm((p) => ({ ...p, last_name: e.target.value }))} />
                  </label>
                  <label className="field">
                    <span>{t(locale, "email")}</span>
                    <input type="email" value={form.email} onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))} />
                  </label>
                  <label className="field">
                    <span>{t(locale, "phone")}</span>
                    <input value={form.phone} onChange={(e) => setForm((p) => ({ ...p, phone: e.target.value }))} />
                  </label>
                </div>
                <div className="admin-form-actions">
                  <button className="primary-button" disabled={savingProfile} type="submit">
                    <Save size={14} /> {savingProfile ? t(locale, "saving") : t(locale, "save")}
                  </button>
                </div>
              </form>
            </section>

            <section className="admin-section">
              <div className="admin-section-head">
                <div>
                  <h3>{t(locale, "changePassword")}</h3>
                  <p>{t(locale, "newPasswordHint")}</p>
                </div>
              </div>
              <form className="admin-form" onSubmit={submitPassword}>
                <div className="admin-form-grid">
                  <label className="field admin-field-span-full">
                    <span>{t(locale, "currentPassword")}</span>
                    <input type="password" value={pwd.current_password} onChange={(e) => setPwd((p) => ({ ...p, current_password: e.target.value }))} autoComplete="current-password" />
                  </label>
                  <label className="field">
                    <span>{t(locale, "newPassword")}</span>
                    <input type="password" minLength={8} value={pwd.new_password} onChange={(e) => setPwd((p) => ({ ...p, new_password: e.target.value }))} autoComplete="new-password" />
                  </label>
                  <label className="field">
                    <span>{t(locale, "confirmNewPassword")}</span>
                    <input type="password" minLength={8} value={pwd.confirm_password} onChange={(e) => setPwd((p) => ({ ...p, confirm_password: e.target.value }))} autoComplete="new-password" />
                  </label>
                </div>
                <div className="admin-form-actions">
                  <button className="primary-button" disabled={savingPassword} type="submit">
                    <KeyRound size={14} /> {savingPassword ? t(locale, "saving") : t(locale, "changePassword")}
                  </button>
                </div>
              </form>
            </section>
          </>
        )}
      </div>
    </main>
  );
}
