import { useCallback, useState } from "react";
import { Download, Eye, Lock, RefreshCw, Upload, UserPlus } from "lucide-react";
import { apiFetch, apiPost } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { AdminModal, DataTable, MetricCard, PageFrame, SegmentedControl, StatusBadge, TabBar, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";

interface CardRecord { id: number; uuid: string; card_type: string; card_uid: string; card_number: string; card_technology: string; status: string; passenger_name: string; passenger_phone: string; balance: string | null; issued_batch: string; batch_serial: string; manufacturer: string; activated_at: string | null; blocked_at: string | null; created_at: string; passenger_account_id: number | null; }
interface PassengerOpt { id: number; full_name: string; phone_number: string; }

export default function CardsPage() {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const loader = useCallback(() => apiFetch("/api/cards/", token!).then((d) => d.results || d), [token]);
  const passengerLoader = useCallback(() => apiFetch("/api/passengers/", token!).then((d) => d.results || d), [token]);
  const { data: allCards, loading, reload } = useAsyncData<CardRecord[]>(loader, [token]);
  const { data: passengers } = useAsyncData<PassengerOpt[]>(passengerLoader, [token]);

  const [tab, setTab] = useState<"physical" | "digital">("physical");
  const [subTab, setSubTab] = useState<"active" | "inactive">("active");
  const [viewing, setViewing] = useState<CardRecord | null>(null);
  const [assignModal, setAssignModal] = useState(false);
  const [assignCard, setAssignCard] = useState<CardRecord | null>(null);
  const [assignPassenger, setAssignPassenger] = useState("");
  const [importModal, setImportModal] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);

  const cards = allCards || [];
  const physical = cards.filter((c) => c.card_type === "physical");
  const digital = cards.filter((c) => c.card_type === "digital");
  const currentList = tab === "physical" ? physical : digital;
  const filtered = subTab === "active"
    ? currentList.filter((c) => c.status === "active")
    : currentList.filter((c) => c.status !== "active");

  const activate = async (uid: string) => {
    try { await apiPost("/api/card-actions/activate/", token!, { card_uid: uid }); showToast("success", t(lc, "activate")); reload(); }
    catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
  };

  const block = async (uid: string) => {
    if (!confirm(`${t(lc, "block")}?`)) return;
    try { await apiPost("/api/card-actions/block/", token!, { card_uid: uid }); showToast("success", t(lc, "block")); reload(); }
    catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
  };

  const doAssign = async () => {
    if (!assignCard || !assignPassenger) return;
    setBusy(true);
    try {
      await apiPost("/api/card-actions/assign/", token!, { card_uid: assignCard.card_uid, passenger_id: Number(assignPassenger) });
      showToast("success", t(lc, "activate"));
      setAssignModal(false); setAssignCard(null); setAssignPassenger(""); reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
    finally { setBusy(false); }
  };

  const doImport = async () => {
    if (!importFile) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", importFile);
      const res = await fetch("/api/import/cards/", { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Erro");
      showToast("success", `${data.imported} cartoes importados.`);
      if (data.errors?.length) showToast("danger", `${data.errors.length} erros.`);
      setImportModal(false); setImportFile(null); reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
    finally { setBusy(false); }
  };

  return (
    <PageFrame kicker={t(lc, "management")} title={t(lc, "cards")}
      action={<>
        <button className="icon-text-button" onClick={async () => { try { const res = await fetch("/api/import/cards/template/", { headers: { Authorization: `Bearer ${token}` } }); const blob = await res.blob(); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = "template_cartoes.xlsx"; a.click(); URL.revokeObjectURL(url); } catch {} }} type="button"><Download size={15} /><span>Template</span></button>
        <button className="icon-text-button" onClick={() => { setImportFile(null); setImportModal(true); }} type="button"><Upload size={15} /><span>{t(lc, "importCsv")}</span></button>
        <button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={15} /><span>{t(lc, "refresh")}</span></button>
      </>}>
      <div className="admin-metric-grid">
        <MetricCard label={t(lc, "total")} value={String(cards.length)} />
        <MetricCard label={t(lc, "active")} value={String(cards.filter((c) => c.status === "active").length)} />
        <MetricCard label={t(lc, "inactive")} value={String(cards.filter((c) => c.status === "inactive").length)} />
        <MetricCard label={t(lc, "blocked")} value={String(cards.filter((c) => c.status === "blocked").length)} />
      </div>

      <TabBar items={[
        { key: "physical", label: `Fisicos (${physical.length})` },
        { key: "digital", label: `Digitais (${digital.length})` },
      ]} value={tab} onChange={(k) => { setTab(k as "physical" | "digital"); setSubTab("active"); }} />

      <div style={{ padding: "12px 0 0" }}>
        <SegmentedControl items={[
          { key: "active", label: `${t(lc, "active")} (${currentList.filter((c) => c.status === "active").length})` },
          { key: "inactive", label: `${t(lc, "inactive")} (${currentList.filter((c) => c.status !== "active").length})` },
        ]} value={subTab} onChange={(k) => setSubTab(k as "active" | "inactive")} />
      </div>

      <DataTable columns={[
        { header: t(lc, "cardNumber"), render: (r: CardRecord) => <TablePrimaryCell title={r.card_number} subtitle={r.passenger_name || t(lc, "noPassenger")} /> },
        { header: t(lc, "balance"), render: (r: CardRecord) => r.balance !== null ? formatCurrency(r.balance) : "-" },
        { header: t(lc, "status"), render: (r: CardRecord) => <StatusBadge value={r.status} /> },
        { header: t(lc, "actions"), className: "table-actions-cell", render: (r: CardRecord) => (
          <div className="admin-inline-actions">
            <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => setViewing(r)} />
            {r.status === "inactive" && (
              <TableActionButton icon={<UserPlus size={15} />} label="Atribuir" onClick={() => { setAssignCard(r); setAssignPassenger(""); setAssignModal(true); }} />
            )}
            {r.status === "active" && (
              <TableActionButton icon={<Lock size={15} />} label={t(lc, "block")} onClick={() => block(r.card_uid)} tone="danger" />
            )}
          </div>
        )},
      ]} rows={filtered} rowKey={(r) => r.uuid} loading={loading} emptyMessage={t(lc, "noCards")} />

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing?.card_number || ""} fields={viewing ? [
        { label: t(lc, "type"), value: viewing.card_type === "physical" ? "Fisico" : "Digital" },
        { label: "UID", value: viewing.card_uid },
        { label: t(lc, "cardTechnology"), value: viewing.card_technology },
        { label: t(lc, "status"), value: <StatusBadge value={viewing.status} /> },
        { label: t(lc, "passenger"), value: viewing.passenger_name || t(lc, "noPassenger") },
        { label: t(lc, "phone"), value: viewing.passenger_phone || "-" },
        { label: t(lc, "balance"), value: viewing.balance !== null ? formatCurrency(viewing.balance) : "-" },
        { label: t(lc, "batch"), value: viewing.issued_batch || "-" },
        { label: "Serial", value: viewing.batch_serial || "-" },
        { label: t(lc, "manufacturer"), value: viewing.manufacturer || "-" },
        { label: t(lc, "activated"), value: formatDateTime(viewing.activated_at) },
        { label: t(lc, "created"), value: formatDateTime(viewing.created_at) },
      ] : []} />

      <AdminModal open={assignModal} onClose={() => setAssignModal(false)} title="Atribuir Cartao a Passageiro">
        <div className="admin-form">
          <p style={{ fontSize: 13, color: "var(--app-text-muted)", marginBottom: 12 }}>
            Cartao <strong>{assignCard?.card_number}</strong> sera activado e vinculado ao passageiro seleccionado.
          </p>
          <label className="field">
            <span>{t(lc, "passenger")}</span>
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

      <AdminModal open={importModal} onClose={() => setImportModal(false)} title="Importar Excel">
        <div className="admin-form">
          <p style={{ fontSize: 13, color: "var(--app-text-muted)", marginBottom: 8 }}>
            Descarregue o template Excel e preencha com os dados do lote de cartoes.
          </p>
          <p style={{ fontSize: 12, color: "var(--app-text-muted)", marginBottom: 12 }}>
            Colunas: card_uid, card_number, card_technology, issued_batch, batch_serial, manufacturer
          </p>
          <label className="field">
            <span>Ficheiro Excel</span>
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
