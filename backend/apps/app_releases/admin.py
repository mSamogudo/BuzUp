from django.contrib import admin

from apps.app_releases.models import AppRelease, DeviceAppUpdate


@admin.register(AppRelease)
class AppReleaseAdmin(admin.ModelAdmin):
    list_display = (
        "app_type", "version_name", "version_code", "is_mandatory",
        "status", "target_device_type", "target_manufacturer", "published_at",
    )
    list_filter = ("app_type", "status", "is_mandatory", "target_manufacturer")
    search_fields = ("version_name", "release_notes")


@admin.register(DeviceAppUpdate)
class DeviceAppUpdateAdmin(admin.ModelAdmin):
    list_display = (
        "device", "app_release", "current_version_code",
        "target_version_code", "status", "deferred_until", "installed_at",
    )
    list_filter = ("status",)
    search_fields = ("device__serial_number",)
