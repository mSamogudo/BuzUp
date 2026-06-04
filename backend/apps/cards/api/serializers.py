from rest_framework import serializers

from apps.cards.models import Card


class CardSerializer(serializers.ModelSerializer):
    passenger_name = serializers.CharField(source="passenger_account.full_name", read_only=True, default="")
    passenger_phone = serializers.CharField(source="passenger_account.phone_number", read_only=True, default="")
    balance = serializers.DecimalField(source="wallet.balance_cached", max_digits=12, decimal_places=2, read_only=True, default=None)

    class Meta:
        model = Card
        fields = (
            "id", "uuid", "card_type", "card_uid", "card_number", "card_technology",
            "status", "passenger_account_id", "passenger_name", "passenger_phone",
            "wallet_id", "balance", "issued_batch", "batch_serial", "manufacturer",
            "activated_at", "blocked_at", "created_at", "updated_at",
        )
        read_only_fields = fields


class CardLookupSerializer(serializers.Serializer):
    card_uid = serializers.CharField(max_length=64)


class CardAssignSerializer(serializers.Serializer):
    card_uid = serializers.CharField(max_length=64)
    passenger_id = serializers.IntegerField()


class CardReplaceSerializer(serializers.Serializer):
    old_card_uid = serializers.CharField(max_length=64)
    new_card_uid = serializers.CharField(max_length=64)
