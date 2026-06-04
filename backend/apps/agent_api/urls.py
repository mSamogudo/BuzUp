from django.urls import path

from apps.agent_api.admin_views import (
    AdminAgentDayCloseDetailView,
    AdminAgentDayCloseExportPdfView,
    AdminAgentDayCloseExportXlsxView,
    AdminAgentDayCloseListView,
    AdminAgentRevenueExportPdfView,
    AdminAgentRevenueExportXlsxView,
    AdminAgentRevenueSummaryView,
)
from apps.agent_api.cards_views import (
    AgentCardCaptureUidView,
    AgentCardLookupView,
    AgentPackagePurchaseView,
    AgentPackagesListView,
    AgentWalletPaymentView,
    AgentWalletTopupView,
)
from apps.agent_api.onboarding_views import AgentPassengerOnboardView
from apps.agent_api.recovery_views import (
    AgentRecoverCardAssociateView,
    AgentRecoverCardRequestOtpView,
    AgentRecoverCardVerifyOtpView,
)
from apps.agent_api.views import (
    AgentCardValidationView,
    AgentCurrentDeviceView,
    AgentDayCloseView,
    AgentDeviceHeartbeatView,
    AgentFareQuoteView,
    AgentLoginView,
    AgentLogoutView,
    AgentMeView,
    AgentPaymentStatusView,
    AgentSaleCreateView,
    AgentSalesHistoryView,
    AgentSalesSummaryView,
    AgentTicketDetailView,
    AgentTicketListView,
    AgentTicketMarkUsedView,
    AgentTicketPdfView,
    AgentTicketVerifyView,
    AgentTripDetailView,
    AgentTripListView,
    PosDeviceActivateView,
    PosDeviceSelfRegisterView,
    PosDeviceStatusView,
)


urlpatterns = [
    # ---- Onboarding (no auth: device must register + be approved before login) ----
    path("devices/self-onboard/", PosDeviceSelfRegisterView.as_view(), name="agent-device-self-onboard"),
    path("devices/status/<str:serial_number>/", PosDeviceStatusView.as_view(), name="agent-device-status"),
    path("devices/activate/", PosDeviceActivateView.as_view(), name="agent-device-activate"),

    # ---- Auth ----
    path("auth/login/", AgentLoginView.as_view(), name="agent-auth-login"),
    path("auth/logout/", AgentLogoutView.as_view(), name="agent-auth-logout"),
    path("me/", AgentMeView.as_view(), name="agent-me"),

    # ---- Device runtime (after login) ----
    path("devices/current/", AgentCurrentDeviceView.as_view(), name="agent-device-current"),
    path("devices/heartbeat/", AgentDeviceHeartbeatView.as_view(), name="agent-device-heartbeat"),
    path("day-close/", AgentDayCloseView.as_view(), name="agent-day-close"),

    path("trips/", AgentTripListView.as_view(), name="agent-trips"),
    path("trips/<int:trip_id>/", AgentTripDetailView.as_view(), name="agent-trip-detail"),
    path("trips/<int:trip_id>/fare/", AgentFareQuoteView.as_view(), name="agent-trip-fare"),

    path("sales/", AgentSaleCreateView.as_view(), name="agent-sale-create"),
    path("sales/history/", AgentSalesHistoryView.as_view(), name="agent-sales-history"),
    path("sales/summary/", AgentSalesSummaryView.as_view(), name="agent-sales-summary"),
    path("payments/<str:payment_reference>/status/", AgentPaymentStatusView.as_view(), name="agent-payment-status"),

    path("tickets/", AgentTicketListView.as_view(), name="agent-tickets"),
    path("tickets/verify/", AgentTicketVerifyView.as_view(), name="agent-ticket-verify"),
    path("validations/card/", AgentCardValidationView.as_view(), name="agent-card-validation"),
    path("tickets/<str:ref>/", AgentTicketDetailView.as_view(), name="agent-ticket-detail"),
    path("tickets/<str:ref>/pdf/", AgentTicketPdfView.as_view(), name="agent-ticket-pdf"),
    path("tickets/<str:ref>/mark-used/", AgentTicketMarkUsedView.as_view(), name="agent-ticket-mark-used"),

    # ---- Cards / wallet / packages (NFC + QR) ----
    path("cards/lookup/", AgentCardLookupView.as_view(), name="agent-card-lookup"),
    path("cards/capture-uid/", AgentCardCaptureUidView.as_view(), name="agent-card-capture-uid"),
    path("topups/wallet/", AgentWalletTopupView.as_view(), name="agent-wallet-topup"),
    path("topups/package/", AgentPackagePurchaseView.as_view(), name="agent-package-topup"),
    path("payments/wallet/", AgentWalletPaymentView.as_view(), name="agent-wallet-pay"),
    path("packages/", AgentPackagesListView.as_view(), name="agent-packages"),
    path("passengers/onboard/", AgentPassengerOnboardView.as_view(), name="agent-passenger-onboard"),
    path("passengers/recover-card/request-otp/", AgentRecoverCardRequestOtpView.as_view(), name="agent-recover-otp-request"),
    path("passengers/recover-card/verify-otp/", AgentRecoverCardVerifyOtpView.as_view(), name="agent-recover-otp-verify"),
    path("passengers/recover-card/associate/", AgentRecoverCardAssociateView.as_view(), name="agent-recover-associate"),

    # Admin endpoints for the agent revenue control module.
    path("admin/day-closes/", AdminAgentDayCloseListView.as_view(), name="agent-admin-day-closes"),
    path("admin/day-closes/<int:pk>/", AdminAgentDayCloseDetailView.as_view(), name="agent-admin-day-close-detail"),
    path("admin/day-closes/<int:pk>/export.pdf", AdminAgentDayCloseExportPdfView.as_view(), name="agent-admin-day-close-pdf"),
    path("admin/day-closes/<int:pk>/export.xlsx", AdminAgentDayCloseExportXlsxView.as_view(), name="agent-admin-day-close-xlsx"),
    path("admin/revenue/", AdminAgentRevenueSummaryView.as_view(), name="agent-admin-revenue"),
    path("admin/revenue/export.pdf", AdminAgentRevenueExportPdfView.as_view(), name="agent-admin-revenue-pdf"),
    path("admin/revenue/export.xlsx", AdminAgentRevenueExportXlsxView.as_view(), name="agent-admin-revenue-xlsx"),
]
