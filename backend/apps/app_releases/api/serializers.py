from rest_framework import serializers

from apps.app_releases.models import AppRelease, DeviceAppUpdate


class AppReleaseSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    file_size_bytes = serializers.IntegerField(read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = AppRelease
        fields = (
            "id", "uuid", "app_type", "version_name", "version_code",
            "apk_url", "download_url", "file_size_bytes", "checksum",
            "release_notes", "is_mandatory",
            "min_supported_version_code", "target_device_type",
            "target_manufacturer", "target_model", "status",
            "published_at", "created_by_name", "created_at", "updated_at",
        )
        read_only_fields = ("id", "uuid", "created_at", "updated_at")

    def get_download_url(self, obj):
        return obj.get_download_url()

    def get_created_by_name(self, obj):
        user = obj.created_by
        if not user:
            return ""
        full = (getattr(user, "get_full_name", lambda: "")() or "").strip()
        return full or getattr(user, "username", "")


class AppReleaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppRelease
        fields = (
            "app_type", "version_name", "version_code",
            "apk_file", "apk_url", "checksum", "release_notes", "is_mandatory",
            "min_supported_version_code", "target_device_type",
            "target_manufacturer", "target_model",
        )

    def validate_apk_file(self, value):
        if value and not value.name.lower().endswith(".apk"):
            raise serializers.ValidationError("O ficheiro deve ter extensao .apk.")
        return value

    def validate(self, attrs):
        if not attrs.get("apk_file") and not attrs.get("apk_url"):
            raise serializers.ValidationError(
                {"apk_file": "Carregue o ficheiro APK ou indique um apk_url."}
            )
        return attrs


class DeviceAppUpdateSerializer(serializers.ModelSerializer):
    device_serial = serializers.CharField(source="device.serial_number", read_only=True)
    release_version = serializers.CharField(source="app_release.version_name", read_only=True)

    class Meta:
        model = DeviceAppUpdate
        fields = (
            "id", "uuid", "device_id", "device_serial",
            "app_release_id", "release_version",
            "current_version_code", "target_version_code",
            "status", "prompted_at", "deferred_until",
            "downloaded_at", "installed_at", "failed_reason",
            "created_at",
        )
        read_only_fields = fields


class CheckUpdateSerializer(serializers.Serializer):
    app_type = serializers.ChoiceField(choices=AppRelease.AppType.choices)
    current_version_code = serializers.IntegerField()
    device_type = serializers.CharField(max_length=24, required=False, default="")
    manufacturer = serializers.CharField(max_length=64, required=False, default="")
