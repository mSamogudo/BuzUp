from django.contrib import admin

from apps.shifts.models import Shift


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ("id", "agent_user", "vehicle", "opened_at", "closed_at",
                    "expected_amount", "counted_amount", "difference", "status")
    list_filter = ("status", "opened_at")
    search_fields = ("agent_user__username", "vehicle__registration", "notes")
    # Os numeros do fecho sao calculados pelo servidor: edita-los aqui era
    # abrir uma porta das traseiras a conta que a tesouraria confere.
    readonly_fields = ("expected_amount", "counted_amount", "difference",
                       "tickets_count", "validations_count",
                       "opened_at", "closed_at", "verified_at")
