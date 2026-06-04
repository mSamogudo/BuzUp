import { useCallback, useState } from "react";
import { Download, Eye, Lock, RefreshCw, Upload, UserPlus } from "lucide-react";
import { apiFetch, apiPost } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { AdminModal, DataTable, MetricCard, PageFrame, SegmentedControl, StatusBadge, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";

interface CardRecord { id: number; uuid: string; card_type: string; card_uid: string; card_number: string; card_technology: string; status: string; passenger_name: string; passenger_phone: string; balance: string | null; issued_batch: string; batch_serial: string; manufacturer: string; activated_at: string | null; created_at: string; }
interface PassengerOpt { id: number; full_name: string; phone_number: string; }

export default function PhysicalCardsPage() {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const loader = useCallback(() => apiFetch("/api/cards/?type=physical", token!).then((d) => d.results || d), [token]);
  const passengerLoader = useCallback(() => apiFetch("/api/passengers/", token!).then((d) => d.results || d), [token]);
  const { data: cards, loading, reload } = useAsyncData<CardRecord[]>(loader, [token]);
  const { data: passengers } = useAsyncData<PassengerOpt[]>(passengerLoader, [token]);
  const [filter, setFilter] = useState<"active" | "inactive">("active");
  const [viewing, setViewing] = useState<CardRecord | null>(null);
  const [assignModal, setAssignModal] = useState(false);
  const [assignCard, setAssignCard] = useState<CardRecord | null>(null);
  const [assignPassenger, setAssignPassenger] = useState("");
  const [importModal, setImportModal] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);

  const all = cards || [];
  const filtered = filter === "active" ? all.filter((c) => c.status === "active") : all.filter((c) => c.status !== "active");

  const block = async (uid: string) => {
    if (!confirm(`${t(lc, "block")}?`)) return;
    try { await apiPost("/api/card-actions/block/", token!, { card_uid: uid }); showToast("success", t(lc, "block")); reload(); }
    catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
  };

  const doAssign = async () => {
    if (!assignCard || !assignPassenger) return; setBusy(true);
    try {
      await apiPost("/api/card-actions/assign/", token!, { card_uid: assignCard.card_uid, passenger_id: Number(assignPassenger) });
      showToast("success", t(lc, "activate")); setAssignModal(false); reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); } finally { setBusy(false); }
  };

  const doImport = async () => {
    if (!importFile) return; setBusy(true);
    try {
      const fd = new FormData(); fd.append("file", importFile);
      const res = await fetch("/api/import/cards/", { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Erro");
      showToast("success", `${data.imported} cartoes importados.`);
      setImportModal(false); reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); } finally { setBusy(false); }
  };

  const downloadTemplate = async () => {
    try {
      const res = await fetch("/api/import/cards/template/", { headers: { Authorization: `Bearer ${token}` } });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = "template_cartoes.xlsx"; a.click(); URL.revokeObjectURL(url);
    } catch {}
  };

  return (
    <PageFrame kicker={t(lc, "management")} title={t(lc, "physicalCards")}
      action={<>
        <button className="icon-text-button" onClick={downloadTemplate} type="button"><Download size={15} /><span>Template</span></button>
        <button className="icon-text-button" onClick={() => { setImportFile(null); setImportModal(true); }} type="button"><Upload size={15} /><span>Importar</span></button>
        <button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={15} /><span>{t(lc, "refresh")}</span></button>
      </>}>
      <div className="admin-metric-grid">
        <MetricCard label={t(lc, "total")} value={String(all.length)} />
        <MetricCard label={t(lc, "active")} value={String(all.filter((c) => c.status === "active").length)} />
        <MetricCard label={t(lc, "inactive")} value={String(all.filter((c) => c.status === "inactive").length)} />
      </div>

      <SegmentedControl items={[
        { key: "active", label: `${t(lc, "active")} (${all.filter((c) => c.status === "active").length})` },
        { key: "inactive", label: `${t(lc, "inactive")} (${all.filter((c) => c.status !== "active").length})` },
      ]} value={filter} onChange={(k) => setFilter(k as "active" | "inactive")} />

      <DataTable columns={[
        { header: t(lc, "cardNumber"), sortKey: "card_number", render: (r: CardRecord) => <TablePrimaryCell title={r.card_number} subtitle={r.passenger_name || t(lc, "noPassenger")} /> },
        { header: t(lc, "status"), render: (r: CardRecord) => <StatusBadge value={r.status} /> },
        { header: t(lc, "actions"), className: "table-actions-cell", render: (r: CardRecord) => (
          <div className="admin-inline-actions">
            <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => setViewing(r)} />
            {r.status === "inactive" && <TableActionButton icon={<UserPlus size={15} />} label="Atribuir" onClick={() => { setAssignCard(r); setAssignPassenger(""); setAssignModal(true); }} />}
            {r.status === "active" && <TableActionButton icon={<Lock size={15} />} label={t(lc, "block")} onClick={() => block(r.card_uid)} tone="danger" />}
          </div>
        )},
      ]} rows={filtered} rowKey={(r) => r.uuid} loading={loading} emptyMessage={t(lc, "noCards")} />

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing?.card_number || ""} fields={viewing ? [
        { label: t(lc, "cardNumber"), value: viewing.card_number },
        { label: "UID", value: viewing.card_uid },
        { label: t(lc, "cardTechnology"), value: viewing.card_technology },
        { label: t(lc, "status"), value: <StatusBadge value={viewing.status} /> },
        { label: t(lc, "passenger"), value: viewing.passenger_name || t(lc, "noPassenger") },
        { label: t(lc, "phone"), value: viewing.passenger_phone || "-" },
        { label: t(lc, "balance"), value: viewing.balance !== null ? formatCurrency(viewing.balance) : "-" },
        { label: t(lc, "batch"), value: viewing.issued_batch || "-" },
        { label: t(lc, "manufacturer"), value: viewing.manufacturer || "-" },
        { label: t(lc, "activated"), value: formatDateTime(viewing.activated_at) },
      ] : []} />

      <AdminModal open={assignModal} onClose={() => setAssignModal(false)} title="Atribuir Cartao">
        <div className="admin-form">
          <p style={{ fontSize: 13, color: "var(--app-text-muted)", marginBottom: 12 }}>
            Cartao <strong>{assignCard?.card_number}</strong> sera activado e vinculado ao passageiro.
          </p>
          <label className="field"><span>{t(lc, "passenger")}</span>
            <select value={assignPassenger} onChange={(e) => setAssignPassenger(e.target.value)}>
              <option value="">{t(lc, "select")}</option>
              {(passengers || []).map((p) => <option key={p.id} value={p.id}>{p.full_name} — {p.phone_number}</option>)}
            </select>
          </label>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy || !assignPassenger} onClick={doAssign} type="button">{busy ? t(lc, "saving") : "Atribuir e Activar"}</button>
            <button className="secondary-button" onClick={() => setAssignModal(false)} type="button">{t(lc, "cancel")}</button>
          </div>
        </div>
      </AdminModal>

      <AdminModal open={importModal} onClose={() => setImportModal(false)} title="Importar Cartoes Excel">
        <div className="admin-form">
          <p style={{ fontSize: 13, color: "var(--app-text-muted)", marginBottom: 12 }}>Descarregue o template Excel e preencha com os dados do lote.</p>
          <label className="field"><span>Ficheiro Excel</span>
            <input type="file" accept=".xlsx,.xls" onChange={(e) => setImportFile(e.target.files?.[0] || null)} />
          </label>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy || !importFile} onClick={doImport} type="button">{busy ? "A importar..." : "Importar"}</button>
            <button className="secondary-button" onClick={() => setImportModal(false)} type="button">{t(lc, "cancel")}</button>
          </div>
        </div>
      </AdminModal>
    </PageFrame>
  );
}
