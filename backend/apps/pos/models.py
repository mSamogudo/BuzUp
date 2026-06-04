from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class PosSession(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Activa"
        CLOSED = "closed", "Encerrada"

    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pos_sessions",
    )
    device = models.ForeignKey(
        "devices.Device", on_delete=models.CASCADE, related_name="pos_sessions",
    )
    allocated_route = models.ForeignKey(
        "routes.Route", on_delete=models.SET_NULL, null=True, blank=True, related_name="pos_sessions",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-opened_at",)
        indexes = [
            models.Index(fields=["agent", "status"]),
            models.Index(fields=["device", "status"]),
        ]

    def __str__(self):
        return f"Session {self.agent} @ {self.device.serial_number} [{self.status}]"
