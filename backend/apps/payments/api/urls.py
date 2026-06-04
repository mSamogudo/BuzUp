from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.payments.api.views import MobileWalletWebhookView, PaymentCallbackView, PaymentIntentViewSet

router = DefaultRouter()
router.register("payments/intents", PaymentIntentViewSet, basename="payment-intents")

urlpatterns = [
    path("", include(router.urls)),
    path("payments/callbacks/<str:provider>/", PaymentCallbackView.as_view(), name="payment-callback"),
    path("payments/webhooks/<str:provider>/", MobileWalletWebhookView.as_view(), name="payment-webhook"),
]
