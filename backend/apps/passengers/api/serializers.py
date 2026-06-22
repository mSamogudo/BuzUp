from rest_framework import serializers

from apps.passengers.models import PassengerAccount
from apps.users.models import User
from apps.users.otp import normalize_otp_phone


class PassengerAccountSerializer(serializers.ModelSerializer):
    has_user_account = serializers.SerializerMethodField()

    class Meta:
        model = PassengerAccount
        fields = (
            "id", "uuid", "full_name", "phone_number", "email",
            "document_type", "document_number", "status", "has_user_account", "created_at", "updated_at",
        )
        read_only_fields = ("id", "uuid", "created_at", "updated_at")

    def get_has_user_account(self, obj):
        phone = normalize_otp_phone(obj.phone_number)
        return bool(phone and User.objects.filter(username=f"passenger_{phone}", deleted_at__isnull=True).exists())


class PassengerAccountDetailSerializer(PassengerAccountSerializer):
    """Detalhe completo do passageiro: carteira, cartoes, transacoes,
    validacoes (viagens), rotas usadas e estatisticas."""

    wallet = serializers.SerializerMethodField()
    cards = serializers.SerializerMethodField()
    recent_transactions = serializers.SerializerMethodField()
    recent_validations = serializers.SerializerMethodField()
    routes_used = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()

    class Meta(PassengerAccountSerializer.Meta):
        fields = PassengerAccountSerializer.Meta.fields + (
            "wallet", "cards", "recent_transactions", "recent_validations", "routes_used", "stats",
        )

    def get_wallet(self, obj):
        w = getattr(obj, "wallet", None)
        if not w:
            return None
        return {
            "id": w.id, "balance": str(w.balance_cached),
            "currency": getattr(w, "currency", ""), "status": w.status,
        }

    def get_cards(self, obj):
        return [{
            "id": c.id, "card_number": c.card_number or c.card_uid,
            "type": c.card_type, "technology": c.card_technology, "status": c.status,
        } for c in obj.cards.all()[:50]]

    def get_recent_transactions(self, obj):
        w = getattr(obj, "wallet", None)
        if not w:
            return []
        return [{
            "created_at": t.created_at, "type": t.type,
            "direction": getattr(t, "direction", ""), "amount": str(t.amount),
            "balance_after": str(getattr(t, "balance_after", "") or ""),
            "reference": t.reference, "status": getattr(t, "status", ""),
        } for t in w.transactions.all().order_by("-created_at")[:20]]

    @staticmethod
    def _amount(v):
        for f in ("amount", "fare_amount", "charged_amount"):
            val = getattr(v, f, None)
            if val is not None:
                return str(val)
        return ""

    def get_recent_validations(self, obj):
        qs = obj.validation_events.select_related(
            "route", "trip", "origin_stop", "destination_stop"
        ).order_by("-created_at")[:20]
        out = []
        for v in qs:
            out.append({
                "created_at": v.created_at,
                "type": v.validation_type,
                "status": v.status,
                "route": str(v.route) if v.route_id else "",
                "trip": str(v.trip) if v.trip_id else "",
                "origin": str(v.origin_stop) if v.origin_stop_id else "",
                "destination": str(v.destination_stop) if v.destination_stop_id else "",
                "amount": self._amount(v),
            })
        return out

    def get_routes_used(self, obj):
        seen, names = set(), []
        for v in obj.validation_events.filter(route__isnull=False).select_related("route")[:500]:
            s = str(v.route)
            if s and s not in seen:
                seen.add(s)
                names.append(s)
        return names[:50]

    def get_stats(self, obj):
        ve = obj.validation_events
        return {
            "validations_total": ve.count(),
            "trips_taken": ve.filter(status="approved").count(),
            "cards_count": obj.cards.count(),
            "travel_passes_count": obj.travel_passes.count() if hasattr(obj, "travel_passes") else 0,
            "guest_checkouts_count": obj.guest_checkouts.count() if hasattr(obj, "guest_checkouts") else 0,
        }


class PassengerAccountCreateSerializer(serializers.ModelSerializer):
    create_account = serializers.BooleanField(write_only=True, required=False, default=False)
    notify_by_sms = serializers.BooleanField(write_only=True, required=False, default=True)

    class Meta:
        model = PassengerAccount
        fields = ("full_name", "phone_number", "email", "document_type", "document_number", "create_account", "notify_by_sms")


class PassengerAccountCreateAccessSerializer(serializers.Serializer):
    notify_by_sms = serializers.BooleanField(required=False, default=True)
