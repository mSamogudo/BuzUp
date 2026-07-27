from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.trips.api.views import (
    AgentViewSet,
    DriverTripActionView,
    DriverTripsView,
    DriverViewSet,
    GenerateTripsView,
    RouteScheduleViewSet,
    TripSearchView,
    TripViewSet,
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
    path("driver/trips/<int:pk>/pause/", DriverTripActionView.as_view(action="pause"), name="driver-trip-pause"),
    path("driver/trips/<int:pk>/resume/", DriverTripActionView.as_view(action="resume"), name="driver-trip-resume"),
    path("driver/trips/<int:pk>/close/", DriverTripActionView.as_view(action="close"), name="driver-trip-close"),
    path("trips/search/", TripSearchView.as_view(), name="trip-search"),
    path("trips/generate/", GenerateTripsView.as_view(), name="trip-generate"),
    path("", include(router.urls)),
]
