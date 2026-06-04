import { useState } from "react";
import { t } from "../lib/i18n";
import { useUi } from "../ui/UiPreferences";
import { PageFrame, TabBar } from "../ui/common";
import PaymentsPage from "./PaymentsPage";
import TopupsPage from "./TopupsPage";
import ValidationsPage from "./ValidationsPage";

export default function FinancialPage() {
  const { locale: lc } = useUi();
  const [tab, setTab] = useState("payments");

  return (
    <PageFrame kicker={t(lc, "financial")} title={t(lc, "financial")}>
      <TabBar items={[
        { key: "payments", label: t(lc, "payments") },
        { key: "topups", label: t(lc, "topups") },
        { key: "validations", label: t(lc, "validations") },
      ]} value={tab} onChange={setTab} />
      {tab === "payments" && <PaymentsPage />}
      {tab === "topups" && <TopupsPage />}
      {tab === "validations" && <ValidationsPage />}
    </PageFrame>
  );
}
