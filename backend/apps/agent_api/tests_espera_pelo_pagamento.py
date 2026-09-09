"""O ecra "a aguardar pagamento" do POS pergunta a operadora.

2026-09-08, 18:30: venda ao balcao por M-Pesa, o passageiro demorou mais de 15 s
no PIN, a cobranca deixou o pagamento pendente, e o bilhete so saiu 352 s
depois — quando o cron passou. O agente e o passageiro ficaram esses 6
minutos a olhar para o ecra. O POS ja chamava o estado de 3 em 3 s; faltava o
estado ir perguntar a quem sabe.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.payments.models import PaymentIntent
from apps.payments.services.gateway import PaymentGatewayResult
from apps.trips.models import Agent


class EsperaPeloPagamentoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="ag", email="ag@x.mz", password="x", phone="849000009")
        Agent.objects.create(user=self.user, full_name="Agente", status=Agent.Status.ACTIVE)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _pendente(self, segundos):
        pi = PaymentIntent.objects.create(
            reference="PAY-AS-ESPERA1", idempotency_key="espera-1",
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS, amount=Decimal("300.00"),
            payer_phone="843923574", status=PaymentIntent.Status.PENDING, provider="MPESA",
            created_by=self.user,
            metadata={"agent_user_id": self.user.id, "gateway_request": {"transactionReference": "MPESPERA"}},
        )
        PaymentIntent.objects.filter(pk=pi.pk).update(created_at=timezone.now() - timedelta(seconds=segundos))
        return pi

    def test_pendente_ha_30s_pergunta_e_devolve_confirmado(self):
        self._pendente(30)
        perguntou = []

        class Gateway:
            def query_payment(self, ref):
                perguntou.append(ref)
                return PaymentGatewayResult(success=True, provider_reference="DI35")

        with patch("apps.payments.services.reconciliation.get_payment_gateway", lambda *a, **k: Gateway()):
            r = self.client.get("/api/agent/payments/PAY-AS-ESPERA1/status/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["status"], "confirmed")
        self.assertEqual(perguntou, ["MPESPERA"], "perguntou pela referencia que a operadora conhece")

    def test_nos_primeiros_segundos_so_le(self):
        self._pendente(5)
        with patch("apps.payments.services.reconciliation.get_payment_gateway") as g:
            r = self.client.get("/api/agent/payments/PAY-AS-ESPERA1/status/")
        self.assertEqual(r.json()["status"], "pending")
        g.assert_not_called()

    def test_numerario_nunca_pergunta(self):
        pi = self._pendente(60)
        PaymentIntent.objects.filter(pk=pi.pk).update(provider="CASH")
        with patch("apps.payments.services.reconciliation.get_payment_gateway") as g:
            self.client.get("/api/agent/payments/PAY-AS-ESPERA1/status/")
        g.assert_not_called()
