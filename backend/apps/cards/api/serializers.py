from rest_framework import serializers

from apps.cards.models import Card
from apps.payments.models import PaymentIntent


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


class CardRecoverySerializer(serializers.ModelSerializer):
    """Historico das recuperacoes de cartao, lido das intencoes de pagamento.

    A recuperacao nao tem tabela propria: e a taxa `card_recovery` que a
    regista, com o resto do processo em `metadata`. Achatamos esses campos para
    que o portal mostre uma lista sem ter de abrir o JSON.
    """

    reason = serializers.SerializerMethodField()
    blocked_cards = serializers.SerializerMethodField()
    old_card_ids = serializers.SerializerMethodField()
    passenger_id = serializers.SerializerMethodField()
    card_id = serializers.SerializerMethodField()
    card_uid = serializers.SerializerMethodField()
    channel = serializers.SerializerMethodField()
    finalised_at = serializers.SerializerMethodField()

    class Meta:
        model = PaymentIntent
        fields = (
            "id", "reference", "status", "amount", "payer_phone", "created_at",
            "reason", "blocked_cards", "old_card_ids", "passenger_id",
            "card_id", "card_uid", "channel", "finalised_at",
        )
        read_only_fields = fields

    def _meta_valor(self, obj, chave, omissao=None):
        return (obj.metadata or {}).get(chave, omissao)

    def get_reason(self, obj):
        return self._meta_valor(obj, "reason", "")

    def get_blocked_cards(self, obj):
        return self._meta_valor(obj, "blocked_cards", 0)

    def get_old_card_ids(self, obj):
        return self._meta_valor(obj, "old_card_ids", [])

    def get_passenger_id(self, obj):
        return self._meta_valor(obj, "passenger_id")

    def get_card_id(self, obj):
        return self._meta_valor(obj, "card_id")

    def get_card_uid(self, obj):
        return self._meta_valor(obj, "card_uid", "")

    def get_channel(self, obj):
        return self._meta_valor(obj, "channel", "")

    def get_finalised_at(self, obj):
        return self._meta_valor(obj, "finalised_at")
