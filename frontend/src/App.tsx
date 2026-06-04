import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import LoginPage from "./auth/LoginPage";
import AdminLayout from "./admin/AdminLayout";
import DashboardPage from "./admin/DashboardPage";
import RoutesPage from "./admin/RoutesPage";
import RouteStopsPage from "./admin/RouteStopsPage";
import StopsPage from "./admin/StopsPage";
import TripsPage from "./admin/TripsPage";
import VehiclesPage from "./admin/VehiclesPage";
import DriversPage from "./admin/DriversPage";
import FaresPage from "./admin/FaresPage";
import PackagesPage from "./admin/PackagesPage";
import PassengersPage from "./admin/PassengersPage";
import PhysicalCardsPage from "./admin/PhysicalCardsPage";
import DigitalCardsPage from "./admin/DigitalCardsPage";
import FinancialPage from "./admin/FinancialPage";
import DevicesPage from "./admin/DevicesPage";
import MapPage from "./admin/MapPage";
import ReleasesPage from "./admin/ReleasesPage";
import UsersPage from "./admin/SystemPage";
import ReportsPage from "./admin/ReportsPage";
import AgentRevenuePage from "./admin/AgentRevenuePage";
import AuditPage from "./admin/AuditPage";
import CheckoutPage from "./public/CheckoutPage";
import BusPaymentPage from "./public/BusPaymentPage";
import PassengerPortalPage from "./passenger/PassengerPortalPage";
import DriverPortalPage from "./driver/DriverPortalPage";
import ProfilePage from "./profile/ProfilePage";
import TripDetailPage from "./admin/TripDetailPage";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import SplashScreen from "./ui/SplashScreen";
import PwaInstallPrompt from "./ui/PwaInstallPrompt";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, passengerId, driverId } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  const path = window.location.pathname;
  if (driverId && !path.startsWith("/driver")) {
    return <Navigate to="/driver" replace />;
  }
  if (passengerId && path.startsWith("/app")) {
    return <Navigate to="/portal" replace />;
  }
  return <>{children}</>;
}

function AppContent() {
  const [splash, setSplash] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setSplash(false), 1400);
    return () => clearTimeout(timer);
  }, []);

  if (splash) return <SplashScreen />;

  return (
    <>
      <Toaster position="top-right" richColors />
      <PwaInstallPrompt />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/bus/:vehicleUuid" element={<BusPaymentPage />} />
        <Route path="/portal" element={<ProtectedRoute><PassengerPortalPage /></ProtectedRoute>} />
        <Route path="/driver" element={<ProtectedRoute><DriverPortalPage /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
        <Route path="/app" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
          <Route index element={<DashboardPage />} />
          <Route path="routes" element={<RoutesPage />} />
          <Route path="routes/:routeId/stops" element={<RouteStopsPage />} />
          <Route path="stops" element={<StopsPage />} />
          <Route path="trips" element={<TripsPage />} />
          <Route path="trips/:tripId" element={<TripDetailPage />} />
          <Route path="vehicles" element={<VehiclesPage />} />
          <Route path="drivers" element={<DriversPage />} />
          <Route path="fares" element={<FaresPage />} />
          <Route path="packages" element={<PackagesPage />} />
          <Route path="passengers" element={<PassengersPage />} />
          <Route path="cards/physical" element={<PhysicalCardsPage />} />
          <Route path="cards/digital" element={<DigitalCardsPage />} />
          <Route path="financial" element={<FinancialPage />} />
          <Route path="devices" element={<DevicesPage />} />
          <Route path="map" element={<MapPage />} />
          <Route path="releases" element={<ReleasesPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="agent-revenue" element={<AgentRevenuePage />} />
          <Route path="audit" element={<AuditPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/app" replace />} />
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
