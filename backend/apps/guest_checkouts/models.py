import hashlib
import secrets
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class GuestCheckout(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        PAYMENT_PENDING = "payment_pending", "Pagamento Pendente"
        PAID = "paid", "Pago"
        ISSUED = "issued", "Emitido"
        EXPIRED = "expired", "Expirado"
        CANCELLED = "cancelled", "Cancelado"
        REFUNDED = "refunded", "Reembolsado"

    reference = models.CharField(max_length=64, unique=True, db_index=True)
    payer_phone = models.CharField(max_length=20)
    buyer_name = models.CharField(max_length=255, blank=True)
    route_code = models.CharField(max_length=32, blank=True)
    route_name = models.CharField(max_length=255, blank=True)
    origin_stop = models.CharField(max_length=255, blank=True)
    destination_stop = models.CharField(max_length=255, blank=True)
    origin_stop_ref = models.ForeignKey(
        "routes.Stop", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="guest_checkouts_origin",
    )
    destination_stop_ref = models.ForeignKey(
        "routes.Stop", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="guest_checkouts_destination",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))],
    )
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))],
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    expires_at = models.DateTimeField(null=True, blank=True)
    linked_passenger = models.ForeignKey(
        "passengers.PassengerAccount", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="guest_checkouts",
    )
    trip = models.ForeignKey(
        "trips.Trip", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="guest_checkouts",
    )

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["payer_phone", "status"]),
            models.Index(fields=["reference"]),
        ]

    def __str__(self):
        return f"{self.reference} | {self.payer_phone} | {self.status}"


class DigitalTravelPass(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        USED = "used", "Usado"
        EXPIRED = "expired", "Expirado"
        CANCELLED = "cancelled", "Cancelado"
        REFUNDED = "refunded", "Reembolsado"

    class DeliveryChannel(models.TextChoices):
        SMS = "sms", "SMS"
        APP = "app", "App"
        LINK = "link", "Link"

    guest_checkout = models.ForeignKey(
        GuestCheckout, on_delete=models.PROTECT,
        null=True, blank=True, related_name="travel_passes",
    )
    passenger_account = models.ForeignKey(
        "passengers.PassengerAccount", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="travel_passes",
    )
    wallet = models.ForeignKey(
        "wallets.Wallet", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="travel_passes",
    )
    trip = models.ForeignKey(
        "trips.Trip", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="travel_passes",
    )
    payer_phone = models.CharField(max_length=20, blank=True)
    route_code = models.CharField(max_length=32, blank=True)
    route_name = models.CharField(max_length=255, blank=True)
    origin_stop = models.CharField(max_length=255, blank=True)
    destination_stop = models.CharField(max_length=255, blank=True)
    origin_stop_ref = models.ForeignKey(
        "routes.Stop", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="travel_passes_origin",
    )
    destination_stop_ref = models.ForeignKey(
        "routes.Stop", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="travel_passes_destination",
    )
    fare_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    token = models.CharField(max_length=128, unique=True, db_index=True)
    token_hash = models.CharField(max_length=128, db_index=True)
    delivery_channel = models.CharField(
        max_length=8, choices=DeliveryChannel.choices, default=DeliveryChannel.SMS,
    )
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["token_hash"]),
            models.Index(fields=["status", "valid_until"]),
        ]

    def __str__(self):
        return f"Pass {self.uuid} | {self.status}"

    @staticmethod
    def generate_token():
        raw = secrets.token_urlsafe(32)
        return raw, hashlib.sha256(raw.encode()).hexdigest()
