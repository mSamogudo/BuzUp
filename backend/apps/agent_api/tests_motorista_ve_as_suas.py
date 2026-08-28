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

        # Percurso e tarifa: sem isto a venda parava antes de chegar a regra.
        from decimal import Decimal

        from apps.fares.models import FareProduct, FareRule
        from apps.routes.models import RouteStop, Stop

        self.origem = Stop.objects.create(code="M-A", name="A", status="active")
        self.destino = Stop.objects.create(code="M-B", name="B", status="active")
        for i, p in enumerate((self.origem, self.destino)):
            RouteStop.objects.create(route=self.rota, stop=p, sequence=i,
                                     direction=RouteStop.Direction.OUTBOUND)
        prod = FareProduct.objects.create(
            name="Avulso", product_type=FareProduct.ProductType.SINGLE_TRIP)
        FareRule.objects.create(fare_product=prod, route=self.rota,
                                calculation_method=FareRule.CalculationMethod.FIXED,
                                fixed_amount=Decimal("250.00"))

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

    # --- E SOBRETUDO: nao pode VENDER na viagem do outro -------------------

    def _vender(self, u, trip):
        c = APIClient()
        c.force_authenticate(u)
        return c.post("/api/agent/sales/", {
            "trip_id": trip.id,
            "origin_stop_id": self.origem.id,
            "destination_stop_id": self.destino.id,
            "payment_method": "cash",
            "passenger_phone": "841234567",
            "quantity": 1,
        }, format="json")

    def test_o_motorista_nao_vende_na_viagem_do_outro(self):
        """O que importa nao e o que ele VE — e o que ele consegue FAZER.

        Esconder a viagem da lista e conveniencia. Se o pedido chegar na mesma
        (uma app antiga, um ecra que ficou aberto, um pedido a mao), o servidor
        tem de recusar.
        """
        r = self._vender(self.u1, self.t2)
        self.assertEqual(r.status_code, 403, r.content)
        self.assertIn("alocada", r.content.decode())

    def test_o_motorista_vende_na_sua(self):
        r = self._vender(self.u1, self.t1)
        self.assertNotEqual(r.status_code, 403, r.content)

    def test_o_agente_de_balcao_vende_em_qualquer_uma(self):
        User = get_user_model()
        u = User.objects.create_user(username="balcao2", email="b2@x.mz", password="x")
        Agent.objects.create(user=u, full_name="Balcao", status=Agent.Status.ACTIVE)
        UserRole.objects.create(
            user=u, role=Role.objects.get_or_create(
                code="pos_agent",
                defaults={"name": "Agente POS", "permissions": ["pos.operate"]})[0])
        self.assertNotEqual(self._vender(u, self.t1).status_code, 403)
        self.assertNotEqual(self._vender(u, self.t2).status_code, 403)

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

    def test_o_superuser_sem_autocarro_ve_todas(self):
        """Precisa de ver tudo para diagnosticar — e nao conduz nada."""
        User = get_user_model()
        u = User.objects.create_superuser(username="root", email="r@x.mz", password="x")
        Agent.objects.create(user=u, full_name="Root", status=Agent.Status.ACTIVE)
        self.assertIn(self.t2.id, self._lista(u))

    def test_o_superuser_que_conduz_ve_so_as_suas(self):
        """O cargo nao anula o autocarro.

        Enquanto o superuser era isento sem excepcao, bastava dar a conta de
        administracao a alguem que tambem conduz para o limite desaparecer para
        ele. E o limite nao e sobre o cargo: um bilhete emitido na viagem
        errada poe o passageiro no autocarro errado, seja quem for que o venda.

        A saida existe e e explicita — tirar-lhe o registo de Motorista.
        """
        User = get_user_model()
        u = User.objects.create_superuser(username="chefe", email="c@x.mz", password="x")
        Agent.objects.create(user=u, full_name="Chefe", status=Agent.Status.ACTIVE)
        carro = Vehicle.objects.create(registration="CHF-01-MP", seated_capacity=30)
        d = Driver.objects.create(user=u, full_name="Chefe", status=Driver.Status.ACTIVE)
        sua = Trip.objects.create(
            route=self.rota, vehicle=carro, driver=d,
            status=Trip.Status.BOARDING,
            planned_departure_at=timezone.now() + timedelta(minutes=30),
        )
        ids = self._lista(u)
        self.assertIn(sua.id, ids)
        self.assertNotIn(self.t1.id, ids)
        self.assertNotIn(self.t2.id, ids)

    def test_tirar_o_registo_de_motorista_devolve_a_vista_completa(self):
        """A saida de diagnostico, e que tem de ser deliberada."""
        User = get_user_model()
        u = User.objects.create_superuser(username="chefe2", email="c2@x.mz", password="x")
        Agent.objects.create(user=u, full_name="Chefe", status=Agent.Status.ACTIVE)
        d = Driver.objects.create(user=u, full_name="Chefe", status=Driver.Status.ACTIVE)
        self.assertNotIn(self.t2.id, self._lista(u))
        d.delete()
        self.assertIn(self.t2.id, self._lista(u))

    # --- um motorista desactivado deixa de ser motorista -------------------

    def test_desactivar_um_motorista_nao_lhe_da_mais_acesso(self):
        """Ao contrario do que eu tinha escrito primeiro.

        Filtrar so por motoristas ACTIVOS fazia com que desactivar um lhe
        desse acesso a TODAS as viagens: deixava de contar como motorista e
        caia na regra do balcao. Uma desactivacao nunca pode alargar
        permissoes.
        """
        self.d1.status = Driver.Status.INACTIVE
        self.d1.save(update_fields=["status"])
        self.assertNotIn(self.t2.id, self._lista(self.u1),
                         "desactivar deu-lhe a viagem do outro")

    def test_motorista_sem_viagens_alocadas_nao_vende_nada(self):
        """A regra do operador: sem viagem atribuida, nao vende para nenhuma."""
        User = get_user_model()
        u = User.objects.create_user(username="semviagens", email="s@x.mz", password="x")
        Agent.objects.create(user=u, full_name="Sem viagens", status=Agent.Status.ACTIVE)
        Driver.objects.create(user=u, full_name="Sem viagens", status=Driver.Status.ACTIVE)
        UserRole.objects.create(user=u, role=self.papel_motorista)

        self.assertEqual(self._lista(u), [], "devia ver a lista vazia")
        for t in (self.t1, self.t2):
            c = APIClient()
            c.force_authenticate(u)
            r = c.post("/api/agent/sales/", {
                "trip_id": t.id,
                "origin_stop_id": self.origem.id,
                "destination_stop_id": self.destino.id,
                "payment_method": "cash",
                "passenger_phone": "841234567",
                "quantity": 1,
            }, format="json")
            self.assertEqual(r.status_code, 403, r.content)


class MotoristaSemViagemTests(MotoristaVeAsSuasTests):
    """E se o pedido nao indicar viagem nenhuma?

    O guarda da venda so corre `if data.get("trip_id")`. Um pedido feito so com
    `route_id` — que a app nunca envia, mas que nada impede — escapava-lhe.
    """

    def test_vender_so_com_a_rota_nao_da_ao_motorista_uma_saida(self):
        c = APIClient()
        c.force_authenticate(self.u1)
        r = c.post("/api/agent/sales/", {
            "route_id": self.rota.id,
            "origin_stop_id": self.origem.id,
            "destination_stop_id": self.destino.id,
            "payment_method": "cash",
            "passenger_phone": "841234567",
            "quantity": 1,
        }, format="json")
        # Sem viagem indicada a venda nao fica ligada a autocarro nenhum: nao
        # ha "viagem do outro" para invadir, e a lotacao nao e tocada. O que
        # NAO pode acontecer e o bilhete sair agarrado a uma viagem concreta
        # que nao e a dele.
        if r.status_code < 300:
            from apps.guest_checkouts.models import GuestCheckout

            gc = GuestCheckout.objects.get(reference=r.json()["sale_reference"])
            self.assertIsNone(gc.trip_id,
                              "uma venda sem viagem indicada nao pode acabar "
                              "agarrada a uma viagem")


class TudoOQueTocaNaViagemDoOutroTests(MotoristaVeAsSuasTests):
    """Um por um, todos os caminhos que abrem a viagem de outro motorista.

    Esconder da lista nao chega, e recusar so a venda tambem nao: o detalhe da
    viagem traz a planta de lugares, e o manifesto traz a lista de quem vai a
    bordo — nomes, documentos e contactos de emergencia de passageiros que nao
    sao dele.
    """

    def _como(self, u):
        c = APIClient()
        c.force_authenticate(u)
        return c

    def test_nao_abre_o_detalhe_da_viagem_do_outro(self):
        r = self._como(self.u1).get(f"/api/agent/trips/{self.t2.id}/")
        self.assertEqual(r.status_code, 403, r.content)

    def test_abre_o_detalhe_da_sua(self):
        r = self._como(self.u1).get(f"/api/agent/trips/{self.t1.id}/")
        self.assertEqual(r.status_code, 200, r.content)

    def test_nao_cota_tarifa_na_viagem_do_outro(self):
        """A tarifa e o passo antes da venda: fechar so a venda deixava-o
        chegar ao fim do fluxo para levar com um erro no ultimo toque."""
        r = self._como(self.u1).post(
            f"/api/agent/trips/{self.t2.id}/fare/",
            {"origin_stop_id": self.origem.id, "destination_stop_id": self.destino.id},
            format="json")
        self.assertEqual(r.status_code, 403, r.content)

    def test_nao_ve_o_manifesto_do_outro(self):
        """Sao dados pessoais de passageiros que nao viajam com ele."""
        r = self._como(self.u1).get(f"/api/driver/trips/{self.t2.id}/manifest/")
        self.assertIn(r.status_code, (403, 404), r.content)

    def test_nao_arranca_nem_encerra_a_viagem_do_outro(self):
        """O bloqueio esta em `start_trip_activity` e devolve 400, nao 403.

        O codigo e discutivel — 403 seria mais exacto — mas o que interessa e
        que a accao e RECUSADA e que a mensagem diz porque. Fixar aqui o 403
        seria inventar um requisito e obrigar a mexer no tratamento de erros da
        app sem ninguem ganhar nada.
        """
        for accao in ("start", "depart", "close"):
            r = self._como(self.u1).post(f"/api/driver/trips/{self.t2.id}/{accao}/")
            self.assertGreaterEqual(r.status_code, 400,
                                    f"{accao} na viagem do outro foi ACEITE")
            self.assertIn("alocada", r.content.decode().lower(),
                          f"{accao}: a recusa nao explica que a viagem nao e dele")

    def test_arranca_a_sua(self):
        """O outro lado: sem isto, nao havia como trabalhar."""
        r = self._como(self.u1).post(f"/api/driver/trips/{self.t1.id}/start/")
        self.assertEqual(r.status_code, 200, r.content)
