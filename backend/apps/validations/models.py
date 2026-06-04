from decimal import Decimal

from django.db import models

from apps.core.models import BaseModel


class ValidationEvent(BaseModel):
    class ValidationType(models.TextChoices):
        CARD_PAY_AS_YOU_GO = "card_pay_as_you_go", "Cartao Pay-as-you-go"
        QR_PAY_AS_YOU_GO = "qr_pay_as_you_go", "QR Pay-as-you-go"
        DIGITAL_TRAVEL_PASS = "digital_travel_pass", "Passe Digital"
        GUEST_DIGITAL_TRAVEL_PASS = "guest_digital_travel_pass", "Passe Digital Convidado"

    class Status(models.TextChoices):
        APPROVED = "approved", "Aprovado"
        DENIED = "denied", "Negado"

    class FailureReason(models.TextChoices):
        NONE = "", ""
        INSUFFICIENT_BALANCE = "insufficient_balance", "Saldo Insuficiente"
        CARD_BLOCKED = "card_blocked", "Cartao Bloqueado"
        ACCOUNT_BLOCKED = "account_blocked", "Conta Bloqueada"
        PASS_ALREADY_USED = "pass_already_used", "Passe Ja Usado"
        PASS_EXPIRED = "pass_expired", "Passe Expirado"
        INVALID_TOKEN = "invalid_token", "Token Invalido"
        ROUTE_NOT_ALLOWED = "route_not_allowed", "Rota Nao Permitida"
        DEVICE_BLOCKED = "device_blocked", "Dispositivo Bloqueado"
        NO_FARE_FOUND = "no_fare_found", "Tarifa Nao Encontrada"

    validation_type = models.CharField(max_length=32, choices=ValidationType.choices)
    passenger_account = models.ForeignKey(
        "passengers.PassengerAccount", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="validation_events",
    )
    wallet = models.ForeignKey(
        "wallets.Wallet", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="validation_events",
    )
    physical_card = models.ForeignKey(
        "cards.Card", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="validation_events",
    )
    digital_travel_pass = models.ForeignKey(
        "guest_checkouts.DigitalTravelPass", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="validation_events",
    )
    route = models.ForeignKey(
        "routes.Route", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="validation_events",
    )
    trip = models.ForeignKey(
        "trips.Trip", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="validation_events",
    )
    origin_stop = models.ForeignKey(
        "routes.Stop", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="validation_events_origin",
    )
    destination_stop = models.ForeignKey(
        "routes.Stop", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="validation_events_dest",
    )
    device = models.ForeignKey(
        "devices.Device", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="validation_events",
    )
    amount_debited = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=16, choices=Status.choices)
    failure_reason = models.CharField(max_length=32, choices=FailureReason.choices, blank=True, default="")
    idempotency_key = models.CharField(max_length=128, unique=True, db_index=True)
    wallet_transaction_ref = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["validation_type", "status"]),
            models.Index(fields=["route", "created_at"]),
            models.Index(fields=["device", "created_at"]),
        ]

    def __str__(self):
        return f"{self.validation_type} [{self.status}] {self.created_at}"
