from django.contrib import admin

from apps.passengers.models import PassengerAccount


@admin.register(PassengerAccount)
class PassengerAccountAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone_number", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("full_name", "phone_number", "email", "document_number")
