from django.contrib import admin

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout


@admin.register(GuestCheckout)
class GuestCheckoutAdmin(admin.ModelAdmin):
    list_display = ("reference", "payer_phone", "route_code", "total_amount", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("reference", "payer_phone", "buyer_name")


@admin.register(DigitalTravelPass)
class DigitalTravelPassAdmin(admin.ModelAdmin):
    list_display = ("uuid", "route_code", "fare_amount", "status", "delivery_channel", "valid_from", "valid_until", "used_at")
    list_filter = ("status", "delivery_channel")
    search_fields = ("uuid", "token_hash", "payer_phone")
