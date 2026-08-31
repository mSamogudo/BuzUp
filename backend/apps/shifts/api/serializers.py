from decimal import Decimal

from rest_framework import serializers

from apps.shifts.models import Shift


class ShiftSerializer(serializers.ModelSerializer):
    agent_name = serializers.SerializerMethodField()
    vehicle_registration = serializers.CharField(
        source="vehicle.registration", read_only=True, default="")
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Shift
        fields = (
            "id", "uuid",
            "agent_user", "agent_name", "agent_profile",
            "vehicle", "vehicle_registration", "device",
            "opened_at", "closed_at", "verified_at",
            "float_amount", "expected_amount", "counted_amount", "difference",
            "tickets_count", "validations_count",
            "status", "status_label", "notes",
            "created_at", "updated_at",
        )
        read_only_fields = fields

    def get_agent_name(self, obj):
        perfil = getattr(obj, "agent_profile", None)
        if perfil and perfil.full_name:
            return perfil.full_name
        user = obj.agent_user
        nome = f"{user.first_name} {user.last_name}".strip()
        return nome or user.username


class ShiftOpenSerializer(serializers.Serializer):
    """Abertura. O agente vem do pedido quando nao for indicado — e o caso do
    POS, onde quem abre o turno e quem o vai fazer."""

    agent_user = serializers.IntegerField(required=False)
    vehicle = serializers.IntegerField(required=False, allow_null=True)
    device = serializers.IntegerField(required=False, allow_null=True)
    float_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=Decimal("0"))


class ShiftCloseSerializer(serializers.Serializer):
    #: So o contado. O esperado e do servidor — ver `services.fechar_turno`.
    counted_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=True, min_value=Decimal("0"))
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class ShiftVerifySerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class ShiftReopenSerializer(serializers.Serializer):
    #: Obrigatorio: reabrir uma caixa dada por boa tem de deixar rasto.
    reason = serializers.CharField(required=True, allow_blank=False, max_length=2000)
