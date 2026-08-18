"""Aceitar os Termos e Condicoes para comprar.

Uma caixa que so existe no browser e decoracao: um pedido feito por fora dele
compraria na mesma. A verificacao vive no servidor, e o que fica guardado nao e
um "sim" — e a VERSAO dos termos que estava publicada nesse dia.

Sem a versao sabia-se que o passageiro aceitou "os termos", mas nao QUAIS. Uns
termos alterados na semana seguinte passariam a valer para tras, e numa disputa
sobre um cancelamento ninguem conseguiria dizer o que ele leu.
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
from apps.guest_checkouts.models import GuestCheckout
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Trip, Vehicle

TERMOS = [{"title": "Bilhetes", "items": ["Os bilhetes nao sao transferiveis."]}]


class AceitacaoDosTermosTests(TestCase):
    def setUp(self):
        self.client = APIClient()
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

    def publicar_termos(self, versao="2026-08"):
        marca = BrandingSettings.load()
        marca.terms_sections = TERMOS
        marca.terms_version = versao
        marca.terms_updated_at = timezone.now()
        marca.save()
        return marca

    def comprar(self, **extra):
        payload = {
            "payer_phone": "841234567",
            "emergency_contact_name": "Maria", "emergency_contact_phone": "849999999",
            "route_code": self.rota.code,
            "origin_stop": self.a.name, "destination_stop": self.b.name,
            "origin_stop_id": self.a.id, "destination_stop_id": self.b.id,
            "trip_id": self.viagem.id, "quantity": 1,
            "passengers": [{"name": "Antonio", "document_number": "110100234567B", "seat": "1A"}],
            **extra,
        }
        return self.client.post(reverse("guest-checkout-create"), payload,
                                format="json", secure=True)

    # --- com termos publicados -------------------------------------------

    def test_sem_aceitar_nao_se_compra(self):
        self.publicar_termos()
        r = self.comprar()
        self.assertEqual(r.status_code, 400, r.data)
        self.assertIn("Termos", r.data["detail"])
        self.assertEqual(GuestCheckout.objects.count(), 0)

    def test_aceitar_a_falso_e_o_mesmo_que_nao_aceitar(self):
        self.publicar_termos()
        self.assertEqual(self.comprar(accept_terms=False).status_code, 400)

    def test_ao_aceitar_fica_registado_o_que_foi_aceite(self):
        self.publicar_termos(versao="2026-08")
        r = self.comprar(accept_terms=True, terms_version="2026-08")
        self.assertEqual(r.status_code, 201, r.data)

        gc = GuestCheckout.objects.get()
        self.assertIsNotNone(gc.terms_accepted_at)
        self.assertEqual(gc.terms_version, "2026-08")

    def test_versao_desactualizada_e_recusada(self):
        """A pagina esteve aberta desde antes de os termos mudarem: o
        passageiro leu outra coisa."""
        self.publicar_termos(versao="2026-09")
        r = self.comprar(accept_terms=True, terms_version="2026-08")
        self.assertEqual(r.status_code, 409, r.data)
        self.assertIn("actualizados", r.data["detail"])
        self.assertEqual(GuestCheckout.objects.count(), 0)

    def test_sem_versao_enviada_aceita_a_publicada(self):
        """Cliente antigo, que ainda nao manda a versao: nao se trava a venda,
        guarda-se a versao em vigor."""
        self.publicar_termos(versao="2026-08")
        r = self.comprar(accept_terms=True)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(GuestCheckout.objects.get().terms_version, "2026-08")

    # --- sem termos publicados -------------------------------------------

    def test_sem_termos_publicados_a_compra_segue(self):
        """Nao se inventa uma barreira onde o operador nao pos nenhuma.

        (Os termos da TPM-TUR vem semeados por migracao, por isso aqui
        apagam-se de proposito para representar um operador que ainda nao
        publicou nenhuns.)
        """
        marca = BrandingSettings.load()
        marca.terms_sections = []
        marca.terms_version = ""
        marca.save()

        r = self.comprar()
        self.assertEqual(r.status_code, 201, r.data)
        gc = GuestCheckout.objects.get()
        self.assertIsNone(gc.terms_accepted_at)
        self.assertEqual(gc.terms_version, "")


class TermosNoEndpointPublicoTests(TestCase):
    def test_os_termos_sao_legiveis_sem_sessao(self):
        """Quem compra tem de os poder ler ANTES de aceitar."""
        marca = BrandingSettings.load()
        marca.terms_sections = TERMOS
        marca.terms_version = "2026-08"
        marca.company_name = "TPM-TUR (PTY)"
        marca.support_email = "info@tpmtur.co.mz"
        marca.save()

        r = self.client.get("/api/branding/", secure=True)
        self.assertEqual(r.status_code, 200, r.content)
        corpo = r.json()
        self.assertEqual(corpo["terms_version"], "2026-08")
        self.assertEqual(corpo["terms_sections"][0]["title"], "Bilhetes")
        self.assertEqual(corpo["company_name"], "TPM-TUR (PTY)")
        self.assertEqual(corpo["support_email"], "info@tpmtur.co.mz")
