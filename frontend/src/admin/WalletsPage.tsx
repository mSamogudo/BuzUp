import { useCallback } from "react";
import { RefreshCw } from "lucide-react";
import { apiFetch } from "../lib/api";
import { formatCurrency, formatDateTime } from "../lib/format";
import { t } from "../lib/i18n";
import { useAuth } from "../auth/AuthContext";
import { useUi } from "../ui/UiPreferences";
import { DataTable, MetricCard, PageFrame, SectionCard, StatusBadge, TabBar, TablePrimaryCell, useAsyncData } from "../ui/common";
import { useState } from "react";

interface WalletRecord { id: number; uuid: string; passenger_name: string; passenger_phone: string; balance_cached: string; currency: string; status: string; created_at: string; }
interface WalletTx { id: number; uuid: string; type: string; direction: string; amount: string; balance_before: string; balance_after: string; reference: string; source: string; status: string; created_at: string; }

export default function WalletsPage() {
  const { token } = useAuth();
  const { locale: lc } = useUi();
  const wLoader = useCallback(() => apiFetch("/api/wallets/", token!).then((d) => d.results || d), [token]);
  const txLoader = useCallback(() => apiFetch("/api/wallet-transactions/", token!).then((d) => d.results || d), [token]);
  const { data: wallets, loading: loadingW, reload: reloadW } = useAsyncData<WalletRecord[]>(wLoader, [token]);
  const { data: txs, loading: loadingT, reload: reloadT } = useAsyncData<WalletTx[]>(txLoader, [token]);
  const reload = () => { reloadW(); reloadT(); };
  const [tab, setTab] = useState<"wallets" | "txs">("wallets");
  const totalBalance = (wallets || []).reduce((s, w) => s + parseFloat(w.balance_cached || "0"), 0);

  return (
    <PageFrame kicker={t(lc, "financial")} title={t(lc, "wallets")}
      action={<button className="icon-text-button" onClick={reload} type="button"><RefreshCw size={16} /><span>{t(lc, "refresh")}</span></button>}>
      <div className="admin-metric-grid">
        <MetricCard label={t(lc, "wallets")} value={String((wallets || []).length)} />
        <MetricCard label={t(lc, "balance")} value={formatCurrency(totalBalance)} />
        <MetricCard label={t(lc, "walletTransactions")} value={String((txs || []).length)} />
      </div>
      <TabBar items={[{ key: "wallets", label: t(lc, "wallets"), count: (wallets || []).length }, { key: "txs", label: t(lc, "walletTransactions"), count: (txs || []).length }]} value={tab} onChange={(k) => setTab(k as "wallets" | "txs")} />
      {tab === "wallets" && (
        <SectionCard title={t(lc, "wallets")}>
          <DataTable columns={[
            { header: t(lc, "passenger"), render: (r: WalletRecord) => <TablePrimaryCell title={r.passenger_name} subtitle={r.passenger_phone} /> },
            { header: t(lc, "balance"), render: (r: WalletRecord) => <strong>{formatCurrency(r.balance_cached, r.currency)}</strong> },
            { header: t(lc, "status"), render: (r: WalletRecord) => <StatusBadge value={r.status} /> },
            { header: t(lc, "created"), render: (r: WalletRecord) => formatDateTime(r.created_at) },
          ]} rows={wallets || []} rowKey={(r) => r.uuid} loading={loadingW} emptyMessage={t(lc, "noWallets")} />
        </SectionCard>
      )}
      {tab === "txs" && (
        <SectionCard title={t(lc, "walletTransactions")}>
          <DataTable columns={[
            { header: t(lc, "reference"), render: (r: WalletTx) => <TablePrimaryCell title={r.reference} subtitle={r.source || "-"} /> },
            { header: t(lc, "type"), render: (r: WalletTx) => r.type.replace(/_/g, " ") },
            { header: t(lc, "direction"), render: (r: WalletTx) => <StatusBadge value={r.direction === "credit" ? "approved" : "denied"} /> },
            { header: t(lc, "amount"), render: (r: WalletTx) => formatCurrency(r.amount) },
            { header: t(lc, "after"), render: (r: WalletTx) => formatCurrency(r.balance_after) },
            { header: t(lc, "date"), render: (r: WalletTx) => formatDateTime(r.created_at) },
          ]} rows={txs || []} rowKey={(r) => r.uuid} loading={loadingT} emptyMessage={t(lc, "noTransactions")} />
        </SectionCard>
      )}
    </PageFrame>
  );
}
