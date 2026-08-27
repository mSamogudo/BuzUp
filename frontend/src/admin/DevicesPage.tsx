import { useCallback, useState, type FormEvent } from "react";
import { Check, Copy, Eye, Lock, RefreshCw, RotateCcw, Trash2, User, UserPlus, X, KeyRound } from "lucide-react";
import { apiFetch, apiPost, apiDelete } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { mensagemDeErro } from "../lib/errors";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { AdminModal, DataTable, MetricCard, PageFrame, SectionCard, StatusBadge, TabBar, TableActionButton, TablePrimaryCell, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";
import { useConfirm } from "../ui/ConfirmDialog";

interface Device {
  id: number; uuid: string; serial_number: string; device_type: string;
  manufacturer: string; model_name: string; status: string; app_version: string;
  last_seen_at: string | null; activation_code: string;
  assigned_agent_id: number | null; assigned_agent_name: string;
  activated_at: string | null; created_at: string;
}
interface AgentOpt { id: number; user_id: number | null; full_name: string; phone: string; status: string; }

export default function DevicesPage({ embedded }: { embedded?: boolean }) {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const { confirm, dialog: confirmDialog } = useConfirm();
  const devLoader = useCallback(() => apiFetch("/api/admin/devices/", token!).then((d) => d.results || d), [token]);
  const agentLoader = useCallback(() => apiFetch("/api/agents/", token!).then((d) => d.results || d), [token]);
  const { data: devices, loading, reload } = useAsyncData<Device[]>(devLoader, [token]);
  const { data: agents } = useAsyncData<AgentOpt[]>(agentLoader, [token]);

  const [viewing, setViewing] = useState<Device | null>(null);
  const [tab, setTab] = useState<"all" | "pending" | "active" | "blocked">("all");
  const [allocateDevice, setAllocateDevice] = useState<Device | null>(null);
  const [allocateAgentId, setAllocateAgentId] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [generatedCode, setGeneratedCode] = useState<{ device: Device; code: string; agent: string } | null>(null);

  const filterRows = (status: string) => (devices || []).filter((d) => {
    if (status === "all") return true;
    if (status === "pending") return d.status === "self_onboarded" || d.status === "pending_activation";
    if (status === "active") return d.status === "active";
    if (status === "blocked") return d.status === "blocked" || d.status === "rejected" || d.status === "retired";
    return true;
  });

  const counts = {
    total: (devices || []).length,
    active: (devices || []).filter((d) => d.status === "active").length,
    pending: (devices || []).filter((d) => d.status === "self_onboarded" || d.status === "pending_activation").length,
    blocked: (devices || []).filter((d) => d.status === "blocked").length,
  };

  const openAllocate = (d: Device) => {
    setAllocateDevice(d);
    setAllocateAgentId(d.assigned_agent_id ? String(d.assigned_agent_id) : "");
  };
  const closeAllocate = () => { setAllocateDevice(null); setAllocateAgentId(""); };

  const submitAllocate = async (e: FormEvent) => {
    e.preventDefault();
    if (!allocateDevice || !allocateAgentId) return;
    setBusy(true);
    try {
      const agent = (agents || []).find((a) => String(a.id) === allocateAgentId);
      const agentUserId = agent?.user_id;
      const res = await apiPost(`/api/admin/devices/${allocateDevice.id}/allocate-agent/`, token!, {
        agent_user_id: agentUserId,
      });
      const code = (res && res.activation_code) || "";
      const dev = { ...allocateDevice, status: res.status, activation_code: code, assigned_agent_name: agent?.full_name || "" };
      setGeneratedCode({ device: dev, code, agent: agent?.full_name || "" });
      closeAllocate();
      reload();
    } catch (err) {
      showToast("danger", mensagemDeErro(err, lc));
    } finally {
      setBusy(false);
    }
  };

  const regenerateCode = async (d: Device) => {
    const ok = await confirm({
      title: t(lc, "newCodeConfirm"),
      message: t(lc, "confirmNewCode", { n: d.serial_number }),
      tone: "danger",
      confirmLabel: "Gerar novo",
    });
    if (!ok) return;
    try {
      const res = await apiPost(`/api/admin/devices/${d.id}/regenerate-code/`, token!, {});
      const code = (res && res.activation_code) || "";
      setGeneratedCode({ device: d, code, agent: d.assigned_agent_name || "" });
      reload();
    } catch (err) { showToast("danger", mensagemDeErro(err, lc)); }
  };

  const approve = async (d: Device) => {
    const ok = await confirm({ title: t(lc, "activateDevice"), message: t(lc, "confirmActivateNoCode", { n: d.serial_number }), tone: "default" });
    if (!ok) return;
    try {
      await apiPost(`/api/admin/devices/${d.id}/approve/`, token!, {});
      showToast("success", t(lc, "okDeviceActivated"));
      reload();
    } catch (err) { showToast("danger", mensagemDeErro(err, lc)); }
  };

  const reject = async (d: Device) => {
    const ok = await confirm({ title: t(lc, "rejectDevice"), message: t(lc, "confirmReject", { n: d.serial_number }), tone: "danger", confirmLabel: t(lc, "reject") });
    if (!ok) return;
    try {
      await apiPost(`/api/admin/devices/${d.id}/reject/`, token!, { rejection_reason: "Rejeitado pelo admin." });
      showToast("success", t(lc, "okDeviceRejected"));
      reload();
    } catch (err) { showToast("danger", mensagemDeErro(err, lc)); }
  };

  const block = async (d: Device) => {
    const newStatus = d.status === "blocked" ? "active" : "blocked";
    const ok = await confirm({
      title: newStatus === "blocked" ? "Bloquear dispositivo" : "Desbloquear dispositivo",
      message: t(lc, "confirmToggle", { a: newStatus === "blocked" ? t(lc, "block") : t(lc, "unblock"), n: d.serial_number }),
      tone: newStatus === "blocked" ? "danger" : "default",
    });
    if (!ok) return;
    try {
      await apiFetch(`/api/admin/devices/${d.id}/`, token!, { method: "PATCH", body: JSON.stringify({ status: newStatus }) });
      showToast("success", newStatus === "blocked" ? t(lc, "okDeviceBlocked") : t(lc, "okDeviceUnblocked"));
      reload();
    } catch (err) { showToast("danger", mensagemDeErro(err, lc)); }
  };

  const remove = async (d: Device) => {
    const ok = await confirm({ title: t(lc, "deleteDevice"), message: t(lc, "confirmDelete", { n: d.serial_number }), tone: "danger", confirmLabel: t(lc, "delete") });
    if (!ok) return;
    try { await apiDelete(`/api/admin/devices/${d.id}/`, token!); showToast("success", t(lc, "okDeviceDeleted")); reload(); }
    catch (err) { showToast("danger", mensagemDeErro(err, lc)); }
  };

  const copyCode = (code: string) => {
    if (!code) return;
    navigator.clipboard.writeText(code).then(() => showToast("success", t(lc, "okCodeCopied")));
  };

  const renderRow = (rows: Device[]) => (
    <DataTable columns={[
      { header: t(lc, "serial"), render: (r: Device) => <TablePrimaryCell
        title={r.serial_number}
        subtitle={`${r.manufacturer} ${r.model_name}`.trim() || r.device_type}
        meta={r.app_version ? `v${r.app_version}` : undefined} /> },
      { header: t(lc, "agent"), render: (r: Device) => r.assigned_agent_name || <span style={{ color: "var(--app-text-muted)" }}>—</span> },
      { header: t(lc, "status"), render: (r: Device) => <StatusBadge value={r.status} /> },
      { header: t(lc, "lastContact"), render: (r: Device) => formatDateTime(r.last_seen_at) },
      { header: t(lc, "actions"), className: "table-actions-cell", render: (r: Device) => (
        <div className="admin-inline-actions">
          <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => setViewing(r)} />
          {(r.status === "self_onboarded" || r.status === "pending_activation") && (
            <>
              <TableActionButton icon={<UserPlus size={15} />} label={r.assigned_agent_id ? t(lc, "changeAgent") : "Alocar agente"} onClick={() => openAllocate(r)} />
              {r.assigned_agent_id && (
                <TableActionButton icon={<KeyRound size={15} />} label={t(lc, "newCode")} onClick={() => regenerateCode(r)} />
              )}
              <TableActionButton icon={<Check size={15} />} label={t(lc, "activateNow")} onClick={() => approve(r)} />
              <TableActionButton icon={<X size={15} />} label={t(lc, "reject")} onClick={() => reject(r)} tone="danger" />
            </>
          )}
          {r.status === "active" && (
            <>
              <TableActionButton icon={<User size={15} />} label={t(lc, "changeAgent")} onClick={() => openAllocate(r)} />
              <TableActionButton icon={<KeyRound size={15} />} label={t(lc, "newCode")} onClick={() => regenerateCode(r)} />
              <TableActionButton icon={<Lock size={15} />} label={t(lc, "block")} onClick={() => block(r)} tone="danger" />
            </>
          )}
          {r.status === "blocked" && (
            <TableActionButton icon={<RotateCcw size={15} />} label={t(lc, "unblock")} onClick={() => block(r)} />
          )}
          <TableActionButton icon={<Trash2 size={15} />} label={t(lc, "delete")} onClick={() => remove(r)} tone="danger" />
        </div>
      )},
    ]} rows={rows} rowKey={(r) => r.uuid} loading={loading} emptyMessage={t(lc, "noDevices")} />
  );

  return (
    <PageFrame kicker={t(lc, "operation")} title={t(lc, "devices")}
      action={<button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={16} /><span>{t(lc, "refresh")}</span></button>}>
      <div className="admin-metric-grid">
        <MetricCard label={t(lc, "total")} value={String(counts.total)} />
        <MetricCard label={t(lc, "active")} value={String(counts.active)} />
        <MetricCard label={t(lc, "pendingPl")} value={String(counts.pending)} />
        <MetricCard label={t(lc, "blockedPl")} value={String(counts.blocked)} />
      </div>

      <TabBar items={[
        { key: "all", label: t(lc, "all"), count: counts.total },
        { key: "pending", label: t(lc, "pendingPl"), count: counts.pending },
        { key: "active", label: t(lc, "activePl"), count: counts.active },
        { key: "blocked", label: t(lc, "blockedPl"), count: counts.blocked },
      ]} value={tab} onChange={(k) => setTab(k as "all" | "pending" | "active" | "blocked")} />

      <SectionCard title={t(lc, "devices")}>
        {renderRow(filterRows(tab))}
      </SectionCard>

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing?.serial_number || ""} fields={viewing ? [
        { label: t(lc, "serial"), value: viewing.serial_number },
        { label: t(lc, "type"), value: viewing.device_type },
        { label: t(lc, "manufacturer"), value: viewing.manufacturer || "-" },
        { label: t(lc, "model"), value: viewing.model_name || "-" },
        { label: t(lc, "version"), value: viewing.app_version || "-" },
        { label: t(lc, "status"), value: <StatusBadge value={viewing.status} /> },
        { label: t(lc, "assignedAgent"), value: viewing.assigned_agent_name || "—" },
        { label: t(lc, "activatedAt"), value: viewing.activated_at ? formatDateTime(viewing.activated_at) : "—" },
        { label: t(lc, "lastSeen"), value: formatDateTime(viewing.last_seen_at) },
        { label: t(lc, "registeredAt"), value: formatDateTime(viewing.created_at) },
      ] : []} />

      <AdminModal open={!!allocateDevice} onClose={closeAllocate} title={`Alocar agente · ${allocateDevice?.serial_number || ""}`}>
        <form className="admin-form" onSubmit={submitAllocate}>
          <p style={{ fontSize: 13, color: "var(--app-text-muted)", marginBottom: 12 }}>
            {t(lc, "onAssignGenerates")} <strong>novo codigo de activacao</strong> para entregar ao agente.
            O codigo aparece na proxima janela.
          </p>
          <div className="admin-form-grid">
            <label className="field admin-field-span-full">
              <span>{t(lc, "agent")}</span>
              <select required value={allocateAgentId} onChange={(e) => setAllocateAgentId(e.target.value)}>
                <option value="">{t(lc, "select")}</option>
                {(agents || []).filter((a) => a.status === "active" && a.user_id).map((a) => (
                  <option key={a.id} value={a.id}>{a.full_name} · {a.phone}</option>
                ))}
              </select>
            </label>
          </div>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy || !allocateAgentId} type="submit">
              {busy ? "A guardar..." : "Alocar e gerar codigo"}
            </button>
            <button className="secondary-button" onClick={closeAllocate} type="button">{t(lc, "cancel")}</button>
          </div>
        </form>
      </AdminModal>

      <AdminModal
        open={!!generatedCode}
        onClose={() => setGeneratedCode(null)}
        title={t(lc, "activationCodeReady")}
      >
        {generatedCode && (
          <div className="admin-form">
            <p style={{ marginBottom: 8 }}>
              {t(lc, "giveCodeToAgent")} <strong>{generatedCode.agent || "—"}</strong> para activar
              o dispositivo <strong>{generatedCode.device.serial_number}</strong>.
            </p>
            <div style={{
              padding: "20px 16px",
              borderRadius: 12,
              background: "rgba(228, 123, 17, 0.08)",
              border: "2px dashed var(--app-accent)",
              textAlign: "center",
              margin: "12px 0",
            }}>
              <div style={{ fontSize: 11, color: "var(--app-text-muted)", textTransform: "uppercase", letterSpacing: 1, fontWeight: 700 }}>
                {t(lc, "activationCodeCaps")}
              </div>
              <div style={{
                fontSize: 40,
                fontWeight: 800,
                letterSpacing: 8,
                color: "var(--app-accent)",
                fontFamily: "ui-monospace, monospace",
                margin: "8px 0",
              }}>
                {generatedCode.code}
              </div>
              <button
                className="secondary-button"
                onClick={() => copyCode(generatedCode.code)}
                type="button"
                style={{ marginTop: 8 }}
              >
                <Copy size={14} /> {t(lc, "copy")}
              </button>
            </div>
            <p style={{ fontSize: 12, color: "var(--app-text-muted)" }}>
              O agente deve introduzir este codigo no ecra de activacao do POS.
              Para gerar um novo codigo (caso este seja comprometido) use a accao t(lc, "newCode") na tabela.
            </p>
            <div className="admin-form-actions">
              <button className="primary-button" onClick={() => setGeneratedCode(null)} type="button">{t(lc, "done")}</button>
            </div>
          </div>
        )}
      </AdminModal>
      {confirmDialog}
    </PageFrame>
  );
}
