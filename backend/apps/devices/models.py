import secrets

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from apps.core.models import BaseModel, active_unique_constraint


class Device(BaseModel):
    class DeviceType(models.TextChoices):
        UROVO_I9100_POS = "urovo_i9100_pos", "UROVO I9100 POS"
        SUNMI_V2S_POS = "sunmi_v2s_pos", "SUNMI V2s POS"
        MOBILE_APP = "mobile_app", "App Mobile"
        ADMIN_BROWSER = "admin_browser", "Browser Admin"

    class Status(models.TextChoices):
        SELF_ONBOARDED = "self_onboarded", "Self-Onboarded"
        PENDING_ACTIVATION = "pending_activation", "Pendente Activacao"
        PENDING_CONFIGURATION = "pending_configuration", "Pendente Configuracao"
        ACTIVE = "active", "Activo"
        REJECTED = "rejected", "Rejeitado"
        BLOCKED = "blocked", "Bloqueado"
        RETIRED = "retired", "Retirado"

    CAPABILITY_CHOICES = [
        ("nfc_reader", "NFC Reader"),
        ("qr_scanner", "QR Scanner"),
        ("thermal_printer", "Thermal Printer"),
        ("camera", "Camera"),
        ("secure_storage", "Secure Storage"),
        ("kiosk_mode", "Kiosk Mode"),
        ("apk_silent_install", "APK Silent Install"),
        ("device_serial_access", "Device Serial Access"),
    ]

    serial_number = models.CharField(max_length=128, db_index=True)
    device_type = models.CharField(max_length=24, choices=DeviceType.choices)
    model_name = models.CharField(max_length=64, blank=True)
    manufacturer = models.CharField(max_length=64, blank=True)
    imei = models.CharField(max_length=32, blank=True)
    android_id = models.CharField(max_length=64, blank=True)
    capabilities = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.SELF_ONBOARDED)
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assigned_devices",
    )
    activation_code = models.CharField(max_length=12, db_index=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    app_version = models.CharField(max_length=32, blank=True)
    app_version_code = models.PositiveIntegerField(default=0)
    configuration = models.JSONField(default=dict, blank=True)
    last_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    last_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    last_speed = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    last_heading = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    last_location_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["device_type", "status"]),
        ]
        constraints = [
            active_unique_constraint("serial_number", name="uq_device_serial_active"),
            active_unique_constraint("activation_code", name="uq_device_activation_code_active"),
        ]

    def __str__(self):
        return f"{self.serial_number} ({self.device_type}) [{self.status}]"

    @staticmethod
    def generate_activation_code():
        return secrets.token_hex(4).upper()


class DeviceActivationRequest(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        APPROVED = "approved", "Aprovado"
        REJECTED = "rejected", "Rejeitado"
        EXPIRED = "expired", "Expirado"

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="activation_requests")
    activation_code = models.CharField(max_length=12, db_index=True)
    requested_serial_number = models.CharField(max_length=128)
    requested_model = models.CharField(max_length=64, blank=True)
    requested_manufacturer = models.CharField(max_length=64, blank=True)
    requested_imei = models.CharField(max_length=32, blank=True)
    requested_android_id = models.CharField(max_length=64, blank=True)
    requested_capabilities = models.JSONField(default=list, blank=True)
    app_version = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="reviewed_activations",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ("-requested_at",)

    def __str__(self):
        return f"Activation {self.activation_code} [{self.status}]"
