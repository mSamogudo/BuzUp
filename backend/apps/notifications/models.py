from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Notification(BaseModel):
    class Kind(models.TextChoices):
        PAYMENT_CONFIRMED = "payment_confirmed", "Pagamento Confirmado"
        PAYMENT_FAILED = "payment_failed", "Pagamento Falhado"
        TICKET_ISSUED = "ticket_issued", "Bilhete Emitido"
        TRIP_UPDATE = "trip_update", "Actualizacao de Viagem"
        CARD_UPDATE = "card_update", "Actualizacao de Cartao"
        SYSTEM = "system", "Sistema"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "read_at"]),
            models.Index(fields=["user", "kind"]),
        ]

    def __str__(self):
        return f"{self.user_id} | {self.kind} | {self.title}"
