import { useCallback, useState, type FormEvent } from "react";
import { Eye, Pencil, Plus, Printer, QrCode, RefreshCw, Trash2 } from "lucide-react";
import { apiFetch, apiPost, apiPatch, apiDelete, apiUpload } from "../lib/api";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { AdminModal, DataTable, PageFrame, SectionCard, StatusBadge, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";
import { useConfirm } from "../ui/ConfirmDialog";

interface Vehicle { id: number; uuid: string; registration: string; make: string; model_name: string; seated_capacity: number; standing_capacity: number; status: string; livrete_url?: string; }

export default function VehiclesPage({ embedded }: { embedded?: boolean }) {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const { confirm, dialog: confirmDialog } = useConfirm();
  const loader = useCallback(() => apiFetch("/api/vehicles/", token!).then((d) => d.results || d), [token]);
  const { data: vehicles, loading, reload } = useAsyncData<Vehicle[]>(loader, [token]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [viewing, setViewing] = useState<Vehicle | null>(null);
  const [qrVehicle, setQrVehicle] = useState<Vehicle | null>(null);
  const [busy, setBusy] = useState(false);
  const [livrete, setLivrete] = useState<File | null>(null);
  const [form, setForm] = useState({ registration: "", make: "", model_name: "", seated_capacity: "0", standing_capacity: "0", status: "active" });

  const reset = () => { setEditId(null); setModalOpen(false); setLivrete(null); setForm({ registration: "", make: "", model_name: "", seated_capacity: "0", standing_capacity: "0", status: "active" }); };

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true);
    try {
      if (livrete) {
        const fd = new FormData();
        fd.append("registration", form.registration);
        fd.append("make", form.make);
        fd.append("model_name", form.model_name);
        fd.append("seated_capacity", String(Number(form.seated_capacity)));
        fd.append("standing_capacity", String(Number(form.standing_capacity)));
        fd.append("status", form.status);
        fd.append("livrete", livrete);
        if (editId) await apiUpload(`/api/vehicles/${editId}/`, token!, fd, "PATCH");
        else await apiUpload("/api/vehicles/", token!, fd, "POST");
      } else {
        const payload = { ...form, seated_capacity: Number(form.seated_capacity), standing_capacity: Number(form.standing_capacity) };
        if (editId) { await apiPatch(`/api/vehicles/${editId}/`, token!, payload); } else { await apiPost("/api/vehicles/", token!, payload); }
      }
      showToast("success", editId ? t(lc, "update") : t(lc, "create")); reset(); reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
    finally { setBusy(false); }
  };

  return (
    <PageFrame kicker={t(lc, "operation")} title={t(lc, "vehicles")}
      action={<>
        <button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={16} /><span>{t(lc, "refresh")}</span></button>
        <button className="primary-button" onClick={() => { reset(); setModalOpen(true); }} type="button"><Plus size={16} /> {t(lc, "newVehicle")}</button>
      </>}>
      <SectionCard title={t(lc, "vehicles")}>
        <DataTable columns={[
          { header: t(lc, "registration"), render: (r: Vehicle) => <TablePrimaryCell title={r.registration} subtitle={`${r.make} ${r.model_name}`.trim() || "-"} meta={`${t(lc, "totalCapacity")}: ${r.seated_capacity + r.standing_capacity}`} /> },
          { header: t(lc, "status"), render: (r: Vehicle) => <StatusBadge value={r.status} /> },
          { header: t(lc, "actions"), className: "table-actions-cell", render: (r: Vehicle) => (
            <div className="admin-inline-actions">
              <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => setViewing(r)} />
              <TableActionButton icon={<QrCode size={15} />} label="QR Code" onClick={() => setQrVehicle(r)} />
              <TableActionButton icon={<Pencil size={15} />} label={t(lc, "edit")} onClick={() => { setEditId(r.id); setForm({ registration: r.registration, make: r.make, model_name: r.model_name, seated_capacity: String(r.seated_capacity), standing_capacity: String(r.standing_capacity), status: r.status }); setModalOpen(true); }} />
              <TableActionButton icon={<Trash2 size={15} />} label={t(lc, "delete")} onClick={async () => { const ok = await confirm({ title: t(lc, "delete"), message: `Tem a certeza que pretende eliminar a viatura ${r.registration}?`, tone: "danger" }); if (!ok) return; try { await apiDelete(`/api/vehicles/${r.id}/`, token!); showToast("success", t(lc, "delete")); reload(); } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); } }} tone="danger" />
            </div>
          )},
        ]} rows={vehicles || []} rowKey={(r) => r.uuid} loading={loading} emptyMessage={t(lc, "noVehicles")} />
      </SectionCard>

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing?.registration || ""} fields={viewing ? [
        { label: t(lc, "registration"), value: viewing.registration },
        { label: t(lc, "make"), value: viewing.make || "-" },
        { label: t(lc, "model"), value: viewing.model_name || "-" },
        { label: t(lc, "seatedCapacity"), value: String(viewing.seated_capacity) },
        { label: t(lc, "standingCapacity"), value: String(viewing.standing_capacity) },
        { label: t(lc, "totalCapacity"), value: String(viewing.seated_capacity + viewing.standing_capacity) },
        { label: t(lc, "status"), value: <StatusBadge value={viewing.status} /> },
        { label: t(lc, "livrete"), value: viewing.livrete_url ? <a href={viewing.livrete_url} target="_blank" rel="noreferrer">{t(lc, "viewLivrete")}</a> : "-" },
      ] : []} />

      <AdminModal open={modalOpen} onClose={reset} title={editId ? t(lc, "editVehicle") : t(lc, "newVehicle")}>
        <form className="admin-form" onSubmit={submit}>
          <div className="admin-form-grid">
            <label className="field"><span>{t(lc, "registration")}</span><input required value={form.registration} onChange={(e) => setForm((p) => ({ ...p, registration: e.target.value }))} /></label>
            <label className="field"><span>{t(lc, "make")}</span><input value={form.make} onChange={(e) => setForm((p) => ({ ...p, make: e.target.value }))} /></label>
            <label className="field"><span>{t(lc, "model")}</span><input value={form.model_name} onChange={(e) => setForm((p) => ({ ...p, model_name: e.target.value }))} /></label>
            <label className="field"><span>{t(lc, "seatedCapacity")}</span><input type="number" min="0" value={form.seated_capacity} onChange={(e) => setForm((p) => ({ ...p, seated_capacity: e.target.value }))} /></label>
            <label className="field"><span>{t(lc, "standingCapacity")}</span><input type="number" min="0" value={form.standing_capacity} onChange={(e) => setForm((p) => ({ ...p, standing_capacity: e.target.value }))} /></label>
            <label className="field"><span>{t(lc, "status")}</span><select value={form.status} onChange={(e) => setForm((p) => ({ ...p, status: e.target.value }))}><option value="active">{t(lc, "active")}</option><option value="maintenance">{t(lc, "maintenance")}</option><option value="retired">{t(lc, "retired")}</option></select></label>
            <label className="field admin-field-span-full"><span>{t(lc, "livrete")}</span><input type="file" accept="application/pdf,image/*" onChange={(e) => setLivrete(e.target.files?.[0] ?? null)} /><small style={{ color: "var(--app-text-muted)", fontSize: 12 }}>{t(lc, "livreteHint")}</small></label>
          </div>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy} type="submit">{busy ? t(lc, "saving") : editId ? t(lc, "update") : t(lc, "create")}</button>
            <button className="secondary-button" onClick={reset} type="button">{t(lc, "cancel")}</button>
          </div>
        </form>
      </AdminModal>

      <AdminModal open={!!qrVehicle} onClose={() => setQrVehicle(null)} title={qrVehicle ? `QR Code · ${qrVehicle.registration}` : "QR Code"}>
        {qrVehicle && (() => {
          const url = `${window.location.origin}/bus/${qrVehicle.uuid}`;
          const qrSrc = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(url)}`;
          return (
            <div className="vehicle-qr">
              <div className="vehicle-qr-print">
                <img alt={`QR Code ${qrVehicle.registration}`} className="vehicle-qr-image" src={qrSrc} />
                <div className="vehicle-qr-info">
                  <strong>{qrVehicle.registration}</strong>
                  <span>{`${qrVehicle.make} ${qrVehicle.model_name}`.trim() || "-"}</span>
                  <small>{url}</small>
                </div>
              </div>
              <div className="admin-form-actions vehicle-qr-actions">
                <button className="primary-button" onClick={() => window.print()} type="button"><Printer size={15} /> Imprimir</button>
                <button className="secondary-button" onClick={() => setQrVehicle(null)} type="button">{t(lc, "cancel")}</button>
              </div>
            </div>
          );
        })()}
      </AdminModal>

      {confirmDialog}
    </PageFrame>
  );
}
