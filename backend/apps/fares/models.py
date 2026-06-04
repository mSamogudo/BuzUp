from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import BaseModel, active_unique_constraint


class AdminFee(BaseModel):
    """Administrative fees managed in the portal: card issuance fees, card
    recovery fees, fines, etc. Looked up by `kind` and (optionally) by
    `code` so commercial can tweak amounts without code release.
    """

    class Kind(models.TextChoices):
        CARD_ISSUANCE = "card_issuance", "Taxa de adesao de cartao"
        CARD_RECOVERY = "card_recovery", "Taxa de recuperacao de cartao"
        FINE = "fine", "Multa"
        OTHER = "other", "Outra"

    code = models.SlugField(max_length=32, db_index=True)
    name = models.CharField(max_length=128)
    kind = models.CharField(max_length=24, choices=Kind.choices)
    amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    currency = models.CharField(max_length=3, default="MZN")
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("kind", "name")
        indexes = [
            models.Index(fields=["kind", "is_active"]),
        ]
        constraints = [
            active_unique_constraint("code", name="uq_admin_fee_code_active"),
        ]

    def __str__(self):
        return f"{self.name} ({self.amount} {self.currency})"

    @classmethod
    def resolve(cls, kind: str, default: Decimal | None = None) -> Decimal:
        """Convenience: return the active amount for a given kind.

        Used by onboarding / recovery so the value comes from the DB instead
        of the historical settings constant.
        """
        row = cls.objects.filter(kind=kind, is_active=True).order_by("-updated_at").first()
        if row:
            return row.amount
        return default or Decimal("0.00")


class FareProduct(BaseModel):
    class ProductType(models.TextChoices):
        SINGLE_TRIP = "single_trip", "Viagem Avulsa"
        DAILY_PASS = "daily_pass", "Passe Diario"
        WEEKLY_PASS = "weekly_pass", "Passe Semanal"
        MONTHLY_PASS = "monthly_pass", "Passe Mensal"

    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        INACTIVE = "inactive", "Inactivo"

    name = models.CharField(max_length=255)
    product_type = models.CharField(max_length=24, choices=ProductType.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} ({self.product_type})"


class FareRule(BaseModel):
    class CalculationMethod(models.TextChoices):
        FIXED = "fixed", "Preco Fixo"
        ORIGIN_DESTINATION = "origin_destination", "Origem/Destino"
        DISTANCE = "distance", "Distancia"
        ZONE = "zone", "Zona"

    class PassengerClass(models.TextChoices):
        STANDARD = "standard", "Normal"
        STUDENT = "student", "Estudante"
        SENIOR = "senior", "Idoso"
        CHILD = "child", "Crianca"

    fare_product = models.ForeignKey(
        FareProduct, on_delete=models.CASCADE, related_name="rules",
    )
    route = models.ForeignKey(
        "routes.Route", on_delete=models.CASCADE,
        null=True, blank=True, related_name="fare_rules",
    )
    origin_stop = models.ForeignKey(
        "routes.Stop", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="fare_rules_origin",
    )
    destination_stop = models.ForeignKey(
        "routes.Stop", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="fare_rules_destination",
    )
    zone = models.CharField(max_length=32, blank=True)
    passenger_class = models.CharField(
        max_length=16, choices=PassengerClass.choices, default=PassengerClass.STANDARD,
    )
    calculation_method = models.CharField(
        max_length=24, choices=CalculationMethod.choices, default=CalculationMethod.FIXED,
    )
    fixed_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    amount_per_km = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00"),
    )
    min_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
    )
    max_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
    )
    distance_min_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    distance_max_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    priority = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-priority", "-created_at")
        indexes = [
            models.Index(fields=["route", "calculation_method", "passenger_class"], name="fare_rule_lookup_idx"),
        ]

    def __str__(self):
        label = f"{self.fare_product.name}"
        if self.route:
            label += f" | {self.route.code}"
        if self.origin_stop and self.destination_stop:
            label += f" | {self.origin_stop.code}->{self.destination_stop.code}"
        return f"{label} = {self.fixed_amount}"
