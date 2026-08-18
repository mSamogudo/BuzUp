"""Um percurso a custo zero nao esta a venda.

Numa carreira internacional a rota tem paragens que existem para o autocarro
parar, mas cujo troco nao se vende — dois pontos dentro da mesma cidade, ou a
paragem tecnica antes da fronteira. O operador marca-os com custo zero.

Enquanto o zero foi tratado como um preco, o site mostrava esse troco a "0 MZN"
e quem o escolhesse levava um bilhete de graca. Agora o zero significa o que o
operador queria dizer: nao vendemos isto.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from apps.fares.models import FareProduct, FareRule
from apps.fares.services import NoFareFoundError, quote_fare
from apps.routes.models import Route, RouteStop, Stop


class PercursoSemVendaTests(TestCase):
    def setUp(self):
        self.rota = Route.objects.create(
            code="RT-INT", name="Maputo x Nelspruit",
            service_type=Route.ServiceType.INTERNATIONAL, status=Route.Status.ACTIVE)
        self.a = Stop.objects.create(code="ST-A", name="Maputo", status="active")
        self.b = Stop.objects.create(code="ST-B", name="Nelspruit", status="active")
        RouteStop.objects.create(route=self.rota, stop=self.a, sequence=1, direction="outbound")
        RouteStop.objects.create(route=self.rota, stop=self.b, sequence=2, direction="outbound")
        self.produto = FareProduct.objects.create(
            name="Avulso", product_type="single_trip", status="active")

    def _tarifa(self, valor):
        FareRule.objects.create(
            fare_product=self.produto, route=self.rota,
            calculation_method=FareRule.CalculationMethod.FIXED,
            fixed_amount=Decimal(valor),
        )

    def test_tarifa_normal_e_devolvida(self):
        self._tarifa("1500.00")
        q = quote_fare(route=self.rota, origin_stop=self.a, destination_stop=self.b)
        self.assertEqual(q.amount, Decimal("1500.00"))

    def test_custo_zero_nao_e_um_preco(self):
        self._tarifa("0.00")
        with self.assertRaises(NoFareFoundError) as ctx:
            quote_fare(route=self.rota, origin_stop=self.a, destination_stop=self.b)
        self.assertIn("nao esta a venda", str(ctx.exception))

    def test_valor_negativo_tambem_e_recusado(self):
        self._tarifa("-50.00")
        with self.assertRaises(NoFareFoundError):
            quote_fare(route=self.rota, origin_stop=self.a, destination_stop=self.b)
