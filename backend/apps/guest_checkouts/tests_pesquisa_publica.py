"""O que o site mostra a quem procura uma viagem.

Duas coisas que estavam a enganar o passageiro:

1. Trocos marcados a custo zero apareciam na lista. Zero nao e um preco — e
   como o operador diz que aquele troco nao se vende. Mostra-lo dava um
   resultado onde o passageiro so podia tropecar (ou, pior, comprar de graca).

2. O cartao do resultado mostrava o preco ao lado do NOME DA ROTA. Numa
   carreira internacional o passageiro escolhe um troco dela — ver "Maputo x
   Nelspruit · 1500 MZN" quando pediu Ressano Garcia → Nelspruit diz-lhe que
   vai pagar a viagem toda.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.fares.models import FareProduct, FareRule
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Trip, Vehicle


class PesquisaPublicaTests(TestCase):
    def setUp(self):
        self.rota = Route.objects.create(
            code="RT-INT", name="Maputo x Nelspruit",
            service_type=Route.ServiceType.INTERNATIONAL, status=Route.Status.ACTIVE)
        self.a = Stop.objects.create(code="ST-RG", name="Ressano Garcia", status="active")
        self.b = Stop.objects.create(code="ST-NLP", name="Nelspruit", status="active")
        RouteStop.objects.create(route=self.rota, stop=self.a, sequence=1, direction="outbound")
        RouteStop.objects.create(route=self.rota, stop=self.b, sequence=2, direction="outbound")
        self.produto = FareProduct.objects.create(
            name="Avulso", product_type="single_trip", status="active")
        self.viatura = Vehicle.objects.create(registration="LJP-553-MP", seated_capacity=52)
        self.amanha = timezone.localdate() + timedelta(days=1)
        self.viagem = Trip.objects.create(
            route=self.rota, vehicle=self.viatura, status=Trip.Status.SCHEDULED,
            planned_departure_at=timezone.now() + timedelta(days=1),
        )

    def _tarifa(self, valor):
        FareRule.objects.create(
            fare_product=self.produto, route=self.rota,
            calculation_method=FareRule.CalculationMethod.FIXED,
            fixed_amount=Decimal(valor),
        )

    def pesquisar(self):
        return self.client.get(
            "/api/public/trips/",
            {"origin": self.a.id, "destination": self.b.id, "date": self.amanha.isoformat()},
        )

    def test_percurso_a_venda_aparece_com_o_seu_preco(self):
        self._tarifa("1500.00")
        r = self.pesquisar()
        self.assertEqual(r.status_code, 200, r.content)
        viagens = r.json()["trips"]
        self.assertEqual(len(viagens), 1)
        self.assertEqual(viagens[0]["fare_amount"], "1500.00")

    def test_o_resultado_diz_o_percurso_escolhido(self):
        self._tarifa("1500.00")
        viagem = self.pesquisar().json()["trips"][0]
        self.assertEqual(viagem["origin_stop"], "Ressano Garcia")
        self.assertEqual(viagem["destination_stop"], "Nelspruit")

    def test_percurso_a_custo_zero_nao_e_mostrado(self):
        self._tarifa("0.00")
        r = self.pesquisar()
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(
            r.json()["trips"], [],
            "um troco que nao se vende nao pode aparecer a quem esta a comprar",
        )

    def test_percurso_sem_tarifa_nenhuma_nao_e_mostrado(self):
        r = self.pesquisar()
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["trips"], [])
