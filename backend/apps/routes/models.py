from django.db import models

from apps.core.models import BaseModel, active_unique_constraint


class Route(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Activa"
        INACTIVE = "inactive", "Inactiva"
        SUSPENDED = "suspended", "Suspensa"

    class ServiceType(models.TextChoices):
        URBAN = "urban", "Urbano / Interurbano"
        INTERPROVINCIAL = "interprovincial", "Interprovincial"
        INTERNATIONAL = "international", "Internacional"

    # Rotas onde o lugar e marcado. Numa carreira urbana ninguem escolhe
    # assento — entra, valida e senta-se onde houver; obrigar a escolher seria
    # um passo inutil numa compra que tem de ser rapida. Numa viagem
    # interprovincial ou internacional, de varias horas, o lugar e do
    # passageiro e tem de ser escolhido.
    SEATED_SERVICE_TYPES = ("interprovincial", "international")

    code = models.CharField(max_length=32, db_index=True, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    service_type = models.CharField(
        max_length=20, choices=ServiceType.choices, default=ServiceType.URBAN,
        help_text="Determina se o passageiro escolhe o lugar na compra.",
    )
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

    @property
    def requires_seat_selection(self) -> bool:
        """O passageiro escolhe o lugar nesta rota?

        Derivado do tipo de servico em vez de ser um campo proprio: eram dois
        valores a poder discordar, e o operador ja diz o que a rota e quando a
        cria. O site, a app e o POS leem isto — nenhum deles pergunta ao
        passageiro que tipo de viagem esta a comprar.
        """
        return self.service_type in self.SEATED_SERVICE_TYPES

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
