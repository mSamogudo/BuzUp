import { useEffect, useState } from "react";
import { Bell, ChevronDown, LogOut, Moon, Power, Sun, UserCircle2, UserCog, X } from "lucide-react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { apiFetch } from "../lib/api";
import { useAuth } from "../auth/AuthContext";
import { getInitials } from "../lib/format";
import { t } from "../lib/i18n";
import { useUi } from "../ui/UiPreferences";
import ThemeCustomizer from "../themes/ThemeCustomizer";
import { useBranding, pickLogo } from "../lib/branding";
import { NAV_ITEMS, visibleNavItems } from "./navigation";
import { useLayoutBarra } from "../themes/useLayoutBarra";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";

interface MeData { username: string; email: string; phone: string; first_name: string; last_name: string; is_superuser: boolean; roles: { name: string; code: string }[]; capabilities: string[]; }

export default function AdminLayout() {
  return (
    <SidebarProvider className="admin-shell">
      <Casca />
    </SidebarProvider>
  );
}

/** Separado do provider porque precisa de `useSidebar()`, que so existe
 *  dentro dele. */
function Casca() {
  const { logout, token } = useAuth();
  const { locale, setLocale, theme, toggleTheme } = useUi();
  const { branding } = useBranding();
  const location = useLocation();
  const navigate = useNavigate();
  const { state, isMobile, setOpenMobile } = useSidebar();
  const { layout } = useLayoutBarra();
  const recolhida = state === "collapsed" && !isMobile;

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

  // Menu filtrado por capacidades: quem não pode abrir uma área não a vê
  // (o servidor continua a validar com 403 — isto é usabilidade, não segurança).
  const navItems = visibleNavItems(NAV_ITEMS, me?.capabilities ?? [], me?.is_superuser ?? true);

  const active = NAV_ITEMS.find((item) =>
    item.end ? location.pathname === item.path : location.pathname.startsWith(item.path),
  );
  const pageTitle = active ? t(locale, active.i18nKey) : "BusUp";
  const displayName = me ? `${me.first_name} ${me.last_name}`.trim() || me.username : "Admin";
  const roleLabel = me?.roles?.[0]?.name || t(locale, "administration");
  const marcaSrc = recolhida
    ? pickLogo(branding.sidebar_mark_url, "/assets/busup/mark.png")
    : pickLogo(branding.sidebar_logo_url, branding.primary_logo_url, "/assets/busup/logo-dark.png");

  /** No telemóvel a barra é uma gaveta: navegar tem de a fechar. */
  const fecharSeMovel = () => { if (isMobile) setOpenMobile(false); };

  const barra = (
    <Sidebar
        key="barra"
        className="admin-sidebar"
        collapsible={layout.recolha}
        side={layout.lado}
        variant={layout.variante}
      >
        <SidebarHeader className="admin-sidebar-head">
          <div className="admin-sidebar-brand">
            <img alt="BusUp" className={recolhida ? "sidebar-logo-collapsed" : "sidebar-logo"} src={marcaSrc} />
          </div>
        </SidebarHeader>

        <SidebarContent>
          {/* O Sidebar do shadcn nao traz marco de navegacao: e uma div com
              uma ul la dentro. O <nav> nomeado devolve o landmark que a casca
              antiga tinha — quem navega por leitor de ecra salta para ca. */}
          <nav aria-label={t(locale, "portal")}>
          <SidebarMenu className="admin-nav">
            {navItems.map((item) => {
              const Icon = item.icon;
              const itemLabel = t(locale, item.i18nKey);
              const isActive = item.end ? location.pathname === item.path : location.pathname.startsWith(item.path);
              const hasChildren = item.children && item.children.length > 0;
              const isExpanded = expandedMenus.has(item.path)
                || (hasChildren && item.children!.some((c) => location.pathname.startsWith(c.path)));

              if (hasChildren) {
                return (
                  <SidebarMenuItem key={item.path}>
                    <SidebarMenuButton
                      aria-expanded={isExpanded}
                      isActive={isActive}
                      onClick={() => toggleMenu(item.path)}
                      tooltip={itemLabel}
                    >
                      <Icon size={18} />
                      <span>{itemLabel}</span>
                      <ChevronDown className={`nav-chevron${isExpanded ? " nav-chevron-open" : ""}`} size={14} />
                    </SidebarMenuButton>
                    {isExpanded && !recolhida && (
                      <SidebarMenuSub>
                        {item.children!.map((child) => {
                          const ChildIcon = child.icon;
                          const childLabel = t(locale, child.i18nKey);
                          return (
                            <SidebarMenuSubItem key={child.path}>
                              <SidebarMenuSubButton asChild isActive={location.pathname.startsWith(child.path)}>
                                <NavLink onClick={fecharSeMovel} to={child.path}>
                                  <ChildIcon size={15} />
                                  <span>{childLabel}</span>
                                </NavLink>
                              </SidebarMenuSubButton>
                            </SidebarMenuSubItem>
                          );
                        })}
                      </SidebarMenuSub>
                    )}
                  </SidebarMenuItem>
                );
              }

              return (
                <SidebarMenuItem key={item.path}>
                  <SidebarMenuButton asChild isActive={isActive} tooltip={itemLabel}>
                    <NavLink onClick={fecharSeMovel} to={item.path}>
                      <Icon size={18} />
                      <span>{itemLabel}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              );
            })}
          </SidebarMenu>
          </nav>
        </SidebarContent>

        <SidebarFooter className="admin-sidebar-footer">
          <div className="admin-user-tile">
            <div className="admin-user-tile-main">
              <div className="admin-user-identity">
                <div className="admin-avatar">{getInitials(displayName)}</div>
                {!recolhida ? (
                  <div className="admin-user-copy-button">
                    <strong>{displayName}</strong>
                    <small>{roleLabel}</small>
                  </div>
                ) : null}
              </div>
              <button className="admin-power-button" onClick={logout} title={t(locale, "signOut")} type="button">
                <Power size={18} />
              </button>
            </div>
            {!recolhida ? (
              <div className="admin-user-tile-footer">
                <div className="admin-sidebar-signature">
                  <small className="admin-version-label">v0.1.0</small>
                  <div className="admin-powered-by">
                    <span>{t(locale, "poweredBy")}</span>
                    <img alt="UpDigital" className="powered-by-logo" src={pickLogo(branding.powered_by_logo_url, "/assets/up-digital-logo/up_digital_light.png")} />
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </SidebarFooter>
      </Sidebar>
  );

  const principal = (
    <SidebarInset key="principal" className="admin-main">
        <header className="admin-topbar">
          <div className="admin-topbar-left">
            {/* Um so gatilho para as duas coisas: recolhe no desktop, abre a
                gaveta no telemovel. Antes eram dois botoes e dois estados. */}
            <SidebarTrigger className="icon-button" />
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
            <ThemeCustomizer />
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
                    <p style={{ color: "var(--app-text-muted)", fontSize: 13, textAlign: "center", padding: 20 }}>{t(locale, "noNotifications")}</p>
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
                        <UserCog size={14} /> {t(locale, "editProfile")}
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
    </SidebarInset>
  );

  return (
    <>
      {/* A ordem no DOM decide de que lado fica a folga: o Sidebar reserva o
          espaco com uma div irma, e essa div cai onde ele estiver. Com a barra
          a direita mas declarada primeiro, o conteudo ganhava um vazio a
          esquerda e era tapado a direita.
          
          As chaves nao sao decorativas: sem elas o React reconcilia por
          posicao e, ao trocar a ordem, desmonta e remonta as duas subarvores.
          O personalizador vive na barra de topo — perdia o estado e fechava-se
          no exacto momento em que se mexia no layout. */}
      {layout.lado === "right" ? [principal, barra] : [barra, principal]}

      {(profileOpen || notifOpen) && (
        <div style={{ position: "fixed", inset: 0, zIndex: 8998 }} onClick={() => { setProfileOpen(false); setNotifOpen(false); }} />
      )}
    </>
  );
}
