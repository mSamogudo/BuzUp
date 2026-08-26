"""Venda a dinheiro no balcao, com o bilhete a seguir por SMS.

Duas coisas distinguem o numerario de tudo o resto que o POS ja fazia:

1. Nao ha gateway. O passageiro paga em notas e a venda nasce liquidada — nao
   ha carteira a debitar nem PIN a esperar. Pedir confirmacao ao gateway poria
   o passageiro a receber um pedido de PIN por um pagamento que ja fez.

2. O dinheiro fica FISICAMENTE com o agente. Todas as outras formas de
   pagamento entram na conta da operadora; esta fica em notas na mao de alguem,
   e o fecho de caixa tem de dizer quanto. Somado as vendas de M-Pesa era
   impossivel saber a quem cobrar o que.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.agent_api.sales import SaleError, create_pos_sale
from apps.fares.models import FareProduct, FareRule
from apps.guest_checkouts.models import GuestCheckout
from apps.payments.models import CASH_PROVIDER, PaymentIntent
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Agent, Trip, Vehicle


class VendaANumerarioTests(TestCase):
    def setUp(self):
        User = get_user_model()
        u = User.objects.create_user(username="agc", email="agc@x.mz", password="x")
        self.agente = Agent.objects.create(user=u, full_name="Agente Balcao")

        self.origem = Stop.objects.create(code="N-A", name="Maputo", status="active")
        self.destino = Stop.objects.create(code="N-B", name="Xai-Xai", status="active")
        self.rota = Route.objects.create(
            code="RT-NUM", name="Numerario", status=Route.Status.ACTIVE,
            service_type="urban")
        for i, p in enumerate((self.origem, self.destino)):
            RouteStop.objects.create(route=self.rota, stop=p, sequence=i,
                                     direction=RouteStop.Direction.OUTBOUND)
        prod = FareProduct.objects.create(
            name="Avulso", product_type=FareProduct.ProductType.SINGLE_TRIP)
        FareRule.objects.create(fare_product=prod, route=self.rota,
                                calculation_method=FareRule.CalculationMethod.FIXED,
                                fixed_amount=Decimal("250.00"))
        v = Vehicle.objects.create(registration="NU-01-AA", seated_capacity=30)
        self.viagem = Trip.objects.create(
            route=self.rota, vehicle=v, status=Trip.Status.BOARDING,
            direction=Trip.Direction.OUTBOUND,
            planned_departure_at=timezone.now() + timedelta(hours=1))

    def _vender(self, metodo="cash", **extra):
        return create_pos_sale(
            agent=self.agente, device=None, trip_id=self.viagem.id, route_id=None,
            origin_stop_id=self.origem.id, destination_stop_id=self.destino.id,
            passenger_phone="841234567", payment_method=metodo,
            **{"quantity": 1, **extra},
        )

    # --- a venda nasce paga ----------------------------------------------

    def test_o_pagamento_nasce_confirmado_sem_gateway(self):
        _gc, pi = self._vender()
        self.assertEqual(pi.status, PaymentIntent.Status.CONFIRMED)
        self.assertEqual(pi.provider, CASH_PROVIDER)
        self.assertEqual(pi.channel, "POS_CASH")

    def test_o_bilhete_e_emitido_no_momento(self):
        """Nao se imprime nada: o bilhete existe e segue por SMS."""
        gc, _pi = self._vender()
        gc.refresh_from_db()
        self.assertEqual(gc.status, GuestCheckout.Status.ISSUED)
        self.assertEqual(gc.travel_passes.count(), 1)

    def test_o_bilhete_vai_por_sms_para_o_telefone_indicado(self):
        """O envio esta em `transaction.on_commit`, e ainda bem: um bilhete
        nao deve sair por SMS se a venda que o gerou for revertida."""
        from unittest.mock import patch

        with patch("apps.guest_checkouts.services.send_sms") as sms:
            with self.captureOnCommitCallbacks(execute=True):
                self._vender()
        self.assertTrue(sms.called, "o bilhete a dinheiro nao seguiu por SMS")
        destino = sms.call_args[0][0]
        self.assertIn("841234567", destino)

    def test_sem_telefone_nao_ha_como_entregar_o_bilhete(self):
        with self.assertRaises(SaleError):
            create_pos_sale(
                agent=self.agente, device=None, trip_id=self.viagem.id, route_id=None,
                origin_stop_id=self.origem.id, destination_stop_id=self.destino.id,
                passenger_phone="", payment_method="cash", quantity=1)

    # --- o dinheiro tem de ser contado a parte ---------------------------

    def test_o_fecho_de_caixa_diz_quanto_dinheiro_ha_para_entregar(self):
        from apps.trips.revenue import calculate_trip_revenue

        self._vender()                      # 250 em notas
        self._vender(metodo="mobile_money") # 250 por M-Pesa (fica pendente)
        r = calculate_trip_revenue(self.viagem)
        self.assertEqual(r["cash"]["revenue"], "250.00",
                         "o numerario tem de aparecer sozinho — e o que o agente entrega")
        self.assertEqual(r["cash"]["count"], 1)

    def test_o_numerario_nao_e_somado_duas_vezes_ao_total(self):
        """`cash` e um recorte do que ja esta em `guest_checkout`."""
        from apps.trips.revenue import calculate_trip_revenue

        self._vender()
        r = calculate_trip_revenue(self.viagem)
        self.assertEqual(r["guest_checkout"]["revenue"], "250.00")
        self.assertEqual(r["cash"]["revenue"], "250.00")
        self.assertEqual(r["total_revenue"], "250.00")

    def test_sem_vendas_a_dinheiro_o_recorte_e_zero(self):
        from apps.trips.revenue import calculate_trip_revenue

        r = calculate_trip_revenue(self.viagem)
        self.assertEqual(r["cash"]["revenue"], "0.00")
        self.assertEqual(r["cash"]["count"], 0)

    # --- o lugar nao pode ficar preso ------------------------------------

    def test_a_lotacao_e_respeitada(self):
        """A venda a dinheiro conta para a lotacao como qualquer outra."""
        from apps.guest_checkouts.capacity import seats_taken_bulk

        self._vender(quantity=3)
        self.assertEqual(seats_taken_bulk([self.viagem]).get(self.viagem.id), 3)


class VendaANumerarioPelaApiTests(TestCase):
    """A venda a dinheiro pelo ENDPOINT, com o corpo que a app manda.

    Os testes de cima chamam `create_pos_sale` directamente e passavam todos —
    mas a venda falhava no terminal com 400. A app so enviava `passenger_phone`
    quando o pagamento era mobile money; a numerario mandava `null`, a chave
    saia do corpo, e o serializer recusava. Nenhum teste de servico podia
    apanhar isso, porque o problema estava na FORMA DO PEDIDO.

    E por isso que este passa pelo HTTP.
    """

    def setUp(self):
        from rest_framework.test import APIClient
        from apps.routes.models import RouteStop

        User = get_user_model()
        u = User.objects.create_user(username="apic", email="apic@x.mz", password="x")
        Agent.objects.create(user=u, full_name="Agente", status=Agent.Status.ACTIVE)

        self.origem = Stop.objects.create(code="AP-A", name="Maputo", status="active")
        self.destino = Stop.objects.create(code="AP-B", name="Xai-Xai", status="active")
        self.rota = Route.objects.create(code="RT-API", name="Api", status=Route.Status.ACTIVE,
                                         service_type="urban")
        for i, p in enumerate((self.origem, self.destino)):
            RouteStop.objects.create(route=self.rota, stop=p, sequence=i, direction="outbound")
        prod = FareProduct.objects.create(
            name="Avulso", product_type=FareProduct.ProductType.SINGLE_TRIP)
        FareRule.objects.create(fare_product=prod, route=self.rota,
                                calculation_method=FareRule.CalculationMethod.FIXED,
                                fixed_amount=Decimal("250.00"))
        v = Vehicle.objects.create(registration="AP-01-AA", seated_capacity=30)
        self.viagem = Trip.objects.create(
            route=self.rota, vehicle=v, status=Trip.Status.BOARDING,
            direction=Trip.Direction.OUTBOUND,
            planned_departure_at=timezone.now() + timedelta(hours=1))

        self.client = APIClient()
        self.client.force_authenticate(u)

    def _post(self, corpo):
        return self.client.post("/api/agent/sales/", corpo, format="json")

    def test_o_corpo_que_a_app_manda_conclui_a_venda(self):
        r = self._post({
            "trip_id": self.viagem.id,
            "origin_stop_id": self.origem.id,
            "destination_stop_id": self.destino.id,
            "payment_method": "cash",
            "passenger_phone": "841234567",
            "quantity": 1,
        })
        self.assertEqual(r.status_code, 201, r.content)
        corpo = r.json()
        self.assertEqual(corpo["payment"]["status"], "confirmed")
        self.assertEqual(corpo["payment"]["provider"], CASH_PROVIDER)
        self.assertEqual(len(corpo["tickets"]), 1, "o bilhete tem de vir na resposta")

    def test_sem_telefone_a_recusa_diz_o_que_falta(self):
        """Era este 400 que o terminal levava — e a mensagem tem de explicar."""
        r = self._post({
            "trip_id": self.viagem.id,
            "origin_stop_id": self.origem.id,
            "destination_stop_id": self.destino.id,
            "payment_method": "cash",
            "quantity": 1,
        })
        self.assertEqual(r.status_code, 400)
        self.assertIn("SMS", str(r.content))

    def test_a_numerario_nao_se_pede_pagamento_ao_gateway(self):
        """O dinheiro ja esta na mao do agente: pedir PIN ao passageiro por um
        pagamento que ele acabou de fazer em notas seria absurdo."""
        from unittest.mock import patch

        with patch("apps.agent_api.views.request_payment") as pedido:
            r = self._post({
                "trip_id": self.viagem.id,
                "origin_stop_id": self.origem.id,
                "destination_stop_id": self.destino.id,
                "payment_method": "cash",
                "passenger_phone": "841234567",
                "quantity": 1,
            })
        self.assertEqual(r.status_code, 201, r.content)
        self.assertFalse(pedido.called)
