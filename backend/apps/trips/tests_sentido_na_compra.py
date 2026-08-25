"""A pesquisa filtra; a COMPRA e que compromete.

O sentido foi posto na pesquisa, e a pesquisa deixou de misturar ida com volta.
Mas a compra recebe um `trip_id` e so verifica que o par origem-destino forma
segmento na ROTA — nao que a partida escolhida va para esse lado.

Basta uma pagina aberta ha uma hora, um "voltar" do browser, uma segunda
tentativa de pagamento, ou o QR do autocarro (que lista as partidas do veiculo,
e o mesmo veiculo faz ida de manha e volta a tarde) para o passageiro comprar
lugar no autocarro que vai para o lado contrario.

Um bilhete e um compromisso. A guarda tem de estar onde se compromete.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.fares.models import FareProduct, FareRule
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Trip, Vehicle


class SentidoNaCompraTests(TestCase):
    def setUp(self):
        self.rota = Route.objects.create(
            code="RT-CMP", name="Compra", status=Route.Status.ACTIVE,
            service_type="interprovincial")
        nomes = ["Maputo", "Meio", "Nelspruit"]
        self.p = {n: Stop.objects.create(code=f"C-{n[:3].upper()}", name=n, status="active")
                  for n in nomes}
        for i, n in enumerate(nomes):
            RouteStop.objects.create(route=self.rota, stop=self.p[n], sequence=i,
                                     direction=RouteStop.Direction.OUTBOUND)
        for i, n in enumerate(reversed(nomes)):
            RouteStop.objects.create(route=self.rota, stop=self.p[n], sequence=i,
                                     direction=RouteStop.Direction.INBOUND)
        prod = FareProduct.objects.create(
            name="Avulso", product_type=FareProduct.ProductType.SINGLE_TRIP)
        FareRule.objects.create(fare_product=prod, route=self.rota,
                                calculation_method=FareRule.CalculationMethod.FIXED,
                                fixed_amount=Decimal("1500.00"))
        v = Vehicle.objects.create(registration="CM-01-AA", seated_capacity=30)
        amanha = timezone.now() + timedelta(days=1)
        self.ida = Trip.objects.create(
            route=self.rota, vehicle=v, status=Trip.Status.SCHEDULED,
            direction=Trip.Direction.OUTBOUND, planned_departure_at=amanha)
        self.volta = Trip.objects.create(
            route=self.rota, vehicle=v, status=Trip.Status.SCHEDULED,
            direction=Trip.Direction.INBOUND,
            planned_departure_at=amanha + timedelta(hours=8))

    def _comprar(self, trip, origem, destino, **extra):
        corpo = {
            "trip_id": trip.id,
            "origin_stop": origem,
            "destination_stop": destino,
            "origin_stop_id": self.p[origem].id,
            "destination_stop_id": self.p[destino].id,
            "payer_phone": "841234567",
            "quantity": 1,
            "accept_terms": True,
            "emergency_contact_name": "Familiar",
            "emergency_contact_phone": "849999999",
            "passengers": [{"name": "Ana Cossa", "document_type": "bi",
                            "document_number": "110100100100A", "seat": "1A"}],
            **extra,
        }
        return self.client.post("/api/guest-checkouts/", corpo,
                                content_type="application/json")

    # --- o buraco ---------------------------------------------------------

    def test_nao_se_compra_a_volta_para_um_percurso_de_ida(self):
        """O passageiro pede Maputo->Nelspruit mas manda a partida da VOLTA."""
        r = self._comprar(self.volta, "Maputo", "Nelspruit")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("sentido", str(r.content).lower())

    def test_nao_se_compra_a_ida_para_um_percurso_de_volta(self):
        r = self._comprar(self.ida, "Nelspruit", "Maputo")
        self.assertEqual(r.status_code, 400, r.content)

    def test_o_sentido_certo_compra_se(self):
        r = self._comprar(self.ida, "Maputo", "Nelspruit")
        self.assertNotEqual(r.status_code, 400, r.content)

    def test_partida_sem_sentido_declarado_continua_a_vender(self):
        """Nao se pode tirar do ar bilhetes que hoje se vendem."""
        v = Vehicle.objects.create(registration="CM-02-AA", seated_capacity=30)
        antiga = Trip.objects.create(
            route=self.rota, vehicle=v, status=Trip.Status.SCHEDULED,
            direction="", planned_departure_at=timezone.now() + timedelta(days=2))
        r = self._comprar(antiga, "Maputo", "Nelspruit")
        self.assertNotEqual(r.status_code, 400, r.content)

    # --- ida e volta ------------------------------------------------------

    def test_a_volta_nao_pode_ser_outra_ida(self):
        """Comprava-se "ida e volta" com dois bilhetes para o mesmo lado."""
        v = Vehicle.objects.create(registration="CM-03-AA", seated_capacity=30)
        outra_ida = Trip.objects.create(
            route=self.rota, vehicle=v, status=Trip.Status.SCHEDULED,
            direction=Trip.Direction.OUTBOUND,
            planned_departure_at=timezone.now() + timedelta(days=2))
        r = self._comprar(self.ida, "Maputo", "Nelspruit",
                          return_trip_id=outra_ida.id)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("sentido", str(r.content).lower())
