from django.urls import include, path

from .api_import import CardTemplateView, ExcelImportView
from .views import HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("import/<str:resource>/", ExcelImportView.as_view(), name="excel-import"),
    path("import/cards/template/", CardTemplateView.as_view(), name="card-template"),
    path("", include("apps.passengers.api.urls")),
    path("", include("apps.wallets.api.urls")),
    path("", include("apps.payments.api.urls")),
    path("", include("apps.guest_checkouts.api.urls")),
    path("", include("apps.cards.api.urls")),
    path("", include("apps.devices.api.urls")),
    path("", include("apps.app_releases.api.urls")),
    path("", include("apps.routes.api.urls")),
    path("", include("apps.fares.api.urls")),
    path("", include("apps.trips.api.urls")),
    path("", include("apps.validations.api.urls")),
    path("", include("apps.reports.api.urls")),
    path("", include("apps.packages.api.urls")),
    path("", include("apps.pos.api.urls")),
    path("", include("apps.users.api.urls_admin")),
    path("agent/", include("apps.agent_api.urls")),
    path("mobile/", include("apps.mobile_api.urls")),
]
