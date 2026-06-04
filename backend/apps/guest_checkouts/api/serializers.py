from django.conf import settings
from rest_framework import serializers

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout


class GuestCheckoutSerializer(serializers.ModelSerializer):
    origin_stop_ref_id = serializers.IntegerField(read_only=True)
    destination_stop_ref_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = GuestCheckout
        fields = (
            "id", "uuid", "reference", "payer_phone", "buyer_name",
            "route_code", "route_name", "origin_stop", "destination_stop",
            "origin_stop_ref_id", "destination_stop_ref_id",
            "quantity", "unit_amount", "total_amount", "status", "trip_id",
            "expires_at", "created_at", "updated_at",
        )
        read_only_fields = fields


class GuestCheckoutCreateSerializer(serializers.Serializer):
    payer_phone = serializers.CharField(max_length=20)
    buyer_name = serializers.CharField(max_length=255, required=False, default="", allow_blank=True)
    route_code = serializers.CharField(max_length=32)
    route_name = serializers.CharField(max_length=255, required=False, default="", allow_blank=True)
    origin_stop = serializers.CharField(max_length=255)
    destination_stop = serializers.CharField(max_length=255)
    origin_stop_id = serializers.IntegerField(required=False)
    destination_stop_id = serializers.IntegerField(required=False)
    trip_id = serializers.IntegerField(required=False)
    quantity = serializers.IntegerField(min_value=1, max_value=10, default=1)
    unit_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)

    def validate(self, attrs):
        origin_id = attrs.get("origin_stop_id")
        destination_id = attrs.get("destination_stop_id")
        if origin_id and destination_id and origin_id == destination_id:
            raise serializers.ValidationError({"destination_stop_id": "Destino deve ser diferente da origem."})

        origin_name = str(attrs.get("origin_stop") or "").strip().lower()
        destination_name = str(attrs.get("destination_stop") or "").strip().lower()
        if origin_name and destination_name and origin_name == destination_name:
            raise serializers.ValidationError({"destination_stop": "Destino deve ser diferente da origem."})
        return attrs


class DigitalTravelPassSerializer(serializers.ModelSerializer):
    origin_stop_ref_id = serializers.IntegerField(read_only=True)
    destination_stop_ref_id = serializers.IntegerField(read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = DigitalTravelPass
        fields = (
            "id", "uuid", "route_code", "route_name",
            "origin_stop", "destination_stop", "fare_amount",
            "origin_stop_ref_id", "destination_stop_ref_id",
            "status", "delivery_channel", "trip_id",
            "valid_from", "valid_until", "used_at", "pdf_url", "created_at",
        )
        read_only_fields = fields

    def get_pdf_url(self, obj):
        if not obj.token:
            return ""
        base = str(getattr(settings, "PUBLIC_BASE_URL", "") or "").rstrip("/")
        return f"{base}/api/public/ticket/{obj.token}/" if base else f"/api/public/ticket/{obj.token}/"


class GuestCheckoutPublicSerializer(serializers.ModelSerializer):
    passes = DigitalTravelPassSerializer(source="travel_passes", many=True, read_only=True)

    class Meta:
        model = GuestCheckout
        fields = (
            "reference", "route_code", "route_name",
            "origin_stop", "destination_stop",
            "quantity", "total_amount", "status", "passes",
        )
        read_only_fields = fields
