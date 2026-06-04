from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.routes.api.views import RouteViewSet, StopViewSet

router = DefaultRouter()
router.register("routes", RouteViewSet, basename="routes")
router.register("stops", StopViewSet, basename="stops")

urlpatterns = [
    path("", include(router.urls)),
]
