from django.conf import settings
from django.db import models

from apps.core.models import BaseModel, active_unique_constraint


class AppRelease(BaseModel):
    class AppType(models.TextChoices):
        POS = "pos", "POS"
        PASSENGER = "passenger", "Passageiro"

    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        PUBLISHED = "published", "Publicado"
        SUSPENDED = "suspended", "Suspenso"
        RETIRED = "retired", "Retirado"

    app_type = models.CharField(max_length=16, choices=AppType.choices)
    version_name = models.CharField(max_length=32)
    version_code = models.PositiveIntegerField()
    apk_file = models.FileField(upload_to="app-releases/", blank=True)
    apk_url = models.URLField(blank=True)
    checksum = models.CharField(max_length=128, blank=True)
    release_notes = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=False)
    min_supported_version_code = models.PositiveIntegerField(default=0)
    target_device_type = models.CharField(max_length=24, blank=True)
    target_manufacturer = models.CharField(max_length=64, blank=True)
    target_model = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="app_releases",
    )

    class Meta:
        ordering = ("-version_code",)
        constraints = [
            active_unique_constraint("app_type", "version_code", name="uq_app_release_version_active"),
        ]

    def __str__(self):
        return f"{self.app_type} v{self.version_name} ({self.version_code}) [{self.status}]"

    def get_download_url(self) -> str:
        """Absolute URL apps use to fetch the APK.

        Prefers the uploaded ``apk_file`` (served by AppReleaseDownloadView with
        the correct android package content-type); falls back to an externally
        hosted ``apk_url`` when no file was uploaded.
        """
        if self.apk_file:
            from django.conf import settings
            base = str(getattr(settings, "PUBLIC_BASE_URL", "") or "").rstrip("/")
            return f"{base}/api/app-releases/{self.id}/download/"
        return self.apk_url or ""

    @property
    def file_size_bytes(self) -> int:
        try:
            return self.apk_file.size if self.apk_file else 0
        except (ValueError, OSError):
            return 0


class DeviceAppUpdate(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PROMPTED = "prompted", "Notificado"
        DEFERRED = "deferred", "Adiado"
        DOWNLOADING = "downloading", "A Descarregar"
        INSTALLED = "installed", "Instalado"
        FAILED = "failed", "Falhado"
        FORCED = "forced", "Forcado"

    device = models.ForeignKey(
        "devices.Device", on_delete=models.CASCADE, related_name="app_updates",
    )
    app_release = models.ForeignKey(
        AppRelease, on_delete=models.CASCADE, related_name="device_updates",
    )
    current_version_code = models.PositiveIntegerField(default=0)
    target_version_code = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    prompted_at = models.DateTimeField(null=True, blank=True)
    deferred_until = models.DateTimeField(null=True, blank=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)
    installed_at = models.DateTimeField(null=True, blank=True)
    failed_reason = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        unique_together = [("device", "app_release")]

    def __str__(self):
        return f"Update {self.device.serial_number} -> v{self.target_version_code} [{self.status}]"
