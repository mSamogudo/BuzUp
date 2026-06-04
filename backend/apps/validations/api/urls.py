from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.validations.api.views import (
    PurchaseTravelPassView,
    TravelPassQuoteView,
    ValidateCardView,
    ValidateGuestPassView,
    ValidateQrView,
    ValidationEventViewSet,
)

router = DefaultRouter()
router.register("admin/validations", ValidationEventViewSet, basename="validations")

urlpatterns = [
    path("", include(router.urls)),
    path("validations/card/", ValidateCardView.as_view(), name="validate-card"),
    path("validations/qr/", ValidateQrView.as_view(), name="validate-qr"),
    path("validations/guest-pass/", ValidateGuestPassView.as_view(), name="validate-guest-pass"),
    path("travel-passes/purchase/", PurchaseTravelPassView.as_view(), name="travel-pass-purchase"),
    path("travel-passes/quote/", TravelPassQuoteView.as_view(), name="travel-pass-quote"),
]
