"""Serializers do CMS. Erros 422 por campo, como o resto da API."""

from rest_framework import serializers

from apps.cms.models import (
    LOCALES,
    EcoSystem,
    MediaAsset,
    Menu,
    MenuItem,
    Page,
    PageBlock,
    PageVersion,
    Plan,
    PlanFeature,
    ScheduledPublication,
    SeoMeta,
)


class I18nField(serializers.JSONField):
    """Campo traduzivel `{"pt": ..., "en": ...}`.

    Aceita tambem uma string simples e promove-a a PT — assim um cliente antigo
    ou um seed rapido nao rebenta, e o editor continua a ver os dois idiomas.
    """

    def __init__(self, *args, allow_list=False, **kwargs):
        self.allow_list = allow_list
        super().__init__(*args, **kwargs)

    def to_internal_value(self, data):
        empty = [] if self.allow_list else ""
        if data is None:
            return {locale: empty for locale in LOCALES}
        if isinstance(data, (str, list)):
            return {"pt": data, "en": empty}
        if not isinstance(data, dict):
            raise serializers.ValidationError("Indique um valor por idioma.")
        extra = set(data) - set(LOCALES)
        if extra:
            raise serializers.ValidationError(f"Idiomas desconhecidos: {', '.join(sorted(extra))}.")
        return {locale: data.get(locale, empty) for locale in LOCALES}


class MediaAssetSerializer(serializers.ModelSerializer):
    alt = I18nField(required=False)
    url = serializers.CharField(read_only=True)
    used_in = serializers.SerializerMethodField()

    class Meta:
        model = MediaAsset
        fields = (
            "id", "uuid", "file", "filename", "url", "mime", "width", "height",
            "bytes", "alt", "folder", "used_in", "created_at", "updated_at", "deleted_at",
        )
        read_only_fields = ("id", "uuid", "url", "mime", "bytes", "created_at", "updated_at", "deleted_at")
        extra_kwargs = {"file": {"required": False}, "filename": {"required": False}}

    def get_used_in(self, obj):
        # So na leitura de detalhe: a varredura dos blocos e cara para uma lista.
        if self.context.get("with_usage"):
            return obj.used_in()
        return None

    def validate_file(self, value):
        if value is None:
            return value
        if value.size > MediaAsset.MAX_BYTES:
            raise serializers.ValidationError("O ficheiro excede 10 MB.")
        mime = getattr(value, "content_type", "") or ""
        if mime and mime not in MediaAsset.ALLOWED_MIME:
            raise serializers.ValidationError("Formato nao aceite. Use PNG, JPG, WEBP, SVG ou PDF.")
        return value


class PageBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageBlock
        fields = ("id", "uuid", "type", "position", "enabled", "content")
        read_only_fields = ("id", "uuid")


class SeoMetaSerializer(serializers.ModelSerializer):
    title = I18nField(required=False)
    description = I18nField(required=False)
    slug = I18nField(required=False)
    keywords = I18nField(required=False)

    class Meta:
        model = SeoMeta
        fields = ("id", "page", "title", "description", "slug", "keywords", "og_image", "no_index")
        read_only_fields = ("id", "page")

    def validate(self, attrs):
        errors = {}
        for field, limit in SeoMeta.LIMITS.items():
            value = attrs.get(field)
            if not isinstance(value, dict):
                continue
            for locale, text in value.items():
                if isinstance(text, str) and len(text) > limit:
                    errors.setdefault(field, []).append(
                        f"{locale.upper()}: maximo {limit} caracteres ({len(text)} usados)."
                    )
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class PageSerializer(serializers.ModelSerializer):
    title = I18nField()
    blocks = PageBlockSerializer(many=True, read_only=True)
    seo = SeoMetaSerializer(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    template_label = serializers.CharField(source="get_template_display", read_only=True)
    updated_by_name = serializers.SerializerMethodField()
    version_number = serializers.SerializerMethodField()
    path = serializers.CharField(read_only=True)

    class Meta:
        model = Page
        fields = (
            "id", "uuid", "slug", "path", "title", "status", "status_label",
            "template", "template_label", "locales", "published_at", "scheduled_for",
            "current_version", "version_number", "blocks", "seo",
            "updated_by_name", "created_at", "updated_at", "deleted_at",
        )
        read_only_fields = (
            "id", "uuid", "status", "published_at", "scheduled_for",
            "current_version", "created_at", "updated_at", "deleted_at",
        )

    def get_updated_by_name(self, obj):
        user = obj.updated_by or obj.created_by
        if not user:
            return ""
        return user.get_full_name() or user.get_username()

    def get_version_number(self, obj):
        return obj.current_version.number if obj.current_version else 0

    def validate_slug(self, value):
        value = (value or "").strip().strip("/")
        if value and not all(part.replace("-", "").isalnum() for part in value.split("/")):
            raise serializers.ValidationError("Use apenas letras, numeros, hifens e barras.")
        qs = Page.objects.filter(slug=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ja existe uma pagina com este endereco.")
        return value

    def validate_locales(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("Indique pelo menos um idioma.")
        unknown = [v for v in value if v not in LOCALES]
        if unknown:
            raise serializers.ValidationError(f"Idiomas desconhecidos: {', '.join(unknown)}.")
        return value


class PageListSerializer(PageSerializer):
    """Lista sem blocos — a tabela de paginas nao precisa do conteudo todo."""

    class Meta(PageSerializer.Meta):
        fields = tuple(f for f in PageSerializer.Meta.fields if f not in ("blocks", "seo"))


class MenuItemSerializer(serializers.ModelSerializer):
    label = I18nField()
    resolved_href = serializers.CharField(read_only=True)

    class Meta:
        model = MenuItem
        fields = ("id", "uuid", "label", "page", "href", "resolved_href", "position", "target", "visible")
        read_only_fields = ("id", "uuid")


class MenuSerializer(serializers.ModelSerializer):
    label = I18nField(required=False)
    items = MenuItemSerializer(many=True, read_only=True)

    class Meta:
        model = Menu
        fields = ("id", "uuid", "key", "label", "items")
        read_only_fields = ("id", "uuid")


class PlanSerializer(serializers.ModelSerializer):
    name = I18nField()
    price_label = I18nField(required=False)
    unit = I18nField(required=False)
    cta_label = I18nField(required=False)
    items = I18nField(required=False, allow_list=True)

    class Meta:
        model = Plan
        fields = (
            "id", "uuid", "name", "price_label", "unit", "cta_label", "items",
            "position", "highlighted", "visible", "created_at", "updated_at", "deleted_at",
        )
        read_only_fields = ("id", "uuid", "created_at", "updated_at", "deleted_at")


class PlanFeatureSerializer(serializers.ModelSerializer):
    label = I18nField()
    urban = I18nField(required=False)
    intercity = I18nField(required=False)
    institutional = I18nField(required=False)

    class Meta:
        model = PlanFeature
        fields = ("id", "uuid", "label", "urban", "intercity", "institutional", "position")
        read_only_fields = ("id", "uuid")


class EcoSystemSerializer(serializers.ModelSerializer):
    note = I18nField(required=False)
    logo_url = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = EcoSystem
        fields = (
            "id", "uuid", "name", "logo", "logo_url", "url", "note",
            "status", "status_label", "position", "created_at", "updated_at", "deleted_at",
        )
        read_only_fields = ("id", "uuid", "created_at", "updated_at", "deleted_at")

    def get_logo_url(self, obj):
        return obj.logo.url if obj.logo else ""


class PageVersionSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    page_slug = serializers.CharField(source="page.slug", read_only=True)

    class Meta:
        model = PageVersion
        fields = (
            "id", "uuid", "page", "page_slug", "number", "author_name", "note",
            "restored_from", "created_at",
        )
        read_only_fields = fields

    def get_author_name(self, obj):
        if not obj.author:
            return "—"
        return obj.author.get_full_name() or obj.author.get_username()


class PageVersionDetailSerializer(PageVersionSerializer):
    class Meta(PageVersionSerializer.Meta):
        fields = PageVersionSerializer.Meta.fields + ("snapshot",)
        read_only_fields = fields


class ScheduledPublicationSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    target_label = serializers.SerializerMethodField()

    class Meta:
        model = ScheduledPublication
        fields = (
            "id", "uuid", "target_type", "target_id", "target_label", "run_at",
            "status", "status_label", "result", "created_at",
        )
        read_only_fields = ("id", "uuid", "status", "result", "created_at")

    def get_target_label(self, obj):
        if obj.target_type == ScheduledPublication.Target.PAGE:
            page = Page.all_objects.filter(pk=obj.target_id).first()
            return page.slug or "(inicial)" if page else f"#{obj.target_id}"
        if obj.target_type == ScheduledPublication.Target.PLAN:
            plan = Plan.all_objects.filter(pk=obj.target_id).first()
            return str(plan) if plan else f"#{obj.target_id}"
        system = EcoSystem.all_objects.filter(pk=obj.target_id).first()
        return system.name if system else f"#{obj.target_id}"

    def validate(self, attrs):
        target_type = attrs.get("target_type", ScheduledPublication.Target.PAGE)
        target_id = attrs.get("target_id")
        model = {
            ScheduledPublication.Target.PAGE: Page,
            ScheduledPublication.Target.PLAN: Plan,
            ScheduledPublication.Target.ECO_SYSTEM: EcoSystem,
        }[target_type]
        if not model.objects.filter(pk=target_id).exists():
            raise serializers.ValidationError({"target_id": "O alvo do agendamento nao existe."})
        return attrs
