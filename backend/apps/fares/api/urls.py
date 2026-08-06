from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.fares.api.matrix_views import (
    FareMatrixFillView,
    FareMatrixImportView,
    FareMatrixReturnView,
    FareMatrixTemplateView,
    FareMatrixView,
)
from apps.fares.api.views import AdminFeeViewSet, ExchangeRateViewSet, FareProductViewSet, FareQuoteView, FareRuleViewSet, PublicExchangeRateView

router = DefaultRouter()
router.register("fare-products", FareProductViewSet, basename="fare-products")
router.register("fare-rules", FareRuleViewSet, basename="fare-rules")
router.register("admin-fees", AdminFeeViewSet, basename="admin-fees")
router.register("exchange-rates", ExchangeRateViewSet, basename="exchange-rates")

urlpatterns = [
    path("", include(router.urls)),
    path("fares/quote/", FareQuoteView.as_view(), name="fare-quote"),
    # Tabela de precos de uma rota (grelha origem x destino).
    path("admin/routes/<int:route_id>/fare-matrix/", FareMatrixView.as_view(), name="fare-matrix"),
    path("admin/routes/<int:route_id>/fare-matrix/fill/", FareMatrixFillView.as_view(), name="fare-matrix-fill"),
    path("admin/routes/<int:route_id>/fare-matrix/template/", FareMatrixTemplateView.as_view(), name="fare-matrix-template"),
    path("admin/routes/<int:route_id>/fare-matrix/import/", FareMatrixImportView.as_view(), name="fare-matrix-import"),
    path("admin/routes/<int:route_id>/fare-matrix/return-direction/", FareMatrixReturnView.as_view(), name="fare-matrix-return"),
    path("public/exchange-rate/", PublicExchangeRateView.as_view(), name="public-exchange-rate"),
]
