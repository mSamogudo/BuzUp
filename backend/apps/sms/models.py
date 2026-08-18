from django.conf import settings
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


class SmsBroadcast(models.Model):
    """Aviso enviado a quem vai a bordo de uma partida (ou de uma rota).

    Existe como registo e nao apenas como um botao: um envio destes custa
    dinheiro, chega a telemoveis de pessoas reais e nao se desfaz. Fica
    escrito quem enviou, o que enviou, para quantos, e quantos falharam.
    """

    class Scope(models.TextChoices):
        TRIP = "trip", "Partida"
        ROUTE = "route", "Rota"

    scope = models.CharField(max_length=8, choices=Scope.choices)
    trip = models.ForeignKey(
        "trips.Trip", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sms_broadcasts",
    )
    route = models.ForeignKey(
        "routes.Route", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sms_broadcasts",
    )
    body = models.TextField()
    recipients = models.PositiveIntegerField(default=0)
    sent = models.PositiveIntegerField(default=0)
    failed = models.PositiveIntegerField(default=0)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sms_broadcasts",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["scope", "created_at"]),
        ]

    def __str__(self):
        alvo = self.trip_id or self.route_id or "?"
        return f"Broadcast {self.scope}:{alvo} -> {self.sent}/{self.recipients}"
