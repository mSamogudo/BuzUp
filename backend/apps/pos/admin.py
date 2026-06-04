from django.contrib import admin

from apps.pos.models import PosSession


@admin.register(PosSession)
class PosSessionAdmin(admin.ModelAdmin):
    list_display = ("agent", "device", "allocated_route", "status", "opened_at", "closed_at")
    list_filter = ("status",)
    search_fields = ("agent__username", "device__serial_number")
