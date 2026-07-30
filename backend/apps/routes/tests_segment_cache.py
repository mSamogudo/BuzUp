"""Cache dos segmentos de rota.

Cachear no caminho do embarque só é aceitável se (a) o resultado for
exactamente o mesmo e (b) uma alteração ao mapa da rota surtir efeito
imediato. Uma tarifa calculada com sequências antigas é dinheiro errado.
"""

from __future__ import annotations

from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.routes.models import Route, RouteStop, Stop
from apps.routes.services import (
    RouteSegmentError,
    invalidate_route_segments,
    resolve_route_segment,
)


class RouteSegmentCacheTests(TestCase):
    def setUp(self):
        cache.clear()
        self.route = Route.objects.create(code="R-SC", name="Rota Cache",
                                          status=Route.Status.ACTIVE)
        self.a = Stop.objects.create(code="SC-A", name="A", status="active")
        self.b = Stop.objects.create(code="SC-B", name="B", status="active")
        self.c = Stop.objects.create(code="SC-C", name="C", status="active")
        RouteStop.objects.create(route=self.route, stop=self.a, sequence=1,
                                 direction="outbound", distance_from_start_km=0)
        RouteStop.objects.create(route=self.route, stop=self.b, sequence=2,
                                 direction="outbound", distance_from_start_km=10)

    def test_second_call_costs_no_queries_and_matches(self):
        with CaptureQueriesContext(connection) as first:
            seg1 = resolve_route_segment(self.route, self.a.id, self.b.id)
        with CaptureQueriesContext(connection) as second:
            seg2 = resolve_route_segment(self.route, self.a.id, self.b.id)

        self.assertEqual(seg1, seg2, "a cache devolveu um segmento diferente")
        self.assertGreater(len(first), 0)
        self.assertEqual(len(second), 0, "a segunda chamada devia vir da cache")

    def test_failure_is_cached_too(self):
        """Descobrir que um par nao forma segmento tambem custa 2 queries."""
        with self.assertRaises(RouteSegmentError):
            resolve_route_segment(self.route, self.a.id, self.c.id)
        with CaptureQueriesContext(connection) as ctx:
            with self.assertRaises(RouteSegmentError):
                resolve_route_segment(self.route, self.a.id, self.c.id)
        self.assertEqual(len(ctx), 0)

    def test_changing_stops_takes_effect_immediately(self):
        """O risco da cache: uma tarifa calculada com o mapa antigo."""
        first = resolve_route_segment(self.route, self.a.id, self.b.id)
        self.assertEqual(first.distance_km, "10.00")

        RouteStop.objects.filter(route=self.route, stop=self.b).update(
            distance_from_start_km=25,
        )
        invalidate_route_segments(self.route.id)

        after = resolve_route_segment(self.route, self.a.id, self.b.id)
        self.assertEqual(
            after.distance_km, "25.00",
            "a alteracao ao mapa da rota nao surtiu efeito — tarifa por distancia errada",
        )

    def test_invalid_input_still_raises_readable_error(self):
        with self.assertRaises(RouteSegmentError):
            resolve_route_segment(self.route, "abc", self.b.id)


class InvalidInputTests(TestCase):
    """Query-params do site público não podem produzir 500.

    A pesquisa pública lê `?origin=` e `?destination=` crus. Um `int()` sobre
    esse valor levantava ValueError, que sem tratamento vira erro de servidor —
    e um 500 no site alimenta a impressão de que "a plataforma está em baixo".
    """

    def setUp(self):
        cache.clear()
        self.route = Route.objects.create(code="R-IN", name="Rota Input",
                                          status=Route.Status.ACTIVE)

    def test_non_numeric_ids_raise_readable_error(self):
        from apps.routes.services import route_segments_for_stop_pair

        with self.assertRaises(RouteSegmentError):
            route_segments_for_stop_pair("abc", "xyz")

    def test_public_search_returns_400_not_500(self):
        from rest_framework.test import APIClient

        res = APIClient().get("/api/public/trips/", {
            "origin": "abc", "destination": "xyz", "date": "2026-08-01",
        })
        self.assertEqual(res.status_code, 400, f"devia ser pedido invalido, veio {res.status_code}")
