import { useState } from "react";
import { t } from "../lib/i18n";
import { useUi } from "../ui/UiPreferences";
import { TabBar } from "../ui/common";
import DevicesPage from "./DevicesPage";
import ReleasesPage from "./ReleasesPage";

export default function OperationsPage() {
  const { locale: lc } = useUi();
  const [tab, setTab] = useState("devices");

  return (
    <>
      <div style={{ padding: "16px 24px 0" }}>
        <TabBar items={[
          { key: "devices", label: t(lc, "devices") },
          { key: "releases", label: t(lc, "releases") },
        ]} value={tab} onChange={setTab} />
      </div>
      {tab === "devices" && <DevicesPage />}
      {tab === "releases" && <ReleasesPage />}
    </>
  );
}
