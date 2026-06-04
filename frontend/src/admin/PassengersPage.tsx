import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Eye, FileText, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { apiFetch, apiPost, apiPatch, apiDelete } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { AdminModal, DataTable, MetricCard, PageFrame, SectionCard, StatusBadge, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";
import { useConfirm } from "../ui/ConfirmDialog";

interface Passenger { id: number; uuid: string; full_name: string; phone_number: string; email: string; document_type: string; document_number: string; status: string; has_user_account: boolean; created_at: string; }
interface CardInfo { id: number; card_number: string; card_type: string; status: string; balance: string | null; card_uid?: string; created_at?: string; }
interface WalletInfo { uuid: string; balance_cached: string; currency: string; status: string; }
interface PkgInfo { package_name: string; discount_type: string; special_balance: string; trips_remaining: number; status: string; expires_at: string; }
interface TxInfo { id: number; type: string; direction: string; amount: string; balance_after: string; reference: string; source: string; created_at: string; status: string; }

const TX_TYPE_LABELS: Record<string, string> = {
  topup: "Recarga",
  fare_debit: "Viagem",
  refund: "Reembolso",
  reversal: "Reversao",
  adjustment: "Ajuste",
  card_transfer: "Transferencia",
  fee: "Taxa/Pacote",
};
const txTypeLabel = (t: string) => TX_TYPE_LABELS[t] || t;

export default function PassengersPage({ embedded }: { embedded?: boolean }) {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const { confirm, dialog: confirmDialog } = useConfirm();
  const loader = useCallback(() => apiFetch("/api/passengers/", token!).then((d) => d.results || d), [token]);
  const { data: rows, loading, reload } = useAsyncData<Passenger[]>(loader, [token]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [viewing, setViewing] = useState<Passenger | null>(null);
  const [viewCards, setViewCards] = useState<CardInfo[]>([]);
  const [viewWallet, setViewWallet] = useState<WalletInfo | null>(null);
  const [viewPkgs, setViewPkgs] = useState<PkgInfo[]>([]);
  const [viewTxs, setViewTxs] = useState<TxInfo[]>([]);
  const [extractModal, setExtractModal] = useState(false);
  const [extractFrom, setExtractFrom] = useState("");
  const [extractTo, setExtractTo] = useState("");
  const [accountBusy, setAccountBusy] = useState(false);
  const [form, setForm] = useState({ full_name: "", phone_number: "", email: "", document_type: "", document_number: "", create_account: false, notify_by_sms: true });
  const f = (k: string, v: string | boolean) => setForm((p) => ({ ...p, [k]: v }));
  const reset = () => { setEditId(null); setModalOpen(false); setForm({ full_name: "", phone_number: "", email: "", document_type: "", document_number: "", create_account: false, notify_by_sms: true }); };

  const openDetail = async (p: Passenger) => {
    setViewing(p);
    setViewCards([]); setViewWallet(null); setViewPkgs([]); setViewTxs([]);
    try {
      const [cards, wallets, pkgs] = await Promise.all([
        apiFetch(`/api/cards/?passenger=${p.id}`, token!).then((d) => d.results || d).catch(() => []),
        apiFetch("/api/wallets/", token!).then((d) => (d.results || d).find((w: any) => w.passenger_account_id === p.id) || null).catch(() => null),
        apiFetch(`/api/passenger-packages/?passenger=${p.id}`, token!).then((d) => d.results || d).catch(() => []),
      ]);
      setViewCards(cards);
      setViewWallet(wallets);
      setViewPkgs(pkgs);
      if (wallets?.uuid) {
        const txs = await apiFetch(`/api/wallet-transactions/?wallet=${wallets.uuid}`, token!)
          .then((d) => d.results || d).catch(() => []);
        setViewTxs(Array.isArray(txs) ? txs.slice(0, 10) : []);
      }
    } catch {}
  };

  const downloadExtract = async () => {
    if (!viewing) return;
    try {
      const params = new URLSearchParams();
      if (extractFrom) params.set("date_from", extractFrom);
      if (extractTo) params.set("date_to", extractTo);
      const res = await fetch(`/api/passengers/${viewing.id}/extract/?${params}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) { showToast("danger", "Erro ao gerar extracto."); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = `extracto-${viewing.full_name.replace(/\s/g, "_")}.pdf`; a.click();
      URL.revokeObjectURL(url);
      setExtractModal(false);
    } catch { showToast("danger", "Erro ao gerar extracto."); }
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true);
    try {
      const payload = editId ? {
        full_name: form.full_name,
        phone_number: form.phone_number,
        email: form.email,
        document_type: form.document_type,
        document_number: form.document_number,
      } : form;
      if (editId) { await apiPatch(`/api/passengers/${editId}/`, token!, payload); showToast("success", t(lc, "update")); }
      else { await apiPost("/api/passengers/", token!, payload); showToast("success", t(lc, "create")); }
      reset(); reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
    finally { setBusy(false); }
  };

  const createAccessAccount = async () => {
    if (!viewing) return;
    setAccountBusy(true);
    try {
      await apiPost(`/api/passengers/${viewing.id}/create-account/`, token!, { notify_by_sms: true });
      showToast("success", "Conta criada e SMS enviado.");
      setViewing({ ...viewing, has_user_account: true });
      reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
    finally { setAccountBusy(false); }
  };

  const remove = async (r: Passenger) => {
    const ok = await confirm({ title: t(lc, "delete"), message: `Tem a certeza que pretende eliminar ${r.full_name}?`, tone: "danger" });
    if (!ok) return;
    try { await apiDelete(`/api/passengers/${r.id}/`, token!); showToast("success", t(lc, "delete")); reload(); }
    catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
  };

  return (
    <PageFrame kicker={t(lc, "management")} title={t(lc, "passengers")}
      action={<>
        <button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={15} /><span>{t(lc, "refresh")}</span></button>
        <button className="primary-button" onClick={() => { reset(); setModalOpen(true); }} type="button"><Plus size={15} /> {t(lc, "newPassenger")}</button>
      </>}>
      <div className="admin-metric-grid">
        <MetricCard label={t(lc, "total")} value={String((rows || []).length)} />
        <MetricCard label={t(lc, "active")} value={String((rows || []).filter((r) => r.status === "active").length)} />
      </div>
      <SectionCard title={t(lc, "passengers")}>
        <DataTable columns={[
          { header: t(lc, "name"), sortKey: "full_name", render: (r: Passenger) => <TablePrimaryCell title={r.full_name} subtitle={r.phone_number} /> },
          { header: t(lc, "status"), sortKey: "status", render: (r: Passenger) => <StatusBadge value={r.status} /> },
          { header: t(lc, "actions"), className: "table-actions-cell", render: (r: Passenger) => (
            <div className="admin-inline-actions">
              <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => openDetail(r)} />
              <TableActionButton icon={<Pencil size={15} />} label={t(lc, "edit")} onClick={() => { setEditId(r.id); setModalOpen(true); setForm({ full_name: r.full_name, phone_number: r.phone_number, email: r.email, document_type: r.document_type || "", document_number: r.document_number, create_account: false, notify_by_sms: true }); }} />
              <TableActionButton icon={<Trash2 size={15} />} label={t(lc, "delete")} onClick={() => remove(r)} tone="danger" />
            </div>
          )},
        ]} rows={rows || []} rowKey={(r) => r.uuid} loading={loading} emptyMessage={t(lc, "noPassengers")} />
      </SectionCard>

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing?.full_name || ""} fields={viewing ? [
        { label: t(lc, "phone"), value: viewing.phone_number },
        { label: t(lc, "email"), value: viewing.email || "-" },
        { label: t(lc, "documentType"), value: viewing.document_type === "bi" ? t(lc, "documentBi") : viewing.document_type === "passport" ? t(lc, "documentPassport") : viewing.document_type === "driving_license" ? t(lc, "documentDrivingLicense") : "-" },
        { label: t(lc, "document"), value: viewing.document_number || "-" },
        { label: "Conta", value: viewing.has_user_account ? "Criada" : "Nao criada" },
        { label: t(lc, "status"), value: <StatusBadge value={viewing.status} /> },
        { label: t(lc, "created"), value: formatDateTime(viewing.created_at) },
      ] : []}>
        {viewing && (
          <>
            {viewWallet && (
              <div style={{ marginTop: 16, padding: "12px 0", borderTop: "1px solid var(--app-border)" }}>
                <h4 style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--app-text-muted)", marginBottom: 8 }}>{t(lc, "balance")}</h4>
                <div style={{ fontSize: 22, fontWeight: 800, color: "var(--app-accent)" }}>{formatCurrency(viewWallet.balance_cached, viewWallet.currency)}</div>
                <div style={{ fontSize: 11, color: "var(--app-text-muted)" }}>{t(lc, "status")}: {viewWallet.status}</div>
              </div>
            )}

            {viewCards.length > 0 && (
              <div style={{ marginTop: 16, padding: "12px 0", borderTop: "1px solid var(--app-border)" }}>
                <h4 style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--app-text-muted)", marginBottom: 8 }}>
                  {t(lc, "cards")} ({viewCards.length})
                </h4>
                {viewCards.map((c, i) => (
                  <div key={i} style={{ padding: "8px 0", borderBottom: "1px solid var(--app-border)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div>
                        <strong style={{ fontSize: 13 }}>{c.card_number || "(sem numero)"}</strong>
                        <div style={{ fontSize: 11, color: "var(--app-text-muted)" }}>
                          {c.card_type === "physical" ? "Fisico" : c.card_type === "digital" ? "Digital" : c.card_type}
                          {c.card_uid ? ` · UID ${c.card_uid.slice(0, 8)}...` : ""}
                        </div>
                        {c.created_at && (
                          <div style={{ fontSize: 10.5, color: "var(--app-text-muted)" }}>
                            Emitido em {formatDateTime(c.created_at)}
                          </div>
                        )}
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <StatusBadge value={c.status} />
                        {c.balance !== null && (
                          <div style={{ fontSize: 12, marginTop: 2 }}>{formatCurrency(c.balance)}</div>
                        )}
                      </div>
                    </div>
                    {c.id && (
                      <div style={{ marginTop: 6 }}>
                        <a href={`/admin/cards?card=${c.id}`}
                           style={{ fontSize: 11, color: "var(--app-accent)", textDecoration: "none" }}>
                          Ver detalhes do cartao →
                        </a>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {viewTxs.length > 0 && (
              <div style={{ marginTop: 16, padding: "12px 0", borderTop: "1px solid var(--app-border)" }}>
                <h4 style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--app-text-muted)", marginBottom: 8 }}>
                  Ultimas transaccoes ({viewTxs.length})
                </h4>
                {viewTxs.map((tx) => (
                  <div key={tx.id} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--app-border)" }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 12.5, fontWeight: 700 }}>{txTypeLabel(tx.type)}</div>
                      <div style={{ fontSize: 10.5, color: "var(--app-text-muted)" }}>
                        {formatDateTime(tx.created_at)}
                      </div>
                      {tx.reference && (
                        <div style={{ fontSize: 10, color: "var(--app-text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 200 }}>
                          {tx.reference}
                        </div>
                      )}
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{
                        fontSize: 13, fontWeight: 800,
                        color: tx.direction === "credit" ? "var(--success, #1FB04A)" : "var(--danger, #EF4444)",
                      }}>
                        {tx.direction === "credit" ? "+" : "-"}{formatCurrency(tx.amount)}
                      </div>
                      <div style={{ fontSize: 10, color: "var(--app-text-muted)" }}>
                        Saldo {formatCurrency(tx.balance_after)}
                      </div>
                    </div>
                  </div>
                ))}
                {viewWallet?.uuid && (
                  <div style={{ marginTop: 8, textAlign: "right" }}>
                    <a href={`/admin/wallet-transactions?wallet=${viewWallet.uuid}`}
                       style={{ fontSize: 11, color: "var(--app-accent)", textDecoration: "none" }}>
                      Ver todas as transaccoes →
                    </a>
                  </div>
                )}
              </div>
            )}

            {viewPkgs.length > 0 && (
              <div style={{ marginTop: 16, padding: "12px 0", borderTop: "1px solid var(--app-border)" }}>
                <h4 style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--app-text-muted)", marginBottom: 8 }}>{t(lc, "packages")}</h4>
                {viewPkgs.map((p, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--app-border)" }}>
                    <div><strong style={{ fontSize: 13 }}>{p.package_name}</strong><br /><span style={{ fontSize: 11, color: "var(--app-text-muted)" }}>{p.discount_type.replace(/_/g, " ")}</span></div>
                    <div style={{ textAlign: "right" }}><StatusBadge value={p.status} /><div style={{ fontSize: 11, color: "var(--app-text-muted)" }}>{formatDateTime(p.expires_at)}</div></div>
                  </div>
                ))}
              </div>
            )}

            <div style={{ marginTop: 16, padding: "12px 0", borderTop: "1px solid var(--app-border)" }}>
              {!viewing.has_user_account && (
                <button className="primary-button" onClick={createAccessAccount} disabled={accountBusy || !viewing.phone_number} type="button" style={{ width: "100%", marginBottom: 10 }}>
                  {accountBusy ? t(lc, "saving") : "Criar conta e notificar por SMS"}
                </button>
              )}
              <button className="icon-text-button" onClick={() => { setExtractFrom(""); setExtractTo(""); setExtractModal(true); }} type="button" style={{ width: "100%" }}>
                <FileText size={15} /><span>Gerar Extracto</span>
              </button>
            </div>
          </>
        )}
      </DetailDrawer>

      <AdminModal open={extractModal} onClose={() => setExtractModal(false)} title="Extracto de Transaccoes">
        <div className="admin-form">
          <p style={{ fontSize: 13, color: "var(--app-text-muted)", marginBottom: 12 }}>
            Seleccione o periodo para gerar o extracto PDF de <strong>{viewing?.full_name}</strong>.
          </p>
          <div className="admin-form-grid">
            <label className="field"><span>Data Inicio</span><input type="date" value={extractFrom} onChange={(e) => setExtractFrom(e.target.value)} /></label>
            <label className="field"><span>Data Fim</span><input type="date" value={extractTo} onChange={(e) => setExtractTo(e.target.value)} /></label>
          </div>
          <div className="admin-form-actions">
            <button className="primary-button" onClick={downloadExtract} type="button"><FileText size={15} /> Gerar PDF</button>
            <button className="secondary-button" onClick={() => setExtractModal(false)} type="button">{t(lc, "cancel")}</button>
          </div>
        </div>
      </AdminModal>

      <AdminModal open={modalOpen} onClose={reset} title={editId ? t(lc, "editPassenger") : t(lc, "newPassenger")}>
        <form className="admin-form" onSubmit={submit}>
          <div className="admin-form-grid">
            <label className="field"><span>{t(lc, "fullName")}</span><input required value={form.full_name} onChange={(e) => f("full_name", e.target.value)} /></label>
            <label className="field"><span>{t(lc, "phone")}</span><input required value={form.phone_number} onChange={(e) => f("phone_number", e.target.value)} /></label>
            <label className="field"><span>{t(lc, "email")}</span><input type="email" value={form.email} onChange={(e) => f("email", e.target.value)} /></label>
            <label className="field"><span>{t(lc, "documentType")}</span>
              <select value={form.document_type} onChange={(e) => f("document_type", e.target.value)}>
                <option value="">{t(lc, "select")}</option>
                <option value="bi">{t(lc, "documentBi")}</option>
                <option value="passport">{t(lc, "documentPassport")}</option>
                <option value="driving_license">{t(lc, "documentDrivingLicense")}</option>
              </select>
            </label>
            <label className="field"><span>{t(lc, "document")}</span><input value={form.document_number} onChange={(e) => f("document_number", e.target.value)} /></label>
            {!editId && (
              <>
                <label className="admin-check-row"><input type="checkbox" checked={form.create_account} onChange={(e) => f("create_account", e.target.checked)} /><span>Criar conta de acesso</span></label>
                <label className="admin-check-row"><input type="checkbox" checked={form.notify_by_sms} onChange={(e) => f("notify_by_sms", e.target.checked)} disabled={!form.create_account} /><span>Notificar por SMS</span></label>
              </>
            )}
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
