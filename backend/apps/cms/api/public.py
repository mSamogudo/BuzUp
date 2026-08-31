"""Entrega do CMS ao site publico: leitura, sem autenticacao, com cache.

Fonte: docs/design-handoff/03-cms-especificacao.md, seccao 2 (bloco final) e 5.

A cache e de cinco minutos e a publicacao invalida-a — ver
`apps.cms.services.invalidate_page_cache`.
"""

from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cms.api.views import read_preview_token
from apps.cms.models import LOCALES, EcoSystem, Menu, Page, Plan, PlanFeature, i18n_get
from apps.cms.services import (
    CACHE_TTL,
    ECO_CACHE_KEY,
    page_cache_key,
    plans_cache_key,
    run_due_publications_throttled,
    serialize_public_eco,
    serialize_public_page,
    serialize_public_plan,
    serialize_public_plan_feature,
    site_cache_key,
)


def _locale(value):
    value = (value or "pt").lower()
    return value if value in LOCALES else "pt"


class PublicSiteView(APIView):
    """Menus, marca e definicoes globais do site."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, locale):
        locale = _locale(locale)
        key = site_cache_key(locale)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)

        menus = {}
        for menu in Menu.objects.prefetch_related("items"):
            menus[menu.key] = {
                "label": i18n_get(menu.label, locale),
                "items": [
                    {
                        "label": i18n_get(item.label, locale),
                        "href": item.resolved_href(),
                        "target": item.target,
                    }
                    for item in menu.items.filter(visible=True).order_by("position", "id")
                ],
            }

        data = {
            "locale": locale,
            "menus": menus,
            "branding": _branding(),
            "pages": [
                {"slug": page.slug, "path": page.path, "title": i18n_get(page.title, locale)}
                for page in Page.objects.filter(status=Page.Status.PUBLISHED)
            ],
        }
        cache.set(key, data, CACHE_TTL)
        return Response(data)


def _branding():
    try:
        from apps.branding.models import BrandingSettings

        settings_row = BrandingSettings.load()
    except Exception:
        return {}
    return {
        "platform_name": settings_row.platform_name,
        "company_name": settings_row.company_name,
        "company_address": settings_row.company_address,
        "company_website": settings_row.company_website,
        "support_email": settings_row.support_email,
        "support_phone": settings_row.support_phone,
        "contact_phones": settings_row.contact_phones,
    }


class PublicPageView(APIView):
    """Pagina publicada, com blocos e SEO no idioma pedido.

    Com `?preview_token=` valido devolve o rascunho — e o que a pre-visualizacao
    do editor abre.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, locale, slug=""):
        # Rede de seguranca do agendamento: o que ja passou da hora vai ao ar
        # antes de servirmos a pagina.
        run_due_publications_throttled()
        locale = _locale(locale)
        slug = (slug or "").strip("/")
        token = request.query_params.get("preview_token")

        if token:
            page_id = read_preview_token(token)
            page = Page.objects.filter(pk=page_id).first() if page_id else None
            if page is None:
                return Response({"detail": "Pre-visualizacao expirada."}, status=404)
            return Response({**serialize_public_page(page, locale), "preview": True})

        key = page_cache_key(slug, locale)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)

        page = Page.objects.filter(slug=slug, status=Page.Status.PUBLISHED).first()
        if page is None:
            return Response({"detail": "Pagina nao encontrada."}, status=404)
        data = serialize_public_page(page, locale)
        cache.set(key, data, CACHE_TTL)
        return Response(data)


class PublicPlansView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, locale):
        locale = _locale(locale)
        key = plans_cache_key(locale)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        data = {
            "plans": [
                serialize_public_plan(plan, locale)
                for plan in Plan.objects.filter(visible=True).order_by("position", "id")
            ],
            "features": [
                serialize_public_plan_feature(feature, locale)
                for feature in PlanFeature.objects.order_by("position", "id")
            ],
        }
        cache.set(key, data, CACHE_TTL)
        return Response(data)


class PublicEcoSystemsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        locale = _locale(request.query_params.get("locale"))
        cached = cache.get(ECO_CACHE_KEY)
        if cached is not None and cached.get("locale") == locale:
            return Response(cached)
        data = {
            "locale": locale,
            "systems": [
                serialize_public_eco(system, locale)
                for system in EcoSystem.objects.filter(status=EcoSystem.Status.PUBLISHED).order_by("position", "id")
            ],
        }
        cache.set(ECO_CACHE_KEY, data, CACHE_TTL)
        return Response(data)
