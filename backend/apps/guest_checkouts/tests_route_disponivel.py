"""Desactivar ou apagar uma rota tem de parar a venda das partidas dela.

Nao parava. Em staging, uma rota apagada — a duplicada da Maputo-Nelspruit —
continuava no site publico com 29 lugares disponiveis e o botao de compra
vivo, para uma partida de dois meses antes. Como o mesmo `sale_state` autoriza
o checkout, o passageiro nao era travado a meio: chegava a pagar uma viagem
numa rota que a operacao ja tinha dado como inexistente.

O portal ja escondia a rota da lista; era so a lista de partidas que nao
olhava para o estado dela.
"""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.fares.models import FareProduct, FareRule
from apps.guest_checkouts.capacity import SeatsUnavailable, lock_trip_for_sale, sale_state
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Driver, Trip, Vehicle


class RotaIndisponivelBase(TestCase):
    def setUp(self):
        self.rota = Route.objects.create(
            code="R-DISP", name="Teste Disponibilidade", status=Route.Status.ACTIVE,
        )
        self.origem = Stop.objects.create(code="SD-A", name="Paragem A", status="active")
        self.destino = Stop.objects.create(code="SD-B", name="Paragem B", status="active")
        RouteStop.objects.create(route=self.rota, stop=self.origem, sequence=1, direction="outbound")
        RouteStop.objects.create(route=self.rota, stop=self.destino, sequence=2, direction="outbound")

        produto = FareProduct.objects.create(
            name="Avulso Disp", product_type="single_trip", status="active",
        )
        FareRule.objects.create(
            fare_product=produto, route=self.rota,
            calculation_method=FareRule.CalculationMethod.FIXED,
            fixed_amount=Decimal("100.00"),
        )
        self.viatura = Vehicle.objects.create(registration="DP-01-MP", seated_capacity=30)
        self.motorista = Driver.objects.create(full_name="Motorista Disp")
        self.viagem = Trip.objects.create(
            route=self.rota, vehicle=self.viatura, driver=self.motorista,
            status=Trip.Status.BOARDING,
            planned_departure_at=timezone.now() + timezone.timedelta(hours=2),
        )

    def _recarregar(self):
        return Trip.objects.select_related("route", "vehicle").get(pk=self.viagem.pk)


class VendaBloqueadaTests(RotaIndisponivelBase):
    def test_rota_activa_vende(self):
        pode, motivo = sale_state(self._recarregar())
        self.assertTrue(pode, motivo)

    def test_rota_desactivada_nao_vende(self):
        self.rota.status = Route.Status.INACTIVE
        self.rota.save(update_fields=["status", "updated_at"])
        pode, motivo = sale_state(self._recarregar())
        self.assertFalse(pode)
        self.assertIn("rota", motivo.lower())

    def test_rota_suspensa_nao_vende(self):
        self.rota.status = Route.Status.SUSPENDED
        self.rota.save(update_fields=["status", "updated_at"])
        pode, _ = sale_state(self._recarregar())
        self.assertFalse(pode)

    def test_rota_apagada_nao_vende(self):
        self.rota.delete()  # soft delete: a linha fica, com `deleted_at`
        pode, motivo = sale_state(self._recarregar())
        self.assertFalse(pode, "uma rota apagada continuava a vender bilhetes")
        self.assertIn("rota", motivo.lower())

    def test_compra_e_recusada_e_nao_so_escondida(self):
        """Esconder o botao nao chega: quem tiver o link continua a poder pagar."""
        from django.db import transaction

        self.rota.delete()
        with self.assertRaises(SeatsUnavailable):
            with transaction.atomic():
                lock_trip_for_sale(self._recarregar(), 1)


class ListagemPublicaTests(RotaIndisponivelBase):
    def test_partida_de_rota_apagada_nao_aparece_a_venda(self):
        url = f"/api/public/trips/?origin={self.origem.id}&destination={self.destino.id}"
        antes = self.client.get(url, secure=True).json()["trips"]
        self.assertTrue(
            any(t["trip_id"] == self.viagem.id and t["on_sale"] for t in antes),
            "a partida devia estar a venda antes de a rota ser apagada",
        )

        self.rota.delete()

        depois = self.client.get(url, secure=True).json()["trips"]
        vendaveis = [t for t in depois if t["trip_id"] == self.viagem.id and t["on_sale"]]
        self.assertEqual(vendaveis, [], "a partida de uma rota apagada ficou a venda")
