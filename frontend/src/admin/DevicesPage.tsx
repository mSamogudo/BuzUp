import { useCallback, useState, type FormEvent } from "react";
import { Check, Copy, Eye, Lock, RefreshCw, RotateCcw, Trash2, User, UserPlus, X, KeyRound } from "lucide-react";
import { apiFetch, apiPost, apiDelete } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
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
      showToast("danger", err instanceof Error ? err.message : "Erro");
    } finally {
      setBusy(false);
    }
  };

  const regenerateCode = async (d: Device) => {
    const ok = await confirm({
      title: "Gerar novo codigo?",
      message: `Vai invalidar o codigo actual de ${d.serial_number}. Se o POS estava activo, sera necessario re-activar com o novo codigo.`,
      tone: "danger",
      confirmLabel: "Gerar novo",
    });
    if (!ok) return;
    try {
      const res = await apiPost(`/api/admin/devices/${d.id}/regenerate-code/`, token!, {});
      const code = (res && res.activation_code) || "";
      setGeneratedCode({ device: d, code, agent: d.assigned_agent_name || "" });
      reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
  };

  const approve = async (d: Device) => {
    const ok = await confirm({ title: "Activar dispositivo", message: `Activar ${d.serial_number} sem codigo?`, tone: "default" });
    if (!ok) return;
    try {
      await apiPost(`/api/admin/devices/${d.id}/approve/`, token!, {});
      showToast("success", "Activado.");
      reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
  };

  const reject = async (d: Device) => {
    const ok = await confirm({ title: "Rejeitar dispositivo", message: `Rejeitar ${d.serial_number}?`, tone: "danger", confirmLabel: "Rejeitar" });
    if (!ok) return;
    try {
      await apiPost(`/api/admin/devices/${d.id}/reject/`, token!, { rejection_reason: "Rejeitado pelo admin." });
      showToast("success", "Rejeitado.");
      reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
  };

  const block = async (d: Device) => {
    const newStatus = d.status === "blocked" ? "active" : "blocked";
    const ok = await confirm({
      title: newStatus === "blocked" ? "Bloquear dispositivo" : "Desbloquear dispositivo",
      message: `${newStatus === "blocked" ? "Bloquear" : "Desbloquear"} ${d.serial_number}?`,
      tone: newStatus === "blocked" ? "danger" : "default",
    });
    if (!ok) return;
    try {
      await apiFetch(`/api/admin/devices/${d.id}/`, token!, { method: "PATCH", body: JSON.stringify({ status: newStatus }) });
      showToast("success", newStatus === "blocked" ? "Bloqueado." : "Desbloqueado.");
      reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
  };

  const remove = async (d: Device) => {
    const ok = await confirm({ title: "Eliminar dispositivo", message: `Eliminar ${d.serial_number}? Esta accao nao pode ser desfeita.`, tone: "danger", confirmLabel: "Eliminar" });
    if (!ok) return;
    try { await apiDelete(`/api/admin/devices/${d.id}/`, token!); showToast("success", "Eliminado."); reload(); }
    catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
  };

  const copyCode = (code: string) => {
    if (!code) return;
    navigator.clipboard.writeText(code).then(() => showToast("success", `Codigo copiado: ${code}`));
  };

  const renderRow = (rows: Device[]) => (
    <DataTable columns={[
      { header: t(lc, "serial"), render: (r: Device) => <TablePrimaryCell
        title={r.serial_number}
        subtitle={`${r.manufacturer} ${r.model_name}`.trim() || r.device_type}
        meta={r.app_version ? `v${r.app_version}` : undefined} /> },
      { header: "Agente", render: (r: Device) => r.assigned_agent_name || <span style={{ color: "var(--app-text-muted)" }}>—</span> },
      { header: t(lc, "status"), render: (r: Device) => <StatusBadge value={r.status} /> },
      { header: t(lc, "lastContact"), render: (r: Device) => formatDateTime(r.last_seen_at) },
      { header: t(lc, "actions"), className: "table-actions-cell", render: (r: Device) => (
        <div className="admin-inline-actions">
          <TableActionButton icon={<Eye size={15} />} label="Ver" onClick={() => setViewing(r)} />
          {(r.status === "self_onboarded" || r.status === "pending_activation") && (
            <>
              <TableActionButton icon={<UserPlus size={15} />} label={r.assigned_agent_id ? "Mudar agente" : "Alocar agente"} onClick={() => openAllocate(r)} />
              {r.assigned_agent_id && (
                <TableActionButton icon={<KeyRound size={15} />} label="Gerar novo codigo" onClick={() => regenerateCode(r)} />
              )}
              <TableActionButton icon={<Check size={15} />} label="Activar agora" onClick={() => approve(r)} />
              <TableActionButton icon={<X size={15} />} label="Rejeitar" onClick={() => reject(r)} tone="danger" />
            </>
          )}
          {r.status === "active" && (
            <>
              <TableActionButton icon={<User size={15} />} label="Mudar agente" onClick={() => openAllocate(r)} />
              <TableActionButton icon={<KeyRound size={15} />} label="Gerar novo codigo" onClick={() => regenerateCode(r)} />
              <TableActionButton icon={<Lock size={15} />} label="Bloquear" onClick={() => block(r)} tone="danger" />
            </>
          )}
          {r.status === "blocked" && (
            <TableActionButton icon={<RotateCcw size={15} />} label="Desbloquear" onClick={() => block(r)} />
          )}
          <TableActionButton icon={<Trash2 size={15} />} label="Eliminar" onClick={() => remove(r)} tone="danger" />
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
        <MetricCard label="Pendentes" value={String(counts.pending)} />
        <MetricCard label="Bloqueados" value={String(counts.blocked)} />
      </div>

      <TabBar items={[
        { key: "all", label: "Todos", count: counts.total },
        { key: "pending", label: "Pendentes", count: counts.pending },
        { key: "active", label: "Activos", count: counts.active },
        { key: "blocked", label: "Bloqueados", count: counts.blocked },
      ]} value={tab} onChange={(k) => setTab(k as "all" | "pending" | "active" | "blocked")} />

      <SectionCard title="Terminais">
        {renderRow(filterRows(tab))}
      </SectionCard>

      <DetailDrawer open={!!viewing} onClose={() => setViewing(null)} title={viewing?.serial_number || ""} fields={viewing ? [
        { label: "Serial", value: viewing.serial_number },
        { label: "Tipo", value: viewing.device_type },
        { label: "Fabricante", value: viewing.manufacturer || "-" },
        { label: "Modelo", value: viewing.model_name || "-" },
        { label: "Versao", value: viewing.app_version || "-" },
        { label: "Estado", value: <StatusBadge value={viewing.status} /> },
        { label: "Agente alocado", value: viewing.assigned_agent_name || "—" },
        { label: "Activado em", value: viewing.activated_at ? formatDateTime(viewing.activated_at) : "—" },
        { label: "Ultimo contacto", value: formatDateTime(viewing.last_seen_at) },
        { label: "Registado em", value: formatDateTime(viewing.created_at) },
      ] : []} />

      <AdminModal open={!!allocateDevice} onClose={closeAllocate} title={`Alocar agente · ${allocateDevice?.serial_number || ""}`}>
        <form className="admin-form" onSubmit={submitAllocate}>
          <p style={{ fontSize: 13, color: "var(--app-text-muted)", marginBottom: 12 }}>
            Ao alocar, o sistema gera um <strong>novo codigo de activacao</strong> para entregar ao agente.
            O codigo aparece na proxima janela.
          </p>
          <div className="admin-form-grid">
            <label className="field admin-field-span-full">
              <span>Agente</span>
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
        title="Codigo de Activacao Gerado"
      >
        {generatedCode && (
          <div className="admin-form">
            <p style={{ marginBottom: 8 }}>
              Entregue este codigo ao agente <strong>{generatedCode.agent || "—"}</strong> para activar
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
                CODIGO DE ACTIVACAO
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
                <Copy size={14} /> Copiar
              </button>
            </div>
            <p style={{ fontSize: 12, color: "var(--app-text-muted)" }}>
              O agente deve introduzir este codigo no ecra de activacao do POS.
              Para gerar um novo codigo (caso este seja comprometido) use a accao "Gerar novo codigo" na tabela.
            </p>
            <div className="admin-form-actions">
              <button className="primary-button" onClick={() => setGeneratedCode(null)} type="button">Concluido</button>
            </div>
          </div>
        )}
      </AdminModal>
      {confirmDialog}
    </PageFrame>
  );
}
