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


class PassengerAccountCreateSerializer(serializers.ModelSerializer):
    create_account = serializers.BooleanField(write_only=True, required=False, default=False)
    notify_by_sms = serializers.BooleanField(write_only=True, required=False, default=True)

    class Meta:
        model = PassengerAccount
        fields = ("full_name", "phone_number", "email", "document_type", "document_number", "create_account", "notify_by_sms")


class PassengerAccountCreateAccessSerializer(serializers.Serializer):
    notify_by_sms = serializers.BooleanField(required=False, default=True)
