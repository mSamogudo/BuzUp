"""Concorrência a valer: dois pedidos ao mesmo tempo, contra o Postgres real.

Estes testes usam `TransactionTestCase` (e não `TestCase`) de propósito: o
`TestCase` embrulha cada teste numa transacção, o que torna invisíveis os
próprios efeitos que queremos observar — `select_for_update` entre threads e
`on_commit`. Cada cenário aqui é um incidente que já aconteceu ou que a
auditoria mostrou ser possível.
"""

from __future__ import annotations

import threading
from decimal import Decimal

from django.db import connections
from django.test import TransactionTestCase
from django.utils import timezone

from apps.cards.models import Card
from apps.fares.models import FareProduct, FareRule
from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.passengers.models import PassengerAccount
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Driver, Trip, Vehicle
from apps.wallets.models import Wallet


def run_together(fn, n=2):
    """Corre `fn(i)` em n threads e devolve os resultados por ordem de índice.

    Cada thread fecha a sua ligação ao terminar: sem isso o Postgres fica com
    ligações penduradas e o teardown do teste bloqueia à espera delas.
    """
    results: list = [None] * n
    barrier = threading.Barrier(n)

    def worker(i):
        try:
            barrier.wait(timeout=10)
            results[i] = fn(i)
        except Exception as exc:  # guardar a excepção para o teste a inspeccionar
            results[i] = exc
        finally:
            connections.close_all()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return results


class ConcurrencyBase(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.route = Route.objects.create(code="R-CC", name="Teste Concorrencia",
                                          status=Route.Status.ACTIVE)
        self.origin = Stop.objects.create(code="ST-A", name="Paragem A", status="active")
        self.destination = Stop.objects.create(code="ST-B", name="Paragem B", status="active")
        RouteStop.objects.create(route=self.route, stop=self.origin, sequence=1, direction="outbound")
        RouteStop.objects.create(route=self.route, stop=self.destination, sequence=2, direction="outbound")

        product = FareProduct.objects.create(name="Avulso CC", product_type="single_trip",
                                             status="active")
        FareRule.objects.create(fare_product=product, route=self.route,
                                calculation_method=FareRule.CalculationMethod.FIXED,
                                fixed_amount=Decimal("100.00"))

        self.driver = Driver.objects.create(full_name="Motorista CC")
        # Um lugar só: qualquer segunda venda é sobrevenda.
        self.vehicle = Vehicle.objects.create(registration="CC-01-MP", seated_capacity=1)
        self.trip = Trip.objects.create(
            route=self.route, vehicle=self.vehicle, driver=self.driver,
            status=Trip.Status.BOARDING,
            planned_departure_at=timezone.now() + timezone.timedelta(hours=2),
        )


class SeatOversellTests(ConcurrencyBase):
    """Um lugar, dois compradores no mesmo instante — só um pode levar."""

    def test_pos_and_web_cannot_sell_the_same_last_seat(self):
        from apps.agent_api.sales import SaleError, create_pos_sale
        from apps.trips.models import Agent

        agent = Agent.objects.create(full_name="Agente CC", status=Agent.Status.ACTIVE)

        def sell(i):
            try:
                gc, _pi = create_pos_sale(
                    agent=agent, device=None, trip_id=self.trip.id, route_id=None,
                    origin_stop_id=self.origin.id, destination_stop_id=self.destination.id,
                    passenger_phone=f"8410000{i:02d}", quantity=1,
                )
                return gc.reference
            except SaleError as e:
                return f"recusado: {e}"

        results = run_together(sell, n=2)
        vendidos = [r for r in results if isinstance(r, str) and not r.startswith("recusado")]
        recusados = [r for r in results if isinstance(r, str) and r.startswith("recusado")]

        self.assertEqual(len(vendidos), 1, f"devia vender exactamente 1 lugar, obtive {results}")
        self.assertEqual(len(recusados), 1, f"o segundo pedido tinha de ser recusado: {results}")
        self.assertEqual(
            GuestCheckout.objects.filter(trip=self.trip).count(), 1,
            "ficou mais do que um checkout a ocupar o unico lugar",
        )


class TicketDoubleValidationTests(ConcurrencyBase):
    """O mesmo bilhete lido por dois validadores ao mesmo tempo."""

    def _issue_pass(self):
        gc = GuestCheckout.objects.create(
            reference="GC-CCTEST01", payer_phone="841000000",
            route_code=self.route.code, route_name=self.route.name,
            origin_stop=self.origin.name, destination_stop=self.destination.name,
            quantity=1, unit_amount=Decimal("100.00"), total_amount=Decimal("100.00"),
            status=GuestCheckout.Status.ISSUED, trip=self.trip,
        )
        raw, token_hash = DigitalTravelPass.generate_token()
        tp = DigitalTravelPass.objects.create(
            guest_checkout=gc, payer_phone="841000000",
            route_code=self.route.code, route_name=self.route.name,
            origin_stop=self.origin.name, destination_stop=self.destination.name,
            trip=self.trip, fare_amount=Decimal("100.00"),
            token=raw, token_hash=token_hash,
            status=DigitalTravelPass.Status.ACTIVE,
            valid_until=timezone.now() + timezone.timedelta(hours=6),
        )
        return tp, raw

    def test_only_one_validator_consumes_the_ticket(self):
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient

        from apps.trips.models import Agent

        tp, raw = self._issue_pass()
        User = get_user_model()
        user = User.objects.create_user(username="agente_cc", password="x", phone="841999999")
        Agent.objects.create(user=user, full_name="Agente CC", status=Agent.Status.ACTIVE)

        def verify(i):
            client = APIClient()
            client.force_authenticate(user=user)
            res = client.post("/api/agent/tickets/verify/", {"token": raw, "consume": True},
                              format="json")
            return res.status_code, res.data.get("consumed"), res.data.get("valid")

        results = run_together(verify, n=2)
        consumidos = [r for r in results if isinstance(r, tuple) and r[1] is True]

        self.assertEqual(
            len(consumidos), 1,
            f"o bilhete devia ser consumido uma unica vez, obtive {results}",
        )
        tp.refresh_from_db()
        self.assertEqual(tp.status, DigitalTravelPass.Status.USED)


class CardChargeRepeatTests(ConcurrencyBase):
    """O incidente relatado: depois de uma cobranca, as seguintes falhavam."""

    def setUp(self):
        super().setUp()
        self.passenger = PassengerAccount.objects.create(
            full_name="Passageiro CC", phone_number="258841234567",
            status=PassengerAccount.Status.ACTIVE,
        )
        self.wallet = Wallet.objects.create(
            passenger_account=self.passenger, balance_cached=Decimal("1000.00"),
            status=Wallet.Status.ACTIVE,
        )
        self.card = Card.objects.create(
            card_uid="04A1B2C3", passenger_account=self.passenger, wallet=self.wallet,
            status=Card.Status.ACTIVE,
        )

    def test_same_card_can_be_charged_again_on_the_same_trip(self):
        """Duas validacoes distintas do mesmo cartao na mesma viagem.

        A referencia do debito era `VAL-{chave[:16]}`; como a chave gerada pelo
        servidor e `card-<uid>-<trip>-<timestamp>`, o corte deixava cair o
        timestamp e a segunda validacao colidia na unique da WalletTransaction.
        Resultado em producao: o cartao ficava sem poder ser cobrado.
        """
        from apps.validations.services import validate_card

        first = validate_card(
            card_uid=self.card.card_uid, route_id=self.route.id,
            origin_stop_id=self.origin.id, destination_stop_id=self.destination.id,
            trip_id=self.trip.id,
            idempotency_key=f"card-{self.card.card_uid}-{self.trip.id}-1700000000",
        )
        second = validate_card(
            card_uid=self.card.card_uid, route_id=self.route.id,
            origin_stop_id=self.origin.id, destination_stop_id=self.destination.id,
            trip_id=self.trip.id,
            idempotency_key=f"card-{self.card.card_uid}-{self.trip.id}-1700009999",
        )

        from apps.validations.models import ValidationEvent
        self.assertEqual(first.status, ValidationEvent.Status.APPROVED)
        self.assertEqual(second.status, ValidationEvent.Status.APPROVED,
                         "a segunda viagem do mesmo cartao tinha de ser cobrada")
        self.assertNotEqual(first.wallet_transaction_ref, second.wallet_transaction_ref)

    def test_repeated_request_with_same_key_charges_once(self):
        """Retry do POS por timeout: um debito, nao dois."""
        from apps.validations.services import validate_card

        key = f"card-{self.card.card_uid}-{self.trip.id}-1700000001"

        def validate(_i):
            return validate_card(
                card_uid=self.card.card_uid, route_id=self.route.id,
                origin_stop_id=self.origin.id, destination_stop_id=self.destination.id,
                trip_id=self.trip.id, idempotency_key=key,
            )

        results = run_together(validate, n=2)
        erros = [r for r in results if isinstance(r, Exception)]
        self.assertEqual(erros, [], f"nenhum pedido devia rebentar: {erros}")

        self.wallet.refresh_from_db()
        self.assertEqual(
            self.wallet.balance_cached, Decimal("900.00"),
            "a mesma chave de idempotencia debitou duas vezes",
        )


class PosSaleAccountLinkTests(CardChargeRepeatTests):
    """Bilhete vendido no POS tem de aparecer na conta do passageiro.

    O incidente: compra por QR do cartao no POS emitia o bilhete sem
    `passenger_account`, e a app (que filtra por essa FK) nunca o mostrava.
    """

    def _agent(self):
        from apps.trips.models import Agent
        return Agent.objects.create(full_name="Agente Link", status=Agent.Status.ACTIVE)

    def test_card_sale_links_ticket_to_the_cardholder(self):
        from apps.agent_api.sales import create_card_sale

        gc, _pi, passes = create_card_sale(
            agent=self._agent(), device=None, trip_id=self.trip.id, route_id=None,
            origin_stop_id=self.origin.id, destination_stop_id=self.destination.id,
            card_uid=self.card.card_uid, quantity=1,
        )
        self.assertEqual(gc.linked_passenger_id, self.passenger.id)
        self.assertEqual(len(passes), 1)
        self.assertEqual(passes[0].passenger_account_id, self.passenger.id,
                         "o bilhete do titular do cartao nao entrou na conta dele")
        # A mesma query da app/portal tem de o encontrar.
        self.assertTrue(
            DigitalTravelPass.objects.filter(passenger_account=self.passenger,
                                             pk=passes[0].pk).exists())

    def test_phone_sale_links_when_phone_has_an_account(self):
        from apps.agent_api.sales import create_pos_sale

        gc, _pi = create_pos_sale(
            agent=self._agent(), device=None, trip_id=self.trip.id, route_id=None,
            origin_stop_id=self.origin.id, destination_stop_id=self.destination.id,
            passenger_phone="841234567",  # a conta guarda 258841234567
            quantity=1,
        )
        self.assertEqual(gc.linked_passenger_id, self.passenger.id)

    def test_phone_sale_without_account_stays_unlinked(self):
        from apps.agent_api.sales import create_pos_sale

        gc, _pi = create_pos_sale(
            agent=self._agent(), device=None, trip_id=self.trip.id, route_id=None,
            origin_stop_id=self.origin.id, destination_stop_id=self.destination.id,
            passenger_phone="847777777", quantity=1,
        )
        self.assertIsNone(gc.linked_passenger_id)


class DayCloseCountsValidationsTests(TicketDoubleValidationTests):
    """Fecho do dia de um agente SEM device registado.

    O incidente: as validacoes so entravam no fecho atraves do device
    atribuido; um agente a validar do proprio telemovel (sem Device) fechava
    o dia sempre a zeros.
    """

    def test_validation_without_device_still_counts_in_day_close(self):
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient

        from apps.trips.models import Agent

        tp, raw = self._issue_pass()
        User = get_user_model()
        user = User.objects.create_user(username="agente_semdev", password="x",
                                        phone="841888888")
        Agent.objects.create(user=user, full_name="Agente Sem Device",
                             status=Agent.Status.ACTIVE)

        client = APIClient()
        client.force_authenticate(user=user)
        res = client.post("/api/agent/tickets/verify/", {"token": raw, "consume": True},
                          format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(res.data.get("consumed"), res.data)

        fecho = client.get("/api/agent/day-close/")
        self.assertEqual(fecho.status_code, 200)
        self.assertEqual(
            fecho.data["totals"]["validations"], 1,
            "a validacao feita sem device registado sumiu do fecho",
        )
        self.assertEqual(len(fecho.data["validations"]), 1)


class QrPassBurnTests(TicketDoubleValidationTests):
    """Bilhete queimado sem registo do embarque — negava a quem pagou."""

    def test_same_key_twice_never_leaves_ticket_used_without_event(self):
        """Duas leituras com a MESMA chave: uma valida, a outra repete-a.

        Antes, o bilhete era marcado USED numa transacao e o ValidationEvent
        criado fora dela: na corrida, o segundo pedido rebentava com 500 e
        deixava o bilhete queimado sem evento. O POS repetia, via USED e
        negava definitivamente — bilhete pago, passageiro em terra.
        """
        from apps.validations.models import ValidationEvent
        from apps.validations.services import validate_qr_pass

        tp, raw = self._issue_pass()
        key = "qr-mesma-chave-1"

        results = run_together(
            lambda _i: validate_qr_pass(token=raw, trip_id=self.trip.id, idempotency_key=key),
            n=2,
        )
        erros = [r for r in results if isinstance(r, Exception)]
        self.assertEqual(erros, [], f"nenhum pedido devia rebentar: {erros}")

        eventos = ValidationEvent.objects.filter(idempotency_key=key)
        self.assertEqual(eventos.count(), 1, "a mesma chave devia produzir um unico registo")

        tp.refresh_from_db()
        aprovado = eventos.first().status == ValidationEvent.Status.APPROVED
        # A regra que importa: bilhete USED se e so se ha embarque aprovado.
        self.assertEqual(
            tp.status == DigitalTravelPass.Status.USED, aprovado,
            "bilhete queimado sem embarque aprovado (ou o contrario)",
        )

    def test_repeated_denial_does_not_blow_up(self):
        """Retry de uma recusa nao pode devolver 500 ao validador."""
        from apps.validations.models import ValidationEvent
        from apps.validations.services import validate_qr_pass

        key = "qr-token-invalido-1"
        first = validate_qr_pass(token="nao-existe-este-token", idempotency_key=key)
        second = validate_qr_pass(token="nao-existe-este-token", idempotency_key=key)

        self.assertEqual(first.status, ValidationEvent.Status.DENIED)
        self.assertEqual(second.id, first.id, "a repeticao devia devolver a mesma recusa")


class PosSeatSaleTests(ConcurrencyBase):
    """Venda no POS com lugar marcado (interprovincial/internacional)."""

    def setUp(self):
        super().setUp()
        from apps.trips.models import Agent

        self.route.service_type = Route.ServiceType.INTERNATIONAL
        self.route.save(update_fields=["service_type"])
        # Espaço para vários lugares nesta suite (a base tem 1 só).
        self.vehicle.seated_capacity = 20
        self.vehicle.seat_layout = "1+2"
        self.vehicle.save(update_fields=["seated_capacity", "seat_layout"])
        self.agent = Agent.objects.create(full_name="Agente Lugares", status=Agent.Status.ACTIVE)

    def _sell(self, seats, phone="841000001", quantity=None):
        from apps.agent_api.sales import create_pos_sale

        return create_pos_sale(
            agent=self.agent, device=None, trip_id=self.trip.id, route_id=None,
            origin_stop_id=self.origin.id, destination_stop_id=self.destination.id,
            passenger_phone=phone, quantity=quantity or max(len(seats), 1),
            seats=seats,
        )

    def test_seat_is_recorded_on_the_ticket(self):
        gc, _pi = self._sell(["3B"])
        self.assertEqual(gc.passengers, [{"seat": "3B"}])

    def test_two_agents_cannot_sell_the_same_seat(self):
        from apps.agent_api.sales import SaleError

        self._sell(["5A"], phone="841000001")

        with self.assertRaises(SaleError) as ctx:
            self._sell(["5A"], phone="841000002")
        self.assertIn("5A", str(ctx.exception))

    def test_simultaneous_sales_of_the_same_seat(self):
        """A corrida a valer: dois agentes, o mesmo lugar, ao mesmo tempo."""
        from apps.agent_api.sales import SaleError

        def sell(i):
            try:
                gc, _ = self._sell(["7C"], phone=f"84100{i:04d}")
                return f"vendido:{gc.reference}"
            except SaleError as e:
                return f"recusado:{e}"

        results = run_together(sell, n=2)
        vendidos = [r for r in results if isinstance(r, str) and r.startswith("vendido")]
        self.assertEqual(
            len(vendidos), 1,
            f"o mesmo lugar foi vendido duas vezes: {results}",
        )


class AppSeatPurchaseTests(ConcurrencyBase):
    """Compra na app do passageiro com lugar marcado.

    Antes desta guarda a app vendia um bilhete interprovincial sem partida e
    sem lugar: ninguem descontava a lotacao e o autocarro podia sair com mais
    gente do que bancos.
    """

    def setUp(self):
        super().setUp()
        self.route.service_type = Route.ServiceType.INTERPROVINCIAL
        self.route.save(update_fields=["service_type"])
        self.vehicle.seated_capacity = 20
        self.vehicle.save(update_fields=["seated_capacity"])

    def _passenger(self, phone):
        acc = PassengerAccount.objects.create(
            full_name=f"Passageiro {phone}", phone_number=phone,
            status=PassengerAccount.Status.ACTIVE,
        )
        Wallet.objects.create(
            passenger_account=acc, balance_cached=Decimal("5000.00"),
            status=Wallet.Status.ACTIVE,
        )
        acc.refresh_from_db()
        return acc

    def _buy(self, phone="842000001", seat="4A", trip_id=-1, emergency="848111222"):
        from apps.guest_checkouts.purchase import purchase_travel_pass

        # Rota interprovincial: o contacto de emergencia e obrigatorio (vai
        # para o manifesto de bordo). Ver `Route.requires_emergency_contact`.
        return purchase_travel_pass(
            passenger=self._passenger(phone), route_id=self.route.id,
            origin_stop_id=self.origin.id, destination_stop_id=self.destination.id,
            trip_id=self.trip.id if trip_id == -1 else trip_id,
            seat=seat, use_package=False,
            emergency_contact_name="Familiar", emergency_contact_phone=emergency,
        )

    def test_seat_is_recorded_on_the_pass(self):
        tp = self._buy(seat="4A")
        self.assertEqual(tp.seat_number, "4A")
        self.assertEqual(tp.trip_id, self.trip.id)

    def test_interprovincial_without_a_seat_is_refused(self):
        from apps.guest_checkouts.purchase import PurchaseError

        with self.assertRaises(PurchaseError) as ctx:
            self._buy(seat="")
        self.assertIn("lugar", str(ctx.exception).lower())

    def test_interprovincial_without_a_departure_is_refused(self):
        from apps.guest_checkouts.purchase import PurchaseError

        with self.assertRaises(PurchaseError) as ctx:
            self._buy(trip_id=None)
        self.assertIn("partida", str(ctx.exception).lower())

    def test_urban_route_ignores_the_seat(self):
        """Numa carreira urbana ninguem marca lugar — guardar um numero de
        banco daria ao passageiro a ideia errada de que tem lugar reservado."""
        self.route.service_type = Route.ServiceType.URBAN
        self.route.save(update_fields=["service_type"])

        tp = self._buy(seat="9Z")
        self.assertEqual(tp.seat_number, "")

    def test_seat_already_sold_at_the_counter_is_refused(self):
        from apps.agent_api.sales import create_pos_sale
        from apps.guest_checkouts.purchase import PurchaseError
        from apps.trips.models import Agent

        agent = Agent.objects.create(full_name="Agente Balcao", status=Agent.Status.ACTIVE)
        create_pos_sale(
            agent=agent, device=None, trip_id=self.trip.id, route_id=None,
            origin_stop_id=self.origin.id, destination_stop_id=self.destination.id,
            passenger_phone="841999999", quantity=1, seats=["6B"],
        )

        with self.assertRaises(PurchaseError) as ctx:
            self._buy(seat="6B")
        self.assertIn("6B", str(ctx.exception))

    def test_app_and_counter_cannot_take_the_same_seat_at_once(self):
        """A corrida a valer: a app e o balcao no mesmo lugar, ao mesmo tempo."""
        from apps.agent_api.sales import SaleError, create_pos_sale
        from apps.guest_checkouts.purchase import PurchaseError
        from apps.trips.models import Agent

        agent = Agent.objects.create(full_name="Agente Corrida", status=Agent.Status.ACTIVE)

        def take(i):
            try:
                if i == 0:
                    tp = self._buy(phone="842000010", seat="8C")
                    return f"levou:app:{tp.id}"
                gc, _ = create_pos_sale(
                    agent=agent, device=None, trip_id=self.trip.id, route_id=None,
                    origin_stop_id=self.origin.id, destination_stop_id=self.destination.id,
                    passenger_phone="841000010", quantity=1, seats=["8C"],
                )
                return f"levou:balcao:{gc.reference}"
            except (PurchaseError, SaleError) as e:
                return f"recusado:{e}"

        results = run_together(take, n=2)
        levaram = [r for r in results if isinstance(r, str) and r.startswith("levou")]
        self.assertEqual(
            len(levaram), 1,
            f"o mesmo lugar 8C foi dado a duas pessoas: {results}",
        )
