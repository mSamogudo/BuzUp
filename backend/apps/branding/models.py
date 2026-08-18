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

    # Contactos do operador, impressos no bilhete e mostrados nas apps.
    # Um passageiro com um problema a bordo (autocarro avariado, acidente,
    # bilhete recusado) tem o bilhete na mao — e ai que o numero tem de estar,
    # nao num site que ele nao vai procurar nesse momento.
    emergency_phone = models.CharField(max_length=32, blank=True)
    support_phone = models.CharField(max_length=32, blank=True)
    support_email = models.EmailField(blank=True)

    # Identificacao do operador. Sai no rodape do portal de compra, no bilhete
    # e nos termos — quem compra tem de saber a quem esta a comprar.
    company_name = models.CharField(max_length=160, blank=True)
    company_address = models.CharField(max_length=255, blank=True)
    company_website = models.CharField(max_length=160, blank=True)
    # Varios numeros: um operador de carreiras tem a central, o balcao e o
    # movel, e o passageiro precisa de todos.
    contact_phones = models.JSONField(default=list, blank=True)

    # --- Termos e condicoes ------------------------------------------------
    #
    # Guardados em ESTRUTURA e nao em HTML: sao texto que o cliente edita no
    # portal, e um campo de HTML editavel e um campo por onde entra qualquer
    # coisa na pagina de compra. Assim cada seccao e um titulo e uma lista de
    # paragrafos, e nada do que la for escrito pode ser interpretado como
    # marcacao.
    #
    # Formato: [{"title": str, "items": [str, ...]}, ...]
    terms_sections = models.JSONField(default=list, blank=True)
    terms_intro = models.TextField(blank=True)
    terms_closing = models.TextField(blank=True)
    # Versao inglesa. Campos proprios e nao um JSON por lingua porque a
    # aplicacao inteira so conhece duas (pt/en) e um par de campos diz-se em
    # duas linhas — um mapa de linguas custaria um editor generico para
    # resolver um problema que ninguem tem.
    #
    # Vazia = cai para a portuguesa. Melhor mostrar os termos na lingua errada
    # do que nao mostrar termos nenhuns a quem esta prestes a comprar.
    terms_sections_en = models.JSONField(default=list, blank=True)
    terms_intro_en = models.TextField(blank=True)
    terms_closing_en = models.TextField(blank=True)
    # A versao viaja com cada compra. Sem ela, saber-se-ia que o passageiro
    # aceitou "os termos" — mas nao QUAIS, e uns termos alterados depois da
    # compra passariam a valer para tras.
    terms_version = models.CharField(max_length=32, blank=True)
    terms_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Configuracao de marca"
        verbose_name_plural = "Configuracao de marca"

    def __str__(self):
        return self.platform_name or "BuzUp"

    @classmethod
    def load(cls) -> "BrandingSettings":
        obj, _ = cls.objects.get_or_create(key="default")
        return obj

    @property
    def has_terms(self) -> bool:
        return bool(self.terms_sections)

    def terms_for(self, locale: str = "pt") -> dict:
        """Termos na lingua pedida, com recurso a portuguesa."""
        if str(locale).lower().startswith("en") and self.terms_sections_en:
            return {
                "sections": self.terms_sections_en,
                "intro": self.terms_intro_en,
                "closing": self.terms_closing_en,
            }
        return {
            "sections": self.terms_sections,
            "intro": self.terms_intro,
            "closing": self.terms_closing,
        }

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
