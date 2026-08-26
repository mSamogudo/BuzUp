"""Cada motorista ve as viagens do SEU autocarro.

A pergunta do operador: "porque e que um motorista ve viagens de outro no POS,
se cada um tem o seu dispositivo e o seu autocarro?"

O limite existia e estava escrito, mas nunca chegava a aplicar-se. Isentava
quem tivesse `pos.operate` — e o papel "Motorista" em PRODUCAO tinha essa
permissao, posta a mao no portal. A migracao que cria o papel deixa-o sem
permissoes nenhumas; alguem a acrescentou, quase de certeza para dar acesso ao
POS, sem saber que ser motorista activo ja bastava (`provision_pos_agent`).

Resultado: os quatro motoristas de producao viam as viagens uns dos outros, e
o codigo que devia impedi-lo estava morto.

A regra passa a depender do facto de CONDUZIR, que nao se desliga por engano
numa caixa de permissoes.
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.routes.models import Route
from apps.trips.models import Agent, Driver, Trip, Vehicle
from apps.users.models import Role, UserRole


class MotoristaVeAsSuasTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.rota = Route.objects.create(code="RT-M", name="Motoristas",
                                         status=Route.Status.ACTIVE,
                                         service_type="interprovincial")
        agora = timezone.now()

        def motorista(nome, matricula):
            u = User.objects.create_user(username=nome, email=f"{nome}@x.mz", password="x")
            Agent.objects.create(user=u, full_name=nome, status=Agent.Status.ACTIVE)
            d = Driver.objects.create(user=u, full_name=nome, status=Driver.Status.ACTIVE)
            v = Vehicle.objects.create(registration=matricula, seated_capacity=30)
            t = Trip.objects.create(route=self.rota, vehicle=v, driver=d,
                                    status=Trip.Status.BOARDING,
                                    planned_departure_at=agora + timedelta(hours=1))
            return u, d, t

        self.u1, self.d1, self.t1 = motorista("amabui", "AA-01-MP")
        self.u2, self.d2, self.t2 = motorista("emaungue", "BB-02-MP")

        # O papel "Motorista" COM `pos.operate`, tal como esta em producao.
        # (E semeado por migracao sem permissoes; aqui reproduz-se o estado
        # real, em que alguem lhe acrescentou a permissao pelo portal.)
        self.papel_motorista, _ = Role.objects.get_or_create(
            code="driver", defaults={"name": "Motorista"})
        self.papel_motorista.permissions = ["pos.operate"]
        self.papel_motorista.save(update_fields=["permissions"])
        for u in (self.u1, self.u2):
            UserRole.objects.create(user=u, role=self.papel_motorista)

    def _lista(self, u):
        c = APIClient()
        c.force_authenticate(u)
        r = c.get("/api/agent/trips/")
        self.assertEqual(r.status_code, 200, r.content)
        return [t["id"] for t in r.json()]

    # --- o caso reportado -------------------------------------------------

    def test_o_motorista_nao_ve_a_viagem_do_outro(self):
        """Era isto que acontecia com os quatro motoristas de producao."""
        self.assertNotIn(self.t2.id, self._lista(self.u1))
        self.assertNotIn(self.t1.id, self._lista(self.u2))

    def test_o_motorista_ve_a_sua(self):
        self.assertIn(self.t1.id, self._lista(self.u1))
        self.assertIn(self.t2.id, self._lista(self.u2))

    def test_o_limite_aplica_se_mesmo_com_pos_operate(self):
        """O ponto todo: era essa permissao que o desligava.

        Quem gere os papeis no portal nao tem de saber que uma caixa de
        permissoes desliga o isolamento entre motoristas.
        """
        self.assertIn("pos.operate", self.papel_motorista.permissions)
        self.assertNotIn(self.t2.id, self._lista(self.u1))

    # --- quem NAO conduz continua a ver tudo ------------------------------

    def test_o_agente_de_balcao_continua_a_ver_todas(self):
        """Nao conduz nenhum autocarro: vende em qualquer um."""
        User = get_user_model()
        u = User.objects.create_user(username="balcao", email="b@x.mz", password="x")
        Agent.objects.create(user=u, full_name="Balcao", status=Agent.Status.ACTIVE)
        UserRole.objects.create(
            user=u, role=Role.objects.get_or_create(
                code="pos_agent",
                defaults={"name": "Agente POS", "permissions": ["pos.operate"]})[0])
        ids = self._lista(u)
        self.assertIn(self.t1.id, ids)
        self.assertIn(self.t2.id, ids)

    def test_o_superuser_ve_todas(self):
        """Precisa de ver tudo para diagnosticar."""
        User = get_user_model()
        u = User.objects.create_superuser(username="root", email="r@x.mz", password="x")
        Agent.objects.create(user=u, full_name="Root", status=Agent.Status.ACTIVE)
        self.assertIn(self.t2.id, self._lista(u))

    # --- um motorista desactivado deixa de ser motorista -------------------

    def test_motorista_inactivo_deixa_de_ter_viagens_proprias(self):
        self.d1.status = Driver.Status.INACTIVE
        self.d1.save(update_fields=["status"])
        # Ja nao conduz: volta a regra do balcao.
        self.assertIn(self.t2.id, self._lista(self.u1))
