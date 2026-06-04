import { useCallback, useState, type FormEvent } from "react";
import { Eye, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { apiFetch, apiPost, apiPatch, apiDelete } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { AdminModal, DataTable, MetricCard, PageFrame, SectionCard, StatusBadge, TabBar, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";
import { useConfirm } from "../ui/ConfirmDialog";

interface Pkg { id: number; uuid: string; name: string; description: string; discount_type: string; discount_value: string; price: string; validity_days: number; max_trips: number; status: string; routes: { route_id: number; route_code: string; route_name: string }[]; }
interface Sub { id: number; uuid: string; passenger_name: string; passenger_phone: string; package_name: string; discount_type: string; special_balance: string; trips_used: number; trips_remaining: number; status: string; activated_at: string; expires_at: string; passenger_account_id: number; package_id: number; }
interface PassengerOpt { id: number; full_name: string; phone_number: string; }
interface RouteOpt { id: number; code: string; name: string; }

export default function PackagesPage({ embedded }: { embedded?: boolean }) {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const { confirm, dialog: confirmDialog } = useConfirm();
  const pkgLoader = useCallback(() => apiFetch("/api/packages/", token!).then((d) => d.results || d), [token]);
  const subLoader = useCallback(() => apiFetch("/api/passenger-packages/", token!).then((d) => d.results || d), [token]);
  const passengerLoader = useCallback(() => apiFetch("/api/passengers/", token!).then((d) => d.results || d), [token]);
  const routeLoader = useCallback(() => apiFetch("/api/routes/", token!).then((d) => d.results || d), [token]);
  const { data: pkgs, loading: lP, reload: rP } = useAsyncData<Pkg[]>(pkgLoader, [token]);
  const { data: subs, loading: lS, reload: rS } = useAsyncData<Sub[]>(subLoader, [token]);
  const { data: passengers } = useAsyncData<PassengerOpt[]>(passengerLoader, [token]);
  const { data: routeOpts } = useAsyncData<RouteOpt[]>(routeLoader, [token]);
  const reload = () => { rP(); rS(); };
  const [tab, setTab] = useState<"packages" | "subs">("packages");
  const [modalOpen, setModalOpen] = useState(false);
  const [subModal, setSubModal] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [viewPkg, setViewPkg] = useState<Pkg | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", discount_type: "percentage", discount_value: "", price: "", validity_days: "30", max_trips: "0", status: "active" });
  const [selectedRoutes, setSelectedRoutes] = useState<Set<number>>(new Set());
  const [subForm, setSubForm] = useState({ passenger_id: "", package_id: "" });
  const f = (k: string, v: string) => setForm((p) => ({ ...p, [k]: v }));
  const toggleRoute = (id: number) => setSelectedRoutes((prev) => { const n = new Set(prev); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const reset = () => { setEditId(null); setModalOpen(false); setForm({ name: "", description: "", discount_type: "percentage", discount_value: "", price: "", validity_days: "30", max_trips: "0", status: "active" }); setSelectedRoutes(new Set()); };

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true);
    const payload = { name: form.name, description: form.description, discount_type: form.discount_type, discount_value: form.discount_value || "0", price: form.price, validity_days: Number(form.validity_days), max_trips: Number(form.max_trips), status: form.status, route_ids: Array.from(selectedRoutes) };
    try {
      if (editId) await apiPatch(`/api/packages/${editId}/`, token!, payload);
      else await apiPost("/api/packages/", token!, payload);
      showToast("success", editId ? t(lc, "update") : t(lc, "create")); reset(); reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
    finally { setBusy(false); }
  };

  const submitSub = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true);
    try {
      await apiPost("/api/packages/subscribe/", token!, { passenger_id: Number(subForm.passenger_id), package_id: Number(subForm.package_id), pay_from_wallet: true });
      showToast("success", t(lc, "subscribe")); setSubModal(false); reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
    finally { setBusy(false); }
  };

  const dt = form.discount_type;

  return (
    <PageFrame kicker={t(lc, "operation")} title={t(lc, "packages")}>
      <TabBar items={[{ key: "packages", label: t(lc, "packages"), count: (pkgs || []).length }, { key: "subs", label: t(lc, "subscriptions"), count: (subs || []).length }]} value={tab} onChange={(k) => setTab(k as "packages" | "subs")} />

      {tab === "packages" && (
        <SectionCard title={t(lc, "packages")}>
          <div className="admin-toolbar"><div className="admin-toolbar-spacer" />
            <button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={15} /><span>{t(lc, "refresh")}</span></button>
            <button className="primary-button" onClick={() => { reset(); setModalOpen(true); }} type="button"><Plus size={15} /> {t(lc, "newPackage")}</button>
          </div>
          <DataTable columns={[
            { header: t(lc, "name"), render: (r: Pkg) => <TablePrimaryCell title={r.name} subtitle={r.discount_type === "percentage" ? `${r.discount_value}%` : r.discount_type === "free_trips" ? `${r.max_trips} viagens` : formatCurrency(r.discount_value)} /> },
            { header: t(lc, "packagePrice"), render: (r: Pkg) => formatCurrency(r.price) },
            { header: t(lc, "actions"), className: "table-actions-cell", render: (r: Pkg) => (
              <div className="admin-inline-actions">
                <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => setViewPkg(r)} />
                <TableActionButton icon={<Pencil size={15} />} label={t(lc, "edit")} onClick={() => { setEditId(r.id); setModalOpen(true); setForm({ name: r.name, description: r.description, discount_type: r.discount_type, discount_value: r.discount_value, price: r.price, validity_days: String(r.validity_days), max_trips: String(r.max_trips), status: r.status }); setSelectedRoutes(new Set((r.routes || []).map((rt) => rt.route_id).filter(Boolean))); }} />
                <TableActionButton icon={<Trash2 size={15} />} label={t(lc, "delete")} onClick={async () => { const ok = await confirm({ title: t(lc, "delete"), message: `Tem a certeza que pretende eliminar o pacote ${r.name}?`, tone: "danger" }); if (!ok) return; try { await apiDelete(`/api/packages/${r.id}/`, token!); reload(); } catch {} }} tone="danger" />
              </div>
            )},
          ]} rows={pkgs || []} rowKey={(r) => r.uuid} loading={lP} emptyMessage={t(lc, "noPackages")} />
        </SectionCard>
      )}

      {tab === "subs" && (
        <SectionCard title={t(lc, "subscriptions")}>
          <div className="admin-toolbar"><div className="admin-toolbar-spacer" />
            <button className="primary-button" onClick={() => { setSubForm({ passenger_id: "", package_id: "" }); setSubModal(true); }} type="button"><Plus size={15} /> {t(lc, "subscribe")}</button>
          </div>
          <DataTable columns={[
            { header: t(lc, "passenger"), render: (r: Sub) => <TablePrimaryCell title={r.passenger_name} subtitle={r.package_name} /> },
            { header: t(lc, "status"), render: (r: Sub) => <StatusBadge value={r.status} /> },
            { header: t(lc, "expiresAt"), render: (r: Sub) => formatDateTime(r.expires_at) },
          ]} rows={subs || []} rowKey={(r) => r.uuid} loading={lS} emptyMessage={t(lc, "noSubscriptions")} />
        </SectionCard>
      )}

      <DetailDrawer open={!!viewPkg} onClose={() => setViewPkg(null)} title={viewPkg?.name || ""} fields={viewPkg ? [
        { label: t(lc, "discountType"), value: viewPkg.discount_type.replace(/_/g, " ") },
        { label: t(lc, "discountValue"), value: viewPkg.discount_type === "percentage" ? `${viewPkg.discount_value}%` : formatCurrency(viewPkg.discount_value) },
        { label: t(lc, "packagePrice"), value: formatCurrency(viewPkg.price) },
        { label: t(lc, "validityDays"), value: `${viewPkg.validity_days} dias` },
        { label: t(lc, "maxTrips"), value: viewPkg.max_trips > 0 ? String(viewPkg.max_trips) : "Ilimitado" },
        { label: t(lc, "packageRoutes"), value: viewPkg.routes.length > 0 ? viewPkg.routes.map((r) => r.route_code).join(", ") : t(lc, "allRoutes") },
        { label: t(lc, "status"), value: <StatusBadge value={viewPkg.status} /> },
      ] : []} />

      <AdminModal open={modalOpen} onClose={reset} title={editId ? t(lc, "editPackage") : t(lc, "newPackage")}>
        <form className="admin-form" onSubmit={submit}>
          <div className="admin-form-grid">
            <label className="field"><span>{t(lc, "name")}</span><input required value={form.name} onChange={(e) => f("name", e.target.value)} /></label>
            <label className="field"><span>{t(lc, "discountType")}</span>
              <select value={form.discount_type} onChange={(e) => f("discount_type", e.target.value)}>
                <option value="percentage">{t(lc, "percentage")}</option>
                <option value="fixed_amount">{t(lc, "fixedAmount")}</option>
                <option value="free_trips">{t(lc, "freeTrips")}</option>
              </select>
            </label>

            {dt === "percentage" && (
              <label className="field"><span>Desconto (%)</span>
                <input required type="number" step="1" min="0" max="100" value={form.discount_value} onChange={(e) => f("discount_value", e.target.value)} />
              </label>
            )}

            {dt === "fixed_amount" && (
              <label className="field"><span>Saldo Especial (MZN)</span>
                <input required type="number" step="0.01" min="0" value={form.discount_value} onChange={(e) => f("discount_value", e.target.value)} />
              </label>
            )}

            {dt === "free_trips" && (
              <label className="field"><span>{t(lc, "maxTrips")}</span>
                <input required type="number" min="1" value={form.max_trips} onChange={(e) => f("max_trips", e.target.value)} />
              </label>
            )}

            <label className="field"><span>{t(lc, "packagePrice")} (MZN)</span>
              <input required type="number" step="0.01" min="0" value={form.price} onChange={(e) => f("price", e.target.value)} />
            </label>
            <label className="field"><span>{t(lc, "validityDays")}</span>
              <input type="number" min="1" value={form.validity_days} onChange={(e) => f("validity_days", e.target.value)} />
            </label>
            <label className="field"><span>{t(lc, "status")}</span>
              <select value={form.status} onChange={(e) => f("status", e.target.value)}>
                <option value="active">{t(lc, "active")}</option>
                <option value="inactive">{t(lc, "inactive")}</option>
              </select>
            </label>
            <div className="field admin-field-span-full">
              <span>{t(lc, "packageRoutes")} ({selectedRoutes.size === 0 ? t(lc, "allRoutes") : selectedRoutes.size})</span>
              <div className="perm-grid" style={{ maxHeight: 180 }}>
                {(routeOpts || []).map((r) => (
                  <label key={r.id} className="perm-check">
                    <input type="checkbox" checked={selectedRoutes.has(r.id)} onChange={() => toggleRoute(r.id)} />
                    <span>{r.code} — {r.name}</span>
                  </label>
                ))}
              </div>
            </div>
            <label className="field admin-field-span-full"><span>{t(lc, "description")}</span><textarea value={form.description} onChange={(e) => f("description", e.target.value)} /></label>
          </div>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy} type="submit">{busy ? t(lc, "saving") : editId ? t(lc, "update") : t(lc, "create")}</button>
            <button className="secondary-button" onClick={reset} type="button">{t(lc, "cancel")}</button>
          </div>
        </form>
      </AdminModal>

      <AdminModal open={subModal} onClose={() => setSubModal(false)} title={t(lc, "subscribe")}>
        <form className="admin-form" onSubmit={submitSub}>
          <div className="admin-form-grid">
            <label className="field"><span>{t(lc, "passenger")}</span>
              <select required value={subForm.passenger_id} onChange={(e) => setSubForm((p) => ({ ...p, passenger_id: e.target.value }))}>
                <option value="">{t(lc, "select")}</option>
                {(passengers || []).map((p) => <option key={p.id} value={p.id}>{p.full_name} — {p.phone_number}</option>)}
              </select>
            </label>
            <label className="field"><span>{t(lc, "packages")}</span>
              <select required value={subForm.package_id} onChange={(e) => setSubForm((p) => ({ ...p, package_id: e.target.value }))}>
                <option value="">{t(lc, "select")}</option>
                {(pkgs || []).filter((p) => p.status === "active").map((p) => <option key={p.id} value={p.id}>{p.name} — {formatCurrency(p.price)}</option>)}
              </select>
            </label>
          </div>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy} type="submit">{busy ? t(lc, "saving") : t(lc, "subscribe")}</button>
            <button className="secondary-button" onClick={() => setSubModal(false)} type="button">{t(lc, "cancel")}</button>
          </div>
        </form>
      </AdminModal>
      {confirmDialog}
    </PageFrame>
  );
}
