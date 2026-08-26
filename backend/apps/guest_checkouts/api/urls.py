from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.guest_checkouts.api.views import (
    GuestCheckoutCreateView,
    GuestCheckoutLookupView,
    GuestCheckoutViewSet,
    PublicBusInfoView,
    PublicDocumentTypesView,
    PublicTripSearchView,
    PublicTripSeatsView,
    TicketPageView,
    TicketPdfView,
)

router = DefaultRouter()
router.register("admin/guest-checkouts", GuestCheckoutViewSet, basename="guest-checkouts-admin")

urlpatterns = [
    path("", include(router.urls)),
    path("guest-checkouts/", GuestCheckoutCreateView.as_view(), name="guest-checkout-create"),
    path("guest-checkouts/<str:reference>/", GuestCheckoutLookupView.as_view(), name="guest-checkout-lookup"),
    path("public/trips/", PublicTripSearchView.as_view(), name="public-trip-search"),
    path("public/trips/<int:trip_id>/seats/", PublicTripSeatsView.as_view(), name="public-trip-seats"),
    path("public/bus/<uuid:vehicle_uuid>/", PublicBusInfoView.as_view(), name="public-bus-info"),
    path("public/document-types/", PublicDocumentTypesView.as_view(), name="public-document-types"),
    # A pagina leve no endereco que vai no SMS; o PDF logo abaixo. A ordem
    # importa: `pdf/` tem de vir antes para nao ser apanhado pelo `<str:token>`.
    path("public/ticket/<str:token>/pdf/", TicketPdfView.as_view(), name="public-ticket-pdf"),
    path("public/ticket/<str:token>/", TicketPageView.as_view(), name="public-ticket"),
]
