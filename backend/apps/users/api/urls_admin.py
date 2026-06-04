from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.users.api.views import (
    AdminUserPasswordResetView,
    AdminUserToggleActiveView,
    AssignRoleView,
    CapabilitiesListView,
    RoleViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register("admin/roles", RoleViewSet, basename="roles")
router.register("admin/users", UserViewSet, basename="users")

urlpatterns = [
    path("", include(router.urls)),
    path("admin/capabilities/", CapabilitiesListView.as_view(), name="capabilities-list"),
    path("admin/assign-role/", AssignRoleView.as_view(), name="assign-role"),
    path(
        "admin/users/<int:pk>/reset-password/",
        AdminUserPasswordResetView.as_view(),
        name="admin-user-reset-password",
    ),
    path(
        "admin/users/<int:pk>/toggle-active/",
        AdminUserToggleActiveView.as_view(),
        name="admin-user-toggle-active",
    ),
]
