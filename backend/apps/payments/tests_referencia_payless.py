"""A referencia que o Payless devolve tem de ficar guardada.

O caso real, apanhado em producao a 19/08/2026: uma venda ao balcao por e-Mola
ficou pendente para sempre. O gateway tinha aceite o pedido — respondeu
`errorCode: "0"`, "Successfully" — mas `provider_reference` ficou VAZIA, porque
a lista de extraccao nao conhecia as chaves que o Payless usa.

Porque e que isso e grave: o e-Mola do Payless **nao tem endpoint de consulta**
(`/search/emola/c2b` responde 404 — verificado contra o gateway real). Logo o
callback e a UNICA maneira de saber que o passageiro pagou. Sem a referencia
guardada, o callback nao casa com pagamento nenhum e o dinheiro entra sem que
o bilhete seja emitido.

A resposta abaixo e a que veio mesmo do Payless, copiada da metadata do
pagamento PAY-AS-2B70B37ADD744EB781.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from apps.payments.models import PaymentIntent
from apps.payments.services.gateway import _interpret_response

# Resposta real do Payless a um pedido e-Mola aceite.
RESPOSTA_EMOLA = {
    "error": 0,
    "original": {
        "message": "Successfully",
        "errorCode": "0",
        "requestId": "28612260819001899287772",
    },
    "gwtransid": "202608191625473999962",
}


class ExtraccaoDaReferenciaTests(TestCase):
    def test_gwtransid_e_guardado(self):
        _, _, ext_ref = _interpret_response("EMOLA", 200, RESPOSTA_EMOLA)
        self.assertEqual(ext_ref, "202608191625473999962")

    def test_sem_gwtransid_cai_no_request_id(self):
        resposta = {k: v for k, v in RESPOSTA_EMOLA.items() if k != "gwtransid"}
        _, _, ext_ref = _interpret_response("EMOLA", 200, resposta)
        self.assertEqual(ext_ref, "28612260819001899287772")

    def test_pedido_aceite_fica_pendente_e_nao_confirmado(self):
        """O e-Mola pede PIN ao passageiro: aceite nao e pago."""
        resultado, _, _ = _interpret_response("EMOLA", 200, RESPOSTA_EMOLA)
        self.assertEqual(resultado, "PENDING")

    def test_as_chaves_antigas_continuam_a_valer(self):
        _, _, ext_ref = _interpret_response("MPESA", 200, {"output_TransactionID": "ABC123"})
        self.assertEqual(ext_ref, "ABC123")


class CallbackEncontraOPagamentoTests(TestCase):
    """O callback e a unica via para o e-Mola: tem de casar sempre."""

    def _pagamento(self, referencia, provider_reference="", resposta=None):
        return PaymentIntent.objects.create(
            reference=referencia,
            idempotency_key=f"idem-{referencia}",
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
            amount=Decimal("1650.00"),
            payer_phone="876671100",
            provider="EMOLA",
            provider_reference=provider_reference,
            status=PaymentIntent.Status.PENDING,
            metadata={"gateway_response": resposta or RESPOSTA_EMOLA},
        )

    def test_casa_pela_referencia_guardada(self):
        from apps.payments.api.views import _resolve_payment_intent

        pi = self._pagamento("PAY-1", provider_reference="202608191625473999962")
        achado = _resolve_payment_intent("", "202608191625473999962", "EMOLA")
        self.assertEqual(achado.pk, pi.pk)

    def test_casa_um_pagamento_antigo_sem_referencia_guardada(self):
        """Os que ficaram orfaos antes da correccao.

        Sem isto continuavam sem salvacao: o e-Mola nao se consulta, e o
        callback era a unica hipotese que lhes restava.
        """
        from apps.payments.api.views import _resolve_payment_intent

        pi = self._pagamento("PAY-2", provider_reference="")
        achado = _resolve_payment_intent("", "202608191625473999962", "EMOLA")
        self.assertEqual(achado.pk, pi.pk)

    def test_casa_um_antigo_pelo_request_id(self):
        from apps.payments.api.views import _resolve_payment_intent

        pi = self._pagamento("PAY-3", provider_reference="")
        achado = _resolve_payment_intent("", "28612260819001899287772", "EMOLA")
        self.assertEqual(achado.pk, pi.pk)

    def test_referencia_desconhecida_nao_casa_com_nada(self):
        """Nunca confirmar o pagamento errado: sem correspondencia, nada feito."""
        from apps.payments.api.views import _resolve_payment_intent

        self._pagamento("PAY-4", provider_reference="")
        self.assertIsNone(_resolve_payment_intent("", "999999999999", "EMOLA"))
