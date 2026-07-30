"""O comando de limpeza periódica corre de 5 em 5 minutos em produção.

Não tinha teste nenhum, e o primeiro erro (usar o `delete()` soft do projecto,
que devolve um int em vez do tuplo do Django) só apareceu ao correr no
servidor. Um comando que corre sozinho e cujo output ninguém lê tem de ser
testado aqui.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.guest_checkouts.models import GuestCheckout
from apps.payments.models import PaymentIntent
from apps.users.models import OtpChallenge


class ExpireStaleTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.expired_checkout = GuestCheckout.objects.create(
            reference="GC-EXP0001", payer_phone="258841000001",
            route_code="R1", origin_stop="A", destination_stop="B",
            quantity=1, unit_amount=Decimal("50.00"), total_amount=Decimal("50.00"),
            status=GuestCheckout.Status.PAYMENT_PENDING,
            expires_at=now - timedelta(minutes=1),
        )
        self.live_checkout = GuestCheckout.objects.create(
            reference="GC-EXP0002", payer_phone="258841000002",
            route_code="R1", origin_stop="A", destination_stop="B",
            quantity=1, unit_amount=Decimal("50.00"), total_amount=Decimal("50.00"),
            status=GuestCheckout.Status.PAYMENT_PENDING,
            expires_at=now + timedelta(minutes=20),
        )
        self.expired_intent = PaymentIntent.objects.create(
            reference="PAY-EXP0001", idempotency_key="exp-0001",
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
            amount=Decimal("50.00"), payer_phone="258841000001",
            guest_checkout=self.expired_checkout,
            status=PaymentIntent.Status.PENDING,
            expires_at=now - timedelta(minutes=1),
        )
        self.old_otp = OtpChallenge.objects.create(
            phone="258841000003", code_hash="x", expires_at=now - timedelta(days=30),
        )
        OtpChallenge.objects.filter(pk=self.old_otp.pk).update(
            created_at=now - timedelta(days=30),
        )
        self.fresh_otp = OtpChallenge.objects.create(
            phone="258841000004", code_hash="y", expires_at=now + timedelta(minutes=5),
        )

    def _run(self, *args) -> str:
        out = StringIO()
        call_command("expire_stale", *args, stdout=out)
        return out.getvalue()

    def test_dry_run_changes_nothing(self):
        output = self._run("--dry-run")
        self.assertIn("dry-run", output)
        self.expired_checkout.refresh_from_db()
        self.assertEqual(self.expired_checkout.status, GuestCheckout.Status.PAYMENT_PENDING)

    def test_expires_only_what_is_past_due(self):
        self._run()

        self.expired_checkout.refresh_from_db()
        self.expired_intent.refresh_from_db()
        self.live_checkout.refresh_from_db()

        self.assertEqual(self.expired_checkout.status, GuestCheckout.Status.EXPIRED)
        self.assertEqual(self.expired_intent.status, PaymentIntent.Status.EXPIRED)
        self.assertEqual(
            self.live_checkout.status, GuestCheckout.Status.PAYMENT_PENDING,
            "um checkout dentro da validade nao pode ser expirado",
        )

    def test_purges_old_otps_for_real(self):
        """`hard_delete`: o soft-delete deixava as linhas na tabela, que e
        consultada em cada login."""
        self._run()
        self.assertFalse(
            OtpChallenge.all_objects.filter(pk=self.old_otp.pk).exists(),
            "o desafio antigo devia ter sido apagado, nao apenas marcado",
        )
        self.assertTrue(
            OtpChallenge.all_objects.filter(pk=self.fresh_otp.pk).exists(),
            "um desafio recente nao pode ser apagado",
        )

    def test_reports_counts(self):
        output = self._run()
        for key in ("checkouts=", "intents=", "pacotes=", "otps=", "tokens="):
            self.assertIn(key, output)
