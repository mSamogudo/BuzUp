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
            "company_name", "company_address", "company_website", "contact_phones",
            # Termos: publicos por definicao — quem compra tem de os poder ler
            # ANTES de aceitar, e nao depois de se autenticar.
            "terms_sections", "terms_intro", "terms_closing",
            "terms_sections_en", "terms_intro_en", "terms_closing_en",
            "terms_version", "terms_updated_at",
            *LOGO_FIELDS,
        )
        read_only_fields = ("updated_at", "terms_updated_at")
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

    def validate_terms_sections_en(self, value):
        return self._validar_seccoes(value)

    def validate_terms_sections(self, value):
        return self._validar_seccoes(value)

    def _validar_seccoes(self, value):
        """Cada seccao tem de ter titulo e pelo menos um paragrafo.

        Sem isto, uma seccao vazia gravada por engano aparecia na pagina de
        compra como um titulo sem nada por baixo — e o passageiro aceitava
        termos com um buraco.
        """
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Formato invalido.")
        if len(value) > 40:
            raise serializers.ValidationError("Demasiadas seccoes (maximo 40).")
        seccoes = TermosSeccaoSerializer(data=value, many=True)
        seccoes.is_valid(raise_exception=True)
        return seccoes.validated_data

    def update(self, instance, validated_data):
        """Mexer nos termos carimba a data e sobe a versao.

        A versao viaja com cada compra: sem a subir, uma alteracao feita hoje
        passava a valer para quem aceitou os termos de ontem — e ninguem
        conseguiria dizer o que essa pessoa aceitou.
        """
        from django.utils import timezone

        campos_dos_termos = {
            "terms_sections", "terms_intro", "terms_closing",
            "terms_sections_en", "terms_intro_en", "terms_closing_en",
        }
        mexeu = any(
            campo in validated_data and validated_data[campo] != getattr(instance, campo)
            for campo in campos_dos_termos
        )
        instancia = super().update(instance, validated_data)
        if mexeu and "terms_version" not in validated_data:
            agora = timezone.now()
            instancia.terms_updated_at = agora
            instancia.terms_version = agora.strftime("%Y-%m-%d.%H%M")
            instancia.save(update_fields=["terms_updated_at", "terms_version", "updated_at"])
        return instancia

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


class TermosSeccaoSerializer(serializers.Serializer):
    """Uma seccao dos termos: um titulo e paragrafos.

    Estrutura, e nao HTML. Um campo de HTML editavel no portal seria um campo
    por onde entra qualquer coisa na pagina de compra publica — e quem edita a
    marca nao devia poder injectar marcacao no browser de quem compra.
    """

    title = serializers.CharField(max_length=160)
    items = serializers.ListField(
        child=serializers.CharField(max_length=2000), min_length=1, max_length=40,
    )
