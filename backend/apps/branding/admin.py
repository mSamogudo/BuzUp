from django.contrib import admin

from apps.branding.models import BrandingSettings


@admin.register(BrandingSettings)
class BrandingSettingsAdmin(admin.ModelAdmin):
    list_display = ("platform_name", "updated_at")

    def has_add_permission(self, request):
        # Singleton: nunca mais do que uma linha.
        return not BrandingSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
