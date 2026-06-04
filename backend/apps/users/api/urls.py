from django.urls import path

from apps.users.api.otp_views import OtpRequestView, OtpVerifyView, PhoneCheckView
from apps.users.api.views import (
    BuzUpTokenObtainPairView,
    BuzUpTokenRefreshView,
    ChangePasswordView,
    MeProfileUpdateView,
    MeView,
    PassengerPortalAdminFeesView,
    PassengerPortalExtractView,
    PassengerPortalPackageSubscribeView,
    PassengerPortalPaymentStatusView,
    PassengerPortalTicketDetailView,
    PassengerPortalTicketsView,
    PassengerPortalTopupView,
    PassengerPortalTransactionDetailView,
    PassengerPortalTransactionsView,
    PassengerPortalView,
    PublicPasswordResetView,
)

urlpatterns = [
    path("token/", BuzUpTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", BuzUpTokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="auth_me"),
    path("me/profile/", MeProfileUpdateView.as_view(), name="auth_me_profile"),
    path("me/passenger-portal/", PassengerPortalView.as_view(), name="passenger_portal"),
    path("me/passenger-portal/topup/", PassengerPortalTopupView.as_view(), name="passenger_portal_topup"),
    path("me/passenger-portal/transactions/", PassengerPortalTransactionsView.as_view(), name="passenger_portal_transactions"),
    path("me/passenger-portal/transactions/<int:tx_id>/", PassengerPortalTransactionDetailView.as_view(), name="passenger_portal_transaction_detail"),
    path("me/passenger-portal/extract/", PassengerPortalExtractView.as_view(), name="passenger_portal_extract"),
    path("me/passenger-portal/packages/subscribe/", PassengerPortalPackageSubscribeView.as_view(), name="passenger_portal_package_subscribe"),
    path("me/passenger-portal/payments/<str:reference>/status/", PassengerPortalPaymentStatusView.as_view(), name="passenger_portal_payment_status"),
    path("me/passenger-portal/admin-fees/", PassengerPortalAdminFeesView.as_view(), name="passenger_portal_admin_fees"),
    path("me/passenger-portal/tickets/", PassengerPortalTicketsView.as_view(), name="passenger_portal_tickets"),
    path("me/passenger-portal/tickets/<int:ticket_id>/", PassengerPortalTicketDetailView.as_view(), name="passenger_portal_ticket_detail"),
    path("change-password/", ChangePasswordView.as_view(), name="auth_change_password"),
    path("password-reset/", PublicPasswordResetView.as_view(), name="auth_password_reset"),
    path("passenger/check/", PhoneCheckView.as_view(), name="passenger_check"),
    path("otp/request/", OtpRequestView.as_view(), name="otp_request"),
    path("otp/verify/", OtpVerifyView.as_view(), name="otp_verify"),
]
