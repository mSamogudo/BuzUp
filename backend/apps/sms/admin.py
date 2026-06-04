from django.contrib import admin

from apps.sms.models import SmsMessage


@admin.register(SmsMessage)
class SmsMessageAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "purpose", "status", "sent_at", "created_at")
    list_filter = ("status", "purpose")
    search_fields = ("phone_number", "body", "provider_reference")
    readonly_fields = ("phone_number", "template", "body", "purpose", "provider_reference", "status", "sent_at", "created_at", "metadata")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
