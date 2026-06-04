import { useState } from "react";
import { t } from "../lib/i18n";
import { useUi } from "../ui/UiPreferences";
import { TabBar } from "../ui/common";
import FaresPage from "./FaresPage";
import PackagesPage from "./PackagesPage";

export default function PricingPage() {
  const { locale: lc } = useUi();
  const [tab, setTab] = useState("fares");

  return (
    <>
      <div style={{ padding: "16px 24px 0" }}>
        <TabBar items={[
          { key: "fares", label: t(lc, "fares") },
          { key: "packages", label: t(lc, "packages") },
        ]} value={tab} onChange={setTab} />
      </div>
      {tab === "fares" && <FaresPage />}
      {tab === "packages" && <PackagesPage />}
    </>
  );
}
