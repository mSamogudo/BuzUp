from rest_framework import serializers

from apps.validations.models import ValidationEvent


class ValidationEventSerializer(serializers.ModelSerializer):
    route_code = serializers.CharField(source="route.code", read_only=True, default="")
    device_serial = serializers.CharField(source="device.serial_number", read_only=True, default="")

    class Meta:
        model = ValidationEvent
        fields = (
            "id", "uuid", "validation_type", "status", "failure_reason",
            "amount_debited", "route_id", "route_code",
            "trip_id", "origin_stop_id", "destination_stop_id",
            "passenger_account_id", "wallet_id",
            "physical_card_id", "digital_travel_pass_id",
            "device_id", "device_serial",
            "idempotency_key", "wallet_transaction_ref",
            "created_at",
        )
        read_only_fields = fields


class ValidateCardSerializer(serializers.Serializer):
    card_uid = serializers.CharField(max_length=64)
    route_id = serializers.IntegerField()
    origin_stop_id = serializers.IntegerField(required=False)
    destination_stop_id = serializers.IntegerField(required=False)
    trip_id = serializers.IntegerField(required=False)
    device_serial = serializers.CharField(max_length=128, required=False, default="")
    idempotency_key = serializers.CharField(max_length=128)

    def validate(self, attrs):
        if attrs.get("origin_stop_id") and attrs.get("destination_stop_id") and attrs["origin_stop_id"] == attrs["destination_stop_id"]:
            raise serializers.ValidationError({"destination_stop_id": "Destino deve ser diferente da origem."})
        return attrs


class ValidateQrSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=128)
    route_id = serializers.IntegerField(required=False)
    trip_id = serializers.IntegerField(required=False)
    device_serial = serializers.CharField(max_length=128, required=False, default="")
    idempotency_key = serializers.CharField(max_length=128)


class ValidateGuestPassSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=128)
    route_id = serializers.IntegerField(required=False)
    trip_id = serializers.IntegerField(required=False)
    device_serial = serializers.CharField(max_length=128, required=False, default="")
    idempotency_key = serializers.CharField(max_length=128)


class PurchaseTravelPassSerializer(serializers.Serializer):
    # route_id is optional: the mobile passenger only picks origin + destination
    # and the backend infers the route from the stop pair.
    route_id = serializers.IntegerField(required=False)
    origin_stop_id = serializers.IntegerField(required=False)
    destination_stop_id = serializers.IntegerField(required=False)
    trip_id = serializers.IntegerField(required=False)
    passenger_package_id = serializers.IntegerField(required=False, allow_null=True)
    use_package = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        if attrs.get("origin_stop_id") and attrs.get("destination_stop_id") and attrs["origin_stop_id"] == attrs["destination_stop_id"]:
            raise serializers.ValidationError({"destination_stop_id": "Destino deve ser diferente da origem."})
        if not attrs.get("route_id") and not (attrs.get("origin_stop_id") and attrs.get("destination_stop_id")):
            raise serializers.ValidationError({"route_id": "Indique a rota ou a origem e o destino."})
        return attrs
