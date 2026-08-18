"""Comprar ida e volta numa so compra.

O cliente permite que o passageiro compre o regresso na mesma altura. E a mesma
compra — um pagamento, um comprovativo — mas sao DUAS viagens: dois autocarros,
duas lotacoes, dois lugares, dois manifestos de bordo.

Por isso a volta e uma partida propria e nao um campo de data no bilhete: o
autocarro do regresso tem a sua lotacao e a sua lista de quem vai a bordo.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.fares.models import FareProduct, FareRule
from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Trip, Vehicle


class IdaEVoltaTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.rota = Route.objects.create(
            code="RT-INT", name="Maputo x Nelspruit",
            service_type=Route.ServiceType.INTERNATIONAL, status=Route.Status.ACTIVE)
        self.a = Stop.objects.create(code="ST-A", name="Polana", status="active")
        self.b = Stop.objects.create(code="ST-B", name="Ilanga", status="active")
        RouteStop.objects.create(route=self.rota, stop=self.a, sequence=1, direction="outbound")
        RouteStop.objects.create(route=self.rota, stop=self.b, sequence=2, direction="outbound")
        RouteStop.objects.create(route=self.rota, stop=self.b, sequence=1, direction="inbound")
        RouteStop.objects.create(route=self.rota, stop=self.a, sequence=2, direction="inbound")

        produto = FareProduct.objects.create(
            name="Avulso", product_type="single_trip", status="active")
        FareRule.objects.create(
            fare_product=produto, route=self.rota,
            calculation_method=FareRule.CalculationMethod.FIXED,
            fixed_amount=Decimal("1650.00"))

        self.viatura = Vehicle.objects.create(registration="AAA-01-MP", seated_capacity=40)
        self.ida = Trip.objects.create(
            route=self.rota, vehicle=self.viatura, status=Trip.Status.SCHEDULED,
            planned_departure_at=timezone.now() + timedelta(days=1))
        self.volta = Trip.objects.create(
            route=self.rota, vehicle=self.viatura, status=Trip.Status.SCHEDULED,
            planned_departure_at=timezone.now() + timedelta(days=5))

    def comprar(self, passageiros=None, **extra):
        payload = {
            "payer_phone": "841234567",
            # Obrigatorio nas rotas com manifesto de bordo.
            "emergency_contact_name": "Maria Joaquim",
            "emergency_contact_phone": "849999999",
            "route_code": self.rota.code,
            "origin_stop": self.a.name, "destination_stop": self.b.name,
            "origin_stop_id": self.a.id, "destination_stop_id": self.b.id,
            "trip_id": self.ida.id,
            "quantity": len(passageiros or [{}]) or 1,
            "passengers": passageiros or [
                {"name": "Antonio Joaquim", "document_number": "110100234567B",
                 "seat": "1A", "return_seat": "5B"}],
            **extra,
        }
        return self.client.post(reverse("guest-checkout-create"), payload,
                                format="json", secure=True)

    # --- o caminho feliz -------------------------------------------------

    def test_uma_compra_gera_dois_bilhetes(self):
        r = self.comprar(return_trip_id=self.volta.id)
        self.assertEqual(r.status_code, 201, r.data)

        gc = GuestCheckout.objects.get()
        self.assertTrue(gc.is_round_trip)
        self.assertEqual(gc.return_trip_id, self.volta.id)
        # Um pagamento cobre os dois trocos.
        self.assertEqual(gc.total_amount, Decimal("3300.00"))
        self.assertEqual(r.data["total_amount"], "3300.00")

        bilhetes = list(DigitalTravelPass.objects.order_by("leg"))
        self.assertEqual(len(bilhetes), 2)

    def test_a_volta_e_o_percurso_ao_contrario(self):
        self.comprar(return_trip_id=self.volta.id)
        volta = DigitalTravelPass.objects.get(leg=DigitalTravelPass.Leg.RETURN)
        ida = DigitalTravelPass.objects.get(leg=DigitalTravelPass.Leg.OUTBOUND)

        self.assertEqual(ida.origin_stop, "Polana")
        self.assertEqual(ida.destination_stop, "Ilanga")
        self.assertEqual(volta.origin_stop, "Ilanga")
        self.assertEqual(volta.destination_stop, "Polana")

    def test_cada_troco_leva_o_seu_lugar_e_a_sua_partida(self):
        """O lugar da volta e outro lugar, noutro autocarro."""
        self.comprar(return_trip_id=self.volta.id)
        ida = DigitalTravelPass.objects.get(leg=DigitalTravelPass.Leg.OUTBOUND)
        volta = DigitalTravelPass.objects.get(leg=DigitalTravelPass.Leg.RETURN)

        self.assertEqual(ida.seat_number, "1A")
        self.assertEqual(ida.trip_id, self.ida.id)
        self.assertEqual(volta.seat_number, "5B")
        self.assertEqual(volta.trip_id, self.volta.id)

    def test_os_bilhetes_sao_distinguiveis_um_do_outro(self):
        self.comprar(return_trip_id=self.volta.id)
        codigos = {t.short_code for t in DigitalTravelPass.objects.all()}
        self.assertEqual(len(codigos), 2, "dois bilhetes com o mesmo codigo curto")

    def test_ida_sozinha_continua_a_funcionar(self):
        r = self.comprar()
        self.assertEqual(r.status_code, 201, r.data)
        gc = GuestCheckout.objects.get()
        self.assertFalse(gc.is_round_trip)
        self.assertEqual(gc.total_amount, Decimal("1650.00"))
        self.assertEqual(DigitalTravelPass.objects.count(), 1)

    def test_duas_pessoas_ida_e_volta_dao_quatro_bilhetes(self):
        r = self.comprar(return_trip_id=self.volta.id, passageiros=[
            {"name": "Ana", "document_number": "110100111111A", "seat": "1A", "return_seat": "5A"},
            {"name": "Beto", "document_number": "110100222222B", "seat": "1B", "return_seat": "5B"},
        ])
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(DigitalTravelPass.objects.count(), 4)
        self.assertEqual(GuestCheckout.objects.get().total_amount, Decimal("6600.00"))
        self.assertEqual(len({t.short_code for t in DigitalTravelPass.objects.all()}), 4)

    # --- o que tem de ser recusado ---------------------------------------

    def test_lugar_de_volta_ja_ocupado(self):
        self.comprar(return_trip_id=self.volta.id)
        r = self.comprar(return_trip_id=self.volta.id, passageiros=[
            {"name": "Outro", "document_number": "110100333333C", "seat": "2A", "return_seat": "5B"}])
        self.assertEqual(r.status_code, 409, r.data)
        self.assertIn("volta", r.data["detail"].lower())

    def test_sem_lugar_de_volta_numa_rota_com_lugar_marcado(self):
        r = self.comprar(return_trip_id=self.volta.id, passageiros=[
            {"name": "Ana", "document_number": "110100111111A", "seat": "1A"}])
        self.assertEqual(r.status_code, 400, r.data)
        self.assertIn("lugar de volta", r.data["detail"].lower())

    def test_a_volta_nao_pode_partir_antes_da_ida(self):
        antes = Trip.objects.create(
            route=self.rota, vehicle=self.viatura, status=Trip.Status.SCHEDULED,
            planned_departure_at=timezone.now() + timedelta(hours=2))
        r = self.comprar(return_trip_id=antes.id)
        self.assertEqual(r.status_code, 400, r.data)
        self.assertIn("depois da ida", r.data["detail"])

    def test_a_volta_nao_pode_ser_a_mesma_partida(self):
        r = self.comprar(return_trip_id=self.ida.id)
        self.assertEqual(r.status_code, 400, r.data)

    def test_volta_noutra_rota_e_recusada(self):
        outra = Route.objects.create(code="RT-OUT", name="Outra", status=Route.Status.ACTIVE)
        alheia = Trip.objects.create(
            route=outra, vehicle=self.viatura, status=Trip.Status.SCHEDULED,
            planned_departure_at=timezone.now() + timedelta(days=6))
        r = self.comprar(return_trip_id=alheia.id)
        self.assertEqual(r.status_code, 400, r.data)

    def test_volta_inexistente(self):
        r = self.comprar(return_trip_id=999999)
        self.assertEqual(r.status_code, 404, r.data)

    def test_nada_e_cobrado_quando_a_volta_e_recusada(self):
        """A compra e uma so: se a volta nao serve, nao se cobra a ida."""
        self.comprar(return_trip_id=999999)
        self.assertEqual(GuestCheckout.objects.count(), 0)
        self.assertEqual(DigitalTravelPass.objects.count(), 0)
