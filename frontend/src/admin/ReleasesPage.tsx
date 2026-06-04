import { useCallback, useRef, useState, type FormEvent } from "react";
import { Eye, Pencil, Plus, RefreshCw } from "lucide-react";
import { apiFetch, apiPost, apiPatch, apiUpload } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { AdminModal, DataTable, PageFrame, SectionCard, StatusBadge, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";

interface Release { id: number; uuid: string; app_type: string; version_name: string; version_code: number; is_mandatory: boolean; status: string; release_notes: string; published_at: string | null; }

export default function ReleasesPage({ embedded }: { embedded?: boolean }) {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const loader = useCallback(() => apiFetch("/api/admin/app-releases/", token!).then((d) => d.results || d), [token]);
  const { data: rows, loading, reload } = useAsyncData<Release[]>(loader, [token]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [viewing, setViewing] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [apkFile, setApkFile] = useState<File | null>(null);
  const apkInputRef = useRef<HTMLInputElement | null>(null);
  const [form, setForm] = useState({ app_type: "pos", version_name: "", version_code: "", release_notes: "", is_mandatory: "false", apk_url: "", checksum: "" });
  const f = (k: string, v: string) => setForm((p) => ({ ...p, [k]: v }));
  const reset = () => { setEditId(null); setModalOpen(false); setApkFile(null); if (apkInputRef.current) apkInputRef.current.value = ""; setForm({ app_type: "pos", version_name: "", version_code: "", release_notes: "", is_mandatory: "false", apk_url: "", checksum: "" }); };

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true);
    try {
      if (editId) {
        // Editing only touches metadata (not the binary).
        const payload = { ...form, version_code: Number(form.version_code), is_mandatory: form.is_mandatory === "true" };
        await apiPatch(`/api/admin/app-releases/${editId}/`, token!, payload);
        showToast("success", t(lc, "update"));
      } else if (apkFile) {
        // New release with an uploaded APK -> multipart.
        const fd = new FormData();
        fd.append("app_type", form.app_type);
        fd.append("version_name", form.version_name);
        fd.append("version_code", String(Number(form.version_code)));
        fd.append("release_notes", form.release_notes);
        fd.append("is_mandatory", form.is_mandatory);
        if (form.apk_url) fd.append("apk_url", form.apk_url);
        fd.append("apk_file", apkFile);
        await apiUpload("/api/admin/app-releases/", token!, fd);
        showToast("success", t(lc, "create"));
      } else {
        // New release pointing at an externally hosted APK URL.
        const payload = { ...form, version_code: Number(form.version_code), is_mandatory: form.is_mandatory === "true" };
        await apiPost("/api/admin/app-releases/", token!, payload);
        showToast("success", t(lc, "create"));
      }
      reset(); reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
    finally { setBusy(false); }
  };

  const publish = async (id: number) => {
    try { await apiPatch(`/api/admin/app-releases/${id}/publish/`, token!, {}); showToast("success", t(lc, "publish")); reload(); }
    catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
  };

  const suspend = async (id: number) => {
    try { await apiPatch(`/api/admin/app-releases/${id}/suspend/`, token!, {}); showToast("success", t(lc, "suspend")); reload(); }
    catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
  };

  return (
    <PageFrame kicker={t(lc, "devices")} title={t(lc, "releases")}
      action={<>
        <button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={16} /><span>{t(lc, "refresh")}</span></button>
        <button className="primary-button" onClick={() => { reset(); setModalOpen(true); }} type="button"><Plus size={16} /> {t(lc, "newRelease")}</button>
      </>}>
      <SectionCard title={t(lc, "releases")}>
        <DataTable columns={[
          { header: t(lc, "version"), render: (r: Release) => <TablePrimaryCell title={`v${r.version_name} (${r.version_code})`} subtitle={r.app_type.toUpperCase()} meta={r.is_mandatory ? t(lc, "mandatory") : t(lc, "optional")} /> },
          { header: t(lc, "releaseNotes"), render: (r: Release) => r.release_notes?.substring(0, 50) || "-" },
          { header: t(lc, "status"), render: (r: Release) => <StatusBadge value={r.status} /> },
          { header: t(lc, "published"), render: (r: Release) => formatDateTime(r.published_at) },
          { header: t(lc, "actions"), className: "table-actions-cell", render: (r: Release) => (
            <div className="admin-inline-actions">
              <TableActionButton icon={<Eye size={15} />} label="Ver" onClick={() => setViewing(r)} />
              <TableActionButton icon={<Pencil size={15} />} label={t(lc, "edit")} onClick={() => { setEditId(r.id); setModalOpen(true); setForm({ app_type: r.app_type, version_name: r.version_name, version_code: String(r.version_code), release_notes: r.release_notes, is_mandatory: r.is_mandatory ? "true" : "false", apk_url: "", checksum: "" }); }} />
              {(r.status === "draft" || r.status === "suspended") && <button className="secondary-button" onClick={() => publish(r.id)}>{t(lc, "publish")}</button>}
              {r.status === "published" && <button className="danger-button" onClick={() => suspend(r.id)}>{t(lc, "suspend")}</button>}
            </div>
          )},
        ]} rows={rows || []} rowKey={(r) => r.uuid} loading={loading} emptyMessage={t(lc, "noReleases")} />
      </SectionCard>

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing?.name || viewing?.serial_number || viewing?.version_name || viewing?.code || ""} fields={viewing ? [
        { label: "Versao", value: viewing.version_name },
        { label: "Code", value: String(viewing.version_code) },
        { label: "Tipo", value: viewing.app_type },
        { label: "Obrigatoria", value: viewing.is_mandatory ? "Sim" : "Nao" },
        { label: "Estado", value: viewing.status },
        { label: "Notas", value: viewing.release_notes || "-" },
        { label: "Publicada", value: viewing.published_at || "-" },
      ] : []} />

      <AdminModal open={modalOpen} onClose={reset} title={editId ? t(lc, "editRelease") : t(lc, "newRelease")}>
        <form className="admin-form" onSubmit={submit}>
          <div className="admin-form-grid">
            <label className="field"><span>{t(lc, "type")}</span><select value={form.app_type} onChange={(e) => f("app_type", e.target.value)}><option value="pos">{t(lc, "pos")}</option><option value="passenger">{t(lc, "passengerApp")}</option></select></label>
            <label className="field"><span>{t(lc, "versionName")}</span><input required placeholder="1.0.0" value={form.version_name} onChange={(e) => f("version_name", e.target.value)} /></label>
            <label className="field"><span>{t(lc, "versionCode")}</span><input required type="number" min="1" value={form.version_code} onChange={(e) => f("version_code", e.target.value)} /></label>
            <label className="field"><span>{t(lc, "mandatory")}</span><select value={form.is_mandatory} onChange={(e) => f("is_mandatory", e.target.value)}><option value="false">{t(lc, "no")}</option><option value="true">{t(lc, "yes")}</option></select></label>
            {!editId && (
              <label className="field admin-field-span-full">
                <span>{t(lc, "apkFile")}</span>
                <input ref={apkInputRef} type="file" accept=".apk,application/vnd.android.package-archive"
                  onChange={(e) => setApkFile(e.target.files?.[0] ?? null)} />
                <small className="field-hint">{t(lc, "apkFileHint")}</small>
              </label>
            )}
            <label className="field admin-field-span-full"><span>{t(lc, "apkUrl")} {t(lc, "optional")}</span><input value={form.apk_url} onChange={(e) => f("apk_url", e.target.value)} placeholder="https://..." /></label>
            <label className="field admin-field-span-full"><span>{t(lc, "releaseNotes")}</span><textarea value={form.release_notes} onChange={(e) => f("release_notes", e.target.value)} /></label>
          </div>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy} type="submit">{busy ? t(lc, "saving") : editId ? t(lc, "update") : t(lc, "create")}</button>
            <button className="secondary-button" onClick={reset} type="button">{t(lc, "cancel")}</button>
          </div>
        </form>
      </AdminModal>
    </PageFrame>
  );
}
