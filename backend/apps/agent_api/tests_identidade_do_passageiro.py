"""Bilhete vendido ao balcao tem de sair com nome e documento.

O defeito reportado: "para viagens internacionais nao estamos solicitando o
nome nem o passaporte do passageiro". O portal publico ja pedia; a venda no POS
nao pedia nada — e e no balcao que o passageiro esta mesmo a frente do agente,
com o documento na mao. O bilhete saia anonimo, o manifesto de bordo saia sem
nomes, e na fronteira nao havia nada para conferir.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.agent_api.sales import SaleError, create_pos_sale
from apps.fares.models import FareProduct, FareRule
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Agent, Trip, Vehicle


class IdentidadeDoPassageiroTests(TestCase):
    def setUp(self):
        User = get_user_model()
        u = User.objects.create_user(username="ag", email="ag@x.mz", password="x")
        self.agente = Agent.objects.create(user=u, full_name="Agente")

        self.origem = Stop.objects.create(code="S-POL", name="Polana", status="active")
        self.destino = Stop.objects.create(code="S-ILA", name="Ilanga", status="active")

    def _rota(self, service_type):
        r = Route.objects.create(
            code=f"RT-{service_type[:4].upper()}", name="Teste",
            status=Route.Status.ACTIVE, service_type=service_type)
        for i, p in enumerate((self.origem, self.destino)):
            RouteStop.objects.create(route=r, stop=p, sequence=i,
                                     direction=RouteStop.Direction.OUTBOUND)
        produto = FareProduct.objects.create(
            name=f"Avulso {service_type}", product_type=FareProduct.ProductType.SINGLE_TRIP)
        FareRule.objects.create(
            fare_product=produto, route=r,
            calculation_method=FareRule.CalculationMethod.FIXED,
            fixed_amount=Decimal("1500.00"))
        v = Vehicle.objects.create(registration=f"MP-{service_type[:2].upper()}-01",
                                   seated_capacity=30)
        t = Trip.objects.create(route=r, vehicle=v, status=Trip.Status.BOARDING,
                                direction=Trip.Direction.OUTBOUND,
                                planned_departure_at=timezone.now() + timedelta(hours=2))
        return r, t

    def _vender(self, trip, **extra):
        return create_pos_sale(
            agent=self.agente, device=None, trip_id=trip.id, route_id=None,
            origin_stop_id=self.origem.id, destination_stop_id=self.destino.id,
            passenger_phone="841234567",
            emergency_contact_name="Familiar", emergency_contact_phone="849999999",
            **{"quantity": 1, **extra},
        )

    # --- o caso reportado ------------------------------------------------

    def test_internacional_sem_nome_e_recusada(self):
        _, t = self._rota("international")
        with self.assertRaises(SaleError) as ctx:
            self._vender(t, passengers=[{"document_type": "passport",
                                         "document_number": "AB123456"}])
        self.assertIn("nome", str(ctx.exception).lower())

    def test_internacional_sem_documento_e_recusada(self):
        _, t = self._rota("international")
        with self.assertRaises(SaleError) as ctx:
            self._vender(t, passengers=[{"name": "Ana Cossa"}])
        self.assertIn("documento", str(ctx.exception).lower())

    def test_internacional_so_aceita_passaporte(self):
        """Na fronteira o BI nao serve."""
        _, t = self._rota("international")
        with self.assertRaises(SaleError) as ctx:
            self._vender(t, passengers=[{"name": "Ana Cossa", "document_type": "bi",
                                         "document_number": "110100100100A"}])
        self.assertIn("passaporte", str(ctx.exception).lower())

    def test_internacional_com_passaporte_emite_bilhete_nominal(self):
        _, t = self._rota("international")
        gc, _pi = self._vender(t, passengers=[
            {"name": "Ana Cossa", "document_type": "passport", "document_number": "AB123456"}])
        pessoa = gc.passengers[0]
        self.assertEqual(pessoa["name"], "Ana Cossa")
        self.assertEqual(pessoa["document_type"], "passport")
        self.assertEqual(pessoa["document_number"], "AB123456")

    def test_documento_mal_formado_e_recusado(self):
        _, t = self._rota("international")
        with self.assertRaises(SaleError) as ctx:
            self._vender(t, passengers=[{"name": "Ana", "document_type": "passport",
                                         "document_number": "AB-123/456789012"}])
        self.assertIn("Ana", str(ctx.exception))

    # --- o urbano nao pode passar a pedir documento ----------------------

    def test_urbano_continua_a_vender_sem_identificacao(self):
        """Pedir o BI para apanhar o autocarro do bairro seria recolher dados
        sem necessidade — e travar uma compra que tem de ser rapida."""
        _, t = self._rota("urban")
        gc, _pi = create_pos_sale(
            agent=self.agente, device=None, trip_id=t.id, route_id=None,
            origin_stop_id=self.origem.id, destination_stop_id=self.destino.id,
            passenger_phone="841234567", quantity=1)
        self.assertIsNotNone(gc)

    # --- varios bilhetes na mesma venda ----------------------------------

    def test_cada_bilhete_leva_o_seu_passageiro(self):
        _, t = self._rota("international")
        gc, _pi = self._vender(t, quantity=2, passengers=[
            {"name": "Ana Cossa", "document_type": "passport", "document_number": "AB123456"},
            {"name": "Joao Sitoe", "document_type": "passport", "document_number": "CD654321"},
        ])
        self.assertEqual([p["name"] for p in gc.passengers], ["Ana Cossa", "Joao Sitoe"])

    def test_falta_o_segundo_passageiro(self):
        _, t = self._rota("international")
        with self.assertRaises(SaleError) as ctx:
            self._vender(t, quantity=2, passengers=[
                {"name": "Ana Cossa", "document_type": "passport", "document_number": "AB123456"}])
        self.assertIn("2", str(ctx.exception))


class TerminalAntigoTests(TestCase):
    """Um terminal que ainda nao tem os campos nao pode deixar de vender.

    Havia 7 terminais em servico quando esta regra nasceu, todos em 1.7.x.
    Exigir-lhes o documento nao tornava o bilhete nominal: parava a venda, com
    o passageiro a frente do agente e nada que ele pudesse fazer.
    """

    def setUp(self):
        from apps.devices.models import Device

        User = get_user_model()
        u = User.objects.create_user(username="ag2", email="ag2@x.mz", password="x")
        self.agente = Agent.objects.create(user=u, full_name="Agente")
        self.origem = Stop.objects.create(code="S-A", name="A", status="active")
        self.destino = Stop.objects.create(code="S-B", name="B", status="active")

        self.rota = Route.objects.create(
            code="RT-INT", name="Internacional", status=Route.Status.ACTIVE,
            service_type="international")
        for i, p in enumerate((self.origem, self.destino)):
            RouteStop.objects.create(route=self.rota, stop=p, sequence=i,
                                     direction=RouteStop.Direction.OUTBOUND)
        produto = FareProduct.objects.create(
            name="Avulso", product_type=FareProduct.ProductType.SINGLE_TRIP)
        FareRule.objects.create(
            fare_product=produto, route=self.rota,
            calculation_method=FareRule.CalculationMethod.FIXED,
            fixed_amount=Decimal("1500.00"))
        v = Vehicle.objects.create(registration="MP-IN-01", seated_capacity=30)
        self.viagem = Trip.objects.create(
            route=self.rota, vehicle=v, status=Trip.Status.BOARDING,
            direction=Trip.Direction.OUTBOUND,
            planned_departure_at=timezone.now() + timedelta(hours=2))
        self.Device = Device

    def _terminal(self, versao):
        return self.Device.objects.create(
            serial_number=f"SN-{versao}", app_version=versao,
            status=self.Device.Status.ACTIVE)

    def _vender(self, device, **extra):
        return create_pos_sale(
            agent=self.agente, device=device, trip_id=self.viagem.id, route_id=None,
            origin_stop_id=self.origem.id, destination_stop_id=self.destino.id,
            passenger_phone="841234567",
            emergency_contact_name="Familiar", emergency_contact_phone="849999999",
            **{"quantity": 1, **extra},
        )

    def test_terminal_antigo_continua_a_vender(self):
        gc, _pi = self._vender(self._terminal("1.7.3"))
        self.assertIsNotNone(gc)

    def test_terminal_actualizado_passa_a_exigir(self):
        with self.assertRaises(SaleError):
            self._vender(self._terminal("1.8.0"))

    def test_terminal_antigo_que_envia_identidade_e_validado(self):
        """Se envia, e para valer: um numero mal formado nao entra."""
        with self.assertRaises(SaleError):
            self._vender(self._terminal("1.7.3"), passengers=[
                {"name": "Ana", "document_type": "bi", "document_number": "123"}])

    def test_versao_ilegivel_nao_trava_a_venda(self):
        """Melhor um bilhete sem nome do que um terminal que nao vende."""
        gc, _pi = self._vender(self._terminal(""))
        self.assertIsNotNone(gc)
