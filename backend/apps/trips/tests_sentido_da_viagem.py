"""Quem procura a ida nao pode receber a volta.

O defeito reportado: "as rotas tem ida e volta mas as viagens nao tem". Uma
rota traz duas listas de paragens — `outbound` e `inbound` — e a pesquisa
publica filtrava apenas pela ROTA. Resultado: quem procurava
Maputo -> Nelspruit recebia tambem as partidas Nelspruit -> Maputo, podia
comprar a errada, e via o percurso escrito ao contrario do que ia acontecer.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.fares.models import FareProduct, FareRule
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Trip, Vehicle


class SentidoDaViagemTests(TestCase):
    def setUp(self):
        self.rota = Route.objects.create(
            code="RT-MPM-NLS", name="Maputo x Nelspruit",
            status=Route.Status.ACTIVE, service_type="international",
        )
        nomes = ["Polana", "Matola", "Ressano", "Ilanga"]
        self.paragens = {
            n: Stop.objects.create(code=f"S-{n[:3].upper()}", name=n, status="active")
            for n in nomes
        }
        for i, n in enumerate(nomes):
            RouteStop.objects.create(route=self.rota, stop=self.paragens[n],
                                     sequence=i, direction=RouteStop.Direction.OUTBOUND)
        for i, n in enumerate(reversed(nomes)):
            RouteStop.objects.create(route=self.rota, stop=self.paragens[n],
                                     sequence=i, direction=RouteStop.Direction.INBOUND)

        # Sem tarifa a pesquisa descarta a partida antes de chegar ao sentido.
        produto = FareProduct.objects.create(
            name="Avulso", product_type=FareProduct.ProductType.SINGLE_TRIP)
        FareRule.objects.create(
            fare_product=produto, route=self.rota,
            calculation_method=FareRule.CalculationMethod.FIXED,
            fixed_amount=Decimal("1500.00"))

        v = Vehicle.objects.create(registration="MP-01-AA", seated_capacity=30)
        self.amanha = (timezone.now() + timedelta(days=1)).replace(hour=6, minute=0,
                                                                   second=0, microsecond=0)
        self.ida = Trip.objects.create(
            route=self.rota, vehicle=v, status=Trip.Status.SCHEDULED,
            direction=Trip.Direction.OUTBOUND, planned_departure_at=self.amanha)
        self.volta = Trip.objects.create(
            route=self.rota, vehicle=v, status=Trip.Status.SCHEDULED,
            direction=Trip.Direction.INBOUND,
            planned_departure_at=self.amanha + timedelta(hours=8))

    def _procurar(self, origem, destino):
        r = self.client.get("/api/public/trips/", {
            "origin": self.paragens[origem].id,
            "destination": self.paragens[destino].id,
            "date": self.amanha.date().isoformat(),
        })
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()["trips"]

    # --- o caso reportado ------------------------------------------------

    def test_procurar_a_ida_nao_traz_a_volta(self):
        ids = [t["trip_id"] for t in self._procurar("Polana", "Ilanga")]
        self.assertIn(self.ida.id, ids)
        self.assertNotIn(self.volta.id, ids,
                         "era aqui que o passageiro comprava bilhete do autocarro contrario")

    def test_procurar_a_volta_nao_traz_a_ida(self):
        ids = [t["trip_id"] for t in self._procurar("Ilanga", "Polana")]
        self.assertIn(self.volta.id, ids)
        self.assertNotIn(self.ida.id, ids)

    # --- as partidas antigas nao podem desaparecer -----------------------

    def test_partida_sem_sentido_declarado_continua_a_aparecer_nos_dois(self):
        """As viagens criadas antes deste campo nao sabem para onde iam.

        Escondê-las seria tirar do ar bilhetes que hoje se vendem; inventar-lhes
        um sentido seria pior. Ficam nos dois ate alguem declarar.
        """
        v2 = Vehicle.objects.create(registration="MP-02-AA", seated_capacity=30)
        antiga = Trip.objects.create(
            route=self.rota, vehicle=v2, status=Trip.Status.SCHEDULED,
            direction="", planned_departure_at=self.amanha + timedelta(hours=2))
        self.assertIn(antiga.id, [t["trip_id"] for t in self._procurar("Polana", "Ilanga")])
        self.assertIn(antiga.id, [t["trip_id"] for t in self._procurar("Ilanga", "Polana")])

    # --- o percurso mostrado ---------------------------------------------

    def test_o_percurso_segue_o_sentido_da_partida(self):
        from apps.routes.services import paragens_no_sentido

        ida = [p["name"] for p in paragens_no_sentido(self.rota, self.ida.direction)]
        volta = [p["name"] for p in paragens_no_sentido(self.rota, self.volta.direction)]
        self.assertEqual(ida[0], "Polana")
        self.assertEqual(ida[-1], "Ilanga")
        self.assertEqual(volta[0], "Ilanga",
                         "a volta mostrava o percurso da ida, e vice-versa")
        self.assertEqual(volta[-1], "Polana")

    def test_sem_sentido_declarado_o_percurso_e_o_da_ida(self):
        from apps.routes.services import paragens_no_sentido

        nomes = [p["name"] for p in paragens_no_sentido(self.rota, "")]
        self.assertEqual(nomes[0], "Polana")

    # --- programar ida e volta a mesma hora ------------------------------

    def test_ida_e_volta_no_mesmo_horario_sao_duas_partidas(self):
        """Sem o sentido na chave, a segunda era descartada como repetida."""
        from apps.trips.services import programar_partidas

        v = Vehicle.objects.create(registration="MP-03-AA", seated_capacity=30)
        dia = (timezone.now() + timedelta(days=3)).date()
        hora = self.amanha.time()
        for sentido in (Trip.Direction.OUTBOUND, Trip.Direction.INBOUND):
            programar_partidas(route=self.rota, dates=[dia], times=[hora],
                               vehicle=v, direction=sentido)
        criadas = Trip.objects.filter(route=self.rota, vehicle=v)
        self.assertEqual(criadas.count(), 2)
        self.assertEqual(
            sorted(criadas.values_list("direction", flat=True)), ["inbound", "outbound"])
