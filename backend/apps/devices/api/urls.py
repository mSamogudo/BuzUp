from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.devices.api.views import (
    ActivationStatusView,
    DeviceActivationRequestViewSet,
    DeviceAllocateAgentView,
    DeviceApproveView,
    DeviceConfigurationView,
    DeviceHeartbeatView,
    DeviceLocationView,
    DeviceRegenerateActivationCodeView,
    DeviceRejectView,
    DeviceViewSet,
    SelfOnboardView,
)

router = DefaultRouter()
router.register("admin/devices", DeviceViewSet, basename="devices")
router.register("admin/device-activations", DeviceActivationRequestViewSet, basename="device-activations")

urlpatterns = [
    path("", include(router.urls)),
    path("devices/self-onboard/", SelfOnboardView.as_view(), name="device-self-onboard"),
    path("devices/activation-status/<str:activation_code>/", ActivationStatusView.as_view(), name="device-activation-status"),
    path("devices/heartbeat/", DeviceHeartbeatView.as_view(), name="device-heartbeat"),
    path("admin/devices/<int:pk>/approve/", DeviceApproveView.as_view(), name="device-approve"),
    path("admin/devices/<int:pk>/allocate-agent/", DeviceAllocateAgentView.as_view(), name="device-allocate-agent"),
    path("admin/devices/<int:pk>/regenerate-code/", DeviceRegenerateActivationCodeView.as_view(), name="device-regenerate-code"),
    path("admin/devices/<int:pk>/reject/", DeviceRejectView.as_view(), name="device-reject"),
    path("admin/devices/<int:pk>/configuration/", DeviceConfigurationView.as_view(), name="device-configuration"),
    path("devices/location/", DeviceLocationView.as_view(), name="device-location"),
]
