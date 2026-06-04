from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.packages.api.views import (
    PackageViewSet,
    PassengerPackageViewSet,
    SubscribeView,
    TopupPackageView,
)

router = DefaultRouter()
router.register("packages", PackageViewSet, basename="packages")
router.register("passenger-packages", PassengerPackageViewSet, basename="passenger-packages")

urlpatterns = [
    path("", include(router.urls)),
    path("packages/subscribe/", SubscribeView.as_view(), name="package-subscribe"),
    path("packages/topup/", TopupPackageView.as_view(), name="package-topup"),
]
