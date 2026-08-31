import { Suspense, lazy, useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import LoginPage from "./auth/LoginPage";
import PortalShell from "./design/portal/PortalShell";
// Cada ecra chega quando alguem la vai, e nao antes.
//
// Estava tudo num ficheiro so de 1,2 MB. Com os 420 ms de ida e volta que
// medimos ate ao servidor, isso sao segundos a olhar para um ecra vazio — e
// paga-os quem abre a pagina de entrada para escrever a senha, que nao precisa
// de nenhum destes ecras. O portal inteiro descarregava para mostrar um
// formulario de login.
//
// O que fica ansioso e so o que se ve sempre: o login, a moldura do portal e
// o arranque.
// As paginas publicas (/, /precos, /contactos) sao a mesma pagina: o que
// muda e o `slug` que o CMS serve. Ver `public/site/SitePage`.
const SitePage = lazy(() => import("./public/site/SitePage"));
const AppsPage = lazy(() => import("./public/apps/AppsPage"));
const BookingPage = lazy(() => import("./public/booking/BookingPage"));
const DashboardPage = lazy(() => import("./admin/DashboardPage"));
const RoutesPage = lazy(() => import("./admin/RoutesPage"));
const RouteStopsPage = lazy(() => import("./admin/RouteStopsPage"));
const StopsPage = lazy(() => import("./admin/StopsPage"));
const OperationPage = lazy(() => import("./admin/OperationPage"));
const VehiclesPage = lazy(() => import("./admin/VehiclesPage"));
const DriversPage = lazy(() => import("./admin/DriversPage"));
const FaresPage = lazy(() => import("./admin/FaresPage"));
const PackagesPage = lazy(() => import("./admin/PackagesPage"));
const PassengersPage = lazy(() => import("./admin/PassengersPage"));
const PhysicalCardsPage = lazy(() => import("./admin/PhysicalCardsPage"));
const DigitalCardsPage = lazy(() => import("./admin/DigitalCardsPage"));
const FinancialPage = lazy(() => import("./admin/FinancialPage"));
const WalletsPage = lazy(() => import("./admin/WalletsPage"));
const GuestCheckoutsPage = lazy(() => import("./admin/GuestCheckoutsPage"));
const PosSessionsPage = lazy(() => import("./admin/PosSessionsPage"));
const DevicesPage = lazy(() => import("./admin/DevicesPage"));
const MapPage = lazy(() => import("./admin/MapPage"));
const ReleasesPage = lazy(() => import("./admin/ReleasesPage"));
const UsersPage = lazy(() => import("./admin/SystemPage"));
const ReportsPage = lazy(() => import("./admin/ReportsPage"));
const AgentRevenuePage = lazy(() => import("./admin/AgentRevenuePage"));
const AuditPage = lazy(() => import("./admin/AuditPage"));
const BrandingPage = lazy(() => import("./admin/BrandingPage"));
const TripDetailPage = lazy(() => import("./admin/TripDetailPage"));
const TripSchedulerPage = lazy(() => import("./admin/TripSchedulerPage"));
const TermsPage = lazy(() => import("./admin/TermsPage"));
const SettingsPage = lazy(() => import("./admin/SettingsPage"));
const WebhookLogPage = lazy(() => import("./admin/WebhookLogPage"));
const CardRecoveriesPage = lazy(() => import("./admin/CardRecoveriesTab"));
const ShiftsProposalPage = lazy(() => import("./admin/ShiftsProposalPage"));
// CMS do site publico. Cada ecra do editor entra so quando alguem la vai.
const CmsPagesPage = lazy(() => import("./admin/cms/PagesPage"));
const CmsPageEditorPage = lazy(() => import("./admin/cms/PageEditorPage"));
const CmsMediaPage = lazy(() => import("./admin/cms/MediaPage"));
const CmsMenusPage = lazy(() => import("./admin/cms/MenusPage"));
const CmsSeoPage = lazy(() => import("./admin/cms/SeoPage"));
const CmsPlansPage = lazy(() => import("./admin/cms/PlansPage"));
const CmsEcoSystemsPage = lazy(() => import("./admin/cms/EcoSystemsPage"));
const CmsRequestsPage = lazy(() => import("./admin/cms/RequestsPage"));
const CmsSchedulesPage = lazy(() => import("./admin/cms/SchedulesPage"));
const CmsVersionsPage = lazy(() => import("./admin/cms/VersionsPage"));
const CmsUsersPage = lazy(() => import("./admin/cms/CmsUsersPage"));
const ErrorScreen = lazy(() => import("./public/errors/ErrorScreen"));
const CheckoutPage = lazy(() => import("./public/CheckoutPage"));
const BusPaymentPage = lazy(() => import("./public/BusPaymentPage"));
const DownloadPage = lazy(() => import("./public/DownloadPage"));
const PassengerPortalPage = lazy(() => import("./passenger/PassengerPortalPage"));
const DriverPortalPage = lazy(() => import("./driver/DriverPortalPage"));
const ProfilePage = lazy(() => import("./profile/ProfilePage"));
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { BrandingProvider } from "./lib/branding";
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
      {/* Uma so fronteira de espera: o ecra que falta e sempre o proximo. */}
      <Suspense fallback={<SplashScreen />}>
      <Routes>
        <Route path="/" element={<SitePage />} />
        <Route path="/precos" element={<SitePage slug="precos" />} />
        <Route path="/contactos" element={<SitePage slug="contactos" />} />
        <Route path="/apps" element={<AppsPage />} />
        <Route path="/baixar" element={<DownloadPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/comprar" element={<BookingPage />} />
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/bus/:vehicleUuid" element={<BusPaymentPage />} />
        <Route path="/portal" element={<ProtectedRoute><PassengerPortalPage /></ProtectedRoute>} />
        <Route path="/driver" element={<ProtectedRoute><DriverPortalPage /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
        <Route path="/app" element={<ProtectedRoute><PortalShell /></ProtectedRoute>}>
          <Route index element={<DashboardPage />} />
          <Route path="routes" element={<RoutesPage />} />
          <Route path="routes/:routeId/stops" element={<RouteStopsPage />} />
          <Route path="stops" element={<StopsPage />} />
          <Route path="trips" element={<OperationPage />} />
          <Route path="trips/schedule" element={<TripSchedulerPage />} />
          <Route path="terms" element={<TermsPage />} />
          <Route path="trips/:tripId" element={<TripDetailPage />} />
          {/* Horários deixaram de ter menu próprio: são um separador das
              viagens. A rota antiga continua a funcionar para não partir
              favoritos e ligações guardadas. */}
          <Route path="schedules" element={<Navigate to="/app/trips?tab=programacoes" replace />} />
          <Route path="vehicles" element={<VehiclesPage />} />
          <Route path="drivers" element={<DriversPage />} />
          <Route path="fares" element={<FaresPage />} />
          <Route path="packages" element={<PackagesPage />} />
          <Route path="passengers" element={<PassengersPage />} />
          <Route path="cards/physical" element={<PhysicalCardsPage />} />
          <Route path="cards/digital" element={<DigitalCardsPage />} />
          <Route path="financial" element={<FinancialPage />} />
          <Route path="wallets" element={<WalletsPage />} />
          <Route path="guest-checkouts" element={<GuestCheckoutsPage />} />
          <Route path="pos-sessions" element={<PosSessionsPage />} />
          <Route path="devices" element={<DevicesPage />} />
          <Route path="map" element={<MapPage />} />
          <Route path="releases" element={<ReleasesPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="agent-revenue" element={<AgentRevenuePage />} />
          <Route path="audit" element={<AuditPage />} />
          <Route path="branding" element={<BrandingPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="financial/webhooks" element={<WebhookLogPage />} />
          <Route path="cards/recoveries" element={<CardRecoveriesPage />} />
          <Route path="shifts" element={<ShiftsProposalPage />} />
          <Route path="cms/pages" element={<CmsPagesPage />} />
          <Route path="cms/pages/:pageId" element={<CmsPageEditorPage />} />
          <Route path="cms/media" element={<CmsMediaPage />} />
          <Route path="cms/menus" element={<CmsMenusPage />} />
          <Route path="cms/seo" element={<CmsSeoPage />} />
          <Route path="cms/plans" element={<CmsPlansPage />} />
          <Route path="cms/eco-systems" element={<CmsEcoSystemsPage />} />
          <Route path="cms/requests" element={<CmsRequestsPage />} />
          <Route path="cms/schedules" element={<CmsSchedulesPage />} />
          <Route path="cms/versions" element={<CmsVersionsPage />} />
          <Route path="cms/users" element={<CmsUsersPage />} />
        </Route>
        {/* Um endereco errado passa a dizer o que aconteceu. Reencaminhar
            tudo para a entrada escondia gralhas de URL e ligacoes partidas. */}
        <Route path="*" element={<ErrorScreen code="404" />} />
      </Routes>
      </Suspense>
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrandingProvider>
        <AppContent />
      </BrandingProvider>
    </AuthProvider>
  );
}
