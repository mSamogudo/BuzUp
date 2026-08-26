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
