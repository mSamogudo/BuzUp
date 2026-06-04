import hashlib

from django.db import models
from django.http import FileResponse, Http404
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
