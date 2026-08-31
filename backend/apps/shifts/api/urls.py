from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.shifts.api.views import ShiftViewSet

router = DefaultRouter()
router.register("shifts", ShiftViewSet, basename="shifts")

urlpatterns = [
    path("", include(router.urls)),
]
