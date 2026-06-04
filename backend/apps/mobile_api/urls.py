"""/api/mobile/* routes consumed by Flutter passenger app.

Auth, login and OTP reuse the existing /api/auth endpoints (token, otp).
Wallet topup reuses /api/auth/me/passenger-portal/topup/.
Travel pass purchase reuses /api/travel-passes/purchase/ + quote.
"""
from django.urls import path

from apps.mobile_api.views import (
    MobileBalanceView,
    MobileCardView,
    MobileMeView,
    MobileNotificationListView,
    MobileNotificationReadAllView,
    MobileNotificationReadView,
    MobilePaymentListView,
    MobilePaymentStatusView,
    MobileTicketDetailView,
    MobileTicketListView,
    MobileTicketPdfView,
    MobileTripHistoryView,
)


urlpatterns = [
    path("me/", MobileMeView.as_view(), name="mobile-me"),

    path("card/", MobileCardView.as_view(), name="mobile-card"),
    path("card/balance/", MobileBalanceView.as_view(), name="mobile-card-balance"),

    path("tickets/", MobileTicketListView.as_view(), name="mobile-tickets"),
    path("tickets/<str:ref>/", MobileTicketDetailView.as_view(), name="mobile-ticket-detail"),
    path("tickets/<str:ref>/pdf/", MobileTicketPdfView.as_view(), name="mobile-ticket-pdf"),

    path("payments/", MobilePaymentListView.as_view(), name="mobile-payments"),
    path("payments/<str:reference>/status/", MobilePaymentStatusView.as_view(), name="mobile-payment-status"),

    path("trips/history/", MobileTripHistoryView.as_view(), name="mobile-trip-history"),

    path("notifications/", MobileNotificationListView.as_view(), name="mobile-notifications"),
    path("notifications/read-all/", MobileNotificationReadAllView.as_view(), name="mobile-notifications-read-all"),
    path("notifications/<int:notification_id>/read/", MobileNotificationReadView.as_view(), name="mobile-notification-read"),
]
