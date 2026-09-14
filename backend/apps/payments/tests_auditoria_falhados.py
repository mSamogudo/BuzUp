"""A segunda volta: um "falhado" que a operadora diz ter cobrado.

A reconciliacao normal so olha para PENDING. Assim que um pagamento e marcado
FAILED, ninguem volta a olhar — e ate 2026-09-10 era o nosso proprio timeout a
marcar assim, com a operadora a debitar o passageiro nesse momento.

A 2026-09-14 uma auditoria a mao encontrou dois casos reais: 1.650 MZN de
28/08 e 3.300 MZN de 31/08, ambos cobrados, nenhum com bilhete, 17 e 14 dias
sem ninguem dar por nada. Estes testes existem para que a proxima vez seja
encontrada no dia seguinte e por ninguem.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.guest_checkouts.models import GuestCheckout
from apps.payments.models import PaymentIntent
from apps.payments.services.gateway import PaymentGatewayResult
from apps.payments.services.reconciliation import (
    MAXIMO_DE_AUDITORIAS,
    auditar_pagamentos_falhados,
)

CAMINHO_GATEWAY = "apps.payments.services.reconciliation.get_payment_gateway"


def _gateway_que_diz(resultado: PaymentGatewayResult):
    class FakeGateway:
        def query_payment(self, referencia):
            return resultado

    return lambda *args, **kwargs: FakeGateway()


class AuditoriaDeFalhadosTests(TestCase):
    def setUp(self):
        self.checkout = GuestCheckout.objects.create(
            reference="GC-AUD0001", payer_phone="258848818277",
            route_code="R1", route_name="Rota 1",
            origin_stop="A", destination_stop="B",
            quantity=1, unit_amount=Decimal("1650.00"), total_amount=Decimal("1650.00"),
            status=GuestCheckout.Status.CANCELLED,
            expires_at=timezone.now() - timedelta(days=2),
        )
        self.intent = PaymentIntent.objects.create(
            reference="PAY-AS-AUD0001",
            idempotency_key="aud-0001",
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
            amount=Decimal("1650.00"),
            payer_phone="258848818277",
            guest_checkout=self.checkout,
            status=PaymentIntent.Status.FAILED,
            provider="MPESA",
            metadata={"gateway_request": {"reference": "MP80ACE35B05BA42C4AE"}},
        )

    def _auditar(self, resultado):
        with patch(CAMINHO_GATEWAY, _gateway_que_diz(resultado)):
            return auditar_pagamentos_falhados()

    # --- o caso que custou 4.950 MZN ---------------------------------------

    def test_money_taken_on_a_failed_payment_is_found(self):
        report = self._auditar(
            PaymentGatewayResult(success=True, provider_reference="DHS4LDBOJYW", provider="MPESA")
        )
        self.assertEqual(report.pagos_sem_bilhete, 1)

        self.intent.refresh_from_db()
        revisao = (self.intent.metadata or {}).get("reconciliation") or {}
        self.assertTrue(revisao.get("needs_manual_review"))
        self.assertIn("COBRADO", revisao.get("reason", ""))
        self.assertEqual(revisao.get("provider_reference"), "DHS4LDBOJYW")

    def test_it_never_issues_a_ticket_on_its_own(self):
        """O checkout ja foi cancelado e o lugar devolvido a lotacao; a viagem
        pode ter partido ha semanas. Emitir criava dois passageiros no mesmo
        lugar, ou um bilhete para um autocarro que ja foi."""
        self._auditar(
            PaymentGatewayResult(success=True, provider_reference="DHS4LDBOJYW", provider="MPESA")
        )
        self.intent.refresh_from_db()
        self.checkout.refresh_from_db()
        self.assertEqual(self.intent.status, PaymentIntent.Status.FAILED)
        self.assertEqual(self.checkout.status, GuestCheckout.Status.CANCELLED)
        self.assertEqual(self.checkout.travel_passes.count(), 0)

    @override_settings(PAYMENT_REVIEW_ALERT_NUMBERS="841111111")
    def test_someone_is_told_once_and_only_once(self):
        pago = PaymentGatewayResult(success=True, provider_reference="DHS4LDBOJYW", provider="MPESA")
        with patch("apps.sms.services.sender.send_sms") as enviar:
            self._auditar(pago)
            self._auditar(pago)
        self.assertEqual(enviar.call_count, 1, "avisar duas vezes pelo mesmo caso e ruido")
        corpo = enviar.call_args[0][1]
        self.assertIn("1650.00", corpo)
        self.assertIn("258848818277", corpo)

    # --- o que nao pode disparar em falso ----------------------------------

    def test_a_real_failure_stays_a_failure_and_wakes_nobody(self):
        with patch("apps.sms.services.sender.send_sms") as enviar:
            report = self._auditar(
                PaymentGatewayResult(
                    success=False, provider="MPESA",
                    detail_message="Solicitacao expirou antes da confirmacao.",
                )
            )
        self.assertEqual(report.pagos_sem_bilhete, 0)
        self.assertEqual(report.mesmo_falhados, 1)
        enviar.assert_not_called()

    def test_a_channel_without_a_query_is_not_an_error(self):
        """O e-Mola nao tem consulta. Nao e defeito nosso e nao pode encher o
        relatorio de erros todos os dias — conta-se a parte."""
        report = self._auditar(
            PaymentGatewayResult(success=False, error="Query not supported.", provider="EMOLA")
        )
        self.assertEqual(report.sem_consulta, 1)
        self.assertEqual(report.erros, [])

    def test_it_stops_asking_after_a_few_tries(self):
        """Perguntar todos os dias para sempre gasta chamadas a operadora sem
        ganho: se ela nao mudou de ideias em tres passagens, nao muda."""
        naopago = PaymentGatewayResult(
            success=False, provider="MPESA", detail_message="expirou"
        )
        for _ in range(MAXIMO_DE_AUDITORIAS):
            self._auditar(naopago)
        report = self._auditar(naopago)
        self.assertEqual(report.verificados, 0)
        self.assertEqual(report.ja_auditados, 1)

    def test_old_failures_are_out_of_the_window(self):
        PaymentIntent.objects.filter(pk=self.intent.pk).update(
            created_at=timezone.now() - timedelta(days=40)
        )
        report = self._auditar(PaymentGatewayResult(success=True, provider="MPESA"))
        self.assertEqual(report.verificados, 0)

    def test_a_confirmed_payment_is_never_touched(self):
        PaymentIntent.objects.filter(pk=self.intent.pk).update(
            status=PaymentIntent.Status.CONFIRMED
        )
        report = self._auditar(PaymentGatewayResult(success=True, provider="MPESA"))
        self.assertEqual(report.verificados, 0)
