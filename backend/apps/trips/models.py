from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
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
    # Disposicao dos bancos, vista de tras para a frente: "<esquerda>+<direita>".
    # A planta que o passageiro ve tem de corresponder ao autocarro real — num
    # 1+2 (comum nos interprovinciais, com bancos individuais de um lado) uma
    # planta 2+2 mostraria lugares que nao existem, e o passageiro escolheria
    # um assento que nao vai encontrar.
    SEAT_LAYOUTS = ("1+1", "1+2", "2+1", "2+2", "2+3", "3+2")
    seat_layout = models.CharField(
        max_length=8,
        choices=[(value, value.replace("+", " + ")) for value in SEAT_LAYOUTS],
        default="2+2",
        help_text="Bancos de cada lado do corredor, ex.: 2+2, 1+2, 3+2.",
    )
    # Ultima fila corrida (sem corredor). Zero = a ultima fila segue o layout.
    last_row_seats = models.PositiveSmallIntegerField(default=0)
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


class Direction(models.TextChoices):
    """Para que lado vai o autocarro.

    Uma rota tem duas listas de paragens — `outbound` e `inbound` — e sao a
    mesma estrada em sentidos opostos. A VIAGEM nao guardava nenhum, e por isso
    quem procurava Maputo->Nelspruit recebia tambem as partidas de
    Nelspruit->Maputo: o sistema so sabia a que rota pertenciam.

    Vazio significa "nao declarado", e nao um sentido por omissao. As viagens
    criadas antes deste campo existir nao tem como saber para onde iam, e
    inventar-lhes um sentido poria passageiros no autocarro errado; enquanto
    nao for declarado, continuam a aparecer nos dois — como sempre apareceram.
    """

    OUTBOUND = "outbound", "Ida"
    INBOUND = "inbound", "Volta"


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
    # As viagens geradas por este horario herdam o sentido. Um horario descreve
    # uma carreira num sentido — a volta tem outro horario.
    direction = models.CharField(
        max_length=8, choices=Direction.choices, blank=True, default="",
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    # Minimo 1: com 0, `generate_daily_trips` entra em ciclo infinito
    # (`current_time += timedelta(minutes=0)` nunca avanca) e consome um worker
    # para sempre. O campo esta exposto na API do backoffice, logo um erro de
    # digitacao chegava para prender o backend.
    frequency_minutes = models.PositiveIntegerField(
        default=30, validators=[MinValueValidator(1)],
    )
    days_of_week = models.JSONField(default=list)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ("route", "start_time")

    def __str__(self):
        return f"{self.route.code} {self.start_time}-{self.end_time} cada {self.frequency_minutes}min"


class Trip(BaseModel):
    # Atalho: `Trip.Direction.OUTBOUND` le-se melhor onde se fala de viagens.
    Direction = Direction

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
    # Terminal que iniciou a viagem (dispositivos livres): e a fonte da posicao
    # GPS "do autocarro" no mapa dos passageiros.
    device = models.ForeignKey(
        "devices.Device", on_delete=models.SET_NULL, null=True, blank=True, related_name="trips",
    )
    # O sentido em que esta partida percorre a rota. Ver `Direction`.
    direction = models.CharField(
        max_length=8, choices=Direction.choices, blank=True, default="", db_index=True,
    )
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

    #: A circular: vende-se em qualquer rota, seja qual for a hora prevista.
    RUNNING_STATUSES = (Status.BOARDING, Status.DEPARTED)
    #: Tudo o que ainda se pode vender numa rota com lugar marcado.
    SELLABLE_STATUSES = (Status.SCHEDULED, *RUNNING_STATUSES)

    class Meta:
        ordering = ("-planned_departure_at",)
        indexes = [
            models.Index(fields=["route", "status"]),
            models.Index(fields=["planned_departure_at"]),
            # O motorista abre "as minhas viagens" a cada embarque, e a lista
            # do POS filtra por estado + hora de partida.
            models.Index(fields=["driver", "status"]),
            models.Index(fields=["status", "planned_departure_at"]),
        ]

    def __str__(self):
        return f"{self.route.code} | {self.planned_departure_at} [{self.status}]"

    @staticmethod
    def sellable_statuses_for(route) -> tuple:
        """Estados em que uma partida DESTA rota ainda se vende.

        Numa carreira com lugar marcado (interprovincial, internacional) o
        bilhete compra-se com dias de antecedencia: uma partida ainda `agendada`
        tem de estar a venda, senao a viagem criada no portal nao aparece no
        balcao nem no site e o agente ve a lista vazia sem nada que o explique.

        Numa carreira urbana e o contrario: vende-se o autocarro que esta ali a
        embarcar. Deixar vender uma partida agendada seria prometer lugar num
        autocarro que ninguem reservou.
        """
        if route is not None and route.requires_seat_selection:
            return Trip.SELLABLE_STATUSES
        return Trip.RUNNING_STATUSES


class TripActivityEvent(BaseModel):
    class EventType(models.TextChoices):
        START = "start", "Abertura do embarque"
        DEPART = "depart", "Partida"
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
    # Manifesto TAL COMO ESTAVA no fecho. Guardado e nao recalculado: um
    # bilhete cancelado dias depois nao pode mudar a lista de quem seguiu
    # naquele autocarro. Ver `apps/trips/manifest.py`.
    manifest = models.JSONField(default=dict, blank=True)
    passengers_aboard = models.PositiveIntegerField(default=0)
    passengers_no_show = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-closed_at",)
        indexes = [
            models.Index(fields=["route", "closed_at"]),
            models.Index(fields=["vehicle", "closed_at"]),
            models.Index(fields=["driver", "closed_at"]),
        ]

    def __str__(self):
        return f"Fecho {self.trip_id} | {self.total_revenue} MZN"
