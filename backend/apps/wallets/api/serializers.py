from decimal import Decimal

from rest_framework import serializers

from apps.wallets.models import Wallet, WalletTransaction


class WalletSerializer(serializers.ModelSerializer):
    passenger_name = serializers.CharField(source="passenger_account.full_name", read_only=True)
    passenger_phone = serializers.CharField(source="passenger_account.phone_number", read_only=True)

    class Meta:
        model = Wallet
        fields = (
            "id", "uuid", "passenger_account_id", "passenger_name", "passenger_phone",
            "balance_cached", "currency", "status", "created_at", "updated_at",
        )
        read_only_fields = fields


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = (
            "id", "uuid", "wallet_id", "type", "direction", "amount",
            "signed_amount", "balance_before", "balance_after",
            "reference", "source", "status", "metadata", "created_at",
        )
        read_only_fields = fields


class TopupRequestSerializer(serializers.Serializer):
    wallet_uuid = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("1.00"))
    payer_phone = serializers.CharField(max_length=20)
