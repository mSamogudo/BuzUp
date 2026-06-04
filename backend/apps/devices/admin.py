from django.contrib import admin

from apps.devices.models import Device, DeviceActivationRequest


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        "serial_number", "device_type", "manufacturer", "model_name",
        "status", "assigned_agent", "app_version", "last_seen_at",
    )
    list_filter = ("status", "device_type", "manufacturer")
    search_fields = ("serial_number", "imei", "android_id", "activation_code")


@admin.register(DeviceActivationRequest)
class DeviceActivationRequestAdmin(admin.ModelAdmin):
    list_display = (
        "activation_code", "device", "status",
        "requested_serial_number", "requested_manufacturer",
        "requested_at", "reviewed_by", "reviewed_at",
    )
    list_filter = ("status",)
    search_fields = ("activation_code", "requested_serial_number", "requested_imei")
