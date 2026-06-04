from rest_framework import serializers

from apps.devices.models import Device, DeviceActivationRequest


class DeviceSerializer(serializers.ModelSerializer):
    assigned_agent_name = serializers.CharField(
        source="assigned_agent.get_full_name", read_only=True, default="",
    )

    class Meta:
        model = Device
        fields = (
            "id", "uuid", "serial_number", "device_type", "model_name",
            "manufacturer", "imei", "android_id", "capabilities",
            "status", "assigned_agent_id", "assigned_agent_name",
            "activation_code", "activated_at", "last_seen_at",
            "app_version", "app_version_code", "configuration",
            "created_at", "updated_at",
        )
        read_only_fields = fields


class DeviceActivationRequestSerializer(serializers.ModelSerializer):
    device_serial = serializers.CharField(source="device.serial_number", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.get_full_name", read_only=True, default="")

    class Meta:
        model = DeviceActivationRequest
        fields = (
            "id", "uuid", "device_id", "device_serial", "activation_code",
            "requested_serial_number", "requested_model", "requested_manufacturer",
            "requested_imei", "requested_android_id", "requested_capabilities",
            "app_version", "status", "requested_at",
            "reviewed_by_id", "reviewed_by_name", "reviewed_at", "rejection_reason",
        )
        read_only_fields = fields


class SelfOnboardSerializer(serializers.Serializer):
    serial_number = serializers.CharField(max_length=128)
    device_type = serializers.ChoiceField(choices=Device.DeviceType.choices)
    model_name = serializers.CharField(max_length=64, required=False, default="")
    manufacturer = serializers.CharField(max_length=64, required=False, default="")
    imei = serializers.CharField(max_length=32, required=False, default="")
    android_id = serializers.CharField(max_length=64, required=False, default="")
    capabilities = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    app_version = serializers.CharField(max_length=32, required=False, default="")


class DeviceApproveSerializer(serializers.Serializer):
    assigned_agent_id = serializers.IntegerField(required=False, allow_null=True)
    capabilities = serializers.ListField(child=serializers.CharField(), required=False)
    configuration = serializers.DictField(required=False, default=dict)


class DeviceRejectSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(required=False, default="")


class DeviceConfigurationSerializer(serializers.Serializer):
    configuration = serializers.DictField()
    capabilities = serializers.ListField(child=serializers.CharField(), required=False)
    assigned_agent_id = serializers.IntegerField(required=False, allow_null=True)


class HeartbeatSerializer(serializers.Serializer):
    serial_number = serializers.CharField(max_length=128)
    app_version = serializers.CharField(max_length=32, required=False, default="")
    app_version_code = serializers.IntegerField(required=False, default=0)
