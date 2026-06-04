from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import BaseModel


class Wallet(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Activa"
        BLOCKED = "blocked", "Bloqueada"
        CLOSED = "closed", "Encerrada"

    passenger_account = models.OneToOneField(
        "passengers.PassengerAccount",
        on_delete=models.PROTECT,
        related_name="wallet",
    )
    balance_cached = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
    )
    currency = models.CharField(max_length=3, default="MZN")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Wallet {self.uuid} | {self.passenger_account} | {self.balance_cached} {self.currency}"

    def recalculate_balance(self):
        from django.db.models import Sum
        result = self.transactions.filter(
            status=WalletTransaction.Status.CONFIRMED,
        ).aggregate(total=Sum("signed_amount"))
        self.balance_cached = result["total"] or Decimal("0.00")
        self.save(update_fields=["balance_cached", "updated_at"])
        return self.balance_cached


class WalletTransaction(BaseModel):
    class Type(models.TextChoices):
        TOPUP = "topup", "Recarga"
        FARE_DEBIT = "fare_debit", "Debito de Viagem"
        REFUND = "refund", "Reembolso"
        REVERSAL = "reversal", "Reversao"
        ADJUSTMENT = "adjustment", "Ajuste"
        CARD_TRANSFER = "card_transfer", "Transferencia de Cartao"
        FEE = "fee", "Taxa"

    class Direction(models.TextChoices):
        CREDIT = "credit", "Credito"
        DEBIT = "debit", "Debito"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        CONFIRMED = "confirmed", "Confirmada"
        FAILED = "failed", "Falhada"
        REVERSED = "reversed", "Revertida"

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="transactions")
    type = models.CharField(max_length=24, choices=Type.choices)
    direction = models.CharField(max_length=8, choices=Direction.choices)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))],
    )
    signed_amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=64, unique=True, db_index=True)
    source = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CONFIRMED)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["wallet", "status"]),
            models.Index(fields=["reference"]),
        ]

    def __str__(self):
        return f"{self.reference} | {self.type} {self.direction} {self.amount}"
