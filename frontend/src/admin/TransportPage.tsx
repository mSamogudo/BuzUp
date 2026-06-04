import { useState } from "react";
import { t } from "../lib/i18n";
import { useUi } from "../ui/UiPreferences";
import { TabBar } from "../ui/common";
import RoutesPage from "./RoutesPage";
import StopsPage from "./StopsPage";
import TripsPage from "./TripsPage";
import VehiclesPage from "./VehiclesPage";

export default function TransportPage() {
  const { locale: lc } = useUi();
  const [tab, setTab] = useState("routes");

  return (
    <>
      <div style={{ padding: "16px 24px 0" }}>
        <TabBar items={[
          { key: "routes", label: t(lc, "routes") },
          { key: "stops", label: t(lc, "stops") },
          { key: "trips", label: t(lc, "trips") },
          { key: "vehicles", label: t(lc, "vehicles") },
        ]} value={tab} onChange={setTab} />
      </div>
      {tab === "routes" && <RoutesPage />}
      {tab === "stops" && <StopsPage />}
      {tab === "trips" && <TripsPage />}
      {tab === "vehicles" && <VehiclesPage />}
    </>
  );
}
