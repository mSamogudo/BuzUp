from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.guest_checkouts.api.views import (
    GuestCheckoutCreateView,
    GuestCheckoutLookupView,
    GuestCheckoutViewSet,
    PublicBusInfoView,
    PublicTripSearchView,
    TicketPdfView,
)

router = DefaultRouter()
router.register("admin/guest-checkouts", GuestCheckoutViewSet, basename="guest-checkouts-admin")

urlpatterns = [
    path("", include(router.urls)),
    path("guest-checkouts/", GuestCheckoutCreateView.as_view(), name="guest-checkout-create"),
    path("guest-checkouts/<str:reference>/", GuestCheckoutLookupView.as_view(), name="guest-checkout-lookup"),
    path("public/trips/", PublicTripSearchView.as_view(), name="public-trip-search"),
    path("public/bus/<uuid:vehicle_uuid>/", PublicBusInfoView.as_view(), name="public-bus-info"),
    path("public/ticket/<str:token>/", TicketPdfView.as_view(), name="public-ticket-pdf"),
]
