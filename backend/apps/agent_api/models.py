from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class RecoverySession(BaseModel):
    """Tracks a card-recovery flow run by an agent on a POS.

    Flow:
      1. Agent calls `request-otp/` → session created (status=PENDING),
         OTP code is hashed and stored. SMS sent to passenger.
      2. Agent calls `verify-otp/` → on match, status=VERIFIED + a single-use
         `recovery_token` is minted.
      3. Agent calls `associate/` with the recovery_token → consumed once.
         status=CONSUMED. Card swap + payment happen in the view.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        VERIFIED = "verified", "Verificada"
        CONSUMED = "consumed", "Consumida"
        EXPIRED = "expired", "Expirada"

    challenge_id = models.CharField(max_length=64, unique=True, db_index=True)
    agent_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="recovery_sessions",
    )
    passenger = models.ForeignKey(
        "passengers.PassengerAccount", on_delete=models.PROTECT,
        related_name="recovery_sessions",
    )
    phone = models.CharField(max_length=20, db_index=True)
    reason = models.CharField(max_length=255, blank=True)
    code_hash = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    recovery_token = models.CharField(max_length=64, db_index=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "expires_at"]),
            models.Index(fields=["recovery_token"]),
        ]

    def __str__(self):
        return f"Recovery {self.challenge_id} [{self.status}]"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at


class AgentDayClose(BaseModel):
    """Persisted snapshot of an agent's day-close submission.

    Captures totals and full payload for admin auditing (revenue control).
    """

    agent_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="day_closes",
    )
    agent_profile = models.ForeignKey(
        "trips.Agent",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="day_closes",
    )
    closed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    date = models.DateField(db_index=True)

    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    sales_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    topups_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    validations_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    tickets_count = models.PositiveIntegerField(default=0)
    validations_count = models.PositiveIntegerField(default=0)
    confirmed_count = models.PositiveIntegerField(default=0)
    pending_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    sessions_closed = models.PositiveIntegerField(default=0)

    # Full payload (sales / topups / validations arrays) for the drilldown view.
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-closed_at",)
        indexes = [
            models.Index(fields=["agent_user", "date"]),
            models.Index(fields=["date", "agent_user"]),
        ]

    def __str__(self):
        return f"Fecho {self.date} | {self.agent_user_id} | {self.total_revenue} MZN"
