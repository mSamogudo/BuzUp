from django.contrib import admin

from apps.leads.models import ContactLead


@admin.register(ContactLead)
class ContactLeadAdmin(admin.ModelAdmin):
    list_display = ("created_at", "source", "profile", "name", "email", "phone", "handled")
    list_filter = ("source", "profile", "handled", "created_at")
    search_fields = ("name", "email", "phone", "organization", "message")
    list_editable = ("handled",)
    readonly_fields = (
        "source", "profile", "name", "organization", "email", "phone",
        "message", "locale", "ip_address", "user_agent", "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        # Leads only arrive through the public site.
        return False
