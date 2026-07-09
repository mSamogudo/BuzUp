import { useEffect, useState } from "react";
import { Bell, ChevronDown, ChevronLeft, ChevronRight, LogOut, Menu, Moon, Power, Sun, UserCircle2, UserCog, X } from "lucide-react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { apiFetch } from "../lib/api";
import { useAuth } from "../auth/AuthContext";
import { getInitials } from "../lib/format";
import { t } from "../lib/i18n";
import { useUi } from "../ui/UiPreferences";
import { StatusBadge } from "../ui/common";
import { NAV_ITEMS } from "./navigation";

interface MeData { username: string; email: string; phone: string; first_name: string; last_name: string; is_superuser: boolean; roles: { name: string; code: string }[]; capabilities: string[]; }

export default function AdminLayout() {
  const { logout, token } = useAuth();
  const { locale, setLocale, theme, toggleTheme } = useUi();
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [expandedMenus, setExpandedMenus] = useState<Set<string>>(new Set());
  const [me, setMe] = useState<MeData | null>(null);

  const toggleMenu = (path: string) => {
    setExpandedMenus((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  useEffect(() => {
    if (token) apiFetch("/api/auth/me/", token).then(setMe).catch(() => {});
  }, [token]);

  const active = NAV_ITEMS.find((item) =>
    item.end ? location.pathname === item.path : location.pathname.startsWith(item.path),
  );
  const pageTitle = active ? t(locale, active.i18nKey) : "BusUp";
  const displayName = me ? `${me.first_name} ${me.last_name}`.trim() || me.username : "Admin";
  const roleLabel = me?.roles?.[0]?.name || t(locale, "administration");
  const sidebarBrandSrc = collapsed ? "/assets/buzup-logo/buzup-mark.png" : "/assets/buzup-logo/buzup-logo.png";

  return (
    <div className="admin-shell">
      <aside className={`admin-sidebar${collapsed ? " admin-sidebar-collapsed" : ""}`}>
        <div className="admin-sidebar-head">
          <div className="admin-sidebar-brand">
            <img alt="BusUp" className={collapsed ? "sidebar-logo-collapsed" : "sidebar-logo"} src={sidebarBrandSrc} />
          </div>
          {!collapsed && (
            <button className="icon-button desktop-only sidebar-collapse-btn" onClick={() => setCollapsed((c) => !c)} type="button">
              <ChevronLeft size={16} />
            </button>
          )}
          {collapsed && (
            <button className="icon-button desktop-only sidebar-expand-btn" onClick={() => setCollapsed((c) => !c)} type="button">
              <ChevronRight size={16} />
            </button>
          )}
        </div>

        <nav className="admin-nav">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const itemLabel = t(locale, item.i18nKey);
            const isActive = item.end ? location.pathname === item.path : location.pathname.startsWith(item.path);
            const hasChildren = item.children && item.children.length > 0;
            const isExpanded = expandedMenus.has(item.path) || (hasChildren && item.children!.some((c) => location.pathname.startsWith(c.path)));

            if (hasChildren) {
              return (
                <div key={item.path} className="admin-nav-group">
                  <button
                    aria-label={itemLabel}
                    className={`admin-nav-item admin-nav-parent${isExpanded ? " admin-nav-parent-open" : ""}`}
                    data-tooltip={collapsed ? itemLabel : undefined}
                    onClick={() => toggleMenu(item.path)}
                    title={collapsed ? itemLabel : undefined}
                    type="button"
                  >
                    <Icon size={18} />
                    {!collapsed ? <><span>{itemLabel}</span><ChevronDown size={14} className={`nav-chevron${isExpanded ? " nav-chevron-open" : ""}`} /></> : null}
                  </button>
                  {isExpanded && !collapsed && (
                    <div className="admin-nav-children">
                      {item.children!.map((child) => {
                        const ChildIcon = child.icon;
                        const childLabel = t(locale, child.i18nKey);
                        const childActive = location.pathname.startsWith(child.path);
                        return (
                          <NavLink
                            aria-label={childLabel}
                            className={`admin-nav-item admin-nav-child${childActive ? " admin-nav-item-active" : ""}`}
                            key={child.path}
                            title={childLabel}
                            to={child.path}
                          >
                            <ChildIcon size={15} />
                            <span>{childLabel}</span>
                          </NavLink>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            }

            return (
              <NavLink
                aria-label={itemLabel}
                className={`admin-nav-item${isActive ? " admin-nav-item-active" : ""}`}
                data-tooltip={collapsed ? itemLabel : undefined}
                key={item.path}
                title={collapsed ? itemLabel : undefined}
                to={item.path}
              >
                <Icon size={18} />
                {!collapsed ? <span>{itemLabel}</span> : null}
              </NavLink>
            );
          })}
        </nav>

        <div className="admin-sidebar-footer">
          <div className="admin-user-tile">
            <div className="admin-user-tile-main">
              <div className="admin-user-identity">
                <div className="admin-avatar">{getInitials(displayName)}</div>
                {!collapsed ? (
                  <div className="admin-user-copy-button">
                    <strong>{displayName}</strong>
                    <small>{roleLabel}</small>
                  </div>
                ) : null}
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                <button className="admin-power-button" onClick={logout} title={t(locale, "signOut")} type="button">
                  <Power size={18} />
                </button>
              </div>
            </div>
            {!collapsed ? (
              <div className="admin-user-tile-footer">
                <div className="admin-sidebar-signature">
                  <small className="admin-version-label">v0.1.0</small>
                  <div className="admin-powered-by">
                    <span>{t(locale, "poweredBy")}</span>
                    <img alt="UpDigital" className="powered-by-logo" src="/assets/up-digital-logo/up_digital_light.png" />
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </aside>

      <div className={`admin-main${collapsed ? " admin-main-collapsed" : ""}`}>
        <header className={`admin-topbar${collapsed ? " admin-topbar-collapsed" : ""}`}>
          <div className="admin-topbar-left">
            <button className="icon-button mobile-only" onClick={() => setMobileOpen(true)} type="button">
              <Menu size={18} />
            </button>
            <div>
              <div className="admin-breadcrumbs">
                <span>{t(locale, "portal")}</span>
                <span>{pageTitle}</span>
              </div>
              <h1>{pageTitle}</h1>
            </div>
          </div>
          <div className="admin-topbar-right">
            <div className="locale-flag-toggle" role="group">
              <button className={`locale-flag-button${locale === "pt" ? " locale-flag-button-active" : ""}`} onClick={() => setLocale("pt")} type="button">PT</button>
              <button className={`locale-flag-button${locale === "en" ? " locale-flag-button-active" : ""}`} onClick={() => setLocale("en")} type="button">EN</button>
            </div>
            <button className="icon-button" onClick={toggleTheme} title={theme === "dark" ? t(locale, "lightMode") : t(locale, "darkMode")} type="button">
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <div style={{ position: "relative" }}>
              <button className="icon-button" onClick={() => { setNotifOpen(!notifOpen); setProfileOpen(false); }} title={t(locale, "notifications")} type="button">
                <Bell size={16} />
              </button>
              {notifOpen && (
                <div className="topbar-popover">
                  <div className="topbar-popover-head">
                    <strong>{t(locale, "notifications")}</strong>
                    <button className="icon-button" onClick={() => setNotifOpen(false)} type="button"><X size={14} /></button>
                  </div>
                  <div className="topbar-popover-body">
                    <p style={{ color: "var(--app-text-muted)", fontSize: 13, textAlign: "center", padding: 20 }}>Sem notificacoes.</p>
                  </div>
                </div>
              )}
            </div>
            <div style={{ position: "relative" }}>
              <button className="icon-button" onClick={() => { setProfileOpen(!profileOpen); setNotifOpen(false); }} title={t(locale, "profile")} type="button">
                <UserCircle2 size={16} />
              </button>
              {profileOpen && me && (
                <div className="topbar-popover topbar-popover-profile">
                  <div className="topbar-popover-head">
                    <strong>{t(locale, "profile")}</strong>
                    <button className="icon-button" onClick={() => setProfileOpen(false)} type="button"><X size={14} /></button>
                  </div>
                  <div className="topbar-popover-body">
                    <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                      <div className="admin-avatar" style={{ width: 44, height: 44, fontSize: 16 }}>{getInitials(displayName)}</div>
                      <div>
                        <strong style={{ fontSize: 14 }}>{displayName}</strong>
                        <div style={{ fontSize: 12, color: "var(--app-text-muted)" }}>{me.email}</div>
                        <div style={{ fontSize: 11, color: "var(--app-text-muted)" }}>{roleLabel}</div>
                      </div>
                    </div>
                    <div className="detail-fields" style={{ fontSize: 12 }}>
                      <div className="detail-field"><dt>{t(locale, "username")}</dt><dd>{me.username}</dd></div>
                      <div className="detail-field"><dt>{t(locale, "phone")}</dt><dd>{me.phone || "-"}</dd></div>
                      <div className="detail-field"><dt>{t(locale, "status")}</dt><dd>{roleLabel}</dd></div>
                    </div>
                    <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                      <button
                        className="secondary-button"
                        onClick={() => { setProfileOpen(false); navigate("/profile"); }}
                        type="button"
                        style={{ flex: 1, fontSize: 12 }}
                      >
                        <UserCog size={14} /> Editar perfil
                      </button>
                      <button className="danger-button" onClick={logout} type="button" style={{ flex: 1, fontSize: 12 }}>
                        <LogOut size={14} /> {t(locale, "signOut")}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        <main className="admin-content">
          <div className="admin-content-inner">
            <Outlet />
          </div>
        </main>
      </div>

      {(profileOpen || notifOpen) && <div style={{ position: "fixed", inset: 0, zIndex: 8998 }} onClick={() => { setProfileOpen(false); setNotifOpen(false); }} />}

      <div className={`admin-mobile-overlay${mobileOpen ? " admin-mobile-overlay-open" : ""}`} onClick={() => setMobileOpen(false)} />
      <aside className={`admin-mobile-drawer${mobileOpen ? " admin-mobile-drawer-open" : ""}`}>
        <div className="admin-mobile-head">
          <div>
            <p className="admin-kicker">BusUp</p>
            <strong>{t(locale, "cashlessTransport")}</strong>
          </div>
          <button className="icon-button" onClick={() => setMobileOpen(false)} type="button"><X size={18} /></button>
        </div>
        <nav className="admin-mobile-nav-grid">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = item.end ? location.pathname === item.path : location.pathname.startsWith(item.path);
            return (
              <NavLink className={`admin-mobile-nav-item${isActive ? " admin-mobile-nav-item-active" : ""}`} key={item.path} onClick={() => setMobileOpen(false)} to={item.path}>
                <Icon size={18} />
                <span>{t(locale, item.i18nKey)}</span>
              </NavLink>
            );
          })}
        </nav>
        <div className="admin-mobile-footer">
          <div className="admin-powered-by">
            <span>{t(locale, "poweredBy")}</span>
            <strong>UpDigital</strong>
          </div>
          <button className="admin-power-button" onClick={logout} type="button"><Power size={18} /></button>
        </div>
      </aside>
    </div>
  );
}
