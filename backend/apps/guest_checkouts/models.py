import hashlib
import secrets
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class GuestCheckout(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        PAYMENT_PENDING = "payment_pending", "Pagamento Pendente"
        PAID = "paid", "Pago"
        ISSUED = "issued", "Emitido"
        EXPIRED = "expired", "Expirado"
        CANCELLED = "cancelled", "Cancelado"
        REFUNDED = "refunded", "Reembolsado"

    reference = models.CharField(max_length=64, unique=True, db_index=True)
    payer_phone = models.CharField(max_length=20)
    buyer_name = models.CharField(max_length=255, blank=True)
    buyer_email = models.EmailField(blank=True)
    # Contacto de emergencia da compra. Cada passageiro pode trazer o seu em
    # `passengers[]`; este e o que vale quando nao trazem — o caso comum de
    # uma familia que viaja junta e da o mesmo numero.
    emergency_contact_name = models.CharField(max_length=120, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    # Passageiros da compra (interurbano): [{name, document_type, document_number}].
    # Fica no checkout porque e recolhido ANTES do pagamento; e a fonte dos
    # passes emitidos quando o pagamento confirma.
    passengers = models.JSONField(default=list, blank=True)
    route_code = models.CharField(max_length=32, blank=True)
    route_name = models.CharField(max_length=255, blank=True)
    origin_stop = models.CharField(max_length=255, blank=True)
    destination_stop = models.CharField(max_length=255, blank=True)
    origin_stop_ref = models.ForeignKey(
        "routes.Stop", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="guest_checkouts_origin",
    )
    destination_stop_ref = models.ForeignKey(
        "routes.Stop", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="guest_checkouts_destination",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))],
    )
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))],
    )
    # Moeda de EXIBICAO escolhida no acto da compra (rotas p/ Africa do Sul).
    # A cobranca e sempre em MZN; isto congela o valor mostrado e a taxa usada.
    display_currency = models.CharField(max_length=3, default="MZN")
    display_total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    expires_at = models.DateTimeField(null=True, blank=True)
    linked_passenger = models.ForeignKey(
        "passengers.PassengerAccount", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="guest_checkouts",
    )
    trip = models.ForeignKey(
        "trips.Trip", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="guest_checkouts",
    )
    # Ida e volta. A volta e a MESMA compra — um pagamento, um comprovativo —
    # mas duas viagens: dois lugares reservados, dois bilhetes, dois manifestos.
    # Por isso e uma partida propria e nao um campo de data: o autocarro da
    # volta tem a sua lotacao, o seu motorista e a sua lista de quem vai a bordo.
    return_trip = models.ForeignKey(
        "trips.Trip", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="guest_checkouts_return",
    )
    # A tarifa da volta e cotada para o percurso invertido, nao copiada da ida:
    # nada obriga uma rota a custar o mesmo nos dois sentidos.
    return_unit_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )

    # Aceitacao dos termos e condicoes, no acto da compra.
    #
    # Guarda-se a VERSAO e nao apenas um sim: sem ela sabia-se que o passageiro
    # aceitou "os termos", mas nao QUAIS — e uns termos alterados depois da
    # compra passariam a valer para tras. Numa disputa sobre um cancelamento ou
    # uma bagagem, e esta linha que diz o que estava escrito nesse dia.
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    # Turno em que a venda foi feita, quando veio do balcao. Nulo para tudo
    # o que e comprado no site: nao ha caixa de agente nenhuma por tras.
    shift = models.ForeignKey(
        "shifts.Shift", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="checkouts", db_index=True,
    )
    terms_version = models.CharField(max_length=32, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["payer_phone", "status"]),
            models.Index(fields=["reference"]),
            # Contar lugares ocupados numa partida (capacity.py) esta no
            # caminho de CADA venda: tem de ser um index scan.
            models.Index(fields=["trip", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.reference} | {self.payer_phone} | {self.status}"

    @property
    def is_round_trip(self) -> bool:
        return self.return_trip_id is not None


class DigitalTravelPass(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        USED = "used", "Usado"
        EXPIRED = "expired", "Expirado"
        CANCELLED = "cancelled", "Cancelado"
        REFUNDED = "refunded", "Reembolsado"

    class DeliveryChannel(models.TextChoices):
        SMS = "sms", "SMS"
        APP = "app", "App"
        LINK = "link", "Link"

    class Leg(models.TextChoices):
        OUTBOUND = "outbound", "Ida"
        RETURN = "return", "Volta"

    class DocumentType(models.TextChoices):
        BI = "bi", "Bilhete de Identidade"
        PASSPORT = "passport", "Passaporte"
        DIRE = "dire", "DIRE"
        CEDULA = "cedula", "Cedula"
        OTHER = "other", "Outro"

    guest_checkout = models.ForeignKey(
        GuestCheckout, on_delete=models.PROTECT,
        null=True, blank=True, related_name="travel_passes",
    )
    passenger_account = models.ForeignKey(
        "passengers.PassengerAccount", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="travel_passes",
    )
    wallet = models.ForeignKey(
        "wallets.Wallet", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="travel_passes",
    )
    trip = models.ForeignKey(
        "trips.Trip", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="travel_passes",
    )
    payer_phone = models.CharField(max_length=20, blank=True)
    route_code = models.CharField(max_length=32, blank=True)
    route_name = models.CharField(max_length=255, blank=True)
    origin_stop = models.CharField(max_length=255, blank=True)
    destination_stop = models.CharField(max_length=255, blank=True)
    origin_stop_ref = models.ForeignKey(
        "routes.Stop", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="travel_passes_origin",
    )
    destination_stop_ref = models.ForeignKey(
        "routes.Stop", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="travel_passes_destination",
    )
    # Identificacao do passageiro: obrigatoria em rotas internacionais
    # (o bilhete e nominal e conferido na fronteira).
    passenger_name = models.CharField(max_length=255, blank=True)
    document_type = models.CharField(max_length=16, choices=DocumentType.choices, blank=True)
    document_number = models.CharField(max_length=64, blank=True)
    seat_number = models.CharField(max_length=8, blank=True)
    # Quem avisar se algo correr mal. Recolhido nas rotas interprovinciais e
    # internacionais (ver `Route.requires_emergency_contact`): sao horas de
    # estrada longe de casa, e num acidente a primeira pergunta e "a quem se
    # telefona". Vive no bilhete e nao so na conta porque quem viaja pode nao
    # ser quem comprou.
    emergency_contact_name = models.CharField(max_length=120, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    # Copia da partida: o passe tem de sobreviver a alteracoes/remocao da viagem.
    departure_at = models.DateTimeField(null=True, blank=True)
    fare_amount = models.DecimalField(max_digits=12, decimal_places=2)
    # Moeda de exibicao escolhida na compra (ver GuestCheckout): o bilhete
    # imprime o preco nesta moeda, congelado a taxa da altura.
    display_currency = models.CharField(max_length=3, default="MZN")
    display_fare_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    token = models.CharField(max_length=128, unique=True, db_index=True)
    token_hash = models.CharField(max_length=128, db_index=True)
    # Codigo curto impresso no bilhete (leitura manual quando o QR falha).
    # Guardado no proprio passe: era derivado em dois sitios com regras
    # diferentes — o POS procurava pelo fim da referencia do checkout e os
    # bilhetes de compras com 2+ lugares (ref BASE-01, BASE-02...) nunca
    # casavam com o codigo impresso.
    short_code = models.CharField(max_length=8, blank=True, db_index=True)
    delivery_channel = models.CharField(
        max_length=8, choices=DeliveryChannel.choices, default=DeliveryChannel.SMS,
    )
    # Ida ou volta. Sem isto, os dois bilhetes de uma ida e volta eram
    # indistinguiveis um do outro — no ecra do passageiro, no manifesto de bordo
    # e para o agente que valida a entrada.
    leg = models.CharField(max_length=8, choices=Leg.choices, default=Leg.OUTBOUND)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["token_hash"]),
            models.Index(fields=["status", "valid_until"]),
            models.Index(fields=["short_code", "status"]),
        ]

    def __str__(self):
        return f"Pass {self.uuid} | {self.status}"

    @staticmethod
    def generate_token():
        raw = secrets.token_urlsafe(32)
        return raw, hashlib.sha256(raw.encode()).hexdigest()
