import os

from rest_framework import serializers

from apps.branding.models import LOGO_FIELDS, BrandingSettings

ALLOWED_LOGO_EXT = (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".ico")


class BrandingSettingsSerializer(serializers.ModelSerializer):
    """Logos sao write-only na entrada (o ficheiro cru) e expostos como
    ``<slot>_url`` (URL absoluta, "" quando nao definido) na saida."""

    class Meta:
        model = BrandingSettings
        fields = ("platform_name", "updated_at", *LOGO_FIELDS)
        read_only_fields = ("updated_at",)
        extra_kwargs = {
            name: {"write_only": True, "required": False, "allow_null": True}
            for name in LOGO_FIELDS
        }

    def _validate_logo(self, value):
        if value and os.path.splitext(value.name)[1].lower() not in ALLOWED_LOGO_EXT:
            raise serializers.ValidationError(
                f"Formato invalido. Use um de: {', '.join(ALLOWED_LOGO_EXT)}."
            )
        return value

    # Aplica a mesma validacao de extensao a todos os slots de logo.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in LOGO_FIELDS:
            setattr(self, f"validate_{name}", self._validate_logo)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        for name in LOGO_FIELDS:
            data[f"{name}_url"] = instance.file_url(name, request)
        return data
