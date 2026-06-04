from django.contrib import admin

from apps.payments.models import PaymentCallback, PaymentIntent


@admin.register(PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
    list_display = ("reference", "purpose", "amount", "currency", "payer_phone", "status", "created_at")
    list_filter = ("purpose", "status", "provider")
    search_fields = ("reference", "idempotency_key", "payer_phone", "provider_reference")


@admin.register(PaymentCallback)
class PaymentCallbackAdmin(admin.ModelAdmin):
    list_display = ("payment_intent", "provider_reference", "signature_valid", "processing_status", "received_at")
    list_filter = ("signature_valid", "processing_status")
    search_fields = ("provider_reference", "payment_intent__reference")
    readonly_fields = ("payment_intent", "provider_reference", "raw_payload", "signature_valid", "processing_status", "received_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
