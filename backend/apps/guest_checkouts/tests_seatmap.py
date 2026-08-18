"""Planta de lugares: quando existe, e com que forma.

Duas regras de negócio distintas, ambas invisíveis para o passageiro (ele só
diz de onde para onde quer ir):

1. Numa carreira urbana não se escolhe lugar; numa interprovincial ou
   internacional escolhe-se.
2. A planta tem de corresponder ao autocarro real — mostrar um 2+2 num
   autocarro 1+2 faz o passageiro escolher um assento que não existe.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.guest_checkouts.seatmap import parse_layout, seat_labels, seat_map, seat_rows
from apps.routes.models import Route
from apps.trips.models import Driver, Trip, Vehicle


class SeatLayoutTests(TestCase):
    """A forma da planta segue o autocarro."""

    def test_two_plus_two(self):
        rows = seat_rows(8, "2+2")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["left"], ["1A", "1B"])
        self.assertEqual(rows[0]["right"], ["1C", "1D"])

    def test_one_plus_two_has_single_seat_on_the_left(self):
        """O caso do interprovincial com bancos individuais de um lado."""
        rows = seat_rows(6, "1+2")
        self.assertEqual(rows[0]["left"], ["1A"])
        self.assertEqual(rows[0]["right"], ["1B", "1C"])
        self.assertEqual(len(rows), 2)

    def test_three_plus_two(self):
        rows = seat_rows(10, "3+2")
        self.assertEqual(rows[0]["left"], ["1A", "1B", "1C"])
        self.assertEqual(rows[0]["right"], ["1D", "1E"])

    def test_last_row_is_full_width(self):
        """A fila do fundo é corrida, sem corredor."""
        rows = seat_rows(13, "2+2", last_row_seats=5)
        self.assertTrue(rows[-1]["full_width"])
        self.assertEqual(len(rows[-1]["left"]), 5)
        self.assertEqual(rows[-1]["right"], [])
        self.assertEqual(len(seat_labels(13, "2+2", 5)), 13)

    def test_partial_last_row_does_not_invent_seats(self):
        """Capacidade que não fecha a fila: 7 lugares num 2+2 são 7, não 8."""
        labels = seat_labels(7, "2+2")
        self.assertEqual(len(labels), 7)
        self.assertEqual(labels[-1], "2C")

    def test_minibus_de_quinze_lugares(self):
        """O caso que expos o defeito no desenho da planta.

        Num autocarro grande a fila incompleta e uma em vinte e quase nao se
        nota. Num minibus de 15 lugares e um quarto da planta: o lado direito
        da ultima fila tem UM banco onde as outras tem dois, e quem desenha tem
        de deixar a coluna vazia em vez de encolher a fila.
        """
        rows = seat_rows(15, "2+2")
        self.assertEqual(len(rows), 4)
        self.assertEqual([len(r["left"]) for r in rows], [2, 2, 2, 2])
        self.assertEqual([len(r["right"]) for r in rows], [2, 2, 2, 1])

    def test_minibus_com_lado_direito_vazio(self):
        """7 lugares num 1+2: a ultima fila nao tem lado direito nenhum."""
        rows = seat_rows(7, "1+2")
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[-1]["left"], ["3A"])
        self.assertEqual(rows[-1]["right"], [])

    def test_minibus_de_doze_fecha_certo(self):
        rows = seat_rows(12, "2+2")
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(len(r["left"]) == 2 and len(r["right"]) == 2 for r in rows))

    def test_lotacao_pequena_nunca_perde_lugares(self):
        """Seja qual for o layout, a planta tem exactamente os lugares que ha."""
        for capacidade in range(1, 21):
            for layout in ("1+1", "1+2", "2+1", "2+2", "2+3", "3+2"):
                with self.subTest(capacidade=capacidade, layout=layout):
                    self.assertEqual(len(seat_labels(capacidade, layout)), capacidade)
                    self.assertEqual(len(set(seat_labels(capacidade, layout))), capacidade,
                                     "duas etiquetas iguais na mesma planta")

    def test_garbage_layout_falls_back(self):
        self.assertEqual(parse_layout("nao-e-layout"), (2, 2))
        self.assertEqual(parse_layout(""), (2, 2))
        self.assertEqual(parse_layout("0+9"), (2, 2))


class SeatSelectionByServiceTypeTests(TestCase):
    """Quem decide se há escolha de lugar é o tipo de serviço da rota."""

    def _trip_for(self, service_type: str, layout: str = "2+2", capacity: int = 12) -> Trip:
        route = Route.objects.create(
            code=f"R-{service_type[:4].upper()}", name=f"Rota {service_type}",
            status=Route.Status.ACTIVE, service_type=service_type,
        )
        vehicle = Vehicle.objects.create(
            registration=f"SM-{service_type[:3]}-MP", seated_capacity=capacity,
            seat_layout=layout,
        )
        driver = Driver.objects.create(full_name="Motorista SM")
        return Trip.objects.create(
            route=route, vehicle=vehicle, driver=driver,
            status=Trip.Status.BOARDING,
            planned_departure_at=timezone.now() + timezone.timedelta(hours=2),
        )

    def test_urban_route_has_no_seat_map(self):
        """O passageiro urbano não passa pela etapa de lugares."""
        data = seat_map(self._trip_for(Route.ServiceType.URBAN))
        self.assertFalse(data["has_seat_map"])
        self.assertFalse(data["seat_selection"])
        self.assertEqual(data["rows"], [])
        self.assertIn("reason", data)

    def test_interprovincial_route_has_seat_map(self):
        data = seat_map(self._trip_for(Route.ServiceType.INTERPROVINCIAL))
        self.assertTrue(data["has_seat_map"])
        self.assertTrue(data["seat_selection"])
        self.assertEqual(data["capacity"], 12)
        self.assertEqual(len(data["rows"]), 3)

    def test_international_route_has_seat_map(self):
        data = seat_map(self._trip_for(Route.ServiceType.INTERNATIONAL))
        self.assertTrue(data["has_seat_map"])

    def test_map_follows_the_vehicle_layout(self):
        data = seat_map(self._trip_for(Route.ServiceType.INTERPROVINCIAL, layout="1+2", capacity=9))
        self.assertEqual(data["layout"], "1+2")
        first = data["rows"][0]
        self.assertEqual([s["label"] for s in first["left"]], ["1A"])
        self.assertEqual([s["label"] for s in first["right"]], ["1B", "1C"])

    def test_seated_route_without_capacity_still_sells(self):
        """Sem lotação registada, é melhor vender sem planta do que bloquear."""
        data = seat_map(self._trip_for(Route.ServiceType.INTERPROVINCIAL, capacity=0))
        self.assertFalse(data["has_seat_map"])
        self.assertTrue(data["seat_selection"])
        self.assertIn("lotacao", data["reason"].lower())


class OccupiedSeatsTests(TestCase):
    """Lugares vendidos aparecem ocupados na planta."""

    def test_sold_seat_is_marked_occupied(self):
        from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout

        route = Route.objects.create(
            code="R-OCC", name="Rota Ocupados", status=Route.Status.ACTIVE,
            service_type=Route.ServiceType.INTERPROVINCIAL,
        )
        vehicle = Vehicle.objects.create(registration="OC-01-MP", seated_capacity=8, seat_layout="2+2")
        trip = Trip.objects.create(
            route=route, vehicle=vehicle, status=Trip.Status.BOARDING,
            planned_departure_at=timezone.now() + timezone.timedelta(hours=2),
        )
        gc = GuestCheckout.objects.create(
            reference="GC-OCC0001", payer_phone="258841000000",
            route_code=route.code, origin_stop="A", destination_stop="B",
            quantity=1, unit_amount=Decimal("100.00"), total_amount=Decimal("100.00"),
            status=GuestCheckout.Status.ISSUED, trip=trip,
        )
        raw, token_hash = DigitalTravelPass.generate_token()
        DigitalTravelPass.objects.create(
            guest_checkout=gc, trip=trip, payer_phone="258841000000",
            route_code=route.code, origin_stop="A", destination_stop="B",
            fare_amount=Decimal("100.00"), token=raw, token_hash=token_hash,
            seat_number="1C", status=DigitalTravelPass.Status.ACTIVE,
        )

        data = seat_map(trip)
        self.assertIn("1C", data["occupied"])
        self.assertEqual(data["available"], 7)
        seat_1c = next(
            s for row in data["rows"] for s in row["seats"] if s["label"] == "1C"
        )
        self.assertTrue(seat_1c["occupied"])
