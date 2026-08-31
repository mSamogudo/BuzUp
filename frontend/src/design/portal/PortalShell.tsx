/**
 * Shell do Portal (inventário A0.1 a A0.6).
 *
 * Barra lateral de largura fixa (84 colapsada, 264 expandida — não expande ao
 * passar o rato), cabeçalho fixo com actualização automática, selector de
 * papel, PT/EN, tema, sino e conta, e o conteúdo em `--surface2`.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Bell, LogOut, Menu, Moon, Sun, UserCog, WifiOff, X } from "lucide-react";
import { apiFetch, apiPost } from "../../lib/api";
import { useAuth } from "../../auth/AuthContext";
import { useUi } from "../../ui/UiPreferences";
import { getInitials } from "../../lib/format";
import { IconButton, Logo, LogoMark, Segmented } from "../ui/kit";
import { NAV_ICON, ROLES, visibleGroups, type NavEntry } from "./nav";
import updigitalLight from "../../assets/busup/logo-updigital-dark.png";
import updigitalDark from "../../assets/busup/logo-updigital-white.png";
import "./portal.css";

const ROLE_KEY = "buzup_portal_role";
const SIDEBAR_KEY = "buzup_portal_sidebar";
const AUTO_KEY = "buzup_portal_auto";
const AUTO_SECONDS = 30;

export interface MeData {
  username: string;
  email: string;
  phone: string;
  first_name: string;
  last_name: string;
  is_superuser: boolean;
  roles: { name: string; code: string }[];
  capabilities: string[];
}

interface PortalCtx {
  me: MeData | null;
  /** Sobe de 1 sempre que a actualização automática dispara. */
  tick: number;
  /** Pede uma actualização imediata a quem estiver a ouvir. */
  refresh: () => void;
  /** Papel escolhido no cabeçalho; `null` = todas as capacidades da conta. */
  role: string | null;
  capabilities: string[];
  can: (...caps: string[]) => boolean;
}

const Ctx = createContext<PortalCtx>({
  me: null,
  tick: 0,
  refresh: () => {},
  role: null,
  capabilities: [],
  can: () => true,
});

export function usePortal() {
  return useContext(Ctx);
}

function NavIcon({ name }: { name: string }) {
  const path = NAV_ICON[name] || NAV_ICON.painel;
  return (
    <span className="bzp-navicon">
      <svg
        aria-hidden="true"
        fill="none"
        height="17"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.6"
        viewBox="0 0 24 24"
        width="17"
      >
        <path d={path} />
      </svg>
    </span>
  );
}

interface Notification {
  id: number;
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
}

export default function PortalShell() {
  const { logout, token } = useAuth();
  const { locale, setLocale, theme, toggleTheme } = useUi();
  const location = useLocation();
  const navigate = useNavigate();

  const [me, setMe] = useState<MeData | null>(null);
  const [collapsed, setCollapsed] = useState(() => {
    try {
      const stored = localStorage.getItem(SIDEBAR_KEY);
      if (stored) return stored === "1";
    } catch {
      /* modo privado */
    }
    // Abaixo de 1200 a barra abre colapsada (§12).
    return typeof window !== "undefined" && window.innerWidth < 1200;
  });
  const [drawer, setDrawer] = useState(false);
  const [role, setRole] = useState<string | null>(() => {
    try {
      return localStorage.getItem(ROLE_KEY) || null;
    } catch {
      return null;
    }
  });
  const [auto, setAuto] = useState(() => {
    try {
      return localStorage.getItem(AUTO_KEY) !== "0";
    } catch {
      return true;
    }
  });
  const [tick, setTick] = useState(0);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unread, setUnread] = useState(0);
  const [openPanel, setOpenPanel] = useState<null | "bell" | "account" | "role">(null);
  /* Barra de sem rede (A0.9): o portal continua a mostrar o que já tem, mas
     diz que o que está no ecrã pode estar desactualizado. */
  const [offline, setOffline] = useState(() => typeof navigator !== "undefined" && !navigator.onLine);
  const headerRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const online = () => setOffline(false);
    const gone = () => setOffline(true);
    window.addEventListener("online", online);
    window.addEventListener("offline", gone);
    return () => {
      window.removeEventListener("online", online);
      window.removeEventListener("offline", gone);
    };
  }, []);

  useEffect(() => {
    if (!token) return;
    apiFetch("/api/auth/me/", token)
      .then(setMe)
      .catch(() => undefined);
  }, [token]);

  const loadNotifications = useCallback(() => {
    if (!token) return;
    apiFetch("/api/notifications/", token)
      .then((data: { results: Notification[]; unread_count: number }) => {
        setNotifications(data.results || []);
        setUnread(data.unread_count || 0);
      })
      .catch(() => undefined);
  }, [token]);

  useEffect(loadNotifications, [loadNotifications, tick]);

  // Actualização automática: 30 segundos, como o indicador do cabeçalho diz.
  useEffect(() => {
    if (!auto) return;
    const id = window.setInterval(() => setTick((n) => n + 1), AUTO_SECONDS * 1000);
    return () => window.clearInterval(id);
  }, [auto]);

  useEffect(() => {
    setDrawer(false);
    setOpenPanel(null);
  }, [location.pathname]);

  useEffect(() => {
    if (!openPanel) return;
    const onDown = (e: MouseEvent) => {
      if (!headerRef.current?.contains(e.target as Node)) setOpenPanel(null);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpenPanel(null);
    };
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [openPanel]);

  const setCollapsedPersisted = (value: boolean) => {
    setCollapsed(value);
    try {
      localStorage.setItem(SIDEBAR_KEY, value ? "1" : "0");
    } catch {
      /* modo privado */
    }
  };

  const setRolePersisted = (value: string | null) => {
    setRole(value);
    try {
      if (value) localStorage.setItem(ROLE_KEY, value);
      else localStorage.removeItem(ROLE_KEY);
    } catch {
      /* modo privado */
    }
  };

  const setAutoPersisted = (value: boolean) => {
    setAuto(value);
    try {
      localStorage.setItem(AUTO_KEY, value ? "1" : "0");
    } catch {
      /* modo privado */
    }
  };

  const capabilities = me?.capabilities ?? [];
  const isSuperuser = me?.is_superuser ?? false;

  const groups = useMemo(
    () => visibleGroups({ caps: capabilities, isSuperuser, role }),
    [capabilities, isSuperuser, role],
  );

  const can = useCallback(
    (...caps: string[]) => {
      if (isSuperuser) return true;
      if (!caps.length) return true;
      return caps.some((c) => capabilities.includes(c));
    },
    [capabilities, isSuperuser],
  );

  const ctx = useMemo<PortalCtx>(
    () => ({ me, tick, refresh: () => setTick((n) => n + 1), role, capabilities, can }),
    [me, tick, role, capabilities, can],
  );

  const displayName = me ? `${me.first_name} ${me.last_name}`.trim() || me.username : "—";
  const roleLabel = role
    ? ROLES.find((r) => r.key === role)?.label || role
    : me?.roles?.[0]?.name || (isSuperuser ? "Administração" : "Conta");

  // O selector PT/EN só aparece nos módulos de conteúdo (A0.4).
  const contentModule = location.pathname.startsWith("/app/cms");

  const markRead = async (id: number) => {
    if (!token) return;
    try {
      await apiPost(`/api/notifications/${id}/read/`, token, {});
    } catch {
      /* a lista volta a carregar no próximo ciclo */
    }
    loadNotifications();
  };

  const markAllRead = async () => {
    if (!token) return;
    try {
      await apiPost("/api/notifications/read-all/", token, {});
    } catch {
      /* idem */
    }
    loadNotifications();
  };

  const renderItem = (item: NavEntry) => (
    <NavLink
      className={({ isActive }) => `bzp-navitem${isActive ? " bzp-navitem-active" : ""}`}
      data-tip={item.label}
      end={item.end}
      key={item.key}
      to={item.path}
    >
      <NavIcon name={item.key} />
      {collapsed ? null : <span className="bzp-navlabel">{item.label}</span>}
    </NavLink>
  );

  return (
    <Ctx.Provider value={ctx}>
      <div className={`bzp-shell${collapsed ? " bzp-shell-collapsed" : ""}`}>
        {drawer ? <div className="bzp-scrim" onClick={() => setDrawer(false)} /> : null}

        <aside className={`bzp-side${drawer ? " bzp-side-open" : ""}`}>
          <div className="bzp-side-head">
            {collapsed ? (
              <button
                aria-label="Expandir a barra lateral"
                className="bzp-side-mark"
                onClick={() => setCollapsedPersisted(false)}
                type="button"
              >
                <LogoMark size={30} />
              </button>
            ) : (
              <>
                <NavLink to="/app">
                  <Logo height={24} />
                </NavLink>
                <IconButton
                  bare
                  icon={<span aria-hidden="true">⟨</span>}
                  label="Colapsar a barra lateral"
                  onClick={() => setCollapsedPersisted(true)}
                />
              </>
            )}
          </div>

          <nav className="bzp-nav" data-bz-nav>
            {groups.map((group, i) => (
              <div key={group.label || `g${i}`}>
                {group.label && !collapsed ? <div className="bzp-navgroup">{group.label}</div> : null}
                {group.label && collapsed ? <div className="bzp-navgroup-rule" /> : null}
                {group.items.map(renderItem)}
              </div>
            ))}
          </nav>

          <div className="bzp-usercard">
            <div className="bzp-userrow">
              <span className="bzp-avatar">{getInitials(displayName)}</span>
              {collapsed ? null : (
                <>
                  <span className="bzp-userinfo">
                    <span className="bzp-username">{displayName}</span>
                    <span className="bzp-userrole">{roleLabel}</span>
                  </span>
                  <IconButton bare icon={<LogOut size={16} />} label="Terminar sessão" onClick={logout} />
                </>
              )}
            </div>
            {collapsed ? null : (
              <div className="bzp-signature">
                <span>v0.1.0</span>
                <span aria-hidden="true">·</span>
                <span>powered by</span>
                <img alt="UpDigital" data-logo="light" src={updigitalLight} />
                <img alt="UpDigital" data-logo="dark" src={updigitalDark} />
              </div>
            )}
          </div>
        </aside>

        <div className="bzp-main">
          <header className="bzp-header" ref={headerRef}>
            <IconButton
              bare
              className="bzp-only-mobile"
              icon={<Menu size={18} />}
              label="Abrir a navegação"
              onClick={() => setDrawer(true)}
            />

            <button
              aria-pressed={auto}
              className={`bzp-auto${auto ? "" : " bzp-auto-off"}`}
              onClick={() => setAutoPersisted(!auto)}
              title={auto ? "Actualização automática ligada" : "Actualização automática desligada"}
              type="button"
            >
              <i aria-hidden="true" />
              Auto {AUTO_SECONDS}s
            </button>

            <span className="bzp-header-spacer" />

            <div style={{ position: "relative" }}>
              <button
                aria-expanded={openPanel === "role"}
                className="bzp-auto"
                onClick={() => setOpenPanel(openPanel === "role" ? null : "role")}
                type="button"
              >
                {roleLabel}
              </button>
              {openPanel === "role" ? (
                <div className="bzp-popover" style={{ width: 260 }}>
                  <div className="bzp-popover-head">
                    Papel activo
                    <IconButton bare icon={<X size={15} />} label="Fechar" onClick={() => setOpenPanel(null)} />
                  </div>
                  <div className="bzp-popover-body">
                    <button
                      className="bzp-popover-item"
                      onClick={() => {
                        setRolePersisted(null);
                        setOpenPanel(null);
                      }}
                      type="button"
                    >
                      <strong>Conta completa</strong>
                      <small>Tudo o que as capacidades da conta permitem</small>
                    </button>
                    {ROLES.map((r) => (
                      <button
                        className="bzp-popover-item"
                        key={r.key}
                        onClick={() => {
                          setRolePersisted(r.key);
                          setOpenPanel(null);
                        }}
                        type="button"
                      >
                        <strong>{r.label}</strong>
                        <small>{r.caps}</small>
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>

            {contentModule ? (
              <Segmented
                ariaLabel="Idioma do conteúdo"
                onChange={(v) => setLocale(v as "pt" | "en")}
                options={[
                  ["pt", "PT"],
                  ["en", "EN"],
                ]}
                value={locale === "en" ? "en" : "pt"}
              />
            ) : null}

            <IconButton
              icon={theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
              label={theme === "dark" ? "Tema claro" : "Tema escuro"}
              onClick={toggleTheme}
            />

            <div className="bzp-bellwrap">
              <IconButton
                icon={<Bell size={17} />}
                label="Notificações"
                onClick={() => setOpenPanel(openPanel === "bell" ? null : "bell")}
              />
              {unread > 0 ? <span aria-hidden="true" className="bzp-belldot" /> : null}
              {openPanel === "bell" ? (
                <div className="bzp-popover">
                  <div className="bzp-popover-head">
                    Notificações
                    <IconButton bare icon={<X size={15} />} label="Fechar" onClick={() => setOpenPanel(null)} />
                  </div>
                  <div className="bzp-popover-body">
                    {notifications.length === 0 ? (
                      <p
                        style={{
                          margin: 0,
                          padding: 26,
                          textAlign: "center",
                          font: "400 13px/1.5 var(--font-ui)",
                          color: "var(--muted2)",
                        }}
                      >
                        Sem notificações.
                      </p>
                    ) : (
                      notifications.map((n) => (
                        <button
                          className={`bzp-popover-item${n.read_at ? "" : " bzp-popover-item-unread"}`}
                          key={n.id}
                          onClick={() => markRead(n.id)}
                          type="button"
                        >
                          <strong>{n.title}</strong>
                          <small>{n.body}</small>
                        </button>
                      ))
                    )}
                  </div>
                  {unread > 0 ? (
                    <div className="bzp-popover-foot">
                      <button
                        onClick={markAllRead}
                        style={{
                          border: 0,
                          background: "none",
                          padding: 0,
                          cursor: "pointer",
                          font: "700 12.5px/1 var(--font-ui)",
                          color: "var(--accent-dk)",
                        }}
                        type="button"
                      >
                        Marcar todas como lidas
                      </button>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>

            <div style={{ position: "relative" }}>
              <IconButton
                icon={<span className="bzp-avatar" style={{ width: 26, height: 26, borderRadius: 9, fontSize: 10 }}>{getInitials(displayName)}</span>}
                label="Conta"
                onClick={() => setOpenPanel(openPanel === "account" ? null : "account")}
              />
              {openPanel === "account" ? (
                <div className="bzp-popover" style={{ width: 280 }}>
                  <div className="bzp-popover-head">
                    Conta
                    <IconButton bare icon={<X size={15} />} label="Fechar" onClick={() => setOpenPanel(null)} />
                  </div>
                  <div className="bzp-popover-body">
                    <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: 4 }}>
                      <strong style={{ font: "700 14px/1.3 var(--font-ui)" }}>{displayName}</strong>
                      <span style={{ font: "400 12.5px/1.4 var(--font-ui)", color: "var(--muted2)" }}>
                        {me?.email || "—"}
                      </span>
                      <span style={{ font: "500 11.5px/1.4 var(--font-mono)", color: "var(--faint)" }}>
                        {me?.username}
                      </span>
                    </div>
                    <button className="bzp-popover-item" onClick={() => navigate("/app/settings")} type="button">
                      <strong>
                        <UserCog size={13} style={{ verticalAlign: -2, marginRight: 6 }} />
                        Definições
                      </strong>
                      <small>Perfil, segurança, preferências e notificações</small>
                    </button>
                    <button className="bzp-popover-item" onClick={logout} type="button">
                      <strong style={{ color: "var(--tone-bad-fg)" }}>
                        <LogOut size={13} style={{ verticalAlign: -2, marginRight: 6 }} />
                        Terminar sessão
                      </strong>
                    </button>
                  </div>
                </div>
              ) : null}
            </div>
          </header>

          {offline ? (
            <div className="bz-offline" role="status">
              <WifiOff aria-hidden="true" size={15} />
              Sem ligação. O que está no ecrã pode estar desactualizado; as alterações não são gravadas.
            </div>
          ) : null}

          <main className="bzp-content">
            <Outlet />
          </main>
        </div>
      </div>
    </Ctx.Provider>
  );
}
