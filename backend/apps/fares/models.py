from decimal import ROUND_CEILING, Decimal

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


class ExchangeRate(BaseModel):
    """Taxa de cambio de EXIBICAO configurada no portal (ex.: ZAR -> MZN).

    O rand e apenas visualizacao para o passageiro (rotas para a Africa do
    Sul): a cobranca e sempre em MZN. A taxa activa converte precos para
    mostrar, e cada bilhete guarda a taxa usada no acto da compra para o
    valor exibido nunca mudar depois de emitido.
    """

    currency = models.CharField(max_length=3, db_index=True)  # ex.: ZAR
    # Quantos MZN vale 1 unidade da moeda. Ex.: 1 ZAR = 4.10 MZN -> rate=4.10
    rate_to_mzn = models.DecimalField(
        max_digits=12, decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
    )
    # A que multiplo se arredonda o valor exibido. 1 = rands inteiros; 5 = de
    # cinco em cinco; 0.01 = ao centavo (sem arredondar, na pratica).
    #
    # Uma divisao por uma taxa quase nunca da um numero redondo: 1000 MZN a
    # 3,87 sao 258,398... e o passageiro ficava a olhar para centavos que
    # ninguem no balcao consegue dar em troco. Arredonda-se sempre PARA CIMA,
    # pela mesma razao que a taxa e posta abaixo do mercado — o valor mostrado
    # nunca pode ser menor do que aquilo que lhe sai da conta.
    rounding_step = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("currency", "-updated_at")
        constraints = [
            active_unique_constraint("currency", name="uq_exchange_rate_currency_active"),
        ]

    def __str__(self):
        return f"1 {self.currency} = {self.rate_to_mzn} MZN"

    def arredondar(self, valor: Decimal) -> Decimal:
        """Sobe `valor` ao proximo multiplo de `rounding_step`."""
        passo = self.rounding_step or Decimal("0.01")
        if passo <= 0:
            passo = Decimal("0.01")
        multiplos = (Decimal(valor) / passo).to_integral_value(rounding=ROUND_CEILING)
        return (multiplos * passo).quantize(Decimal("0.01"))

    @classmethod
    def current(cls, currency: str) -> "ExchangeRate | None":
        code = (currency or "").strip().upper()
        if not code or code == "MZN":
            return None
        return cls.objects.filter(currency=code, is_active=True).first()

    @classmethod
    def convert_from_mzn(cls, amount_mzn: Decimal, currency: str) -> tuple[Decimal, Decimal] | None:
        """(valor_convertido, taxa) para exibicao, ou None se nao configurada."""
        row = cls.current(currency)
        if not row:
            return None
        converted = row.arredondar(Decimal(amount_mzn) / row.rate_to_mzn)
        return converted, row.rate_to_mzn
