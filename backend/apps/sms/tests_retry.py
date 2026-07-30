"""Reenvio de SMS falhados.

O caso que motiva isto: alguém compra um bilhete sem smartphone e depende do
SMS para o receber. O provedor devolve 500, a falha era definitiva, e a pessoa
fica sem bilhete tendo pago.
"""

from __future__ import annotations

from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.sms.models import SmsMessage


def _run(*args) -> str:
    out = StringIO()
    call_command("retry_failed_sms", *args, stdout=out)
    return out.getvalue()


class RetryFailedSmsTests(TestCase):
    def setUp(self):
        self.failed = SmsMessage.objects.create(
            phone_number="258841234567",
            body="BuzUp: o seu bilhete GC-XXXX",
            purpose="GUEST_PASS_DELIVERY",
            status=SmsMessage.Status.FAILED,
            metadata={"response_status": 500, "provider": "BLUTEKI"},
        )

    def test_transient_failure_is_resent(self):
        sent = SmsMessage(
            phone_number=self.failed.phone_number, body=self.failed.body,
            status=SmsMessage.Status.SENT,
        )
        sent.save()
        with patch("apps.sms.management.commands.retry_failed_sms.send_sms", return_value=sent) as mock:
            output = _run()

        mock.assert_called_once()
        self.assertIn("entregues=1", output)
        self.failed.refresh_from_db()
        self.assertEqual(self.failed.attempts, 2)
        self.assertEqual(
            self.failed.metadata.get("recovered_by"), sent.pk,
            "o registo original devia apontar para o envio que teve sucesso",
        )

    def test_permanent_failure_is_not_retried(self):
        """Um numero invalido nao melhora com tentativas."""
        SmsMessage.objects.all().delete()
        bad = SmsMessage.objects.create(
            phone_number="", body="x", status=SmsMessage.Status.FAILED,
            metadata={"error": "missing_phone"},
        )
        with patch("apps.sms.management.commands.retry_failed_sms.send_sms") as mock:
            output = _run()

        mock.assert_not_called()
        self.assertIn("permanentes=1", output)
        bad.refresh_from_db()
        self.assertEqual(
            bad.attempts, 3,
            "devia ficar marcado como esgotado para nao voltar a ser procurado",
        )

    def test_gives_up_after_max_attempts(self):
        self.failed.attempts = 3
        self.failed.save(update_fields=["attempts"])
        with patch("apps.sms.management.commands.retry_failed_sms.send_sms") as mock:
            output = _run()
        mock.assert_not_called()
        self.assertIn("candidatos=0", output)

    def test_old_failures_are_left_alone(self):
        """Passada a janela, o SMS já não tem utilidade — reenviar só confunde."""
        SmsMessage.objects.filter(pk=self.failed.pk).update(
            created_at=timezone.now() - timedelta(hours=48),
        )
        with patch("apps.sms.management.commands.retry_failed_sms.send_sms") as mock:
            output = _run()
        mock.assert_not_called()
        self.assertIn("candidatos=0", output)

    def test_still_failing_is_counted_but_not_lost(self):
        # Nao gravado de proposito: gravar criava um SEGUNDO registo falhado
        # que entrava tambem nos candidatos e falseava a contagem. O comando
        # so le o `status` neste caminho.
        still_failed = SmsMessage(
            phone_number=self.failed.phone_number, body=self.failed.body,
            status=SmsMessage.Status.FAILED,
        )
        with patch("apps.sms.management.commands.retry_failed_sms.send_sms", return_value=still_failed):
            output = _run()

        self.assertIn("reenviados=1", output)
        self.assertIn("entregues=0", output)
        self.failed.refresh_from_db()
        self.assertEqual(self.failed.attempts, 2, "a tentativa tem de ser contada")
