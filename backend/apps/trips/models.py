from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel, active_unique_constraint


class Vehicle(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        MAINTENANCE = "maintenance", "Em Manutencao"
        RETIRED = "retired", "Retirado"

    registration = models.CharField(max_length=20, db_index=True)
    make = models.CharField(max_length=64, blank=True)
    model_name = models.CharField(max_length=64, blank=True)
    seated_capacity = models.PositiveIntegerField(default=0)
    standing_capacity = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    # Livrete (documento de registo do veiculo) — PDF ou imagem.
    livrete = models.FileField(upload_to="vehicles/livrete/", blank=True)

    class Meta:
        ordering = ("registration",)
        constraints = [
            active_unique_constraint("registration", name="uq_vehicle_reg_active"),
        ]

    def __str__(self):
        return self.registration


class Driver(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        INACTIVE = "inactive", "Inactivo"
        SUSPENDED = "suspended", "Suspenso"

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    license_number = models.CharField(max_length=32, blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="driver_profile",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ("full_name",)

    def __str__(self):
        return self.full_name


class Agent(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        INACTIVE = "inactive", "Inactivo"
        SUSPENDED = "suspended", "Suspenso"

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="agent_profile",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ("full_name",)

    def __str__(self):
        return self.full_name


class RouteSchedule(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        INACTIVE = "inactive", "Inactivo"

    DAYS_CHOICES = [
        (0, "Segunda"), (1, "Terca"), (2, "Quarta"),
        (3, "Quinta"), (4, "Sexta"), (5, "Sabado"), (6, "Domingo"),
    ]

    route = models.ForeignKey("routes.Route", on_delete=models.CASCADE, related_name="schedules")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name="schedules")
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name="schedules")
    agent = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True, blank=True, related_name="schedules")
    start_time = models.TimeField()
    end_time = models.TimeField()
    frequency_minutes = models.PositiveIntegerField(default=30)
    days_of_week = models.JSONField(default=list)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ("route", "start_time")

    def __str__(self):
        return f"{self.route.code} {self.start_time}-{self.end_time} cada {self.frequency_minutes}min"


class Trip(BaseModel):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Agendada"
        BOARDING = "boarding", "Embarque"
        DEPARTED = "departed", "Em Viagem"
        PAUSED = "paused", "Em Repouso"
        COMPLETED = "completed", "Concluida"
        CANCELLED = "cancelled", "Cancelada"

    route = models.ForeignKey("routes.Route", on_delete=models.PROTECT, related_name="trips")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name="trips")
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name="trips")
    agent = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True, blank=True, related_name="trips")
    schedule = models.ForeignKey(RouteSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name="trips")
    planned_departure_at = models.DateTimeField(null=True, blank=True)
    actual_departure_at = models.DateTimeField(null=True, blank=True)
    planned_arrival_at = models.DateTimeField(null=True, blank=True)
    actual_arrival_at = models.DateTimeField(null=True, blank=True)
    activity_started_at = models.DateTimeField(null=True, blank=True)
    activity_paused_at = models.DateTimeField(null=True, blank=True)
    activity_closed_at = models.DateTimeField(null=True, blank=True)
    pause_seconds = models.PositiveIntegerField(default=0)
    closure_summary = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SCHEDULED)

    class Meta:
        ordering = ("-planned_departure_at",)
        indexes = [
            models.Index(fields=["route", "status"]),
            models.Index(fields=["planned_departure_at"]),
        ]

    def __str__(self):
        return f"{self.route.code} | {self.planned_departure_at} [{self.status}]"


class TripActivityEvent(BaseModel):
    class EventType(models.TextChoices):
        START = "start", "Inicio"
        PAUSE = "pause", "Repouso"
        RESUME = "resume", "Retoma"
        CLOSE = "close", "Fecho"

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="activity_events")
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_events")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="trip_activity_events",
    )
    event_type = models.CharField(max_length=16, choices=EventType.choices)
    occurred_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-occurred_at",)
        indexes = [
            models.Index(fields=["trip", "event_type"]),
            models.Index(fields=["driver", "occurred_at"]),
        ]

    def __str__(self):
        return f"{self.trip_id} {self.event_type} {self.occurred_at}"


class TripRevenueClosure(BaseModel):
    trip = models.OneToOneField(Trip, on_delete=models.PROTECT, related_name="revenue_closure")
    route = models.ForeignKey("routes.Route", on_delete=models.PROTECT, related_name="trip_revenue_closures")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name="trip_revenue_closures")
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name="trip_revenue_closures")
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="trip_revenue_closures",
    )
    opened_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(default=timezone.now)
    pause_seconds = models.PositiveIntegerField(default=0)
    guest_checkout_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    app_pass_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    wallet_validation_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    direct_payment_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    summary = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-closed_at",)
        indexes = [
            models.Index(fields=["route", "closed_at"]),
            models.Index(fields=["vehicle", "closed_at"]),
            models.Index(fields=["driver", "closed_at"]),
        ]

    def __str__(self):
        return f"Fecho {self.trip_id} | {self.total_revenue} MZN"
