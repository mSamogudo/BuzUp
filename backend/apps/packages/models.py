from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import BaseModel, active_unique_constraint


class Package(BaseModel):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentagem"
        FIXED_AMOUNT = "fixed_amount", "Valor Fixo"
        FREE_TRIPS = "free_trips", "Viagens Gratis"

    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        INACTIVE = "inactive", "Inactivo"

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=16, choices=DiscountType.choices)
    discount_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    price = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    validity_days = models.PositiveIntegerField(default=30)
    max_trips = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} ({self.discount_type} {self.discount_value})"


class PackageRoute(BaseModel):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="routes")
    route = models.ForeignKey("routes.Route", on_delete=models.CASCADE, related_name="package_routes")

    class Meta:
        constraints = [
            active_unique_constraint("package", "route", name="uq_package_route_active"),
        ]

    def __str__(self):
        return f"{self.package.name} -> {self.route.code}"


class PassengerPackage(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        EXPIRED = "expired", "Expirado"
        CANCELLED = "cancelled", "Cancelado"
        EXHAUSTED = "exhausted", "Esgotado"

    passenger_account = models.ForeignKey(
        "passengers.PassengerAccount", on_delete=models.CASCADE,
        related_name="packages",
    )
    package = models.ForeignKey(Package, on_delete=models.PROTECT, related_name="subscriptions")
    wallet = models.ForeignKey(
        "wallets.Wallet", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="package_subscriptions",
    )
    special_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
    )
    trips_used = models.PositiveIntegerField(default=0)
    trips_remaining = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    activated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ("-activated_at",)
        indexes = [
            models.Index(fields=["passenger_account", "status"]),
            models.Index(fields=["status", "expires_at"]),
        ]

    def __str__(self):
        return f"{self.passenger_account} | {self.package.name} [{self.status}]"
