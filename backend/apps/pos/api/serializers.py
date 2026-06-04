from decimal import Decimal

from rest_framework import serializers

from apps.pos.models import PosSession


class PosSessionSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source="agent.get_full_name", read_only=True, default="")
    device_serial = serializers.CharField(source="device.serial_number", read_only=True)
    route_code = serializers.CharField(source="allocated_route.code", read_only=True, default="")
    route_name = serializers.CharField(source="allocated_route.name", read_only=True, default="")

    class Meta:
        model = PosSession
        fields = (
            "id", "uuid", "agent_id", "agent_name",
            "device_id", "device_serial",
            "allocated_route_id", "route_code", "route_name",
            "status", "opened_at", "closed_at",
        )
        read_only_fields = fields


class OpenSessionSerializer(serializers.Serializer):
    device_serial = serializers.CharField(max_length=128)
    route_id = serializers.IntegerField(required=False, allow_null=True)


class PosCardValidateSerializer(serializers.Serializer):
    card_uid = serializers.CharField(max_length=64)
    idempotency_key = serializers.CharField(max_length=128)


class PosQrValidateSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=128)
    idempotency_key = serializers.CharField(max_length=128)


class PosCardTopupSerializer(serializers.Serializer):
    card_uid = serializers.CharField(max_length=64)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("1.00"))
    payer_phone = serializers.CharField(max_length=20)


class PosPackageTopupSerializer(serializers.Serializer):
    card_uid = serializers.CharField(max_length=64)
    package_id = serializers.IntegerField()
