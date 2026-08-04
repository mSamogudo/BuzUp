"""Validacao por cartao: o bilhete manda, e nas viagens longas e obrigatorio.

Tres situacoes, com consequencias diferentes se falharem:

* **O passageiro ja tem bilhete** — cobrar outra vez ao toque era faze-lo pagar
  a mesma viagem duas vezes, e so daria por isso ao ver o extracto.
* **Rota longa sem bilhete** — descontar da carteira ali punha um passageiro a
  bordo sem lugar marcado e sem contacto de emergencia, portanto fora do
  manifesto. Num acidente nao havia a quem telefonar.
* **Carreira urbana sem bilhete** — aqui descontar E o produto. Passar a
  recusar parava a cobranca ao toque nos cartoes todos.
"""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.cards.models import Card
from apps.fares.models import FareProduct, FareRule
from apps.guest_checkouts.models import DigitalTravelPass
from apps.passengers.models import PassengerAccount
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Trip, Vehicle
from apps.validations.models import ValidationEvent
from apps.validations.services import validate_card
from apps.wallets.models import Wallet


class ValidacaoPorCartaoBase(TestCase):
    def setUp(self):
        self.urbana = Route.objects.create(
            code="R-URB-V", name="Circular",
            service_type=Route.ServiceType.URBAN, status=Route.Status.ACTIVE,
        )
        self.longa = Route.objects.create(
            code="R-INT-V", name="Maputo - Xai-Xai",
            service_type=Route.ServiceType.INTERPROVINCIAL, status=Route.Status.ACTIVE,
        )
        self.origem = Stop.objects.create(code="ST-VA", name="Paragem A", status="active")
        self.destino = Stop.objects.create(code="ST-VB", name="Paragem B", status="active")
        for rota in (self.urbana, self.longa):
            RouteStop.objects.create(route=rota, stop=self.origem, sequence=1, direction="outbound")
            RouteStop.objects.create(route=rota, stop=self.destino, sequence=2, direction="outbound")
            produto = FareProduct.objects.create(
                name=f"Avulso {rota.code}",
                product_type=FareProduct.ProductType.SINGLE_TRIP,
                status=FareProduct.Status.ACTIVE,
            )
            FareRule.objects.create(
                fare_product=produto, route=rota,
                calculation_method=FareRule.CalculationMethod.FIXED,
                fixed_amount=Decimal("50.00"),
            )

        self.passageiro = PassengerAccount.objects.create(
            full_name="Ana Cossa", phone_number="849555111",
            status=PassengerAccount.Status.ACTIVE,
        )
        self.carteira = Wallet.objects.create(
            passenger_account=self.passageiro,
            balance_cached=Decimal("1000.00"), status="active",
        )
        self.cartao = Card.objects.create(
            card_uid="CARD-VAL-1", passenger_account=self.passageiro,
            wallet=self.carteira, status=Card.Status.ACTIVE,
        )

    def _bilhete(self, rota, *, trip=None, status=DigitalTravelPass.Status.ACTIVE):
        return DigitalTravelPass.objects.create(
            passenger_account=self.passageiro, wallet=self.carteira,
            route_code=rota.code, route_name=rota.name,
            origin_stop=self.origem.name, destination_stop=self.destino.name,
            fare_amount=Decimal("50.00"), status=status, trip=trip,
            token=f"tok-{rota.code}-{timezone.now().timestamp()}",
            token_hash=f"h-{rota.code}-{timezone.now().timestamp()}",
            valid_from=timezone.now(),
            valid_until=timezone.now() + timezone.timedelta(hours=24),
        )

    def _validar(self, rota, chave, trip=None):
        return validate_card(
            card_uid=self.cartao.card_uid, route_id=rota.id,
            origin_stop_id=self.origem.id, destination_stop_id=self.destino.id,
            trip_id=trip.id if trip else None,
            idempotency_key=chave,
        )

    def _saldo(self):
        self.carteira.refresh_from_db()
        return self.carteira.balance_cached


class BilheteExistenteTests(ValidacaoPorCartaoBase):
    def test_bilhete_da_rota_e_usado_sem_debitar(self):
        tp = self._bilhete(self.urbana)
        antes = self._saldo()

        ev = self._validar(self.urbana, "k-1")

        self.assertEqual(ev.status, ValidationEvent.Status.APPROVED)
        self.assertEqual(ev.validation_type, ValidationEvent.ValidationType.DIGITAL_TRAVEL_PASS)
        self.assertEqual(ev.digital_travel_pass_id, tp.id)
        self.assertEqual(self._saldo(), antes, "cobrou o bilhete outra vez ao toque")

        tp.refresh_from_db()
        self.assertEqual(tp.status, DigitalTravelPass.Status.USED)
        self.assertIsNotNone(tp.used_at)

    def test_bilhete_de_outra_rota_nao_serve(self):
        # Bilhete da rota longa, toque numa carreira urbana: nao e este.
        self._bilhete(self.longa)
        antes = self._saldo()

        ev = self._validar(self.urbana, "k-2")

        self.assertEqual(ev.status, ValidationEvent.Status.APPROVED)
        self.assertEqual(ev.validation_type, ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO)
        self.assertEqual(self._saldo(), antes - Decimal("50.00"))

    def test_bilhete_ja_usado_nao_e_reaproveitado(self):
        self._bilhete(self.urbana, status=DigitalTravelPass.Status.USED)
        antes = self._saldo()

        ev = self._validar(self.urbana, "k-3")

        # Sem bilhete activo: numa urbana desconta, como sempre.
        self.assertEqual(ev.validation_type, ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO)
        self.assertEqual(self._saldo(), antes - Decimal("50.00"))

    def test_bilhete_de_outra_partida_nao_serve(self):
        viatura = Vehicle.objects.create(registration="BBB-22-MC", seated_capacity=20, status="active")
        manha = Trip.objects.create(route=self.urbana, vehicle=viatura,
                                    planned_departure_at=timezone.now(),
                                    status=Trip.Status.BOARDING)
        tarde = Trip.objects.create(route=self.urbana, vehicle=viatura,
                                    planned_departure_at=timezone.now() + timezone.timedelta(hours=8),
                                    status=Trip.Status.BOARDING)
        self._bilhete(self.urbana, trip=manha)
        antes = self._saldo()

        ev = self._validar(self.urbana, "k-4", trip=tarde)

        self.assertEqual(ev.validation_type, ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO,
                         "usou um bilhete comprado para outra partida")
        self.assertEqual(self._saldo(), antes - Decimal("50.00"))


class RotaLongaExigeBilheteTests(ValidacaoPorCartaoBase):
    def test_sem_bilhete_recusa_e_manda_comprar(self):
        antes = self._saldo()

        ev = self._validar(self.longa, "k-5")

        self.assertEqual(ev.status, ValidationEvent.Status.DENIED)
        self.assertEqual(ev.failure_reason, ValidationEvent.FailureReason.NO_TICKET_FOR_ROUTE)
        self.assertEqual(self._saldo(), antes,
                         "debitou numa viagem longa sem bilhete, sem lugar nem manifesto")

    def test_com_bilhete_deixa_embarcar(self):
        tp = self._bilhete(self.longa)
        antes = self._saldo()

        ev = self._validar(self.longa, "k-6")

        self.assertEqual(ev.status, ValidationEvent.Status.APPROVED)
        self.assertEqual(ev.digital_travel_pass_id, tp.id)
        self.assertEqual(self._saldo(), antes)

    def test_saldo_cheio_nao_compra_a_viagem_longa(self):
        # O ponto: nao e falta de dinheiro. E falta de bilhete.
        self.carteira.balance_cached = Decimal("50000.00")
        self.carteira.save(update_fields=["balance_cached"])

        ev = self._validar(self.longa, "k-7")

        self.assertEqual(ev.failure_reason, ValidationEvent.FailureReason.NO_TICKET_FOR_ROUTE)


class CarreiraUrbanaMantemDebitoTests(ValidacaoPorCartaoBase):
    def test_sem_bilhete_desconta_como_sempre(self):
        antes = self._saldo()

        ev = self._validar(self.urbana, "k-8")

        self.assertEqual(ev.status, ValidationEvent.Status.APPROVED)
        self.assertEqual(ev.validation_type, ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO)
        self.assertEqual(ev.amount_debited, Decimal("50.00"))
        self.assertEqual(self._saldo(), antes - Decimal("50.00"))

    def test_repetir_a_mesma_chave_nao_cobra_duas_vezes(self):
        antes = self._saldo()
        self._validar(self.urbana, "k-9")
        self._validar(self.urbana, "k-9")
        self.assertEqual(self._saldo(), antes - Decimal("50.00"))
