"""A versão em bloco do cálculo de receita tem de dar exactamente o mesmo.

O relatório operacional passou a usar `calculate_trips_revenue_bulk` para
deixar de fazer ~8000 queries num pedido. É código que soma dinheiro: o único
teste que interessa é o que compara, viagem a viagem, com o cálculo original.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.passengers.models import PassengerAccount
from apps.payments.models import PaymentIntent
from apps.routes.models import Route, Stop
from apps.trips.models import Driver, Trip, Vehicle
from apps.trips.revenue import calculate_trip_revenue, calculate_trips_revenue_bulk
from apps.validations.models import ValidationEvent


class RevenueBulkEquivalenceTests(TestCase):
    def setUp(self):
        self.route = Route.objects.create(code="R-RB", name="Rota Receita",
                                          status=Route.Status.ACTIVE)
        self.stop_a = Stop.objects.create(code="RB-A", name="A", status="active")
        self.stop_b = Stop.objects.create(code="RB-B", name="B", status="active")
        driver = Driver.objects.create(full_name="Motorista RB")
        vehicle = Vehicle.objects.create(registration="RB-01-MP", seated_capacity=50)

        self.trips = []
        base = timezone.now() - timezone.timedelta(hours=4)
        for i in range(4):
            self.trips.append(Trip.objects.create(
                route=self.route, vehicle=vehicle, driver=driver,
                status=Trip.Status.COMPLETED,
                planned_departure_at=base + timezone.timedelta(minutes=40 * i),
            ))

        passenger = PassengerAccount.objects.create(
            full_name="Passageiro RB", phone_number="258845550001",
            status=PassengerAccount.Status.ACTIVE,
        )

        # Viagem 0: venda de balcão (2 bilhetes) + validação por carteira.
        GuestCheckout.objects.create(
            reference="GC-RB-0001", payer_phone="258845550002",
            route_code=self.route.code, origin_stop="A", destination_stop="B",
            quantity=2, unit_amount=Decimal("75.00"), total_amount=Decimal("150.00"),
            status=GuestCheckout.Status.ISSUED, trip=self.trips[0],
        )
        ValidationEvent.objects.create(
            validation_type=ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO,
            status=ValidationEvent.Status.APPROVED, trip=self.trips[0],
            route=self.route, amount_debited=Decimal("25.00"),
            idempotency_key="rb-val-1",
        )
        # Uma recusa, para conferir as contagens.
        ValidationEvent.objects.create(
            validation_type=ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO,
            status=ValidationEvent.Status.DENIED, trip=self.trips[0],
            route=self.route, amount_debited=Decimal("0.00"),
            idempotency_key="rb-val-2",
        )

        # Viagem 1: bilhete comprado na app (sem checkout) + pagamento directo.
        raw, token_hash = DigitalTravelPass.generate_token()
        DigitalTravelPass.objects.create(
            passenger_account=passenger, trip=self.trips[1],
            route_code=self.route.code, origin_stop="A", destination_stop="B",
            fare_amount=Decimal("90.00"), token=raw, token_hash=token_hash,
            status=DigitalTravelPass.Status.USED,
        )
        PaymentIntent.objects.create(
            reference="PAY-RB-DIRECT-1", idempotency_key="rb-direct-1",
            purpose=PaymentIntent.Purpose.DIRECT_TRIP_PAYMENT,
            amount=Decimal("60.00"), payer_phone="258845550003",
            status=PaymentIntent.Status.CONFIRMED,
            metadata={"trip_id": self.trips[1].id},
        )

        # Viagem 2: validação de bilhete digital (valor nominal, não receita).
        ValidationEvent.objects.create(
            validation_type=ValidationEvent.ValidationType.GUEST_DIGITAL_TRAVEL_PASS,
            status=ValidationEvent.Status.APPROVED, trip=self.trips[2],
            route=self.route, amount_debited=Decimal("75.00"),
            idempotency_key="rb-val-3",
        )
        # Viagem 3 fica sem movimento: os zeros também têm de coincidir.

    def test_bulk_matches_per_trip_calculation(self):
        bulk = calculate_trips_revenue_bulk(self.trips)
        for trip in self.trips:
            self.assertEqual(
                bulk[trip.id], calculate_trip_revenue(trip),
                f"a receita da viagem {trip.id} difere entre o calculo em bloco e o original",
            )

    def test_bulk_cost_does_not_grow_with_trips(self):
        with CaptureQueriesContext(connection) as few:
            calculate_trips_revenue_bulk(self.trips[:1])
        with CaptureQueriesContext(connection) as many:
            calculate_trips_revenue_bulk(self.trips)
        self.assertEqual(
            len(many), len(few),
            f"o custo cresce com o numero de viagens ({len(few)} -> {len(many)})",
        )

    def test_empty_input_costs_nothing(self):
        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(calculate_trips_revenue_bulk([]), {})
        self.assertEqual(len(ctx), 0)
