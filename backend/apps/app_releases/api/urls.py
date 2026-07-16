from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from apps.app_releases.api.views import (
    AppDownloadPageView,
    AppLatestDownloadView,
    AppLatestInfoView,
    AppReleaseDownloadView,
    AppReleasePublishView,
    AppReleaseViewSet,
    AppReleaseSuspendView,
    CheckUpdateView,
    DeferUpdateView,
    DeviceAppUpdateViewSet,
)

router = DefaultRouter()
router.register("admin/app-releases", AppReleaseViewSet, basename="app-releases")
router.register("admin/device-app-updates", DeviceAppUpdateViewSet, basename="device-app-updates")

urlpatterns = [
    path("", include(router.urls)),
    re_path(r"^baixar/?$", AppDownloadPageView.as_view(), name="app-download-page"),
    re_path(
        r"^(?P<slug>pos|passageiro|passenger|mobile)/?$",
        AppLatestDownloadView.as_view(),
        name="app-short-download",
    ),
    path("apps/latest/", AppLatestInfoView.as_view(), name="app-latest-info"),
    path("apps/<slug:slug>/download/", AppLatestDownloadView.as_view(), name="app-latest-download"),
    path("app-releases/check/", CheckUpdateView.as_view(), name="app-release-check"),
    path("app-releases/<int:pk>/download/", AppReleaseDownloadView.as_view(), name="app-release-download"),
    path("app-releases/<int:pk>/defer/", DeferUpdateView.as_view(), name="app-release-defer"),
    path("admin/app-releases/<int:pk>/publish/", AppReleasePublishView.as_view(), name="app-release-publish"),
    path("admin/app-releases/<int:pk>/suspend/", AppReleaseSuspendView.as_view(), name="app-release-suspend"),
]
