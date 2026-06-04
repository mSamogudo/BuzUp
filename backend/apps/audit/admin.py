from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "entity_type", "entity_id", "created_at")
    list_filter = ("action", "entity_type")
    search_fields = ("entity_id", "actor__username")
    readonly_fields = ("actor", "action", "entity_type", "entity_id", "before", "after", "ip_address", "device", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
