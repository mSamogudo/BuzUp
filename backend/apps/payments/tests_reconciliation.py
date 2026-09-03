"""Reconciliação: o webhook perdido deixa de significar passageiro sem bilhete.

O cenário real: a rede móvel oscila, o webhook do M-Pesa nunca chega, o
passageiro pagou e o `PaymentIntent` fica `PENDING` para sempre. Estes testes
fixam o comportamento nos três desfechos possíveis.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.payments.models import PaymentIntent
from apps.payments.services.gateway import PaymentGatewayResult
from apps.payments.services.reconciliation import referencia_para_consulta, reconcile_pending_payments
from apps.passengers.models import PassengerAccount
from apps.wallets.models import Wallet


def _gateway_saying(result: PaymentGatewayResult):
    """Substitui o gateway por um que responde sempre `result`."""

    class FakeGateway:
        def query_payment(self, provider_reference: str):
            return result

    return lambda *args, **kwargs: FakeGateway()


class ReconciliationTests(TestCase):
    def setUp(self):
        self.checkout = GuestCheckout.objects.create(
            reference="GC-RECON0001", payer_phone="258841234567",
            route_code="R1", route_name="Rota 1",
            origin_stop="A", destination_stop="B",
            quantity=1, unit_amount=Decimal("150.00"), total_amount=Decimal("150.00"),
            status=GuestCheckout.Status.PAYMENT_PENDING,
            expires_at=timezone.now() + timedelta(minutes=20),
        )
        self.intent = PaymentIntent.objects.create(
            reference="PAY-GC-RECON0001",
            idempotency_key="recon-0001",
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
            amount=Decimal("150.00"),
            payer_phone="258841234567",
            guest_checkout=self.checkout,
            status=PaymentIntent.Status.PENDING,
            provider="MPESA",
            provider_reference="MP-EXTERNAL-1",
        )
        # Envelhecer o pagamento: a reconciliação ignora os recentes, porque um
        # pagamento acabado de iniciar está legitimamente pendente.
        PaymentIntent.objects.filter(pk=self.intent.pk).update(
            created_at=timezone.now() - timedelta(minutes=30),
        )

    def test_confirmed_by_gateway_issues_the_ticket(self):
        """O caso que motiva tudo: pagou, o webhook perdeu-se, agora recebe."""
        with patch(
            "apps.payments.services.reconciliation.get_payment_gateway",
            _gateway_saying(PaymentGatewayResult(success=True, provider_reference="MP-EXTERNAL-1")),
        ):
            report = reconcile_pending_payments(min_age_minutes=5)

        self.assertEqual(report.confirmed, 1, report.as_line())
        self.intent.refresh_from_db()
        self.checkout.refresh_from_db()
        self.assertEqual(self.intent.status, PaymentIntent.Status.CONFIRMED)
        self.assertEqual(self.checkout.status, GuestCheckout.Status.ISSUED)
        self.assertEqual(
            DigitalTravelPass.objects.filter(guest_checkout=self.checkout).count(), 1,
            "o bilhete devia ter sido emitido",
        )

    def test_failed_by_gateway_releases_the_seat(self):
        with patch(
            "apps.payments.services.reconciliation.get_payment_gateway",
            _gateway_saying(PaymentGatewayResult(success=False, error="Saldo insuficiente")),
        ):
            report = reconcile_pending_payments(min_age_minutes=5)

        self.assertEqual(report.failed, 1, report.as_line())
        self.intent.refresh_from_db()
        self.checkout.refresh_from_db()
        self.assertEqual(self.intent.status, PaymentIntent.Status.FAILED)
        self.assertEqual(
            self.checkout.status, GuestCheckout.Status.CANCELLED,
            "o lugar tinha de voltar a estar disponivel",
        )

    def test_still_pending_is_left_alone(self):
        with patch(
            "apps.payments.services.reconciliation.get_payment_gateway",
            _gateway_saying(PaymentGatewayResult(success=False, pending=True)),
        ):
            report = reconcile_pending_payments(min_age_minutes=5)

        self.assertEqual(report.still_pending, 1, report.as_line())
        self.intent.refresh_from_db()
        self.assertEqual(self.intent.status, PaymentIntent.Status.PENDING)

    def test_recent_payments_are_not_touched(self):
        """Enquanto o passageiro digita o PIN, não há nada a reconciliar."""
        PaymentIntent.objects.filter(pk=self.intent.pk).update(created_at=timezone.now())
        with patch(
            "apps.payments.services.reconciliation.get_payment_gateway",
            _gateway_saying(PaymentGatewayResult(success=True)),
        ):
            report = reconcile_pending_payments(min_age_minutes=5)

        self.assertEqual(report.checked, 0, report.as_line())
        self.intent.refresh_from_db()
        self.assertEqual(self.intent.status, PaymentIntent.Status.PENDING)

    def test_confirmed_after_expiry_is_flagged_not_issued(self):
        """Confirmado depois do checkout expirar: o lugar pode estar revendido.

        Emitir automaticamente criaria dois passageiros no mesmo lugar. O
        dinheiro é reconhecido, mas a decisão entre reemitir e reembolsar fica
        para uma pessoa.
        """
        self.checkout.status = GuestCheckout.Status.EXPIRED
        self.checkout.expires_at = timezone.now() - timedelta(minutes=5)
        self.checkout.save(update_fields=["status", "expires_at"])

        with patch(
            "apps.payments.services.reconciliation.get_payment_gateway",
            _gateway_saying(PaymentGatewayResult(success=True, provider_reference="MP-EXTERNAL-1")),
        ):
            report = reconcile_pending_payments(min_age_minutes=5)

        self.assertEqual(report.needs_review, 1, report.as_line())
        self.assertEqual(report.confirmed, 0)
        self.intent.refresh_from_db()
        self.assertEqual(
            self.intent.status, PaymentIntent.Status.PENDING,
            "nao deve confirmar sozinho um pagamento cujo lugar pode estar vendido",
        )
        self.assertTrue(
            self.intent.metadata.get("reconciliation", {}).get("needs_manual_review"),
            "o caso tinha de ficar sinalizado para revisao",
        )
        self.assertEqual(
            DigitalTravelPass.objects.filter(guest_checkout=self.checkout).count(), 0,
            "nao pode emitir bilhete para um lugar possivelmente revendido",
        )

    def test_gateway_error_does_not_stop_the_others(self):
        """Um pagamento problemático não pode travar a reconciliação restante."""
        other_checkout = GuestCheckout.objects.create(
            reference="GC-RECON0002", payer_phone="258849999999",
            route_code="R1", origin_stop="A", destination_stop="B",
            quantity=1, unit_amount=Decimal("150.00"), total_amount=Decimal("150.00"),
            status=GuestCheckout.Status.PAYMENT_PENDING,
            expires_at=timezone.now() + timedelta(minutes=20),
        )
        other = PaymentIntent.objects.create(
            reference="PAY-GC-RECON0002", idempotency_key="recon-0002",
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
            amount=Decimal("150.00"), payer_phone="258849999999",
            guest_checkout=other_checkout, status=PaymentIntent.Status.PENDING,
            provider="MPESA", provider_reference="MP-EXTERNAL-2",
        )
        PaymentIntent.objects.filter(pk=other.pk).update(
            created_at=timezone.now() - timedelta(minutes=30),
        )

        class FlakyGateway:
            def query_payment(self, provider_reference: str):
                if provider_reference == "MP-EXTERNAL-1":
                    raise TimeoutError("gateway sem resposta")
                return PaymentGatewayResult(success=True, provider_reference=provider_reference)

        with patch(
            "apps.payments.services.reconciliation.get_payment_gateway",
            lambda *a, **k: FlakyGateway(),
        ):
            report = reconcile_pending_payments(min_age_minutes=5)

        self.assertEqual(len(report.errors), 1, report.as_line())
        self.assertEqual(report.confirmed, 1, "o segundo pagamento tinha de ser reconciliado")


class WalletTopupReconciliationTests(TestCase):
    """Recargas não têm lugar associado: confirmar é sempre seguro."""

    def test_expired_wallet_topup_is_still_credited(self):
        passenger = PassengerAccount.objects.create(
            full_name="Passageiro Recon", phone_number="258841112222",
            status=PassengerAccount.Status.ACTIVE,
        )
        wallet = Wallet.objects.create(
            passenger_account=passenger, balance_cached=Decimal("0.00"),
            status=Wallet.Status.ACTIVE,
        )
        intent = PaymentIntent.objects.create(
            reference="PAY-TOP-RECON1", idempotency_key="recon-top-1",
            purpose=PaymentIntent.Purpose.MOBILE_WALLET_TOPUP,
            amount=Decimal("500.00"), payer_phone="258841112222",
            wallet=wallet, status=PaymentIntent.Status.PENDING,
            provider="MPESA", provider_reference="MP-TOP-1",
            expires_at=timezone.now() - timedelta(minutes=10),
        )
        PaymentIntent.objects.filter(pk=intent.pk).update(
            created_at=timezone.now() - timedelta(minutes=30),
        )

        with patch(
            "apps.payments.services.reconciliation.get_payment_gateway",
            _gateway_saying(PaymentGatewayResult(success=True, provider_reference="MP-TOP-1")),
        ):
            report = reconcile_pending_payments(min_age_minutes=5)

        self.assertEqual(report.confirmed, 1, report.as_line())
        wallet.refresh_from_db()
        self.assertEqual(
            wallet.balance_cached, Decimal("500.00"),
            "o passageiro pagou a recarga — o saldo tem de aparecer",
        )


class ReferenciaDaConsultaTests(TestCase):
    """Por que referencia se pergunta a operadora.

    No caso para que a reconciliacao existe — o pedido morreu no nosso timeout
    — a `provider_reference` esta vazia, e perguntava-se pela nossa `PAY-GC-...`,
    que a operadora nunca viu. Respondia `data: []`, lia-se pendente, e o
    pagamento ficava assim ate expirar. 6.600 MT a 2026-09-03.
    """

    def _intent(self, **extra):
        return PaymentIntent.objects.create(
            reference="PAY-GC-BC49262D46054E1DB9", idempotency_key="k-" + str(extra.get("provider", "")),
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS, amount=Decimal("6600.00"),
            payer_phone="258843923574", status=PaymentIntent.Status.PENDING, **extra,
        )

    def test_pergunta_pelo_que_foi_enviado(self):
        pi = self._intent(provider="MPESA", metadata={"gateway_request": {
            "transactionReference": "MPBC49262D46054E1DB9", "thirdPartyReference": "BZBC49262D46054E1DB9"}})
        self.assertEqual(referencia_para_consulta(pi), "MPBC49262D46054E1DB9")

    def test_sem_metadata_deriva_a_compactada(self):
        pi = self._intent(provider="MPESA")
        self.assertEqual(referencia_para_consulta(pi), "MPBC49262D46054E1DB9")

    def test_nunca_pergunta_pela_nossa_referencia_no_mpesa(self):
        pi = self._intent(provider="MPESA", provider_reference="")
        self.assertNotEqual(referencia_para_consulta(pi), pi.reference)

    def test_a_reconciliacao_usa_essa_referencia(self):
        """Ponta a ponta: o gateway recebe a compactada, nao a nossa."""
        from apps.guest_checkouts.models import GuestCheckout

        gc = GuestCheckout.objects.create(
            reference="GC-BC49262D46054E1DB9", payer_phone="258843923574",
            route_code="R1", route_name="Rota 1", origin_stop="A", destination_stop="B",
            quantity=1, unit_amount=Decimal("6600.00"), total_amount=Decimal("6600.00"),
            status=GuestCheckout.Status.PAYMENT_PENDING,
            expires_at=timezone.now() + timedelta(minutes=20),
        )
        pi = self._intent(provider="MPESA", guest_checkout=gc,
                          metadata={"gateway_request": {"transactionReference": "MPBC49262D46054E1DB9"}})
        PaymentIntent.objects.filter(pk=pi.pk).update(created_at=timezone.now() - timedelta(minutes=30))
        perguntou = []

        class Gateway:
            def query_payment(self, ref):
                perguntou.append(ref)
                return PaymentGatewayResult(success=True, provider_reference="DI35LFZBWZL")

        with patch("apps.payments.services.reconciliation.get_payment_gateway", lambda *a, **k: Gateway()):
            reconcile_pending_payments(min_age_minutes=5)
        self.assertEqual(perguntou, ["MPBC49262D46054E1DB9"])
        pi.refresh_from_db()
        self.assertEqual(pi.status, PaymentIntent.Status.CONFIRMED)
        self.assertEqual(pi.provider_reference, "DI35LFZBWZL")
