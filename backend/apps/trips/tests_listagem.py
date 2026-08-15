"""A lista de viagens do portal tem de mostrar a operação, não o futuro longínquo.

Depois de gerar um mês de partidas por horário, o portal passou a mostrar
apenas viagens "agendadas": a ordenação do modelo é `-planned_departure_at`,
logo a primeira página trazia as 200 partidas MAIS DISTANTES — todas
agendadas, todas de daqui a semanas — e a operação de hoje não aparecia em
lado nenhum. Os contadores do cabeçalho eram calculados sobre essa mesma
página, por isso mentiam.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.routes.models import Route
from apps.trips.models import Driver, Trip, Vehicle
from apps.users.models import Role, UserRole


class ListagemBase(APITestCase):
    def setUp(self):
        self.rota = Route.objects.create(code="R-LIST", name="Lista", status=Route.Status.ACTIVE)
        self.viatura = Vehicle.objects.create(registration="LS-01-MP", seated_capacity=30)
        self.motorista = Driver.objects.create(full_name="Motorista Lista")
        agora = timezone.now()

        self.hoje = Trip.objects.create(
            route=self.rota, vehicle=self.viatura, driver=self.motorista,
            status=Trip.Status.SCHEDULED, planned_departure_at=agora + timedelta(hours=2))
        self.a_circular = Trip.objects.create(
            route=self.rota, vehicle=self.viatura, driver=self.motorista,
            status=Trip.Status.BOARDING, planned_departure_at=agora + timedelta(minutes=30))
        self.passada = Trip.objects.create(
            route=self.rota, vehicle=self.viatura, driver=self.motorista,
            status=Trip.Status.COMPLETED, planned_departure_at=agora - timedelta(days=3))
        # As distantes são as que empurravam tudo o resto para fora da página.
        self.distantes = [
            Trip.objects.create(
                route=self.rota, vehicle=self.viatura, driver=self.motorista,
                status=Trip.Status.SCHEDULED,
                planned_departure_at=agora + timedelta(days=20 + d))
            for d in range(5)
        ]

        User = get_user_model()
        u = User.objects.create_user(username="op", email="op@exemplo.co.mz", password="x")
        papel = Role.objects.create(name="Operações", code="ops", permissions=["trips.read", "trips.manage"])
        UserRole.objects.create(user=u, role=papel)
        self.client.force_authenticate(u)

    def ids(self, resposta):
        dados = resposta.json()
        return [t["id"] for t in (dados.get("results") or dados)]


class PeriodoTests(ListagemBase):
    def test_por_omissao_traz_o_mais_proximo_primeiro(self):
        r = self.client.get("/api/trips/")
        self.assertEqual(r.status_code, 200)
        ids = self.ids(r)
        self.assertEqual(
            ids[0], self.a_circular.id,
            "a primeira linha tem de ser a partida mais próxima, não a mais distante",
        )
        self.assertNotIn(self.passada.id, ids, "o passado não entra no que está por acontecer")

    def test_hoje_traz_so_o_dia_de_hoje(self):
        ids = self.ids(self.client.get("/api/trips/?when=hoje"))
        self.assertIn(self.hoje.id, ids)
        self.assertIn(self.a_circular.id, ids)
        self.assertNotIn(self.passada.id, ids)
        for t in self.distantes:
            self.assertNotIn(t.id, ids, "uma partida de daqui a 20 dias não é de hoje")

    def test_passadas_traz_o_historico_do_mais_recente_para_tras(self):
        ids = self.ids(self.client.get("/api/trips/?when=passadas"))
        self.assertEqual(ids, [self.passada.id])

    def test_todas_inclui_passado_e_futuro(self):
        ids = self.ids(self.client.get("/api/trips/?when=todas"))
        self.assertIn(self.passada.id, ids)
        self.assertIn(self.hoje.id, ids)

    def test_uma_pagina_pequena_continua_a_mostrar_a_operacao(self):
        """O defeito reproduzido: com a página cheia, o que interessa some.

        Antes, pedir a primeira página devolvia as partidas mais distantes.
        Agora, mesmo com espaço para três, vêm as três mais próximas.
        """
        ids = self.ids(self.client.get("/api/trips/?page_size=3"))
        self.assertEqual(ids, [self.a_circular.id, self.hoje.id, self.distantes[0].id])


class ContadoresTests(ListagemBase):
    def test_contadores_vem_da_base_de_dados(self):
        r = self.client.get("/api/trips/summary/")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["hoje"], 2, "as duas de hoje, independentemente da paginação")
        self.assertEqual(d["circulacao"], 1)
        self.assertEqual(d["agendadas"], 6)
        self.assertEqual(d["total"], 8)

    def test_quem_so_le_viagens_ve_os_contadores(self):
        User = get_user_model()
        u = User.objects.create_user(username="leitor", email="l@exemplo.co.mz", password="x")
        papel = Role.objects.create(name="Leitor", code="leitor", permissions=["trips.read"])
        UserRole.objects.create(user=u, role=papel)
        self.client.force_authenticate(u)
        self.assertEqual(self.client.get("/api/trips/summary/").status_code, 200)

    def test_sem_capacidade_nao_ve(self):
        User = get_user_model()
        u = User.objects.create_user(username="ninguem", email="n@exemplo.co.mz", password="x")
        self.client.force_authenticate(u)
        self.assertEqual(self.client.get("/api/trips/summary/").status_code, 403)
