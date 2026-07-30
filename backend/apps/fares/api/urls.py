from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.fares.api.views import AdminFeeViewSet, ExchangeRateViewSet, FareProductViewSet, FareQuoteView, FareRuleViewSet, PublicExchangeRateView

router = DefaultRouter()
router.register("fare-products", FareProductViewSet, basename="fare-products")
router.register("fare-rules", FareRuleViewSet, basename="fare-rules")
router.register("admin-fees", AdminFeeViewSet, basename="admin-fees")
router.register("exchange-rates", ExchangeRateViewSet, basename="exchange-rates")

urlpatterns = [
    path("", include(router.urls)),
    path("fares/quote/", FareQuoteView.as_view(), name="fare-quote"),
    path("public/exchange-rate/", PublicExchangeRateView.as_view(), name="public-exchange-rate"),
]
