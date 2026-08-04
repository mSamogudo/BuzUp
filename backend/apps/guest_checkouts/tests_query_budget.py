"""Orçamento de queries dos endpoints mais expostos.

Um N+1 não parte nada em desenvolvimento com três partidas na base de dados —
aparece em produção, na hora de ponta, quando já há dezenas. O teste certo não
é congelar o número absoluto de queries (muda a cada refactor legítimo) mas
verificar que esse número **não cresce** com a quantidade de dados.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.fares.models import FareProduct, FareRule
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Driver, Trip, Vehicle


class PublicTripSearchQueryBudgetTests(TestCase):
    """A pesquisa pública do site: sem autenticação e a mais exposta de todas."""

    def setUp(self):
        self.route = Route.objects.create(code="R-QB", name="Rota Orcamento",
                                          status=Route.Status.ACTIVE)
        self.origin = Stop.objects.create(code="QB-A", name="Paragem A", status="active")
        self.destination = Stop.objects.create(code="QB-B", name="Paragem B", status="active")
        RouteStop.objects.create(route=self.route, stop=self.origin, sequence=1, direction="outbound")
        RouteStop.objects.create(route=self.route, stop=self.destination, sequence=2, direction="outbound")

        product = FareProduct.objects.create(name="Avulso QB", product_type="single_trip",
                                             status="active")
        FareRule.objects.create(fare_product=product, route=self.route,
                                calculation_method=FareRule.CalculationMethod.FIXED,
                                fixed_amount=Decimal("100.00"))

        self.driver = Driver.objects.create(full_name="Motorista QB")
        self.vehicle = Vehicle.objects.create(registration="QB-01-MP", seated_capacity=50)

    def _add_trips(self, n: int):
        base = timezone.now() + timezone.timedelta(hours=3)
        existing = Trip.objects.count()
        for i in range(n):
            Trip.objects.create(
                route=self.route, vehicle=self.vehicle, driver=self.driver,
                status=Trip.Status.BOARDING,
                planned_departure_at=base + timezone.timedelta(minutes=17 * (existing + i)),
            )
        # A pesquisa tem de ser feita no dia EM QUE AS PARTIDAS CAEM, e nao
        # "hoje": as partidas sao criadas a agora+3h, portanto a partir das 21h
        # locais caem no dia seguinte e a pesquisa de hoje vinha vazia. O teste
        # falhava todas as noites, sempre pela mesma razao e sem relacao com o
        # que estava a medir (o numero de queries).
        self._search_date = timezone.localtime(base).date()

    def _search_queries(self) -> int:
        client = APIClient()
        params = {
            "origin": self.origin.id,
            "destination": self.destination.id,
            "date": getattr(self, "_search_date", timezone.localdate()).isoformat(),
        }
        with CaptureQueriesContext(connection) as ctx:
            res = client.get("/api/public/trips/", params)
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(res.data.get("trips"), "a pesquisa devia devolver partidas")
        return len(ctx)

    def test_query_count_does_not_grow_with_trips(self):
        """Antes: origem e destino buscados dentro do ciclo, `quote_fare`
        repetido por partida em vez de por rota, e a lotação contada duas vezes
        por partida (`seats_available` e outra vez dentro de `sale_state`) —
        cerca de 40 queries por partida. Agora o custo é praticamente fixo.
        """
        self._add_trips(2)
        few = self._search_queries()

        self._add_trips(18)  # 20 partidas no total
        many = self._search_queries()

        self.assertLessEqual(
            many, few + 2,
            f"o custo cresce com o numero de partidas ({few} -> {many}): ha um N+1",
        )

    def test_absolute_cost_stays_modest(self):
        """Rede de segurança: o endpoint é público e sem autenticação."""
        self._add_trips(20)
        self.assertLess(
            self._search_queries(), 30,
            "a pesquisa publica passou a custar demasiado por pedido",
        )
