import { useState } from "react";
import { t } from "../lib/i18n";
import { useUi } from "../ui/UiPreferences";
import { TabBar } from "../ui/common";
import PaymentsPage from "./PaymentsPage";
import TopupsPage from "./TopupsPage";
import ValidationsPage from "./ValidationsPage";

// Nota: cada sub-página traz o seu próprio PageFrame (título/kicker/métricas);
// aqui fica só o selector de tab — um PageFrame exterior duplicava o cabeçalho.
export default function FinancialPage() {
  const { locale: lc } = useUi();
  const [tab, setTab] = useState("payments");

  return (
    <div>
      <div style={{ marginBottom: 4 }}>
        <TabBar items={[
          { key: "payments", label: t(lc, "payments") },
          { key: "topups", label: t(lc, "topups") },
          { key: "validations", label: t(lc, "validations") },
        ]} value={tab} onChange={setTab} />
      </div>
      {tab === "payments" && <PaymentsPage />}
      {tab === "topups" && <TopupsPage />}
      {tab === "validations" && <ValidationsPage />}
    </div>
  );
}
