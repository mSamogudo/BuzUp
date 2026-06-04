from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.fares.api.views import AdminFeeViewSet, FareProductViewSet, FareQuoteView, FareRuleViewSet

router = DefaultRouter()
router.register("fare-products", FareProductViewSet, basename="fare-products")
router.register("fare-rules", FareRuleViewSet, basename="fare-rules")
router.register("admin-fees", AdminFeeViewSet, basename="admin-fees")

urlpatterns = [
    path("", include(router.urls)),
    path("fares/quote/", FareQuoteView.as_view(), name="fare-quote"),
]
