from django.db import models

from apps.core.models import BaseModel, active_unique_constraint


class Route(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Activa"
        INACTIVE = "inactive", "Inactiva"
        SUSPENDED = "suspended", "Suspensa"

    code = models.CharField(max_length=32, db_index=True, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ("code",)
        constraints = [
            active_unique_constraint("code", name="uq_route_code_active"),
        ]

    def save(self, *args, **kwargs):
        if not str(self.code or "").strip():
            from apps.core.utils import generate_code_from_name
            self.code = generate_code_from_name(self.name, "RT", Route, "code", instance=self)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Stop(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Activa"
        INACTIVE = "inactive", "Inactiva"

    code = models.CharField(max_length=32, db_index=True, blank=True)
    name = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ("code",)
        constraints = [
            active_unique_constraint("code", name="uq_stop_code_active"),
        ]

    def save(self, *args, **kwargs):
        if not str(self.code or "").strip():
            from apps.core.utils import generate_code_from_name
            self.code = generate_code_from_name(self.name, "ST", Stop, "code", instance=self)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"


class RouteStop(BaseModel):
    class Direction(models.TextChoices):
        OUTBOUND = "outbound", "Ida"
        INBOUND = "inbound", "Volta"

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="route_stops")
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name="route_stops")
    sequence = models.PositiveIntegerField()
    distance_from_start_km = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    direction = models.CharField(
        max_length=16, choices=Direction.choices, default=Direction.OUTBOUND,
    )

    class Meta:
        ordering = ("route", "direction", "sequence")
        constraints = [
            active_unique_constraint("route", "direction", "sequence", name="uq_route_stop_sequence_active"),
            active_unique_constraint("route", "direction", "stop", name="uq_route_stop_once_active"),
        ]

    def __str__(self):
        return f"{self.route.code} [{self.direction}] #{self.sequence} {self.stop.name}"
