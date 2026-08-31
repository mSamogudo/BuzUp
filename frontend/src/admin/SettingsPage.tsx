/**
 * Portal A1.25 — Definições.
 *
 * Quatro separadores: perfil, segurança (senha e verificação em dois passos),
 * preferências (idioma e tema) e notificações.
 */
import { useCallback, useEffect, useState } from "react";
import { Save } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { apiFetch, apiPatch, apiPost } from "../lib/api";
import { showToast } from "../lib/toast";
import { formatDateTime } from "../lib/format";
import { useUi } from "../ui/UiPreferences";
import {
  Button,
  Card,
  Field,
  IconButton,
  InlineError,
  Input,
  PageHeader,
  Pill,
  Segmented,
  Switch,
  Tabs,
  TableSkeleton,
} from "../design/ui";

type Tab = "perfil" | "seguranca" | "preferencias" | "notificacoes";

interface Me {
  id: number;
  username: string;
  email: string;
  phone: string;
  first_name: string;
  last_name: string;
  is_superuser: boolean;
  is_2fa_enabled: boolean;
  last_login: string | null;
  roles: { name: string; code: string }[];
  capabilities: string[];
}

const NOTIFY_KEY = "buzup_portal_notify";

export default function SettingsPage() {
  const { token } = useAuth();
  const { locale, setLocale, theme, themeChoice, setTheme } = useUi();
  const [tab, setTab] = useState<Tab>("perfil");
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [profile, setProfile] = useState({ first_name: "", last_name: "", email: "" });
  const [passwords, setPasswords] = useState({ old_password: "", new_password: "", confirm: "" });
  const [twoFactor, setTwoFactor] = useState({ password: "", pending: false });
  const [notify, setNotify] = useState<Record<string, boolean>>(() => {
    try {
      return JSON.parse(localStorage.getItem(NOTIFY_KEY) || "{}");
    } catch {
      return {};
    }
  });

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    apiFetch("/api/auth/me/", token)
      .then((data: Me) => {
        setMe(data);
        setProfile({ first_name: data.first_name, last_name: data.last_name, email: data.email });
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(load, [load]);

  const saveProfile = async () => {
    if (!token) return;
    setSaving(true);
    setError(null);
    try {
      const data: Me = await apiPatch("/api/auth/me/profile/", token, profile);
      setMe(data);
      showToast("success", "Perfil actualizado.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const changePassword = async () => {
    if (!token) return;
    if (passwords.new_password !== passwords.confirm) {
      setError("A confirmação não coincide com a nova senha.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await apiPost("/api/auth/change-password/", token, {
        old_password: passwords.old_password,
        new_password: passwords.new_password,
      });
      setPasswords({ old_password: "", new_password: "", confirm: "" });
      showToast("success", "Senha actualizada.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const toggleTwoFactor = async (enabled: boolean) => {
    if (!token || !me) return;
    if (!twoFactor.password) {
      setTwoFactor({ password: "", pending: true });
      setError("Escreva a senha actual para alterar a verificação em dois passos.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await apiPost("/api/auth/me/2fa/", token, { enabled, current_password: twoFactor.password });
      setMe({ ...me, is_2fa_enabled: enabled });
      setTwoFactor({ password: "", pending: false });
      showToast("success", enabled ? "Verificação em dois passos ligada." : "Verificação em dois passos desligada.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const setNotifyKey = (key: string, value: boolean) => {
    const next = { ...notify, [key]: value };
    setNotify(next);
    try {
      localStorage.setItem(NOTIFY_KEY, JSON.stringify(next));
    } catch {
      /* modo privado */
    }
  };

  if (loading) {
    return (
      <div className="bz-page">
        <PageHeader crumbs={["Sistema", "Definições"]} title="Definições" />
        <TableSkeleton cols={2} rows={4} />
      </div>
    );
  }

  return (
    <div className="bz-page">
      <PageHeader
        crumbs={["Sistema", "Definições"]}
        description="Dados da conta, segurança, idioma e tema, e o que quer receber."
        title="Definições"
      />

      {error ? <InlineError>{error}</InlineError> : null}

      <Tabs
        onChange={setTab}
        options={[
          ["perfil", "Perfil"],
          ["seguranca", "Segurança"],
          ["preferencias", "Preferências"],
          ["notificacoes", "Notificações"],
        ]}
        value={tab}
      />

      {tab === "perfil" ? (
        <Card large>
          <div className="bz-formgrid">
            <Field label="Nome">
              <Input onChange={(e) => setProfile({ ...profile, first_name: e.target.value })} value={profile.first_name} />
            </Field>
            <Field label="Apelido">
              <Input onChange={(e) => setProfile({ ...profile, last_name: e.target.value })} value={profile.last_name} />
            </Field>
            <Field label="Email">
              <Input onChange={(e) => setProfile({ ...profile, email: e.target.value })} type="email" value={profile.email} />
            </Field>
            <Field
              hint="O telefone é a identidade da conta em toda a plataforma; a alteração passa pelo suporte."
              label="Telefone"
            >
              <Input disabled mono readOnly value={me?.phone || "—"} />
            </Field>
            <Field label="Utilizador">
              <Input disabled mono readOnly value={me?.username || ""} />
            </Field>
            <Field label="Papéis">
              <div style={{ display: "flex", gap: 8, alignItems: "center", height: 44, flexWrap: "wrap" }}>
                {me?.is_superuser ? <Pill tone="info">Administração</Pill> : null}
                {(me?.roles || []).map((role) => (
                  <Pill key={role.code} tone="mute">
                    {role.name}
                  </Pill>
                ))}
              </div>
            </Field>
          </div>
          <div style={{ marginTop: 18 }}>
            <Button icon={<Save size={16} />} loading={saving} onClick={saveProfile}>
              Guardar alterações
            </Button>
          </div>
        </Card>
      ) : null}

      {tab === "seguranca" ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 16 }}>
          <Card large>
            <h2 className="bz-page-title" style={{ fontSize: 18, marginBottom: 14 }}>
              Alterar senha
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <Field label="Senha actual" required>
                <Input
                  autoComplete="current-password"
                  onChange={(e) => setPasswords({ ...passwords, old_password: e.target.value })}
                  type="password"
                  value={passwords.old_password}
                />
              </Field>
              <Field hint="Mínimo de 8 caracteres." label="Nova senha" required>
                <Input
                  autoComplete="new-password"
                  onChange={(e) => setPasswords({ ...passwords, new_password: e.target.value })}
                  type="password"
                  value={passwords.new_password}
                />
              </Field>
              <Field label="Confirmar nova senha" required>
                <Input
                  autoComplete="new-password"
                  onChange={(e) => setPasswords({ ...passwords, confirm: e.target.value })}
                  type="password"
                  value={passwords.confirm}
                />
              </Field>
              <div>
                <Button
                  disabled={!passwords.old_password || passwords.new_password.length < 8}
                  loading={saving}
                  onClick={changePassword}
                >
                  Alterar senha
                </Button>
              </div>
            </div>
          </Card>

          <Card large>
            <h2 className="bz-page-title" style={{ fontSize: 18, marginBottom: 14 }}>
              Verificação em dois passos
            </h2>
            <p className="bz-page-desc" style={{ marginBottom: 14 }}>
              Com a verificação ligada, entrar no portal exige um código enviado por SMS além da senha.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <Field label="Senha actual" required>
                <Input
                  autoComplete="current-password"
                  onChange={(e) => setTwoFactor({ ...twoFactor, password: e.target.value })}
                  type="password"
                  value={twoFactor.password}
                />
              </Field>
              <Switch
                checked={Boolean(me?.is_2fa_enabled)}
                /* Desligar é decisão de superadministrador: a conta nasce com a
                   verificação ligada porque abre tarifas, cartões e receita. */
                disabled={Boolean(me?.is_2fa_enabled) && !me?.is_superuser}
                label={me?.is_2fa_enabled ? "Ligada" : "Desligada"}
                onChange={(v) => toggleTwoFactor(v)}
              />
              {me?.is_2fa_enabled && !me?.is_superuser ? (
                <span className="bz-field-hint">
                  Só um superadministrador pode desligar a verificação em dois passos.
                </span>
              ) : null}
              <span className="bz-field-hint">
                Último acesso: {me?.last_login ? formatDateTime(me.last_login) : "—"}
              </span>
            </div>
          </Card>
        </div>
      ) : null}

      {tab === "preferencias" ? (
        <Card large>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <Field hint="O portal é em português; o CMS e o site público têm PT e EN." label="Idioma">
              <Segmented
                ariaLabel="Idioma"
                onChange={(v) => setLocale(v as "pt" | "en")}
                options={[
                  ["pt", "Português"],
                  ["en", "English"],
                ]}
                value={locale === "en" ? "en" : "pt"}
              />
            </Field>
            <Field hint={`Neste momento: ${theme === "dark" ? "escuro" : "claro"}.`} label="Tema">
              <Segmented
                ariaLabel="Tema"
                onChange={(v) => setTheme(v === "system" ? null : (v as "light" | "dark"))}
                options={[
                  ["light", "Claro"],
                  ["dark", "Escuro"],
                  ["system", "Sistema"],
                ]}
                value={themeChoice ?? "system"}
              />
            </Field>
          </div>
        </Card>
      ) : null}

      {tab === "notificacoes" ? (
        <Card large>
          <p className="bz-page-desc" style={{ marginBottom: 18 }}>
            O que quer ver no sino do portal. A escolha é deste dispositivo.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {[
              ["payment", "Pagamentos confirmados e falhados"],
              ["trip", "Alterações de viagem"],
              ["card", "Cartões e carteiras"],
              ["system", "Avisos do sistema"],
            ].map(([key, label]) => (
              <Switch
                checked={notify[key] !== false}
                key={key}
                label={label}
                onChange={(v) => setNotifyKey(key, v)}
              />
            ))}
          </div>
        </Card>
      ) : null}
    </div>
  );
}
