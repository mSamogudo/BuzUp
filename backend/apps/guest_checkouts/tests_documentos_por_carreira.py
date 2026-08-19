"""Que documento serve em cada carreira.

Numa rota INTERNACIONAL atravessa-se uma fronteira, e a fronteira so aceita
passaporte. Oferecer BI, DIRE ou cedula na compra e deixar o passageiro
escolher um documento com que nao vai passar — e ele so descobre em Ressano
Garcia, com o autocarro a espera e sem direito a reembolso (ver a seccao da
bagagem dos termos da TPM-TUR).

Numa interprovincial viaja-se dentro de Mocambique e qualquer identificacao
serve. Numa urbana nao se pede documento nenhum.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.branding.models import BrandingSettings
from apps.fares.models import FareProduct, FareRule
from apps.guest_checkouts.documents import (
    DocumentError,
    allowed_document_types,
    public_rules,
    validate_document_for,
)
from apps.guest_checkouts.models import GuestCheckout
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Trip, Vehicle


class RegrasPorCarreiraTests(TestCase):
    def test_internacional_so_aceita_passaporte(self):
        self.assertEqual(allowed_document_types("international"), ("passport",))

    def test_interprovincial_aceita_qualquer_identificacao(self):
        permitidos = allowed_document_types("interprovincial")
        for tipo in ("bi", "passport", "dire", "cedula", "other"):
            self.assertIn(tipo, permitidos)

    def test_sem_carreira_indicada_devolve_tudo(self):
        self.assertIn("bi", allowed_document_types(None))

    def test_bi_e_recusado_numa_internacional(self):
        with self.assertRaises(DocumentError) as ctx:
            validate_document_for("international", "bi", "110100123456A")
        self.assertIn("Passaporte", str(ctx.exception))

    def test_passaporte_passa_numa_internacional(self):
        self.assertEqual(
            validate_document_for("international", "passport", "ab123456"), "AB123456")

    def test_bi_passa_numa_interprovincial(self):
        self.assertEqual(
            validate_document_for("interprovincial", "bi", "1101 0012 3456 A"),
            "110100123456A")

    def test_a_forma_continua_a_ser_validada(self):
        """Ser do tipo certo nao chega: o numero tem de ter a forma certa."""
        with self.assertRaises(DocumentError):
            validate_document_for("international", "passport", "AB")


class ListaPublicaTests(TestCase):
    def test_endpoint_filtra_pela_carreira(self):
        r = self.client.get(reverse("public-document-types"),
                            {"service_type": "international"}, secure=True)
        self.assertEqual(r.status_code, 200, r.content)
        tipos = [d["value"] for d in r.json()["document_types"]]
        self.assertEqual(tipos, ["passport"])

    def test_endpoint_sem_carreira_devolve_todos(self):
        r = self.client.get(reverse("public-document-types"), secure=True)
        tipos = [d["value"] for d in r.json()["document_types"]]
        self.assertIn("bi", tipos)
        self.assertIn("passport", tipos)

    def test_as_regras_de_forma_acompanham(self):
        so_passaporte = public_rules("international")
        self.assertEqual(len(so_passaporte), 1)
        self.assertEqual(so_passaporte[0]["max_length"], 9)


class CompraInternacionalTests(TestCase):
    """O servidor recusa, nao apenas o formulario esconde."""

    def setUp(self):
        self.client = APIClient()
        marca = BrandingSettings.load()
        marca.terms_sections = [{"title": "Bilhetes", "items": ["Nao transferiveis."]}]
        marca.terms_version = "t1"
        marca.save()

        self.rota = Route.objects.create(
            code="RT-INT", name="Maputo x Nelspruit",
            service_type=Route.ServiceType.INTERNATIONAL, status=Route.Status.ACTIVE)
        self.a = Stop.objects.create(code="ST-A", name="Polana", status="active")
        self.b = Stop.objects.create(code="ST-B", name="Ilanga", status="active")
        RouteStop.objects.create(route=self.rota, stop=self.a, sequence=1, direction="outbound")
        RouteStop.objects.create(route=self.rota, stop=self.b, sequence=2, direction="outbound")
        produto = FareProduct.objects.create(
            name="Avulso", product_type="single_trip", status="active")
        FareRule.objects.create(
            fare_product=produto, route=self.rota,
            calculation_method=FareRule.CalculationMethod.FIXED,
            fixed_amount=Decimal("1650.00"))
        viatura = Vehicle.objects.create(registration="AAA-01-MP", seated_capacity=40)
        self.viagem = Trip.objects.create(
            route=self.rota, vehicle=viatura, status=Trip.Status.SCHEDULED,
            planned_departure_at=timezone.now() + timedelta(days=1))

    def comprar(self, passageiro):
        return self.client.post(reverse("guest-checkout-create"), {
            "payer_phone": "841234567",
            "emergency_contact_name": "Maria", "emergency_contact_phone": "849999999",
            "route_code": self.rota.code,
            "origin_stop": self.a.name, "destination_stop": self.b.name,
            "origin_stop_id": self.a.id, "destination_stop_id": self.b.id,
            "trip_id": self.viagem.id, "quantity": 1,
            "accept_terms": True, "terms_version": "t1",
            "passengers": [passageiro],
        }, format="json", secure=True)

    def test_compra_com_bi_e_recusada(self):
        r = self.comprar({"name": "Antonio", "document_type": "bi",
                          "document_number": "110100234567B", "seat": "1A"})
        self.assertEqual(r.status_code, 400, r.data)
        self.assertIn("Passaporte", r.data["detail"])
        self.assertEqual(GuestCheckout.objects.count(), 0)

    def test_compra_com_passaporte_passa(self):
        r = self.comprar({"name": "Antonio", "document_type": "passport",
                          "document_number": "AB123456", "seat": "1A"})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(GuestCheckout.objects.count(), 1)
