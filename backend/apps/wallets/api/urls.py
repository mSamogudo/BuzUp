from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.wallets.api.views import TopupView, WalletTransactionViewSet, WalletViewSet

router = DefaultRouter()
router.register("wallets", WalletViewSet, basename="wallets")
router.register("wallet-transactions", WalletTransactionViewSet, basename="wallet-transactions")

urlpatterns = [
    path("", include(router.urls)),
    path("wallet/topups/", TopupView.as_view(), name="wallet-topup"),
]
