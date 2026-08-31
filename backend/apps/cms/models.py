"""Modelo de dados do CMS do site publico.

Fonte: docs/design-handoff/03-cms-especificacao.md, seccao 1.

Principio do handoff: o site publico nao tem texto no codigo. Cada bloco,
rotulo, preco, pergunta de FAQ e ligacao de rodape vive aqui, em PT e EN.

Os campos traduziveis sao JSON no formato ``{"pt": "...", "en": "..."}``. E
propositadamente um dicionario simples e nao uma tabela de traducoes: o editor
grava sempre os dois idiomas ao mesmo tempo e a leitura publica faz-se por
idioma unico, portanto uma juncao por linha so acrescentava custo.
"""

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel

LOCALES = ("pt", "en")


def empty_i18n():
    return {"pt": "", "en": ""}


def empty_i18n_list():
    return {"pt": [], "en": []}


def default_locales():
    return ["pt", "en"]


def i18n_get(value, locale, fallback="pt"):
    """Le um campo i18n com recuo para PT quando o idioma pedido esta vazio.

    Uma lista vazia e um valor legitimo (uma seccao sem marcadores) e tem de
    continuar a ser uma lista do outro lado — se virasse string, o site
    rebentava a iterar sobre ela.
    """
    if not isinstance(value, dict):
        return value if value is not None else ""
    if locale in value:
        got = value[locale]
        if got is not None and got != "":
            return got
    got = value.get(fallback)
    return got if got is not None else ""


class AuthoredModel(BaseModel):
    """Autoria de quem criou e de quem alterou pela ultima vez."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )

    class Meta:
        abstract = True


class MediaAsset(AuthoredModel):
    """Biblioteca de media (1.4). Aceita PNG, JPG, WEBP, SVG e PDF ate 10 MB."""

    MAX_BYTES = 10 * 1024 * 1024
    ALLOWED_MIME = (
        "image/png", "image/jpeg", "image/webp", "image/svg+xml", "application/pdf",
    )

    file = models.FileField(upload_to="cms/media/")
    filename = models.CharField(max_length=255)
    mime = models.CharField(max_length=64)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    bytes = models.PositiveIntegerField(default=0)
    alt = models.JSONField(default=empty_i18n, blank=True)
    folder = models.CharField(max_length=120, blank=True, default="")

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["folder", "-created_at"])]

    def __str__(self):
        return self.filename

    @property
    def url(self):
        try:
            return self.file.url
        except ValueError:
            return ""

    def used_in(self):
        """Paginas que referenciam este ficheiro.

        A procura e feita sobre o JSON dos blocos porque um bloco pode apontar
        para media de varias formas (item de logo, imagem de bloco, imagem de
        partilha) e nao vale a pena uma tabela de ligacao para o volume deste
        site.
        """
        needle = self.pk
        hits = []
        for block in PageBlock.objects.select_related("page").all():
            if _json_has_media(block.content, needle):
                if block.page_id not in [p["id"] for p in hits]:
                    hits.append({"id": block.page_id, "slug": block.page.slug, "title": block.page.title})
        for seo in SeoMeta.objects.select_related("page").filter(og_image_id=needle):
            if seo.page_id not in [p["id"] for p in hits]:
                hits.append({"id": seo.page_id, "slug": seo.page.slug, "title": seo.page.title})
        return hits

    def in_use(self):
        if EcoSystem.objects.filter(logo_id=self.pk).exists():
            return True
        return bool(self.used_in())


def _json_has_media(node, media_id):
    if isinstance(node, dict):
        if node.get("media_id") == media_id:
            return True
        return any(_json_has_media(v, media_id) for v in node.values())
    if isinstance(node, list):
        return any(_json_has_media(v, media_id) for v in node)
    return False


class Page(AuthoredModel):
    """Pagina do site publico (1.1)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        REVIEW = "review", "Em revisao"
        SCHEDULED = "scheduled", "Agendado"
        PUBLISHED = "published", "Publicado"

    class Template(models.TextChoices):
        LANDING = "landing", "Landing"
        PRICING = "pricing", "Precos"
        CONTACT = "contact", "Contactos"
        APPS = "apps", "Apps"
        GENERIC = "generic", "Generica"

    # "" e a pagina inicial. A unicidade so vale entre paginas vivas: uma
    # pagina arquivada nao pode prender o slug para sempre.
    slug = models.CharField(max_length=120, blank=True, default="")
    title = models.JSONField(default=empty_i18n)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    template = models.CharField(max_length=16, choices=Template.choices, default=Template.GENERIC)
    locales = models.JSONField(default=default_locales)
    published_at = models.DateTimeField(null=True, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    current_version = models.ForeignKey(
        "cms.PageVersion", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )

    class Meta:
        ordering = ("slug",)
        constraints = [
            models.UniqueConstraint(
                fields=["slug"], condition=models.Q(deleted_at__isnull=True),
                name="cms_page_slug_unico_activo",
            )
        ]

    def __str__(self):
        return self.slug or "(inicial)"

    @property
    def path(self):
        return "/" if not self.slug else f"/{self.slug}"


class PageBlock(BaseModel):
    """Um bloco por seccao da pagina, ordenado (1.2)."""

    class Type(models.TextChoices):
        HEROI = "heroi", "Heroi"
        LOGOS = "logos", "Faixa de logos"
        RECURSOS = "recursos", "Funcionalidades"
        PASSOS = "passos", "Comecar em tres passos"
        PORQUE = "porque", "Porque BusUp"
        CASOS = "casos", "Casos"
        PRECOS = "precos", "Precos"
        FAQ = "faq", "FAQ"
        FORM = "form", "Formulario"
        ECO = "eco", "Ecossistema"
        CTA = "cta", "CTA"
        RICHTEXT = "richtext", "Texto"
        MEDIA = "media", "Media"

    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="blocks")
    type = models.CharField(max_length=16, choices=Type.choices)
    position = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)
    content = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("position", "id")
        indexes = [models.Index(fields=["page", "position"])]

    def __str__(self):
        return f"{self.page} · {self.type} #{self.position}"


class Menu(BaseModel):
    """Menus do cabecalho e do rodape (1.5)."""

    class Key(models.TextChoices):
        HEADER = "header", "Cabecalho"
        FOOTER_PRODUCT = "footer_product", "Rodape · Produto"
        FOOTER_CONTACT = "footer_contact", "Rodape · Contacto"
        FOOTER_ECO = "footer_eco", "Rodape · Ecossistema"

    key = models.CharField(max_length=32, choices=Key.choices, unique=True)
    label = models.JSONField(default=empty_i18n)

    class Meta:
        ordering = ("key",)

    def __str__(self):
        return self.key


class MenuItem(BaseModel):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name="items")
    label = models.JSONField(default=empty_i18n)
    page = models.ForeignKey(Page, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    href = models.CharField(max_length=400, blank=True, default="")
    position = models.PositiveIntegerField(default=0)
    target = models.CharField(max_length=10, blank=True, default="")
    visible = models.BooleanField(default=True)

    class Meta:
        ordering = ("position", "id")

    def resolved_href(self):
        if self.page_id and self.page:
            return self.page.path
        return self.href


class SeoMeta(BaseModel):
    """SEO e partilha por pagina (1.6). Limites do editor em `LIMITS`."""

    LIMITS = {"title": 60, "description": 160, "slug": 40, "keywords": 90}

    page = models.OneToOneField(Page, on_delete=models.CASCADE, related_name="seo")
    title = models.JSONField(default=empty_i18n, blank=True)
    description = models.JSONField(default=empty_i18n, blank=True)
    slug = models.JSONField(default=empty_i18n, blank=True)
    keywords = models.JSONField(default=empty_i18n, blank=True)
    og_image = models.ForeignKey(MediaAsset, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    no_index = models.BooleanField(default=False)

    def __str__(self):
        return f"SEO · {self.page}"


class Plan(AuthoredModel):
    """Planos comerciais (1.7). Alimentam a landing e a pagina de precos."""

    name = models.JSONField(default=empty_i18n)
    price_label = models.JSONField(default=empty_i18n)
    unit = models.JSONField(default=empty_i18n, blank=True)
    cta_label = models.JSONField(default=empty_i18n, blank=True)
    items = models.JSONField(default=empty_i18n_list, blank=True)
    position = models.PositiveIntegerField(default=0)
    highlighted = models.BooleanField(default=False)
    visible = models.BooleanField(default=True)

    class Meta:
        ordering = ("position", "id")

    def __str__(self):
        return i18n_get(self.name, "pt")


class PlanFeature(BaseModel):
    """Linha da tabela comparativa da pagina de precos (1.8)."""

    label = models.JSONField(default=empty_i18n)
    urban = models.JSONField(default=empty_i18n, blank=True)
    intercity = models.JSONField(default=empty_i18n, blank=True)
    institutional = models.JSONField(default=empty_i18n, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("position", "id")

    def __str__(self):
        return i18n_get(self.label, "pt")


class EcoSystem(AuthoredModel):
    """Sistemas do ecossistema UpDigital (1.9)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        PUBLISHED = "published", "Publicado"

    name = models.CharField(max_length=80)
    logo = models.ForeignKey(MediaAsset, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    url = models.URLField(blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PUBLISHED)
    position = models.PositiveIntegerField(default=0)
    # O desenho mostra tambem uma nota curta por sistema, por baixo do nome.
    note = models.JSONField(default=empty_i18n, blank=True)

    class Meta:
        ordering = ("position", "id")

    def __str__(self):
        return self.name


class PageVersion(BaseModel):
    """Historico de versoes (1.10).

    Cada gravacao cria uma versao. Restaurar cria uma versao nova a partir da
    antiga: o historico nunca perde nada.
    """

    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="versions")
    number = models.PositiveIntegerField(default=1)
    snapshot = models.JSONField(default=dict)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    note = models.CharField(max_length=200, blank=True, default="")
    restored_from = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ("-number",)
        constraints = [
            models.UniqueConstraint(fields=["page", "number"], name="cms_versao_numero_unico"),
        ]

    def __str__(self):
        return f"{self.page} v{self.number}"


class ScheduledPublication(BaseModel):
    """Publicacoes agendadas (1.11). Um worker publica no momento marcado."""

    class Target(models.TextChoices):
        PAGE = "page", "Pagina"
        PLAN = "plan", "Plano"
        ECO_SYSTEM = "eco_system", "Sistema do ecossistema"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Agendada"
        DONE = "done", "Publicada"
        FAILED = "failed", "Falhou"
        CANCELLED = "cancelled", "Cancelada"

    target_type = models.CharField(max_length=16, choices=Target.choices, default=Target.PAGE)
    target_id = models.PositiveIntegerField()
    run_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SCHEDULED)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    result = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("run_at",)
        indexes = [models.Index(fields=["status", "run_at"])]

    def __str__(self):
        return f"{self.target_type}#{self.target_id} @ {self.run_at:%Y-%m-%d %H:%M}"
