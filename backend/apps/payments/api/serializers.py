from rest_framework import serializers

from apps.payments.models import PaymentCallback, PaymentIntent


_SOURCE_BY_PURPOSE = {
    "mobile_wallet_topup": "MOBILE",
    "app_travel_pass_purchase": "MOBILE",
    "pos_card_topup": "POS",
    "direct_trip_payment": "POS",
    "guest_travel_pass_purchase": "PORTAL",
    "refund": "PORTAL",
}

_PROVIDER_LABELS = {
    "mpesa": "M-Pesa",
    "emola": "E-Mola",
    "mock": "Teste (MOCK)",
    "real_test_mode": "Teste (real)",
    "card": "Cartao",
    "cash": "Numerario",
    "wallet": "Carteira BuzUp",
}


class PaymentIntentSerializer(serializers.ModelSerializer):
    wallet_uuid = serializers.SerializerMethodField()
    wallet_passenger_name = serializers.SerializerMethodField()
    wallet_passenger_phone = serializers.SerializerMethodField()
    guest_payer_name = serializers.SerializerMethodField()
    created_by_username = serializers.SerializerMethodField()
    created_by_full_name = serializers.SerializerMethodField()
    purpose_label = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    provider_label = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    payer_display_name = serializers.SerializerMethodField()
    payer_display_phone = serializers.SerializerMethodField()
    needs_review = serializers.SerializerMethodField()
    review_reason = serializers.SerializerMethodField()

    class Meta:
        model = PaymentIntent
        fields = (
            "id", "uuid", "reference", "idempotency_key", "purpose", "purpose_label",
            "amount", "currency",
            "payer_phone", "provider", "provider_label", "channel", "status", "status_label",
            "source",
            "wallet_uuid", "wallet_passenger_name", "wallet_passenger_phone",
            "guest_payer_name",
            "created_by_username", "created_by_full_name",
            "payer_display_name", "payer_display_phone",
            "provider_reference", "expires_at", "confirmed_at",
            "metadata", "needs_review", "review_reason", "created_at", "updated_at",
        )
        read_only_fields = fields

    def _reconciliation(self, obj) -> dict:
        return (obj.metadata or {}).get("reconciliation") or {}

    def get_needs_review(self, obj) -> bool:
        """Pagamento confirmado no gateway que nao pode ser emitido sozinho.

        Acontece quando a confirmacao chega depois do checkout expirar: o lugar
        pode ter sido revendido, logo a decisao entre reemitir e reembolsar e
        de uma pessoa. Sinalizar aqui e o que faz o caso aparecer no portal.
        """
        return bool(self._reconciliation(obj).get("needs_manual_review"))

    def get_review_reason(self, obj) -> str:
        return str(self._reconciliation(obj).get("reason") or "")

    def get_wallet_uuid(self, obj):
        if not obj.wallet_id or not obj.wallet:
            return None
        return str(obj.wallet.uuid)

    def get_wallet_passenger_name(self, obj):
        if not obj.wallet_id or not obj.wallet:
            return ""
        return obj.wallet.passenger_account.full_name

    def get_wallet_passenger_phone(self, obj):
        if not obj.wallet_id or not obj.wallet:
            return ""
        return obj.wallet.passenger_account.phone_number

    def get_guest_payer_name(self, obj):
        gc = getattr(obj, "guest_checkout", None)
        if not gc:
            return ""
        return getattr(gc, "payer_name", "") or ""

    def get_created_by_username(self, obj):
        u = getattr(obj, "created_by", None)
        return getattr(u, "username", "") if u else ""

    def get_created_by_full_name(self, obj):
        u = getattr(obj, "created_by", None)
        if not u:
            return ""
        first = getattr(u, "first_name", "") or ""
        last = getattr(u, "last_name", "") or ""
        full = f"{first} {last}".strip()
        return full or getattr(u, "username", "") or ""

    def get_purpose_label(self, obj):
        return obj.get_purpose_display() if obj.purpose else ""

    def get_status_label(self, obj):
        return obj.get_status_display() if obj.status else ""

    def get_provider_label(self, obj):
        key = (obj.provider or "").lower()
        return _PROVIDER_LABELS.get(key, (obj.provider or "").upper() or "")

    def get_source(self, obj):
        return _SOURCE_BY_PURPOSE.get(obj.purpose, "OUTRO")

    def get_payer_display_name(self, obj):
        if obj.wallet_id and obj.wallet:
            return obj.wallet.passenger_account.full_name or ""
        gc = getattr(obj, "guest_checkout", None)
        if gc and getattr(gc, "payer_name", ""):
            return gc.payer_name
        u = getattr(obj, "created_by", None)
        if u:
            first = getattr(u, "first_name", "") or ""
            last = getattr(u, "last_name", "") or ""
            full = f"{first} {last}".strip()
            return full or getattr(u, "username", "") or ""
        return ""

    def get_payer_display_phone(self, obj):
        if obj.wallet_id and obj.wallet:
            phone = obj.wallet.passenger_account.phone_number
            if phone:
                return phone
        return obj.payer_phone or ""


class PaymentCallbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentCallback
        fields = (
            "id", "payment_intent_id", "provider_reference",
            "signature_valid", "processing_status", "received_at",
        )
        read_only_fields = fields


class PaymentCallbackLogSerializer(serializers.ModelSerializer):
    """O que o gateway enviou, tal como chegou.

    E o primeiro sitio onde se olha quando um pagamento fica pendente: da-se a
    referencia ao operador e ve-se se o webhook chegou, se vinha assinado e o
    que trazia dentro.
    """

    reference = serializers.CharField(source="payment_intent.reference", read_only=True)
    provider = serializers.CharField(source="payment_intent.provider", read_only=True)
    intent_status = serializers.CharField(source="payment_intent.status", read_only=True)
    amount = serializers.DecimalField(
        source="payment_intent.amount", max_digits=12, decimal_places=2, read_only=True,
    )
    payer_phone = serializers.CharField(source="payment_intent.payer_phone", read_only=True)

    class Meta:
        model = PaymentCallback
        fields = (
            "id", "payment_intent_id", "reference", "provider", "intent_status",
            "amount", "payer_phone", "provider_reference", "signature_valid",
            "processing_status", "raw_payload", "received_at",
        )
        read_only_fields = fields


class PaymentCallbackIngestSerializer(serializers.Serializer):
    reference = serializers.CharField()
    provider_reference = serializers.CharField(required=False, default="")
    status = serializers.ChoiceField(choices=["confirmed", "failed"])
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
