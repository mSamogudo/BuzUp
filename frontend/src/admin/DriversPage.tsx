import { useCallback, useState, type FormEvent } from "react";
import { Eye, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { apiFetch, apiPost, apiPatch, apiDelete } from "../lib/api";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { AdminModal, DataTable, PageFrame, SectionCard, StatusBadge, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";
import { useConfirm } from "../ui/ConfirmDialog";

interface Driver { id: number; uuid: string; user_id: number | null; user_display: string; full_name: string; phone: string; license_number: string; status: string; }

export default function DriversPage() {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const { confirm, dialog: confirmDialog } = useConfirm();
  const loader = useCallback(() => apiFetch("/api/drivers/", token!).then((d) => d.results || d), [token]);
  const { data: drivers, loading, reload } = useAsyncData<Driver[]>(loader, [token]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [viewing, setViewing] = useState<Driver | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ full_name: "", phone: "", license_number: "", status: "active" });

  const reset = () => { setEditId(null); setModalOpen(false); setForm({ full_name: "", phone: "", license_number: "", status: "active" }); };

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true);
    try {
      if (editId) { await apiPatch(`/api/drivers/${editId}/`, token!, form); } else { await apiPost("/api/drivers/", token!, form); }
      showToast("success", editId ? t(lc, "update") : t(lc, "create")); reset(); reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
    finally { setBusy(false); }
  };

  return (
    <PageFrame kicker={t(lc, "operation")} title={t(lc, "drivers")}
      action={<>
        <button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={16} /><span>{t(lc, "refresh")}</span></button>
        <button className="primary-button" onClick={() => { reset(); setModalOpen(true); }} type="button"><Plus size={16} /> {t(lc, "newDriver")}</button>
      </>}>
      <SectionCard title={t(lc, "drivers")}>
        <DataTable columns={[
          { header: t(lc, "name"), render: (r: Driver) => <TablePrimaryCell title={r.full_name} subtitle={r.phone || "-"} meta={r.license_number ? `${t(lc, "license")}: ${r.license_number}` : undefined} /> },
          { header: t(lc, "status"), render: (r: Driver) => <StatusBadge value={r.status} /> },
          { header: t(lc, "actions"), className: "table-actions-cell", render: (r: Driver) => (
            <div className="admin-inline-actions">
              <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => setViewing(r)} />
              <TableActionButton icon={<Pencil size={15} />} label={t(lc, "edit")} onClick={() => { setEditId(r.id); setForm({ full_name: r.full_name, phone: r.phone, license_number: r.license_number, status: r.status }); setModalOpen(true); }} />
              <TableActionButton icon={<Trash2 size={15} />} label={t(lc, "delete")} onClick={async () => { const ok = await confirm({ title: t(lc, "delete"), message: `Tem a certeza que pretende eliminar ${r.full_name}?`, tone: "danger" }); if (!ok) return; try { await apiDelete(`/api/drivers/${r.id}/`, token!); reload(); } catch {} }} tone="danger" />
            </div>
          )},
        ]} rows={drivers || []} rowKey={(r) => r.uuid} loading={loading} emptyMessage={t(lc, "noDrivers")} />
      </SectionCard>

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing?.full_name || ""} fields={viewing ? [
        { label: t(lc, "fullName"), value: viewing.full_name },
        { label: t(lc, "phone"), value: viewing.phone || "-" },
        { label: t(lc, "license"), value: viewing.license_number || "-" },
        { label: "Utilizador de Login", value: viewing.user_display || "Sera criado ao guardar" },
        { label: t(lc, "status"), value: <StatusBadge value={viewing.status} /> },
      ] : []} />

      <AdminModal open={modalOpen} onClose={reset} title={editId ? t(lc, "editDriver") : t(lc, "newDriver")}>
        <form className="admin-form" onSubmit={submit}>
          <p style={{ fontSize: 12, color: "var(--app-text-muted)", marginBottom: 12 }}>
            O utilizador de login do motorista e criado automaticamente a partir do telefone.
          </p>
          <div className="admin-form-grid">
            <label className="field"><span>{t(lc, "fullName")}</span><input required value={form.full_name} onChange={(e) => setForm((p) => ({ ...p, full_name: e.target.value }))} /></label>
            <label className="field"><span>{t(lc, "phone")}</span><input required value={form.phone} onChange={(e) => setForm((p) => ({ ...p, phone: e.target.value }))} placeholder="84/85/86/87..." /></label>
            <label className="field"><span>{t(lc, "license")}</span><input value={form.license_number} onChange={(e) => setForm((p) => ({ ...p, license_number: e.target.value }))} /></label>
            <label className="field"><span>{t(lc, "status")}</span><select value={form.status} onChange={(e) => setForm((p) => ({ ...p, status: e.target.value }))}><option value="active">{t(lc, "active")}</option><option value="inactive">{t(lc, "inactive")}</option><option value="suspended">{t(lc, "suspended")}</option></select></label>
          </div>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy} type="submit">{busy ? t(lc, "saving") : editId ? t(lc, "update") : t(lc, "create")}</button>
            <button className="secondary-button" onClick={reset} type="button">{t(lc, "cancel")}</button>
          </div>
        </form>
      </AdminModal>
      {confirmDialog}
    </PageFrame>
  );
}
