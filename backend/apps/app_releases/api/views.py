import hashlib

from django.db import models
from django.http import FileResponse, Http404, HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.app_releases.api.serializers import (
    AppReleaseCreateSerializer,
    AppReleaseSerializer,
    CheckUpdateSerializer,
    DeviceAppUpdateSerializer,
)
from apps.app_releases.models import AppRelease, DeviceAppUpdate
from apps.core.permissions import HasCapabilities
from apps.core.viewsets import BaseModelViewSet


def _sha256_of(file_field) -> str:
    h = hashlib.sha256()
    file_field.open("rb")
    try:
        for chunk in file_field.chunks():
            h.update(chunk)
    finally:
        file_field.close()
    return h.hexdigest()


class AppReleaseViewSet(BaseModelViewSet):
    queryset = AppRelease.all_objects.all()
    serializer_class = AppReleaseSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    required_capabilities_by_action = {
        "list": ("devices.read",),
        "retrieve": ("devices.read",),
        "create": ("devices.manage",),
        "update": ("devices.manage",),
        "partial_update": ("devices.manage",),
        "destroy": ("devices.manage",),
    }

    def get_serializer_class(self):
        if self.action == "create":
            return AppReleaseCreateSerializer
        return AppReleaseSerializer

    def perform_create(self, serializer):
        release = serializer.save(created_by=self.request.user)
        # Auto-fill checksum from the uploaded APK so apps can verify integrity.
        if release.apk_file and not release.checksum:
            release.checksum = _sha256_of(release.apk_file)
            release.save(update_fields=["checksum", "updated_at"])


class AppReleaseDownloadView(APIView):
    """Streams the uploaded APK with the correct android content-type.

    Public so terminals/phones can pull the binary directly from the update
    prompt without an auth header.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, pk):
        # Public download only serves PUBLISHED releases — never DRAFT/SUSPENDED
        # (those are only reachable through the authenticated admin viewset).
        release = AppRelease.objects.filter(
            pk=pk, status=AppRelease.Status.PUBLISHED,
        ).first()
        if not release or not release.apk_file:
            raise Http404("APK nao encontrado.")
        filename = f"buzup-{release.app_type}-{release.version_name}.apk"
        response = FileResponse(
            release.apk_file.open("rb"),
            content_type="application/vnd.android.package-archive",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Cache-Control"] = "no-store"
        return response


APP_SLUGS = {
    "pos": AppRelease.AppType.POS,
    "passageiro": AppRelease.AppType.PASSENGER,
    "passenger": AppRelease.AppType.PASSENGER,
    "mobile": AppRelease.AppType.PASSENGER,
}


def _latest_published(app_type):
    return (
        AppRelease.objects.filter(app_type=app_type, status=AppRelease.Status.PUBLISHED)
        .order_by("-version_code")
        .first()
    )


class AppLatestDownloadView(APIView):
    """Link de download AMIGAVEL e estavel: serve sempre a ultima versao
    publicada da app (sem id), ex. /api/apps/pos/download/."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, slug):
        app_type = APP_SLUGS.get(slug.lower())
        if not app_type:
            raise Http404("App desconhecida.")
        release = _latest_published(app_type)
        if not release or not release.apk_file:
            raise Http404("Sem versao publicada.")
        filename = f"buzup-{release.app_type}-{release.version_name}.apk"
        response = FileResponse(
            release.apk_file.open("rb"),
            content_type="application/vnd.android.package-archive",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Cache-Control"] = "no-store"
        return response


class AppDownloadPageView(APIView):
    """Pagina de download partilhavel (um so link) com as duas apps."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            from apps.branding.models import BrandingSettings

            brand = BrandingSettings.load()
            name = brand.platform_name or "BusUp"
            logo = brand.file_url("primary_logo", request) or brand.file_url("sidebar_logo", request)
        except Exception:
            name, logo = "BusUp", ""

        pos = _latest_published(AppRelease.AppType.POS)
        psg = _latest_published(AppRelease.AppType.PASSENGER)

        def card(titulo, desc, slug, rel):
            if not rel:
                return (
                    f'<div class="card"><h2>{titulo}</h2><p>{desc}</p>'
                    '<span class="soon">Em breve</span></div>'
                )
            return (
                f'<div class="card"><h2>{titulo}</h2><p>{desc}</p>'
                f'<a class="btn" href="/api/apps/{slug}/download/">Baixar APK '
                f'<small>v{rel.version_name}</small></a></div>'
            )

        logo_html = f'<img src="{logo}" alt="{name}" class="logo">' if logo else f"<h1>{name}</h1>"
        html = f"""<!doctype html><html lang="pt"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} - Descarregar apps</title>
<style>
:root{{color-scheme:light dark}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
background:#0D3B66;color:#fff;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}}
.wrap{{width:100%;max-width:560px;text-align:center}}
.logo{{max-height:64px;margin-bottom:8px}}
h1{{margin:0 0 4px;font-size:28px}}
.sub{{opacity:.8;margin-bottom:28px;font-size:14px}}
.card{{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.15);
border-radius:16px;padding:22px;margin:14px 0;text-align:left}}
.card h2{{margin:0 0 4px;font-size:18px}}
.card p{{margin:0 0 16px;opacity:.8;font-size:13px}}
.btn{{display:inline-flex;align-items:center;gap:8px;background:#2d8cf0;color:#fff;
text-decoration:none;font-weight:700;padding:12px 18px;border-radius:10px}}
.btn small{{opacity:.85;font-weight:500}}
.soon{{opacity:.6;font-size:13px}}
.foot{{margin-top:24px;opacity:.6;font-size:12px}}
</style></head><body><div class="wrap">
{logo_html}
<div class="sub">Descarregar as aplicacoes Android</div>
{card("App Passageiro", "Para passageiros: carregar saldo, comprar bilhetes, validar viagens.", "passageiro", psg)}
{card("App POS", "Para motoristas/agentes nos terminais SUNMI/Urovo.", "pos", pos)}
<div class="foot">Abrir no telemovel Android e instalar o APK.</div>
</div></body></html>"""
        return HttpResponse(html, content_type="text/html; charset=utf-8")


class AppReleasePublishView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("devices.manage",)

    def patch(self, request, pk):
        try:
            release = AppRelease.objects.get(pk=pk)
        except AppRelease.DoesNotExist:
            return Response({"detail": "Release nao encontrada."}, status=status.HTTP_404_NOT_FOUND)

        if release.status not in (AppRelease.Status.DRAFT, AppRelease.Status.SUSPENDED):
            return Response({"detail": f"Release em estado {release.status}."}, status=status.HTTP_400_BAD_REQUEST)

        release.status = AppRelease.Status.PUBLISHED
        release.published_at = timezone.now()
        release.save(update_fields=["status", "published_at", "updated_at"])
        return Response(AppReleaseSerializer(release).data)


class AppReleaseSuspendView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("devices.manage",)

    def patch(self, request, pk):
        try:
            release = AppRelease.objects.get(pk=pk)
        except AppRelease.DoesNotExist:
            return Response({"detail": "Release nao encontrada."}, status=status.HTTP_404_NOT_FOUND)

        release.status = AppRelease.Status.SUSPENDED
        release.save(update_fields=["status", "updated_at"])
        return Response(AppReleaseSerializer(release).data)


class CheckUpdateView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = CheckUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        qs = AppRelease.objects.filter(
            app_type=data["app_type"],
            status=AppRelease.Status.PUBLISHED,
            version_code__gt=data["current_version_code"],
        )
        if data.get("device_type"):
            qs = qs.filter(models.Q(target_device_type="") | models.Q(target_device_type=data["device_type"]))
        if data.get("manufacturer"):
            qs = qs.filter(models.Q(target_manufacturer="") | models.Q(target_manufacturer=data["manufacturer"]))

        release = qs.order_by("-version_code").first()

        if not release:
            return Response({"update_available": False})

        return Response({
            "update_available": True,
            "release_id": release.id,
            "version_name": release.version_name,
            "version_code": release.version_code,
            "is_mandatory": release.is_mandatory,
            "release_notes": release.release_notes,
            "download_url": release.get_download_url(),
            "checksum": release.checksum,
            "file_size_bytes": release.file_size_bytes,
        })


class DeferUpdateView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, pk):
        try:
            release = AppRelease.objects.get(pk=pk)
        except AppRelease.DoesNotExist:
            return Response({"detail": "Release nao encontrada."}, status=status.HTTP_404_NOT_FOUND)

        if release.is_mandatory:
            return Response({"detail": "Actualizacao obrigatoria nao pode ser adiada."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"deferred": True})


class DeviceAppUpdateViewSet(BaseModelViewSet):
    queryset = DeviceAppUpdate.all_objects.select_related("device", "app_release").all()
    serializer_class = DeviceAppUpdateSerializer
    http_method_names = ["get", "head", "options"]
    required_capabilities_by_action = {
        "list": ("devices.read",),
        "retrieve": ("devices.read",),
    }
