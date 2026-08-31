import { useCallback, useState, type FormEvent } from "react";
import { Eye, KeyRound, Pencil, Plus, Power, RefreshCw, Trash2 } from "lucide-react";
import { apiFetch, apiPost, apiPatch, apiDelete } from "../lib/api";
import { t, type Locale, type TranslationKey } from "../lib/i18n";
import { mensagemDeErro } from "../lib/errors";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { AdminModal, DataTable, PageFrame, SectionCard, StatusBadge, TabBar, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";
import { useConfirm } from "../ui/ConfirmDialog";

interface UserRecord { id: number; uuid: string; username: string; email: string; phone: string; first_name: string; last_name: string; is_active: boolean; roles: { id: number; role_id: number; role_name: string; role_code: string }[]; created_at: string; }
interface RoleRecord { id: number; uuid: string; name: string; code: string; permissions: string[]; description: string; is_system: boolean; }

// A etiqueta nasce do proprio codigo da permissao: "routes.manage" le-se
// "Rotas: Gerir". Antes eram 34 etiquetas escritas a mao, so em portugues —
// e cada permissao nova no backend chegava aqui sem nome nenhum.
const AREAS: Record<string, TranslationKey> = {
  passengers: "passengers", wallets: "wallets", cards: "cards", routes: "routes",
  stops: "stops", trips: "trips", fares: "fares", vehicles: "vehicles",
  drivers: "drivers", devices: "devices", payments: "payments",
  validations: "validations", reports: "reports", reconciliation: "reconciliation",
  audit: "audit", users: "users", roles: "permRoles", packages: "packages",
  imports: "permImports", pos: "pos",
};
const ACCOES: Record<string, TranslationKey> = {
  read: "permView", manage: "permManage", operate: "permOperate",
};
const PERMISSOES = [
  "passengers.read", "passengers.manage", "wallets.read", "wallets.manage",
  "cards.read", "cards.manage", "routes.read", "routes.manage",
  "stops.read", "stops.manage", "trips.read", "trips.manage",
  "fares.read", "fares.manage", "vehicles.read", "vehicles.manage",
  "drivers.read", "drivers.manage", "devices.read", "devices.manage",
  "payments.read", "payments.manage", "validations.read", "reports.read",
  "reconciliation.read", "audit.read", "users.read", "users.manage",
  "roles.read", "roles.manage", "packages.read", "packages.manage",
  "imports.manage", "pos.operate",
];
const permissoes = (lc: Locale) => PERMISSOES.map((key) => {
  const [area, accao] = key.split(".");
  const nome = AREAS[area] ? t(lc, AREAS[area]) : area;
  return { key, label: `${nome}: ${ACCOES[accao] ? t(lc, ACCOES[accao]) : accao}` };
});

function UsersTab() {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const { confirm, dialog: confirmDialog } = useConfirm();
  const loader = useCallback(() => apiFetch("/api/admin/users/", token!).then((d) => d.results || d), [token]);
  const rolesLoader = useCallback(() => apiFetch("/api/admin/roles/", token!).then((d) => d.results || d), [token]);
  const { data: rows, loading, reload } = useAsyncData<UserRecord[]>(loader, [token]);
  const { data: roleOpts } = useAsyncData<RoleRecord[]>(rolesLoader, [token]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [viewing, setViewing] = useState<UserRecord | null>(null);
  const [form, setForm] = useState({ username: "", email: "", phone: "", first_name: "", last_name: "", password: "", is_active: true, role_ids: [] as number[] });
  const f = (k: string, v: string | boolean) => setForm((p) => ({ ...p, [k]: v }));
  const reset = () => {
    setEditId(null);
    setModalOpen(false);
    setForm({ username: "", email: "", phone: "", first_name: "", last_name: "", password: "", is_active: true, role_ids: [] });
  };

  const openEdit = (user: UserRecord) => {
    setEditId(user.id);
    setForm({
      username: user.username,
      email: user.email,
      phone: user.phone || "",
      first_name: user.first_name || "",
      last_name: user.last_name || "",
      password: "",
      is_active: user.is_active,
      role_ids: user.roles.map((role) => role.role_id),
    });
    setModalOpen(true);
  };

  const toggleRole = (roleId: number) => {
    setForm((prev) => ({
      ...prev,
      role_ids: prev.role_ids.includes(roleId)
        ? prev.role_ids.filter((id) => id !== roleId)
        : [...prev.role_ids, roleId],
    }));
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true);
    const payload = { ...form };
    if (editId && !payload.password) delete (payload as Partial<typeof payload>).password;
    try {
      if (editId) await apiPatch(`/api/admin/users/${editId}/`, token!, payload);
      else await apiPost("/api/admin/users/", token!, payload);
      showToast("success", editId ? t(lc, "okUserUpdated") : t(lc, "okUserCreated")); reset(); reload();
    }
    catch (err) { showToast("danger", mensagemDeErro(err, lc)); }
    finally { setBusy(false); }
  };

  const handleResetPassword = async (user: UserRecord) => {
    const ok = await confirm({
      title: t(lc, "resetPassword"),
      message: t(lc, "confirmResetPassword", { n: user.username }),
      confirmLabel: "Repor",
    });
    if (!ok) return;
    try {
      const res = await apiPost(`/api/admin/users/${user.id}/reset-password/`, token!, {});
      showToast("success", (res && res.detail) || t(lc, "okPasswordReset"));
    } catch (err) {
      showToast("danger", mensagemDeErro(err, lc));
    }
  };

  const handleToggleActive = async (user: UserRecord) => {
    const ok = await confirm({
      title: user.is_active ? "Desactivar utilizador" : "Activar utilizador",
      message: t(lc, "confirmToggle", { a: user.is_active ? t(lc, "deactivate") : t(lc, "activate"), n: user.username }),
      tone: user.is_active ? "danger" : "default",
      confirmLabel: user.is_active ? "Desactivar" : "Activar",
    });
    if (!ok) return;
    try {
      await apiPost(`/api/admin/users/${user.id}/toggle-active/`, token!, {});
      showToast("success", user.is_active ? t(lc, "okUserDeactivated") : t(lc, "okUserActivated"));
      reload();
    } catch (err) {
      showToast("danger", mensagemDeErro(err, lc));
    }
  };

  return (
    <SectionCard title={t(lc, "users")}>
      <div className="admin-toolbar"><div className="admin-toolbar-spacer" />
        <button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={15} /><span>{t(lc, "refresh")}</span></button>
        <button className="primary-button" onClick={() => { reset(); setModalOpen(true); }} type="button"><Plus size={15} /> {t(lc, "create")}</button>
      </div>
      <DataTable columns={[
        { header: t(lc, "name"), sortKey: "username", render: (r: UserRecord) => <TablePrimaryCell title={`${r.first_name} ${r.last_name}`.trim() || r.username} subtitle={r.email} /> },
        { header: t(lc, "status"), render: (r: UserRecord) => <StatusBadge value={r.is_active ? "active" : "inactive"} /> },
        { header: t(lc, "actions"), className: "table-actions-cell", render: (r: UserRecord) => (
          <div className="admin-inline-actions">
            <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => setViewing(r)} />
            <TableActionButton icon={<Pencil size={15} />} label={t(lc, "edit")} onClick={() => openEdit(r)} />
            <TableActionButton icon={<KeyRound size={15} />} label={t(lc, "resetPassword")} onClick={() => void handleResetPassword(r)} />
            <TableActionButton icon={<Power size={15} />} label={r.is_active ? "Desactivar" : "Activar"} onClick={() => void handleToggleActive(r)} tone={r.is_active ? "danger" : "default"} />
          </div>
        )},
      ]} rows={rows || []} rowKey={(r) => r.uuid} loading={loading} emptyMessage={t(lc, "noData")} />

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing ? `${viewing.first_name} ${viewing.last_name}`.trim() || viewing.username : ""} fields={viewing ? [
        { label: t(lc, "username"), value: viewing.username },
        { label: t(lc, "email"), value: viewing.email },
        { label: t(lc, "phone"), value: viewing.phone || "-" },
        { label: t(lc, "status"), value: <StatusBadge value={viewing.is_active ? "active" : "inactive"} /> },
        { label: t(lc, "roles"), value: viewing.roles.map((r) => r.role_name).join(", ") || "-" },
      ] : []} />

      <AdminModal open={modalOpen} onClose={reset} title={editId ? t(lc, "edit") : t(lc, "create")}>
        <form className="admin-form" onSubmit={submit}>
          <div className="admin-form-grid">
            <label className="field"><span>{t(lc, "username")}</span><input required value={form.username} onChange={(e) => f("username", e.target.value)} /></label>
            <label className="field"><span>{t(lc, "email")}</span><input required type="email" value={form.email} onChange={(e) => f("email", e.target.value)} /></label>
            <label className="field"><span>{t(lc, "name")}</span><input value={form.first_name} onChange={(e) => f("first_name", e.target.value)} /></label>
            <label className="field"><span>{t(lc, "lastName")}</span><input value={form.last_name} onChange={(e) => f("last_name", e.target.value)} /></label>
            <label className="field"><span>{t(lc, "phone")}</span><input value={form.phone} onChange={(e) => f("phone", e.target.value)} /></label>
            <label className="field"><span>{t(lc, "status")}</span><select value={form.is_active ? "active" : "inactive"} onChange={(e) => f("is_active", e.target.value === "active")}><option value="active">{t(lc, "active")}</option><option value="inactive">{t(lc, "inactive")}</option></select></label>
            <label className="field"><span>{t(lc, "password")}</span><input required={!editId} type="password" minLength={8} placeholder={editId ? "Deixar vazio para manter" : ""} value={form.password} onChange={(e) => f("password", e.target.value)} /></label>
          </div>
          <div style={{ margin: "12px 0 8px" }}>
            <strong style={{ fontSize: 13 }}>Roles ({form.role_ids.length})</strong>
          </div>
          <div className="perm-grid">
            {(roleOpts || []).map((role) => (
              <label key={role.id} className="perm-check">
                <input type="checkbox" checked={form.role_ids.includes(role.id)} onChange={() => toggleRole(role.id)} />
                <span>{role.name}</span>
              </label>
            ))}
          </div>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy} type="submit">{busy ? t(lc, "saving") : editId ? t(lc, "update") : t(lc, "create")}</button>
            <button className="secondary-button" onClick={reset} type="button">{t(lc, "cancel")}</button>
          </div>
        </form>
      </AdminModal>
      {confirmDialog}
    </SectionCard>
  );
}

function RolesTab() {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const loader = useCallback(() => apiFetch("/api/admin/roles/", token!).then((d) => d.results || d), [token]);
  const { data: rows, loading, reload } = useAsyncData<RoleRecord[]>(loader, [token]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [viewing, setViewing] = useState<RoleRecord | null>(null);
  const [formName, setFormName] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [selectedPerms, setSelectedPerms] = useState<Set<string>>(new Set());

  const reset = () => { setEditId(null); setModalOpen(false); setFormName(""); setFormDesc(""); setSelectedPerms(new Set()); };

  const togglePerm = (key: string) => {
    setSelectedPerms((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const selectAll = () => setSelectedPerms(new Set(permissoes(lc).map((p) => p.key)));
  const clearAll = () => setSelectedPerms(new Set());

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true);
    const payload = { name: formName, description: formDesc, permissions: Array.from(selectedPerms) };
    try {
      if (editId) await apiPatch(`/api/admin/roles/${editId}/`, token!, payload);
      else await apiPost("/api/admin/roles/", token!, payload);
      showToast("success", editId ? t(lc, "okRoleUpdated") : t(lc, "okRoleCreated")); reset(); reload();
    } catch (err) { showToast("danger", mensagemDeErro(err, lc)); }
    finally { setBusy(false); }
  };

  return (
    <SectionCard title={t(lc, "roles")}>
      <div className="admin-toolbar"><div className="admin-toolbar-spacer" />
        <button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={15} /><span>{t(lc, "refresh")}</span></button>
        <button className="primary-button" onClick={() => { reset(); setModalOpen(true); }} type="button"><Plus size={15} /> {t(lc, "create")}</button>
      </div>
      <DataTable columns={[
        { header: t(lc, "name"), sortKey: "name", render: (r: RoleRecord) => <TablePrimaryCell title={r.name} subtitle={r.code} /> },
        { header: t(lc, "permissions"), render: (r: RoleRecord) => `${r.permissions.includes("*") ? t(lc, "allRoutes") : r.permissions.length}` },
        { header: t(lc, "actions"), className: "table-actions-cell", render: (r: RoleRecord) => (
          <div className="admin-inline-actions">
            <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => setViewing(r)} />
            <TableActionButton icon={<Pencil size={15} />} label={t(lc, "edit")} onClick={() => { setEditId(r.id); setFormName(r.name); setFormDesc(r.description); setSelectedPerms(new Set(r.permissions)); setModalOpen(true); }} />
            {!r.is_system && <TableActionButton icon={<Trash2 size={15} />} label={t(lc, "delete")} onClick={async () => { if (!confirm(t(lc, "confirmDelete", { n: r.name }))) return; try { await apiDelete(`/api/admin/roles/${r.id}/`, token!); showToast("success", t(lc, "okRoleDeleted")); reload(); } catch (err) { showToast("danger", mensagemDeErro(err, lc)); } }} tone="danger" />}
          </div>
        )},
      ]} rows={rows || []} rowKey={(r) => r.uuid} loading={loading} emptyMessage={t(lc, "noData")} />

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing?.name || ""} fields={viewing ? [
        { label: t(lc, "name"), value: viewing.name },
        { label: t(lc, "code"), value: viewing.code },
        { label: t(lc, "description"), value: viewing.description || "-" },
        { label: t(lc, "permissions"), value: viewing.permissions.includes("*") ? "Todas (Super Admin)" : viewing.permissions.join(", ") },
      ] : []} />

      <AdminModal open={modalOpen} onClose={reset} title={editId ? t(lc, "edit") + " Role" : "Nova Role"}>
        <form className="admin-form" onSubmit={submit}>
          <div className="admin-form-grid">
            <label className="field admin-field-span-full"><span>{t(lc, "name")}</span><input required value={formName} onChange={(e) => setFormName(e.target.value)} placeholder={t(lc, "egRoleName")} /></label>
            <label className="field admin-field-span-full"><span>{t(lc, "description")}</span><textarea value={formDesc} onChange={(e) => setFormDesc(e.target.value)} /></label>
          </div>
          <div style={{ margin: "12px 0 8px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <strong style={{ fontSize: 13 }}>Permissoes ({selectedPerms.size})</strong>
            <div style={{ display: "flex", gap: 8 }}>
              <button type="button" className="secondary-button" style={{ fontSize: 11, padding: "3px 10px" }} onClick={selectAll}>{t(lc, "allRoutes")}</button>
              <button type="button" className="secondary-button" style={{ fontSize: 11, padding: "3px 10px" }} onClick={clearAll}>{t(lc, "clear")}</button>
            </div>
          </div>
          <div className="perm-grid">
            {permissoes(lc).map((p) => (
              <label key={p.key} className="perm-check">
                <input type="checkbox" checked={selectedPerms.has(p.key)} onChange={() => togglePerm(p.key)} />
                <span>{p.label}</span>
              </label>
            ))}
          </div>
          <div className="admin-form-actions" style={{ marginTop: 16 }}>
            <button className="primary-button" disabled={busy} type="submit">{busy ? t(lc, "saving") : editId ? t(lc, "update") : t(lc, "create")}</button>
            <button className="secondary-button" onClick={reset} type="button">{t(lc, "cancel")}</button>
          </div>
        </form>
      </AdminModal>
    </SectionCard>
  );
}

export default function UsersPage() {
  const { locale: lc } = useUi();
  const [tab, setTab] = useState("users");

  return (
    <PageFrame kicker={t(lc, "management")} title={t(lc, "users")}>
      <TabBar items={[
        { key: "users", label: t(lc, "users") },
        { key: "roles", label: t(lc, "roles") },
      ]} value={tab} onChange={setTab} />
      {tab === "users" && <UsersTab />}
      {tab === "roles" && <RolesTab />}
    </PageFrame>
  );
}
