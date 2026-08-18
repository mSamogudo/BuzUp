"""O que o balcao ve na lista de partidas.

O incidente: o cliente criou a viagem no portal, foi ao POS, e a lista estava
vazia. Nao havia erro nenhum — a viagem ficava `agendada` (e o unico estado com
que uma viagem nasce) e o POS so mostrava as que ja estavam em embarque. Ou
seja: a unica maneira de vender era o motorista abrir o embarque primeiro, o
que numa carreira internacional acontece horas depois de o bilhete ser vendido.

A regra passou a ser uma so, em `Trip.sellable_statuses_for`: numa rota com
lugar marcado vende-se com antecedencia; numa urbana vende-se o autocarro que
esta ali.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Agent, Trip, Vehicle


class PartidasNoBalcaoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="balcao", password="x", email="balcao@x.mz", phone="849000001")
        Agent.objects.create(full_name="Agente", user=self.user, status=Agent.Status.ACTIVE)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.viatura = Vehicle.objects.create(registration="AAA-01-MP", seated_capacity=40)

    def _rota(self, code, service_type):
        rota = Route.objects.create(
            code=code, name=code, service_type=service_type, status=Route.Status.ACTIVE)
        a = Stop.objects.create(code=f"{code}-A", name="A", status="active")
        b = Stop.objects.create(code=f"{code}-B", name="B", status="active")
        RouteStop.objects.create(route=rota, stop=a, sequence=1, direction="outbound")
        RouteStop.objects.create(route=rota, stop=b, sequence=2, direction="outbound")
        return rota

    def _viagem(self, rota, status, partida):
        return Trip.objects.create(
            route=rota, vehicle=self.viatura, status=status, planned_departure_at=partida)

    def ids_listados(self):
        r = self.client.get("/api/agent/trips/")
        self.assertEqual(r.status_code, 200, r.content)
        return {t["id"] for t in r.json()}

    def test_partida_agendada_de_rota_internacional_aparece(self):
        """O caso do cliente: viagem criada hoje para amanha, vendida hoje."""
        rota = self._rota("R-INT", Route.ServiceType.INTERNATIONAL)
        viagem = self._viagem(rota, Trip.Status.SCHEDULED, timezone.now() + timedelta(days=1))
        self.assertIn(viagem.id, self.ids_listados())

    def test_partida_agendada_de_rota_urbana_nao_aparece(self):
        """Na urbana vende-se o autocarro que esta ali, nao o de amanha."""
        rota = self._rota("R-URB", Route.ServiceType.URBAN)
        viagem = self._viagem(rota, Trip.Status.SCHEDULED, timezone.now() + timedelta(days=1))
        self.assertNotIn(viagem.id, self.ids_listados())

    def test_urbana_em_embarque_aparece(self):
        rota = self._rota("R-URB2", Route.ServiceType.URBAN)
        viagem = self._viagem(rota, Trip.Status.BOARDING, timezone.now())
        self.assertIn(viagem.id, self.ids_listados())

    def test_partida_atrasada_continua_a_venda(self):
        """O autocarro atrasa-se; o balcao nao pode fechar a venda no minuto."""
        rota = self._rota("R-INT2", Route.ServiceType.INTERNATIONAL)
        viagem = self._viagem(rota, Trip.Status.SCHEDULED, timezone.now() - timedelta(hours=1))
        self.assertIn(viagem.id, self.ids_listados())

    def test_partida_de_daqui_a_um_mes_nao_enche_a_lista(self):
        rota = self._rota("R-INT3", Route.ServiceType.INTERNATIONAL)
        viagem = self._viagem(rota, Trip.Status.SCHEDULED, timezone.now() + timedelta(days=30))
        self.assertNotIn(viagem.id, self.ids_listados())

    def test_partida_encerrada_nao_aparece(self):
        rota = self._rota("R-INT4", Route.ServiceType.INTERNATIONAL)
        viagem = self._viagem(rota, Trip.Status.COMPLETED, timezone.now() + timedelta(hours=2))
        self.assertNotIn(viagem.id, self.ids_listados())

    def test_tarifa_de_partida_agendada_e_calculavel(self):
        """Sem isto o agente ve a partida na lista e leva com erro ao avancar."""
        from apps.fares.models import FareProduct, FareRule

        rota = self._rota("R-INT5", Route.ServiceType.INTERNATIONAL)
        produto = FareProduct.objects.create(
            name="Avulso", product_type="single_trip", status="active")
        FareRule.objects.create(
            fare_product=produto, route=rota,
            calculation_method=FareRule.CalculationMethod.FIXED,
            fixed_amount=Decimal("1500.00"),
        )
        viagem = self._viagem(rota, Trip.Status.SCHEDULED, timezone.now() + timedelta(days=1))
        paragens = list(RouteStop.objects.filter(route=rota).order_by("sequence"))
        r = self.client.post(
            f"/api/agent/trips/{viagem.id}/fare/",
            {"origin_stop_id": paragens[0].stop_id, "destination_stop_id": paragens[1].stop_id},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["fare_amount"], "1500.00")
