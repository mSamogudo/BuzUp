from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.trips.api.views import (
    AgentViewSet,
    DriverTripActionView,
    DriverTripManifestView,
    DriverTripsView,
    DriverViewSet,
    GenerateTripsView,
    ProgramarPartidasView,
    RouteScheduleViewSet,
    TripManifestPdfView,
    TripManifestView,
    TripSearchView,
    TripViewSet,
    VehicleSeatPreviewView,
    VehicleViewSet,
)

router = DefaultRouter()
router.register("vehicles", VehicleViewSet, basename="vehicles")
router.register("drivers", DriverViewSet, basename="drivers")
router.register("agents", AgentViewSet, basename="agents")
router.register("schedules", RouteScheduleViewSet, basename="schedules")
router.register("trips", TripViewSet, basename="trips")

urlpatterns = [
    # Rotas explicitas ANTES do router: o detail do TripViewSet (trips/<pk>/)
    # engolia trips/search/ e trips/generate/ e respondia 405.
    path("driver/trips/", DriverTripsView.as_view(), name="driver-trips"),
    path("driver/trips/<int:pk>/start/", DriverTripActionView.as_view(action="start"), name="driver-trip-start"),
    path("driver/trips/<int:pk>/depart/", DriverTripActionView.as_view(action="depart"), name="driver-trip-depart"),
    path("driver/trips/<int:pk>/pause/", DriverTripActionView.as_view(action="pause"), name="driver-trip-pause"),
    path("driver/trips/<int:pk>/resume/", DriverTripActionView.as_view(action="resume"), name="driver-trip-resume"),
    path("driver/trips/<int:pk>/close/", DriverTripActionView.as_view(action="close"), name="driver-trip-close"),
    path("driver/trips/<int:pk>/manifest/", DriverTripManifestView.as_view(), name="driver-trip-manifest"),
    path("trips/<int:pk>/manifest/", TripManifestView.as_view(), name="trip-manifest"),
    path("trips/<int:pk>/manifest.pdf", TripManifestPdfView.as_view(), name="trip-manifest-pdf"),
    path("vehicles/seat-preview/", VehicleSeatPreviewView.as_view(), name="vehicle-seat-preview"),
    path("trips/search/", TripSearchView.as_view(), name="trip-search"),
    path("trips/generate/", GenerateTripsView.as_view(), name="trip-generate"),
    path("trips/schedule-days/", ProgramarPartidasView.as_view(), name="trip-schedule-days"),
    path("", include(router.urls)),
]
