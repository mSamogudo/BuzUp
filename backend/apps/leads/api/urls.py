from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.leads.api.views import PublicServiceRequestView, ServiceRequestViewSet

router = DefaultRouter()
router.register("admin/service-requests", ServiceRequestViewSet, basename="service-requests")

urlpatterns = [
    path("public/service-requests/", PublicServiceRequestView.as_view(), name="public-service-request"),
    path("", include(router.urls)),
]
