from rest_framework import serializers

from apps.leads.models import ServiceRequest


class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = ("name", "organization", "phone", "email", "interest", "fleet_size", "message")

    def validate_phone(self, value):
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) < 9:
            raise serializers.ValidationError("Indique um telefone valido.")
        return value.strip()


class ServiceRequestSerializer(serializers.ModelSerializer):
    interest_label = serializers.CharField(source="get_interest_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ServiceRequest
        fields = (
            "id", "uuid", "name", "organization", "phone", "email",
            "interest", "interest_label", "fleet_size", "message",
            "status", "status_label", "source", "created_at", "updated_at",
        )
        read_only_fields = ("id", "uuid", "created_at", "updated_at")
