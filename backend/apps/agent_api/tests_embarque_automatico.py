"""A primeira venda abre o embarque.

O motorista tinha de carregar em "abrir embarque" antes de poder vender. Era um
toque a mais para uma coisa que a propria venda ja prova: se ha passageiros a
comprar, o autocarro esta a receber gente.

E o registo fica MAIS fiel: `activity_started_at` passa a marcar o instante em
que o embarque comecou de facto — a primeira venda — em vez de depender de
alguem se lembrar de carregar num botao, o que numa fila cheia acontece tarde
ou nao acontece.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.fares.models import FareProduct, FareRule
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Agent, Driver, Trip, Vehicle


class EmbarqueAutomaticoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        u = User.objects.create_user(username="ag", email="ag@x.mz", password="x")
        self.agente = Agent.objects.create(user=u, full_name="Agente",
                                           status=Agent.Status.ACTIVE)
        self.motorista = Driver.objects.create(full_name="Motorista",
                                               status=Driver.Status.ACTIVE)
        self.origem = Stop.objects.create(code="E-A", name="A", status="active")
        self.destino = Stop.objects.create(code="E-B", name="B", status="active")
        self.rota = Route.objects.create(code="RT-EMB", name="Embarque",
                                         status=Route.Status.ACTIVE,
                                         service_type="interprovincial")
        for i, p in enumerate((self.origem, self.destino)):
            RouteStop.objects.create(route=self.rota, stop=p, sequence=i,
                                     direction=RouteStop.Direction.OUTBOUND)
        prod = FareProduct.objects.create(
            name="Avulso", product_type=FareProduct.ProductType.SINGLE_TRIP)
        FareRule.objects.create(fare_product=prod, route=self.rota,
                                calculation_method=FareRule.CalculationMethod.FIXED,
                                fixed_amount=Decimal("300.00"))
        self.v = Vehicle.objects.create(registration="EM-01-AA", seated_capacity=30)
        self.viagem = Trip.objects.create(
            route=self.rota, vehicle=self.v, driver=self.motorista,
            status=Trip.Status.SCHEDULED, direction=Trip.Direction.OUTBOUND,
            planned_departure_at=timezone.now() + timedelta(hours=2))
        self.client = APIClient()
        self.client.force_authenticate(u)

    def _vender(self):
        return self.client.post("/api/agent/sales/", {
            "trip_id": self.viagem.id,
            "origin_stop_id": self.origem.id,
            "destination_stop_id": self.destino.id,
            "payment_method": "cash",
            "passenger_phone": "841234567",
            "quantity": 1,
            "emergency_contact_name": "Familiar",
            "emergency_contact_phone": "849999999",
            "passengers": [{"name": "Ana Cossa", "document_type": "bi",
                            "document_number": "110100100100A"}],
        }, format="json")

    # --- o pedido --------------------------------------------------------

    def test_a_primeira_venda_abre_o_embarque(self):
        self.assertEqual(self.viagem.status, Trip.Status.SCHEDULED)
        r = self._vender()
        self.assertEqual(r.status_code, 201, r.content)
        self.viagem.refresh_from_db()
        self.assertEqual(self.viagem.status, Trip.Status.BOARDING)

    def test_a_hora_do_embarque_e_a_da_primeira_venda(self):
        antes = timezone.now()
        self._vender()
        self.viagem.refresh_from_db()
        self.assertIsNotNone(self.viagem.activity_started_at)
        self.assertGreaterEqual(self.viagem.activity_started_at, antes)

    def test_a_partida_agendada_aparece_na_lista_para_poder_ser_vendida(self):
        """Sem isto o automatico nunca dispara: a viagem nao aparece, o agente
        nao a escolhe, e a primeira venda nao acontece."""
        r = self.client.get("/api/agent/trips/")
        self.assertIn(self.viagem.id, [t["id"] for t in r.json()])

    # --- o que NAO pode mudar --------------------------------------------

    def test_a_hora_de_saida_continua_por_marcar(self):
        """Abrir o embarque nao e partir. Juntar as duas coisas foi um defeito
        ja corrigido, e a hora de saida e o unico registo que diz se o
        autocarro se atrasou."""
        self._vender()
        self.viagem.refresh_from_db()
        self.assertIsNone(self.viagem.actual_departure_at)

    def test_a_segunda_venda_nao_mexe_na_hora_do_embarque(self):
        self._vender()
        self.viagem.refresh_from_db()
        primeira = self.viagem.activity_started_at
        self._vender()
        self.viagem.refresh_from_db()
        self.assertEqual(self.viagem.activity_started_at, primeira)

    def test_uma_viagem_ja_a_caminho_nao_volta_para_embarque(self):
        self.viagem.status = Trip.Status.DEPARTED
        self.viagem.save(update_fields=["status"])
        self._vender()
        self.viagem.refresh_from_db()
        self.assertEqual(self.viagem.status, Trip.Status.DEPARTED)

    def test_venda_antecipada_nao_abre_o_embarque_de_amanha(self):
        """A guarda que a venda antecipada obrigou a por.

        Desde que o balcao voltou a vender para outro dia, a primeira venda
        para amanha punha a viagem de amanha em embarque HOJE. Partiam-se duas
        coisas de uma vez: perdia-se o registo de quando o embarque comecou de
        facto — que e a razao de ser deste automatismo — e a viagem passava a
        contar como "a circular", ficando na lista do balcao ate ao dia
        seguinte.
        """
        self.viagem.planned_departure_at = timezone.now() + timedelta(days=1)
        self.viagem.save(update_fields=["planned_departure_at"])
        r = self._vender()
        self.assertEqual(r.status_code, 201, r.content)
        self.viagem.refresh_from_db()
        self.assertEqual(self.viagem.status, Trip.Status.SCHEDULED)
        self.assertIsNone(self.viagem.activity_started_at)

    def test_partida_sem_data_continua_a_abrir_o_embarque(self):
        """Nao ha por onde julga-la, e e o caso da urbana vendida com o
        autocarro ali a frente."""
        self.viagem.planned_departure_at = None
        self.viagem.save(update_fields=["planned_departure_at"])
        self._vender()
        self.viagem.refresh_from_db()
        self.assertEqual(self.viagem.status, Trip.Status.BOARDING)

    def test_venda_sem_motorista_atribuido_abre_o_embarque_na_mesma(self):
        """Venda ao balcao numa partida sem motorista: nao ha ciclo de
        motorista para abrir, mas a viagem tem de ficar vendavel."""
        self.viagem.driver = None
        self.viagem.save(update_fields=["driver"])
        r = self._vender()
        self.assertEqual(r.status_code, 201, r.content)
        self.viagem.refresh_from_db()
        self.assertEqual(self.viagem.status, Trip.Status.BOARDING)
