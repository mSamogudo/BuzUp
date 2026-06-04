from django.contrib import admin

from apps.validations.models import ValidationEvent


@admin.register(ValidationEvent)
class ValidationEventAdmin(admin.ModelAdmin):
    list_display = (
        "validation_type", "status", "amount_debited",
        "route", "device", "failure_reason", "created_at",
    )
    list_filter = ("validation_type", "status", "failure_reason")
    search_fields = ("idempotency_key", "wallet_transaction_ref")
    readonly_fields = (
        "validation_type", "passenger_account", "wallet", "physical_card",
        "digital_travel_pass", "route", "trip", "origin_stop", "destination_stop",
        "device", "amount_debited", "status", "failure_reason",
        "idempotency_key", "wallet_transaction_ref", "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
