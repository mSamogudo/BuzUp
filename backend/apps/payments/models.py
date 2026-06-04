from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import BaseModel


class PaymentIntent(BaseModel):
    class Purpose(models.TextChoices):
        MOBILE_WALLET_TOPUP = "mobile_wallet_topup", "Recarga App"
        POS_CARD_TOPUP = "pos_card_topup", "Recarga POS"
        GUEST_TRAVEL_PASS = "guest_travel_pass_purchase", "Bilhete Convidado"
        APP_TRAVEL_PASS = "app_travel_pass_purchase", "Bilhete App"
        DIRECT_TRIP_PAYMENT = "direct_trip_payment", "Pagamento Directo"
        REFUND = "refund", "Reembolso"

    class Status(models.TextChoices):
        CREATED = "created", "Criado"
        PENDING = "pending", "Pendente"
        CONFIRMED = "confirmed", "Confirmado"
        FAILED = "failed", "Falhado"
        EXPIRED = "expired", "Expirado"
        REVERSED = "reversed", "Revertido"

    reference = models.CharField(max_length=64, unique=True, db_index=True)
    idempotency_key = models.CharField(max_length=128, unique=True, db_index=True)
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.CharField(max_length=3, default="MZN")
    payer_phone = models.CharField(max_length=20)
    provider = models.CharField(max_length=32, blank=True)
    channel = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CREATED)
    wallet = models.ForeignKey(
        "wallets.Wallet", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="payment_intents",
    )
    guest_checkout = models.ForeignKey(
        "guest_checkouts.GuestCheckout", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="payment_intents",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="payment_intents",
    )
    provider_reference = models.CharField(max_length=128, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["payer_phone"]),
        ]

    def __str__(self):
        return f"{self.reference} | {self.purpose} | {self.amount} {self.currency} | {self.status}"


class PaymentCallback(BaseModel):
    payment_intent = models.ForeignKey(
        PaymentIntent, on_delete=models.PROTECT, related_name="callbacks",
    )
    provider_reference = models.CharField(max_length=128, blank=True)
    raw_payload = models.JSONField(default=dict)
    signature_valid = models.BooleanField(default=False)
    processing_status = models.CharField(max_length=16, default="received")
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-received_at",)

    def __str__(self):
        return f"Callback {self.pk} for {self.payment_intent.reference}"
