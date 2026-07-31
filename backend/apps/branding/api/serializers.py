import os

from rest_framework import serializers

from apps.branding.models import LOGO_FIELDS, BrandingSettings

# SVG fora: e um documento XML que pode conter <script>, e os logos sao
# servidos do mesmo dominio do portal. Um administrador com `settings.manage`
# a carregar um SVG malicioso executava codigo no browser de todos os outros —
# XSS armazenado, com os tokens de sessao ao alcance. Os formatos raster
# cobrem todos os usos reais de um logotipo.
ALLOWED_LOGO_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico")

# Um logotipo nao precisa de mais do que isto; sem limite, o ficheiro entrava
# inteiro na memoria do worker.
MAX_LOGO_BYTES = 2 * 1024 * 1024

# Assinaturas dos formatos aceites. Verificar so a extensao deixava passar um
# ficheiro arbitrario renomeado para .png.
_MAGIC = (
    b"\x89PNG\r\n\x1a\n",       # PNG
    b"\xff\xd8\xff",              # JPEG
    b"GIF87a", b"GIF89a",           # GIF
    b"\x00\x00\x01\x00",         # ICO
)


class BrandingSettingsSerializer(serializers.ModelSerializer):
    """Logos sao write-only na entrada (o ficheiro cru) e expostos como
    ``<slot>_url`` (URL absoluta, "" quando nao definido) na saida."""

    class Meta:
        model = BrandingSettings
        fields = (
            "platform_name", "updated_at",
            # Contactos: publicos de proposito — o bilhete, o site e as apps
            # mostram-nos a quem precisa deles, e nao ha nada de sensivel num
            # numero de apoio.
            "emergency_phone", "support_phone", "support_email",
            *LOGO_FIELDS,
        )
        read_only_fields = ("updated_at",)
        extra_kwargs = {
            name: {"write_only": True, "required": False, "allow_null": True}
            for name in LOGO_FIELDS
        }

    def _validate_logo(self, value):
        if not value:
            return value
        if os.path.splitext(value.name)[1].lower() not in ALLOWED_LOGO_EXT:
            raise serializers.ValidationError(
                f"Formato invalido. Use um de: {', '.join(ALLOWED_LOGO_EXT)}."
            )
        if value.size and value.size > MAX_LOGO_BYTES:
            raise serializers.ValidationError(
                f"Ficheiro demasiado grande (maximo {MAX_LOGO_BYTES // (1024 * 1024)} MB)."
            )
        # Conteudo, nao so o nome: le o inicio do ficheiro e confirma que e
        # mesmo uma imagem dos formatos aceites.
        head = value.read(16)
        value.seek(0)
        is_webp = head[:4] == b"RIFF" and head[8:12] == b"WEBP"
        if not (is_webp or any(head.startswith(sig) for sig in _MAGIC)):
            raise serializers.ValidationError(
                "O ficheiro nao parece ser uma imagem valida."
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
