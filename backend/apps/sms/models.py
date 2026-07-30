from django.db import models


class SmsMessage(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        SENT = "sent", "Enviada"
        DELIVERED = "delivered", "Entregue"
        FAILED = "failed", "Falhada"

    phone_number = models.CharField(max_length=20)
    template = models.CharField(max_length=64, blank=True)
    body = models.TextField()
    purpose = models.CharField(max_length=64, blank=True)
    provider_reference = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Quantas vezes esta mensagem foi tentada. Sem isto, uma falha do provedor
    # era definitiva: o bilhete ficava emitido e o passageiro nunca recebia o
    # link. Ver `manage.py retry_failed_sms`.
    attempts = models.PositiveSmallIntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["phone_number", "created_at"]),
            # A procura do retry: falhadas, recentes, por ordem de chegada.
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"SMS {self.pk} to {self.phone_number} [{self.status}]"
