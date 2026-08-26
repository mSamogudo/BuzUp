"""O bilhete diz COMO foi pago, e nao so quanto custou.

Ao balcao isso importa: numa reclamacao ou numa devolucao a primeira pergunta e
"pagou como?", e a resposta andava a ser procurada no sistema em vez de estar
no papel que o passageiro tem na mao.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.guest_checkouts.ticket_pdf import _forma_de_pagamento
from apps.payments.models import PaymentIntent


class FormaDePagamentoNoBilheteTests(TestCase):
    def _bilhete(self, provider=None, status="confirmed"):
        gc = GuestCheckout.objects.create(
            reference=f"GC-{provider or 'SEM'}-{status}", payer_phone="258841234567",
            route_code="RT-X", route_name="Rota", origin_stop="A", destination_stop="B",
            quantity=1, unit_amount=Decimal("100.00"), total_amount=Decimal("100.00"),
            status=GuestCheckout.Status.ISSUED,
            expires_at=timezone.now() + timedelta(days=1))
        if provider is not None:
            PaymentIntent.objects.create(
                reference=f"PAY-{gc.reference}", idempotency_key=gc.reference,
                purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
                amount=Decimal("100.00"), payer_phone="258841234567",
                guest_checkout=gc, provider=provider, status=status)
        raw, h = DigitalTravelPass.generate_token()
        return DigitalTravelPass.objects.create(
            guest_checkout=gc, payer_phone="258841234567",
            route_code="RT-X", route_name="Rota",
            origin_stop="A", destination_stop="B",
            fare_amount=Decimal("100.00"), token=raw, token_hash=h,
            status=DigitalTravelPass.Status.ACTIVE)

    def test_mpesa(self):
        self.assertEqual(_forma_de_pagamento(self._bilhete("MPESA")), "M-Pesa")

    def test_emola(self):
        self.assertEqual(_forma_de_pagamento(self._bilhete("EMOLA")), "e-Mola")

    def test_numerario(self):
        self.assertEqual(_forma_de_pagamento(self._bilhete("CASH")), "Numerario")

    def test_cartao(self):
        self.assertEqual(_forma_de_pagamento(self._bilhete("wallet")), "Cartao")

    # --- melhor nao dizer nada do que dizer errado ------------------------

    def test_sem_pagamento_confirmado_nao_inventa(self):
        self.assertEqual(_forma_de_pagamento(self._bilhete(None)), "")

    def test_pagamento_por_confirmar_nao_conta(self):
        self.assertEqual(_forma_de_pagamento(self._bilhete("MPESA", status="pending")), "")

    def test_provedor_desconhecido_fica_em_branco(self):
        """`MOCK` so existe em ambientes de teste e nao se imprime."""
        self.assertEqual(_forma_de_pagamento(self._bilhete("MOCK")), "")

    # --- e o PDF continua a sair -----------------------------------------

    def test_o_pdf_e_gerado_com_a_forma_de_pagamento(self):
        from apps.guest_checkouts.ticket_pdf import generate_tickets_pdf

        b = generate_tickets_pdf([self._bilhete("CASH")])
        self.assertGreater(len(b), 1000)
        self.assertTrue(b.startswith(b"%PDF"))
