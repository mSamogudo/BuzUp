from django.contrib import admin

from apps.wallets.models import Wallet, WalletTransaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("uuid", "passenger_account", "balance_cached", "currency", "status", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("uuid", "passenger_account__full_name", "passenger_account__phone_number")
    readonly_fields = ("balance_cached",)


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ("reference", "wallet", "type", "direction", "amount", "status", "created_at")
    list_filter = ("type", "direction", "status")
    search_fields = ("reference", "wallet__uuid")
    readonly_fields = (
        "wallet", "type", "direction", "amount", "signed_amount",
        "balance_before", "balance_after", "reference", "source",
        "status", "metadata", "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
