"""Uma viagem que ja partiu tem de continuar a poder abrir-se.

O erro reportado: "No trips matches the given query" ao abrir uma viagem no
portal. A causa nao era a viagem ter desaparecido — era o filtro da LISTAGEM a
ser aplicado tambem a quem pedia uma viagem pelo numero.

A listagem, por omissao, mostra o que esta por acontecer: `planned_departure_at
>= agora`. Aplicado ao `retrieve`, esse mesmo filtro escondia todas as partidas
ja saidas. Em producao eram quatro das seis — e sao precisamente as que se vao
consultar DEPOIS de acontecerem: o manifesto, a receita, quem foi a bordo.

Quando se pede uma viagem pelo numero ela ja esta identificada. Nao ha nada
para filtrar.
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.routes.models import Route
from apps.trips.models import Trip, Vehicle
from apps.users.models import Role, UserRole


class AbrirViagemTests(TestCase):
    def setUp(self):
        User = get_user_model()
        u = User.objects.create_user(username="op", email="op@x.mz", password="x")
        papel = Role.objects.create(name="Operacoes", code="ops-abrir",
                                    permissions=["trips.read", "trips.manage"])
        UserRole.objects.create(user=u, role=papel)
        self.client = APIClient()
        self.client.force_authenticate(u)

        self.rota = Route.objects.create(code="R-AB", name="Abrir", status=Route.Status.ACTIVE)
        v = Vehicle.objects.create(registration="AB-01-MP", seated_capacity=30)
        agora = timezone.now()
        self.ontem = Trip.objects.create(
            route=self.rota, vehicle=v, status=Trip.Status.COMPLETED,
            planned_departure_at=agora - timedelta(days=1))
        self.hoje_ja_saiu = Trip.objects.create(
            route=self.rota, vehicle=v, status=Trip.Status.SCHEDULED,
            planned_departure_at=agora - timedelta(hours=3))
        self.amanha = Trip.objects.create(
            route=self.rota, vehicle=v, status=Trip.Status.SCHEDULED,
            planned_departure_at=agora + timedelta(days=1))

    # --- o caso reportado ------------------------------------------------

    def test_abrir_uma_viagem_de_ontem(self):
        r = self.client.get(f"/api/trips/{self.ontem.id}/")
        self.assertEqual(r.status_code, 200,
                         "era aqui que dava 'No trips matches the given query'")
        self.assertEqual(r.json()["id"], self.ontem.id)

    def test_abrir_uma_agendada_cuja_hora_ja_passou(self):
        """O autocarro atrasou-se; a viagem continua a existir."""
        r = self.client.get(f"/api/trips/{self.hoje_ja_saiu.id}/")
        self.assertEqual(r.status_code, 200)

    def test_editar_uma_viagem_passada(self):
        r = self.client.patch(f"/api/trips/{self.ontem.id}/",
                              {"status": "cancelled"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)

    def test_apagar_uma_viagem_passada(self):
        r = self.client.delete(f"/api/trips/{self.ontem.id}/")
        self.assertIn(r.status_code, (200, 204), r.content)

    def test_o_manifesto_de_uma_viagem_passada(self):
        """E depois de acontecer que o manifesto interessa."""
        r = self.client.get(f"/api/trips/{self.ontem.id}/manifest/")
        self.assertEqual(r.status_code, 200, r.content)

    # --- a listagem continua a filtrar -----------------------------------

    def test_a_lista_por_omissao_mostra_so_o_que_esta_por_sair(self):
        """O filtro nao desapareceu: mudou de sitio."""
        ids = [t["id"] for t in self.client.get("/api/trips/").json()["results"]]
        self.assertIn(self.amanha.id, ids)
        self.assertNotIn(self.ontem.id, ids)

    def test_a_lista_de_passadas_traz_o_historico(self):
        ids = [t["id"] for t in self.client.get("/api/trips/?when=passadas").json()["results"]]
        self.assertIn(self.ontem.id, ids)

    def test_a_lista_por_rota_continua_a_filtrar(self):
        outra = Route.objects.create(code="R-OUT", name="Outra", status=Route.Status.ACTIVE)
        ids = [t["id"] for t in
               self.client.get(f"/api/trips/?route={outra.id}&when=todas").json()["results"]]
        self.assertEqual(ids, [])

    def test_um_numero_que_nao_existe_continua_a_dar_404(self):
        self.assertEqual(self.client.get("/api/trips/999999/").status_code, 404)
