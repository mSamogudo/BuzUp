from django.conf import settings
from django.db import models

from apps.core.models import BaseModel

# Os "slots" de logo que o portal/apps/relatorios consomem. A ordem aqui e a
# usada na serializacao e na pagina do portal. Cada slot e um FileField (sem
# Pillow) servido por /media/, e exposto como `<slot>_url` (URL absoluta).
LOGO_FIELDS = (
    "primary_logo",      # logo principal do cliente (fallback global)
    "sidebar_logo",      # cabecalho/sidebar do portal (expandido)
    "sidebar_mark",      # marca compacta do portal (sidebar recolhida)
    "auth_logo",         # pagina de login (portal)
    "pos_logo",          # app POS
    "mobile_logo",       # app do passageiro
    "report_logo",       # cabecalho dos relatorios/PDF
    "powered_by_logo",   # "powered by" (UpDigital), rodape/relatorios
    "favicon",           # favicon do portal
)


class BrandingSettings(BaseModel):
    """Configuracao de marca (logos) editavel pelo portal — linha unica.

    GET e publico (apps e ecra de login carregam ao arrancar); a escrita exige
    a capacidade ``settings.manage``. Cada logo cai para ``primary_logo`` do
    lado de quem consome quando o slot especifico nao estiver definido.
    """

    # Singleton: uma so linha, sempre obtida via load().
    key = models.CharField(max_length=32, unique=True, default="default", editable=False)

    platform_name = models.CharField(max_length=120, blank=True, default="BuzUp")

    primary_logo = models.FileField(upload_to="branding/", blank=True)
    sidebar_logo = models.FileField(upload_to="branding/", blank=True)
    sidebar_mark = models.FileField(upload_to="branding/", blank=True)
    auth_logo = models.FileField(upload_to="branding/", blank=True)
    pos_logo = models.FileField(upload_to="branding/", blank=True)
    mobile_logo = models.FileField(upload_to="branding/", blank=True)
    report_logo = models.FileField(upload_to="branding/", blank=True)
    powered_by_logo = models.FileField(upload_to="branding/", blank=True)
    favicon = models.FileField(upload_to="branding/", blank=True)

    class Meta:
        verbose_name = "Configuracao de marca"
        verbose_name_plural = "Configuracao de marca"

    def __str__(self):
        return self.platform_name or "BuzUp"

    @classmethod
    def load(cls) -> "BrandingSettings":
        obj, _ = cls.objects.get_or_create(key="default")
        return obj

    def file_url(self, field_name: str, request=None) -> str:
        """URL absoluta de um slot de logo (string vazia quando nao definido)."""
        f = getattr(self, field_name, None)
        if not f:
            return ""
        url = f.url
        if request is not None:
            return request.build_absolute_uri(url)
        base = str(getattr(settings, "PUBLIC_BASE_URL", "") or "").rstrip("/")
        return f"{base}{url}"
