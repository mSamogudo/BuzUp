"""Tentar outra vez depois de falhar o PIN.

O caso reportado: o passageiro escolhe o lugar 2C, o M-Pesa pede-lhe o PIN, ele
engana-se (ou nem chega a introduzi-lo). Tenta outra vez — e o sistema diz-lhe
que o 2C esta ocupado. Esta: por ele proprio, minutos antes.

Um lugar fica reservado enquanto a compra espera pagamento, e isso e certo:
sem a reserva, dois compradores levavam o mesmo lugar. So que ela vale contra
TERCEIROS, nunca contra quem a fez.
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
from apps.guest_checkouts.seatmap import occupied_seats
from apps.payments.models import PaymentIntent
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Trip, Vehicle

TELEFONE = "841234567"


class RetomarCompraTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        marca = BrandingSettings.load()
        marca.terms_sections = [{"title": "Bilhetes", "items": ["Nao transferiveis."]}]
        marca.terms_version = "t1"
        marca.save()

        self.rota = Route.objects.create(
            code="RT-RET", name="Retomar",
            service_type=Route.ServiceType.INTERNATIONAL, status=Route.Status.ACTIVE)
        self.a = Stop.objects.create(code="ST-RA", name="A", status="active")
        self.b = Stop.objects.create(code="ST-RB", name="B", status="active")
        RouteStop.objects.create(route=self.rota, stop=self.a, sequence=1, direction="outbound")
        RouteStop.objects.create(route=self.rota, stop=self.b, sequence=2, direction="outbound")
        produto = FareProduct.objects.create(
            name="Avulso", product_type="single_trip", status="active")
        FareRule.objects.create(
            fare_product=produto, route=self.rota,
            calculation_method=FareRule.CalculationMethod.FIXED,
            fixed_amount=Decimal("1000.00"))
        viatura = Vehicle.objects.create(registration="RET-01-MP", seated_capacity=20)
        self.viagem = Trip.objects.create(
            route=self.rota, vehicle=viatura, status=Trip.Status.SCHEDULED,
            planned_departure_at=timezone.now() + timedelta(days=1))

    def _reserva(self, telefone=TELEFONE, lugar="2C", estado_pagamento=None):
        """Uma tentativa anterior a segurar o lugar."""
        gc = GuestCheckout.objects.create(
            reference=f"GC-ANTERIOR-{telefone}-{lugar}", payer_phone=telefone,
            origin_stop="A", destination_stop="B", quantity=1,
            unit_amount=Decimal("1000.00"), total_amount=Decimal("1000.00"),
            status=GuestCheckout.Status.PAYMENT_PENDING,
            trip=self.viagem,
            passengers=[{"name": "Antonio", "seat": lugar}],
            expires_at=timezone.now() + timedelta(minutes=25),
        )
        if estado_pagamento:
            PaymentIntent.objects.create(
                reference=f"PAY-{gc.reference}", idempotency_key=f"i-{gc.reference}",
                purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
                amount=Decimal("1000.00"), payer_phone=telefone,
                provider="MPESA", status=estado_pagamento, guest_checkout=gc,
            )
        return gc

    def comprar(self, telefone=TELEFONE, lugar="2C"):
        return self.client.post(reverse("guest-checkout-create"), {
            "payer_phone": telefone,
            "emergency_contact_name": "Maria", "emergency_contact_phone": "849999999",
            "route_code": self.rota.code,
            "origin_stop": "A", "destination_stop": "B",
            "origin_stop_id": self.a.id, "destination_stop_id": self.b.id,
            "trip_id": self.viagem.id, "quantity": 1,
            "accept_terms": True, "terms_version": "t1",
            "passengers": [{"name": "Antonio", "document_type": "passport",
                            "document_number": "AB123456", "seat": lugar}],
        }, format="json", secure=True)

    # --- o caso reportado ------------------------------------------------

    def test_depois_do_pin_errado_pode_tentar_outra_vez(self):
        """O que falhou: PIN errado, e o lugar ficava preso pelo proprio."""
        anterior = self._reserva(estado_pagamento=PaymentIntent.Status.FAILED)
        self.assertIn("2C", occupied_seats(self.viagem))

        r = self.comprar()
        self.assertEqual(r.status_code, 201, r.data)

        anterior.refresh_from_db()
        self.assertEqual(anterior.status, GuestCheckout.Status.CANCELLED,
                         "a tentativa morta tinha de largar o lugar")

    def test_pagamento_expirado_tambem_liberta(self):
        self._reserva(estado_pagamento=PaymentIntent.Status.EXPIRED)
        self.assertEqual(self.comprar().status_code, 201)

    def test_pagamento_revertido_tambem_liberta(self):
        self._reserva(estado_pagamento=PaymentIntent.Status.REVERSED)
        self.assertEqual(self.comprar().status_code, 201)

    # --- o que NAO se pode libertar --------------------------------------

    def test_pagamento_ainda_vivo_nao_e_largado(self):
        """Largar seria abrir uma segunda cobranca pelo mesmo lugar.

        O passageiro pode estar a introduzir o PIN nesse momento. O que muda e
        a mensagem: em vez de "escolha outro lugar", diz-se-lhe que ja tem um
        pagamento a decorrer.
        """
        anterior = self._reserva(estado_pagamento=PaymentIntent.Status.PENDING)
        r = self.comprar()
        self.assertEqual(r.status_code, 409, r.data)
        self.assertIn("pagamento a decorrer", r.data["detail"].lower())
        self.assertEqual(r.data["checkout_reference"], anterior.reference)

        anterior.refresh_from_db()
        self.assertEqual(anterior.status, GuestCheckout.Status.PAYMENT_PENDING)

    def test_o_lugar_de_outra_pessoa_continua_ocupado(self):
        """A reserva vale contra terceiros — e a razao de ela existir."""
        self._reserva(telefone="849990000", estado_pagamento=PaymentIntent.Status.FAILED)
        r = self.comprar(telefone=TELEFONE)
        self.assertEqual(r.status_code, 409, r.data)
        self.assertIn("ocupado", r.data["detail"].lower())
        self.assertNotIn("pagamento a decorrer", r.data["detail"].lower())

    def test_uma_compra_ja_paga_nunca_e_largada(self):
        """Mesmo sendo do proprio: ela ja tem dinheiro atras."""
        gc = self._reserva(estado_pagamento=PaymentIntent.Status.CONFIRMED)
        gc.status = GuestCheckout.Status.PAID
        gc.save(update_fields=["status"])

        r = self.comprar()
        self.assertEqual(r.status_code, 409, r.data)
        gc.refresh_from_db()
        self.assertEqual(gc.status, GuestCheckout.Status.PAID)

    def test_o_mesmo_numero_com_e_sem_indicativo_e_a_mesma_pessoa(self):
        """O telefone chega ora com 258 a frente ora sem."""
        anterior = self._reserva(telefone="258841234567",
                                 estado_pagamento=PaymentIntent.Status.FAILED)
        self.assertEqual(self.comprar(telefone="841234567").status_code, 201)
        anterior.refresh_from_db()
        self.assertEqual(anterior.status, GuestCheckout.Status.CANCELLED)
