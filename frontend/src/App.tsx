import { useEffect, useState, lazy, Suspense } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import SplashScreen from "./ui/SplashScreen";
import PwaInstallPrompt from "./ui/PwaInstallPrompt";

// Entry-critical & pre-rendered routes stay eager: they drive first paint /
// LCP and must hydrate without an extra chunk round-trip.
import LandingPage from "./public/LandingPage";
import PricingPage from "./public/PricingPage";
import ContactPage from "./public/ContactPage";
import { PublicLayout } from "./public/site/PublicLayout";
import LoginPage from "./auth/LoginPage";
import AdminLayout from "./admin/AdminLayout";

// Everything below first paint is split into its own chunk so the initial
// bundle no longer ships leaflet, recharts and 20+ admin pages up front.
const DashboardPage = lazy(() => import("./admin/DashboardPage"));
const RoutesPage = lazy(() => import("./admin/RoutesPage"));
const RouteStopsPage = lazy(() => import("./admin/RouteStopsPage"));
const StopsPage = lazy(() => import("./admin/StopsPage"));
const TripsPage = lazy(() => import("./admin/TripsPage"));
const TripDetailPage = lazy(() => import("./admin/TripDetailPage"));
const VehiclesPage = lazy(() => import("./admin/VehiclesPage"));
const DriversPage = lazy(() => import("./admin/DriversPage"));
const FaresPage = lazy(() => import("./admin/FaresPage"));
const PackagesPage = lazy(() => import("./admin/PackagesPage"));
const PassengersPage = lazy(() => import("./admin/PassengersPage"));
const PhysicalCardsPage = lazy(() => import("./admin/PhysicalCardsPage"));
const DigitalCardsPage = lazy(() => import("./admin/DigitalCardsPage"));
const FinancialPage = lazy(() => import("./admin/FinancialPage"));
const DevicesPage = lazy(() => import("./admin/DevicesPage"));
const MapPage = lazy(() => import("./admin/MapPage"));
const ReleasesPage = lazy(() => import("./admin/ReleasesPage"));
const UsersPage = lazy(() => import("./admin/SystemPage"));
const ReportsPage = lazy(() => import("./admin/ReportsPage"));
const AgentRevenuePage = lazy(() => import("./admin/AgentRevenuePage"));
const AuditPage = lazy(() => import("./admin/AuditPage"));
const CheckoutPage = lazy(() => import("./public/CheckoutPage"));
const BusPaymentPage = lazy(() => import("./public/BusPaymentPage"));
const PassengerPortalPage = lazy(() => import("./passenger/PassengerPortalPage"));
const DriverPortalPage = lazy(() => import("./driver/DriverPortalPage"));
const ProfilePage = lazy(() => import("./profile/ProfilePage"));

function RouteFallback() {
  return (
    <div className="route-fallback" role="status" aria-label="A carregar">
      <div className="route-fallback-spinner" />
    </div>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, passengerId, driverId } = useAuth();
  const { pathname } = useLocation();
  if (!token) return <Navigate to="/login" replace />;
  if (driverId && !pathname.startsWith("/driver")) {
    return <Navigate to="/driver" replace />;
  }
  if (passengerId && pathname.startsWith("/app")) {
    return <Navigate to="/portal" replace />;
  }
  return <>{children}</>;
}

const PUBLIC_MARKETING_PATHS = new Set([
  "/", "/tarifas", "/contacto", "/en", "/en/tarifas", "/en/contacto",
]);

function AppContent() {
  // Public marketing pages skip the splash so crawlers (and pre-render
  // snapshots) see real content immediately and LCP stays fast.
  const isMarketing = PUBLIC_MARKETING_PATHS.has(window.location.pathname);
  const [splash, setSplash] = useState(!isMarketing);

  useEffect(() => {
    if (!splash) return;
    // Short brand beat only — the app is already interactive behind it.
    const timer = setTimeout(() => setSplash(false), 600);
    return () => clearTimeout(timer);
  }, [splash]);

  if (splash) return <SplashScreen />;

  return (
    <>
      <Toaster position="top-right" richColors />
      <PwaInstallPrompt />
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route element={<PublicLayout />}>
            <Route path="/" element={<LandingPage lang="pt" />} />
            <Route path="/tarifas" element={<PricingPage lang="pt" />} />
            <Route path="/contacto" element={<ContactPage lang="pt" />} />
            <Route path="/en" element={<LandingPage lang="en" />} />
            <Route path="/en/tarifas" element={<PricingPage lang="en" />} />
            <Route path="/en/contacto" element={<ContactPage lang="en" />} />
          </Route>
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
      </Suspense>
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
