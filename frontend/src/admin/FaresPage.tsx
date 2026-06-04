import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Eye, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { apiFetch, apiPost, apiPatch, apiDelete } from "../lib/api";
import { formatCurrency } from "../lib/format";
import { t } from "../lib/i18n";
import { showToast } from "../lib/toast";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { AdminModal, DataTable, PageFrame, SectionCard, StatusBadge, TableActionButton, TablePrimaryCell, TabBar, useAsyncData } from "../ui/common";
import { DetailDrawer } from "../ui/DetailDrawer";
import { useConfirm } from "../ui/ConfirmDialog";

interface FareProduct { id: number; uuid: string; name: string; product_type: string; status: string; }
interface FareRule { id: number; uuid: string; fare_product_id: number; fare_product_name: string; route_id: number | null; route_code: string; origin_stop_name: string; destination_stop_name: string; calculation_method: string; fixed_amount: string; amount_per_km: string; min_amount: string; max_amount: string; distance_min_km: string | null; distance_max_km: string | null; passenger_class: string; priority: number; origin_stop_id: number | null; destination_stop_id: number | null; }
interface AdminFee { id: number; uuid: string; code: string; name: string; kind: string; amount: string; currency: string; description: string; is_active: boolean; created_at: string; }
interface RouteOption { id: number; code: string; name: string; }
interface StopOption { id: number; code: string; name: string; }
interface RouteStopOption { stop_id: number; stop_code: string; stop_name: string; sequence: number; direction: string; }

export default function FaresPage({ embedded }: { embedded?: boolean }) {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const { confirm, dialog: confirmDialog } = useConfirm();
  const pLoader = useCallback(() => apiFetch("/api/fare-products/", token!).then((d) => d.results || d), [token]);
  const rLoader = useCallback(() => apiFetch("/api/fare-rules/", token!).then((d) => d.results || d), [token]);
  const routeLoader = useCallback(() => apiFetch("/api/routes/", token!).then((d) => d.results || d), [token]);
  const feesLoader = useCallback(() => apiFetch("/api/admin-fees/", token!).then((d) => d.results || d), [token]);
  const { data: products, loading: lP, reload: rP } = useAsyncData<FareProduct[]>(pLoader, [token]);
  const { data: rules, loading: lR, reload: rR } = useAsyncData<FareRule[]>(rLoader, [token]);
  const { data: routeOpts } = useAsyncData<RouteOption[]>(routeLoader, [token]);
  const { data: fees, loading: lF, reload: rF } = useAsyncData<AdminFee[]>(feesLoader, [token]);
  const reload = () => { rP(); rR(); rF(); };
  const [tab, setTab] = useState<"rules" | "products" | "fees">("rules");
  const [feeModal, setFeeModal] = useState(false);
  const [editFee, setEditFee] = useState<number | null>(null);
  const [feeForm, setFeeForm] = useState({ code: "", name: "", kind: "card_issuance", amount: "0.00", currency: "MZN", description: "", is_active: true });

  const [ruleModal, setRuleModal] = useState(false);
  const [prodModal, setProdModal] = useState(false);
  const [editR, setEditR] = useState<number | null>(null);
  const [editP, setEditP] = useState<number | null>(null);
  const [viewR, setViewR] = useState<FareRule | null>(null);
  const [busy, setBusy] = useState(false);
  const [pForm, setPForm] = useState({ name: "", product_type: "single_trip", status: "active" });
  const [rForm, setRForm] = useState({ fare_product: "", route: "", origin_stop: "", destination_stop: "", calculation_method: "fixed", fixed_amount: "", amount_per_km: "", min_amount: "", max_amount: "", distance_min_km: "", distance_max_km: "", passenger_class: "standard", priority: "0" });
  const [routeStopOpts, setRouteStopOpts] = useState<StopOption[]>([]);

  useEffect(() => {
    if (!ruleModal || !rForm.route) {
      setRouteStopOpts([]);
      return;
    }
    let active = true;
    apiFetch(`/api/routes/${rForm.route}/stops/`, token!)
      .then((data) => {
        if (!active) return;
        const seen = new Set<number>();
        const items = ((data.results || data || []) as RouteStopOption[])
          .filter((item) => {
            if (seen.has(item.stop_id)) return false;
            seen.add(item.stop_id);
            return true;
          })
          .map((item) => ({ id: item.stop_id, code: item.stop_code, name: item.stop_name }));
        setRouteStopOpts(items);
      })
      .catch(() => { if (active) setRouteStopOpts([]); });
    return () => { active = false; };
  }, [rForm.route, ruleModal, token]);

  const submitP = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true);
    try {
      if (editP) await apiPatch(`/api/fare-products/${editP}/`, token!, pForm);
      else await apiPost("/api/fare-products/", token!, pForm);
      showToast("success", editP ? t(lc, "update") : t(lc, "create")); setProdModal(false); setEditP(null); reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
    finally { setBusy(false); }
  };

  const submitR = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true);
    const payload: Record<string, unknown> = {
      fare_product: Number(rForm.fare_product),
      route: rForm.route ? Number(rForm.route) : null,
      calculation_method: rForm.calculation_method,
      passenger_class: rForm.passenger_class,
      priority: Number(rForm.priority),
      fixed_amount: rForm.fixed_amount || "0",
      amount_per_km: rForm.amount_per_km || "0",
      min_amount: rForm.min_amount || "0",
      max_amount: rForm.max_amount || "0",
    };
    if (rForm.calculation_method === "origin_destination") {
      payload.origin_stop = rForm.origin_stop ? Number(rForm.origin_stop) : null;
      payload.destination_stop = rForm.destination_stop ? Number(rForm.destination_stop) : null;
      payload.distance_min_km = null;
      payload.distance_max_km = null;
    } else if (rForm.calculation_method === "distance") {
      payload.origin_stop = null;
      payload.destination_stop = null;
      payload.distance_min_km = rForm.distance_min_km !== "" ? rForm.distance_min_km : null;
      payload.distance_max_km = rForm.distance_max_km !== "" ? rForm.distance_max_km : null;
    } else {
      payload.origin_stop = null;
      payload.destination_stop = null;
      payload.distance_min_km = null;
      payload.distance_max_km = null;
    }
    try {
      if (editR) await apiPatch(`/api/fare-rules/${editR}/`, token!, payload);
      else await apiPost("/api/fare-rules/", token!, payload);
      showToast("success", editR ? t(lc, "update") : t(lc, "create")); setRuleModal(false); setEditR(null); reload();
    } catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
    finally { setBusy(false); }
  };

  const method = rForm.calculation_method;

  return (
    <PageFrame kicker={t(lc, "operation")} title={t(lc, "fares")}>
      <TabBar items={[
        { key: "rules", label: t(lc, "fareRules"), count: (rules || []).length },
        { key: "products", label: t(lc, "fareProducts"), count: (products || []).length },
        { key: "fees", label: "Taxas administrativas", count: (fees || []).length },
      ]} value={tab} onChange={(k) => setTab(k as "rules" | "products" | "fees")} />

      {tab === "rules" && (
        <SectionCard title={t(lc, "fareRules")}>
          <div className="admin-toolbar"><div className="admin-toolbar-spacer" />
            <button className="primary-button" onClick={() => { setEditR(null); setRForm({ fare_product: "", route: "", origin_stop: "", destination_stop: "", calculation_method: "fixed", fixed_amount: "", amount_per_km: "", min_amount: "", max_amount: "", distance_min_km: "", distance_max_km: "", passenger_class: "standard", priority: "0" }); setRuleModal(true); }} type="button"><Plus size={15} /> {t(lc, "newRule")}</button>
          </div>
          <DataTable columns={[
            { header: t(lc, "route"), render: (r: FareRule) => <TablePrimaryCell title={r.route_code || t(lc, "allRoutes")} subtitle={r.fare_product_name} /> },
            { header: t(lc, "price"), render: (r: FareRule) => formatCurrency(r.fixed_amount) },
            { header: t(lc, "actions"), className: "table-actions-cell", render: (r: FareRule) => (
              <div className="admin-inline-actions">
                <TableActionButton icon={<Eye size={15} />} label={t(lc, "view")} onClick={() => setViewR(r)} />
                <TableActionButton icon={<Pencil size={15} />} label={t(lc, "edit")} onClick={() => { setEditR(r.id); setRForm({ fare_product: String(r.fare_product_id), route: r.route_id ? String(r.route_id) : "", origin_stop: r.origin_stop_id ? String(r.origin_stop_id) : "", destination_stop: r.destination_stop_id ? String(r.destination_stop_id) : "", calculation_method: r.calculation_method, fixed_amount: r.fixed_amount, amount_per_km: r.amount_per_km || "", min_amount: r.min_amount || "", max_amount: r.max_amount || "", distance_min_km: r.distance_min_km != null ? String(r.distance_min_km) : "", distance_max_km: r.distance_max_km != null ? String(r.distance_max_km) : "", passenger_class: r.passenger_class, priority: String(r.priority) }); setRuleModal(true); }} />
                <TableActionButton icon={<Trash2 size={15} />} label={t(lc, "delete")} onClick={async () => { const ok = await confirm({ title: t(lc, "delete"), message: "Tem a certeza que pretende eliminar esta regra de tarifa?", tone: "danger" }); if (!ok) return; try { await apiDelete(`/api/fare-rules/${r.id}/`, token!); reload(); } catch {} }} tone="danger" />
              </div>
            )},
          ]} rows={rules || []} rowKey={(r) => r.uuid} loading={lR} emptyMessage={t(lc, "noRules")} />
        </SectionCard>
      )}

      {tab === "products" && (
        <SectionCard title={t(lc, "fareProducts")}>
          <div className="admin-toolbar"><div className="admin-toolbar-spacer" />
            <button className="primary-button" onClick={() => { setEditP(null); setPForm({ name: "", product_type: "single_trip", status: "active" }); setProdModal(true); }} type="button"><Plus size={15} /> {t(lc, "newProduct")}</button>
          </div>
          <DataTable columns={[
            { header: t(lc, "name"), render: (r: FareProduct) => <TablePrimaryCell title={r.name} subtitle={r.product_type.replace(/_/g, " ")} /> },
            { header: t(lc, "status"), render: (r: FareProduct) => <StatusBadge value={r.status} /> },
            { header: t(lc, "actions"), className: "table-actions-cell", render: (r: FareProduct) => (
              <div className="admin-inline-actions">
                <TableActionButton icon={<Pencil size={15} />} label={t(lc, "edit")} onClick={() => { setEditP(r.id); setPForm({ name: r.name, product_type: r.product_type, status: r.status }); setProdModal(true); }} />
                <TableActionButton icon={<Trash2 size={15} />} label={t(lc, "delete")} onClick={async () => { const ok = await confirm({ title: t(lc, "delete"), message: `Tem a certeza que pretende eliminar o produto ${r.name}?`, tone: "danger" }); if (!ok) return; try { await apiDelete(`/api/fare-products/${r.id}/`, token!); reload(); } catch {} }} tone="danger" />
              </div>
            )},
          ]} rows={products || []} rowKey={(r) => r.uuid} loading={lP} emptyMessage={t(lc, "noProducts")} />
        </SectionCard>
      )}

      {tab === "fees" && (
        <SectionCard title="Taxas administrativas" description="Configure as taxas cobradas no registo, recuperacao de cartao, multas e outras.">
          <div className="admin-toolbar"><div className="admin-toolbar-spacer" />
            <button className="primary-button" type="button" onClick={() => {
              setEditFee(null);
              setFeeForm({ code: "", name: "", kind: "card_issuance", amount: "0.00", currency: "MZN", description: "", is_active: true });
              setFeeModal(true);
            }}><Plus size={15} /> Nova taxa</button>
          </div>
          <DataTable columns={[
            { header: "Nome", render: (r: AdminFee) => <TablePrimaryCell title={r.name} subtitle={r.code} /> },
            { header: "Tipo", render: (r: AdminFee) => <StatusBadge value={r.kind} /> },
            { header: "Valor", render: (r: AdminFee) => `${formatCurrency(r.amount)} ${r.currency}` },
            { header: "Estado", render: (r: AdminFee) => <StatusBadge value={r.is_active ? "active" : "inactive"} /> },
            { header: t(lc, "actions"), className: "table-actions-cell", render: (r: AdminFee) => (
              <div className="admin-inline-actions">
                <TableActionButton icon={<Pencil size={15} />} label={t(lc, "edit")} onClick={() => {
                  setEditFee(r.id);
                  setFeeForm({ code: r.code, name: r.name, kind: r.kind, amount: r.amount, currency: r.currency, description: r.description || "", is_active: r.is_active });
                  setFeeModal(true);
                }} />
                <TableActionButton icon={<Trash2 size={15} />} label={t(lc, "delete")} onClick={async () => {
                  const ok = await confirm({ title: t(lc, "delete"), message: `Eliminar taxa ${r.name}?`, tone: "danger" });
                  if (!ok) return;
                  try { await apiDelete(`/api/admin-fees/${r.id}/`, token!); reload(); }
                  catch (err) { showToast("danger", err instanceof Error ? err.message : "Erro"); }
                }} tone="danger" />
              </div>
            )},
          ]} rows={fees || []} rowKey={(r) => r.uuid} loading={lF} emptyMessage="Sem taxas configuradas." />
        </SectionCard>
      )}

      <DetailDrawer open={!!viewR} onClose={() => setViewR(null)} title="Regra de Tarifa" fields={viewR ? [
        { label: t(lc, "fareProducts"), value: viewR.fare_product_name },
        { label: t(lc, "route"), value: viewR.route_code || t(lc, "allRoutes") },
        { label: t(lc, "method"), value: viewR.calculation_method },
        { label: t(lc, "price"), value: formatCurrency(viewR.fixed_amount) },
        { label: t(lc, "origin"), value: viewR.origin_stop_name || "-" },
        { label: t(lc, "destination"), value: viewR.destination_stop_name || "-" },
        { label: t(lc, "passengerClass"), value: viewR.passenger_class },
        { label: t(lc, "priority"), value: String(viewR.priority) },
      ] : []} />

      <AdminModal open={ruleModal} onClose={() => setRuleModal(false)} title={editR ? t(lc, "editRule") : t(lc, "newRule")}>
        <form className="admin-form" onSubmit={submitR}>
          <div className="admin-form-grid">
            <label className="field"><span>{t(lc, "fareProducts")}</span>
              <select required value={rForm.fare_product} onChange={(e) => setRForm((f) => ({ ...f, fare_product: e.target.value }))}>
                <option value="">{t(lc, "select")}</option>
                {(products || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </label>
            <label className="field"><span>{t(lc, "route")}</span>
              <select required value={rForm.route} onChange={(e) => setRForm((f) => ({ ...f, route: e.target.value, origin_stop: "", destination_stop: "" }))}>
                <option value="">{t(lc, "select")}</option>
                {(routeOpts || []).map((r) => <option key={r.id} value={r.id}>{r.code} — {r.name}</option>)}
              </select>
            </label>
            <label className="field"><span>{t(lc, "method")}</span>
              <select value={rForm.calculation_method} onChange={(e) => setRForm((f) => ({ ...f, calculation_method: e.target.value }))}>
                <option value="fixed">{t(lc, "fixedMethod")}</option>
                <option value="origin_destination">{t(lc, "originDestMethod")}</option>
                <option value="distance">{t(lc, "distanceMethod")}</option>
              </select>
            </label>
            <label className="field"><span>{t(lc, "passengerClass")}</span>
              <select value={rForm.passenger_class} onChange={(e) => setRForm((f) => ({ ...f, passenger_class: e.target.value }))}>
                <option value="standard">{t(lc, "standard")}</option>
                <option value="student">{t(lc, "student")}</option>
                <option value="senior">{t(lc, "senior")}</option>
                <option value="child">{t(lc, "child")}</option>
              </select>
            </label>

            {(method === "fixed" || method === "origin_destination") && (
              <label className="field"><span>{t(lc, "fixedPrice")} (MZN)</span>
                <input required type="number" step="0.01" min="0" value={rForm.fixed_amount} onChange={(e) => setRForm((f) => ({ ...f, fixed_amount: e.target.value }))} />
              </label>
            )}

            {method === "distance" && (
              <>
                <label className="field"><span>Distancia minima (km)</span>
                  <input required type="number" step="0.1" min="0" value={rForm.distance_min_km} onChange={(e) => setRForm((f) => ({ ...f, distance_min_km: e.target.value }))} />
                </label>
                <label className="field"><span>Distancia maxima (km)</span>
                  <input required type="number" step="0.1" min="0" value={rForm.distance_max_km} onChange={(e) => setRForm((f) => ({ ...f, distance_max_km: e.target.value }))} />
                </label>
                <label className="field"><span>Valor por Km (MZN)</span>
                  <input type="number" step="0.01" min="0" value={rForm.amount_per_km} onChange={(e) => setRForm((f) => ({ ...f, amount_per_km: e.target.value }))} />
                </label>
                <label className="field"><span>Preco Fixo (MZN)</span>
                  <input type="number" step="0.01" min="0" value={rForm.fixed_amount} onChange={(e) => setRForm((f) => ({ ...f, fixed_amount: e.target.value }))} />
                </label>
                <label className="field"><span>Minimo (MZN)</span>
                  <input type="number" step="0.01" min="0" value={rForm.min_amount} onChange={(e) => setRForm((f) => ({ ...f, min_amount: e.target.value }))} />
                </label>
                <label className="field"><span>Maximo (MZN)</span>
                  <input type="number" step="0.01" min="0" value={rForm.max_amount} onChange={(e) => setRForm((f) => ({ ...f, max_amount: e.target.value }))} />
                </label>
              </>
            )}

            {method === "origin_destination" && (
              <>
                <label className="field"><span>{t(lc, "origin")}</span>
                  <select disabled={!rForm.route} required value={rForm.origin_stop} onChange={(e) => setRForm((f) => ({ ...f, origin_stop: e.target.value }))}>
                    <option value="">{rForm.route ? t(lc, "select") : t(lc, "route")}</option>
                    {routeStopOpts.map((s) => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
                  </select>
                </label>
                <label className="field"><span>{t(lc, "destination")}</span>
                  <select disabled={!rForm.route} required value={rForm.destination_stop} onChange={(e) => setRForm((f) => ({ ...f, destination_stop: e.target.value }))}>
                    <option value="">{rForm.route ? t(lc, "select") : t(lc, "route")}</option>
                    {routeStopOpts.map((s) => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
                  </select>
                </label>
              </>
            )}
          </div>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy} type="submit">{busy ? t(lc, "saving") : editR ? t(lc, "update") : t(lc, "create")}</button>
            <button className="secondary-button" onClick={() => setRuleModal(false)} type="button">{t(lc, "cancel")}</button>
          </div>
        </form>
      </AdminModal>

      {confirmDialog}

      <AdminModal open={prodModal} onClose={() => setProdModal(false)} title={editP ? t(lc, "editProduct") : t(lc, "newProduct")}>
        <form className="admin-form" onSubmit={submitP}>
          <div className="admin-form-grid">
            <label className="field"><span>{t(lc, "name")}</span><input required value={pForm.name} onChange={(e) => setPForm((f) => ({ ...f, name: e.target.value }))} /></label>
            <label className="field"><span>{t(lc, "type")}</span>
              <select value={pForm.product_type} onChange={(e) => setPForm((f) => ({ ...f, product_type: e.target.value }))}>
                <option value="single_trip">{t(lc, "singleTrip")}</option>
                <option value="daily_pass">{t(lc, "dailyPass")}</option>
                <option value="weekly_pass">{t(lc, "weeklyPass")}</option>
                <option value="monthly_pass">{t(lc, "monthlyPass")}</option>
              </select>
            </label>
            <label className="field"><span>{t(lc, "status")}</span>
              <select value={pForm.status} onChange={(e) => setPForm((f) => ({ ...f, status: e.target.value }))}>
                <option value="active">{t(lc, "active")}</option>
                <option value="inactive">{t(lc, "inactive")}</option>
              </select>
            </label>
          </div>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy} type="submit">{busy ? t(lc, "saving") : editP ? t(lc, "update") : t(lc, "create")}</button>
            <button className="secondary-button" onClick={() => setProdModal(false)} type="button">{t(lc, "cancel")}</button>
          </div>
        </form>
      </AdminModal>

      <AdminModal open={feeModal} onClose={() => setFeeModal(false)} title={editFee ? "Editar taxa" : "Nova taxa"}>
        <form className="admin-form" onSubmit={async (e: FormEvent) => {
          e.preventDefault();
          setBusy(true);
          try {
            const payload = {
              code: feeForm.code.trim(),
              name: feeForm.name.trim(),
              kind: feeForm.kind,
              amount: feeForm.amount,
              currency: feeForm.currency.trim() || "MZN",
              description: feeForm.description,
              is_active: feeForm.is_active,
            };
            if (editFee) await apiPatch(`/api/admin-fees/${editFee}/`, token!, payload);
            else await apiPost(`/api/admin-fees/`, token!, payload);
            setFeeModal(false); reload();
            showToast("success", editFee ? "Taxa actualizada." : "Taxa criada.");
          } catch (err) {
            showToast("danger", err instanceof Error ? err.message : "Erro");
          } finally { setBusy(false); }
        }}>
          <div className="admin-form-grid">
            <label className="field"><span>Codigo (slug)</span>
              <input required value={feeForm.code} onChange={(e) => setFeeForm((f) => ({ ...f, code: e.target.value }))} placeholder="ex: card-issuance-2026" />
            </label>
            <label className="field"><span>Nome</span>
              <input required value={feeForm.name} onChange={(e) => setFeeForm((f) => ({ ...f, name: e.target.value }))} />
            </label>
            <label className="field"><span>Tipo</span>
              <select value={feeForm.kind} onChange={(e) => setFeeForm((f) => ({ ...f, kind: e.target.value }))}>
                <option value="card_issuance">Taxa de adesao de cartao</option>
                <option value="card_recovery">Taxa de recuperacao de cartao</option>
                <option value="fine">Multa</option>
                <option value="other">Outra</option>
              </select>
            </label>
            <label className="field"><span>Valor</span>
              <input required type="number" min="0" step="0.01" value={feeForm.amount}
                     onChange={(e) => setFeeForm((f) => ({ ...f, amount: e.target.value }))} />
            </label>
            <label className="field"><span>Moeda</span>
              <input value={feeForm.currency} maxLength={3} onChange={(e) => setFeeForm((f) => ({ ...f, currency: e.target.value.toUpperCase() }))} />
            </label>
            <label className="field"><span>Estado</span>
              <select value={feeForm.is_active ? "1" : "0"} onChange={(e) => setFeeForm((f) => ({ ...f, is_active: e.target.value === "1" }))}>
                <option value="1">Activa</option>
                <option value="0">Inactiva</option>
              </select>
            </label>
            <label className="field" style={{ gridColumn: "1 / -1" }}>
              <span>Descricao</span>
              <input value={feeForm.description} onChange={(e) => setFeeForm((f) => ({ ...f, description: e.target.value }))} />
            </label>
          </div>
          <div className="admin-form-actions">
            <button className="primary-button" disabled={busy} type="submit">{busy ? t(lc, "saving") : editFee ? t(lc, "update") : t(lc, "create")}</button>
            <button className="secondary-button" onClick={() => setFeeModal(false)} type="button">{t(lc, "cancel")}</button>
          </div>
        </form>
      </AdminModal>
    </PageFrame>
  );
}
