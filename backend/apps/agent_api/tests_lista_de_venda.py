"""O balcao so vende o que esta a circular.

A lista abria com 14 viagens das quais 3 estavam a acontecer; as outras 11 eram
a mesma rota repetida dia apos dia, com o mesmo nome e o mesmo autocarro. Para
vender ao passageiro que esta a frente isso e ruido — e ruido com risco, porque
uma linha tocada por engano manda o bilhete para o autocarro de amanha.

A TPM-TUR nao vende antecipado ao balcao — mas as partidas de HOJE aparecem,
porque e a primeira venda que abre o embarque. Amanha em diante nao aparece.

O ciclo do motorista vive noutro endpoint e CONTINUA a mostrar as agendadas —
e la que o embarque se abre. Se um dia alguem estreitar esse tambem, o
motorista fica sem forma de arrancar a viagem, e e por isso que ha aqui um
teste a proteger cada um dos dois lados.
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.routes.models import Route
from apps.trips.models import Agent, Driver, Trip, Vehicle


class ListaDeVendaTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.u = User.objects.create_user(username="ag", email="ag@x.mz", password="x")
        self.agente = Agent.objects.create(user=self.u, full_name="Agente",
                                           status=Agent.Status.ACTIVE)
        self.rota = Route.objects.create(code="RT-L", name="Lista",
                                         status=Route.Status.ACTIVE,
                                         service_type="international")
        v = Vehicle.objects.create(registration="LI-01-AA", seated_capacity=30)
        agora = timezone.now()
        self.a_circular = Trip.objects.create(
            route=self.rota, vehicle=v, status=Trip.Status.BOARDING,
            planned_departure_at=agora + timedelta(minutes=30))
        self.hoje_por_abrir = Trip.objects.create(
            route=self.rota, vehicle=v, status=Trip.Status.SCHEDULED,
            planned_departure_at=agora + timedelta(hours=2))
        self.amanha = Trip.objects.create(
            route=self.rota, vehicle=v, status=Trip.Status.SCHEDULED,
            planned_departure_at=agora + timedelta(days=1))

        self.client = APIClient()
        self.client.force_authenticate(self.u)

    def _lista(self):
        r = self.client.get("/api/agent/trips/")
        self.assertEqual(r.status_code, 200, r.content)
        return [t["id"] for t in r.json()]

    # --- o que o balcao ve ------------------------------------------------

    def test_mostra_o_que_esta_a_circular(self):
        self.assertIn(self.a_circular.id, self._lista())

    def test_nao_mostra_a_partida_de_amanha(self):
        """Era esta que fazia o agente vender para o autocarro errado."""
        self.assertNotIn(self.amanha.id, self._lista())

    def test_mostra_a_de_hoje_ainda_com_o_embarque_por_abrir(self):
        """ESTA REGRA MUDOU DUAS VEZES. Vale a pena saber porque.

        Primeiro tirou-se o prazo de sete dias (nao se vende antecipado ao
        balcao). Depois tirou-se tambem as agendadas por completo, a pedido —
        e abrir o embarque passou a ser o acto que punha o autocarro a venda.

        Voltaram quando o embarque passou a abrir-se sozinho na PRIMEIRA VENDA
        (`abrir_embarque_se_preciso`): sem aparecerem na lista, o agente nunca
        as podia escolher, a primeira venda nunca acontecia, e o automatico era
        codigo morto. As duas regras juntas nao funcionavam.

        A janela do DIA concilia as duas: nao ha venda antecipada, e o
        autocarro que o motorista vai trabalhar hoje esta la sem ele ter de
        carregar em nada antes.
        """
        self.assertIn(self.hoje_por_abrir.id, self._lista())

    def test_continua_na_lista_depois_de_abrir_o_embarque(self):
        self.hoje_por_abrir.status = Trip.Status.BOARDING
        self.hoje_por_abrir.save(update_fields=["status"])
        self.assertIn(self.hoje_por_abrir.id, self._lista())

    def test_uma_viagem_pausada_nao_aparece(self):
        """Comportamento ANTERIOR a esta alteracao, deixado como estava.

        `Trip.RUNNING_STATUSES` nunca incluiu `paused`, e `sellable_statuses_for`
        tambem nao — a venda ja era recusada a uma partida em pausa muito antes
        desta lista mudar. Fica escrito porque nao e obvio: um autocarro parado
        na fronteira esta a meio da viagem, mas o sistema trata-o como fechado
        a novas vendas.
        """
        self.a_circular.status = Trip.Status.PAUSED
        self.a_circular.save(update_fields=["status"])
        self.assertNotIn(self.a_circular.id, self._lista())

    # --- o motorista nao pode ficar sem forma de arrancar -----------------

    def test_o_ecra_do_motorista_continua_a_ver_as_agendadas(self):
        """Se esta lista tambem as escondesse, nao havia como abrir o embarque
        — e nada voltava a aparecer no balcao, nunca."""
        motorista = Driver.objects.create(user=self.u, full_name="Motorista")
        for t in (self.hoje_por_abrir, self.amanha, self.a_circular):
            t.driver = motorista
            t.save(update_fields=["driver"])
        r = self.client.get("/api/driver/trips/")
        self.assertEqual(r.status_code, 200, r.content)
        ids = [t["id"] for t in r.json()]
        self.assertIn(self.hoje_por_abrir.id, ids)


class ViagemEsquecidaTests(TestCase):
    """Uma viagem que ninguem encerrou nao pode vender para sempre.

    "A circular" nao tinha limite de tempo: em producao havia uma partida em
    embarque desde 22/08 e outra em viagem desde 25/08, ambas por encerrar, e o
    balcao vendia para as duas. O passageiro sairia com bilhete para um
    autocarro que partiu ha quatro dias.
    """

    def setUp(self):
        User = get_user_model()
        u = User.objects.create_user(username="ag2", email="ag2@x.mz", password="x")
        Agent.objects.create(user=u, full_name="Agente", status=Agent.Status.ACTIVE)
        self.rota = Route.objects.create(code="RT-E", name="Esquecida",
                                         status=Route.Status.ACTIVE,
                                         service_type="international")
        self.v = Vehicle.objects.create(registration="ES-01-AA", seated_capacity=30)
        self.client = APIClient()
        self.client.force_authenticate(u)

    def _ids(self):
        r = self.client.get("/api/agent/trips/")
        self.assertEqual(r.status_code, 200, r.content)
        return [t["id"] for t in r.json()]

    def test_viagem_em_embarque_ha_quatro_dias_nao_vende(self):
        t = Trip.objects.create(
            route=self.rota, vehicle=self.v, status=Trip.Status.BOARDING,
            planned_departure_at=timezone.now() - timedelta(days=4))
        self.assertNotIn(t.id, self._ids())

    def test_viagem_a_decorrer_desde_a_madrugada_continua_a_vender(self):
        """Percurso longo com atraso — 10 horas ainda e uma viagem a serio."""
        t = Trip.objects.create(
            route=self.rota, vehicle=self.v, status=Trip.Status.DEPARTED,
            planned_departure_at=timezone.now() - timedelta(hours=10))
        self.assertIn(t.id, self._ids())

    def test_viagem_sem_hora_prevista_continua_a_aparecer(self):
        """Nao ha por onde julga-la; escondê-la era pior do que mostra-la."""
        t = Trip.objects.create(
            route=self.rota, vehicle=self.v, status=Trip.Status.BOARDING,
            planned_departure_at=None)
        self.assertIn(t.id, self._ids())
