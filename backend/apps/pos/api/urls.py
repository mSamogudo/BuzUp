from django.urls import path

from apps.pos.api.views import (
    ActiveSessionView,
    CloseSessionView,
    OpenSessionView,
    PosCardTopupView,
    PosCardValidateView,
    PosPackageSubscribeView,
    PosQrValidateView,
)

urlpatterns = [
    path("pos/sessions/open/", OpenSessionView.as_view(), name="pos-session-open"),
    path("pos/sessions/close/", CloseSessionView.as_view(), name="pos-session-close"),
    path("pos/sessions/active/", ActiveSessionView.as_view(), name="pos-session-active"),
    path("pos/validate/card/", PosCardValidateView.as_view(), name="pos-validate-card"),
    path("pos/validate/qr/", PosQrValidateView.as_view(), name="pos-validate-qr"),
    path("pos/card-topups/", PosCardTopupView.as_view(), name="pos-card-topup"),
    path("pos/package-subscribe/", PosPackageSubscribeView.as_view(), name="pos-package-subscribe"),
]
