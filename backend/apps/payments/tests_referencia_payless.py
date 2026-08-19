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

    def test_as_chaves_antigas_continuam_a_valer(self):
        _, _, ext_ref = _interpret_response("MPESA", 200, {"output_TransactionID": "ABC123"})
        self.assertEqual(ext_ref, "ABC123")


# Recusa real, copiada do eTicketing em producao (mesma carteira e-Mola).
RECUSA_EMOLA = {
    "error": 0,
    "original": {
        "message": "Customer did not enter PIN",
        "errorCode": "11",
        "requestId": "28612260809001877541837",
    },
    "gwtransid": "202608091510379003138",
}


class DesfechoDoEmolaTests(TestCase):
    """O e-Mola do Payless e SINCRONO: a resposta e o desfecho.

    A chamada espera pelo PIN do cliente. `errorCode: "0"` significa que o
    dinheiro saiu; `"11"` que o cliente nao confirmou. Nao ha estado
    intermedio — e nao ha para onde perguntar depois, porque o
    `/search/emola/c2b` do Payless nao existe (404, verificado).

    O nosso codigo lia `message` e `code` no topo do JSON, mas o Payless poe
    ambos dentro de `original`. Nao encontrando nada, tudo caia no "pendente"
    do fim da cadeia: o pagamento feito nunca virava bilhete, e o recusado
    nunca libertava o lugar.
    """

    def test_pagamento_feito_e_sucesso(self):
        resultado, _, _ = _interpret_response("EMOLA", 200, RESPOSTA_EMOLA)
        self.assertEqual(
            resultado, "SUCCESS",
            "o passageiro pagou e o dinheiro entrou — isto tem de emitir bilhete",
        )

    def test_cliente_que_nao_confirma_e_falha(self):
        resultado, detalhe, _ = _interpret_response("EMOLA", 200, RECUSA_EMOLA)
        self.assertEqual(
            resultado, "FAILED",
            "sem PIN nao ha dinheiro: deixar pendente prendia o lugar para sempre",
        )
        self.assertIn("PIN", detalhe)

    def test_a_recusa_tambem_guarda_a_referencia(self):
        """Para se poder rastrear com a Bluteki o que quer que tenha acontecido."""
        _, _, ext_ref = _interpret_response("EMOLA", 200, RECUSA_EMOLA)
        self.assertEqual(ext_ref, "202608091510379003138")

    def test_o_erro_do_topo_nao_e_o_desfecho(self):
        """`error: 0` diz que o pedido chegou ao gateway, nao que foi pago.

        As duas respostas — a paga e a recusada — trazem `error: 0`. Quem
        olhasse so para ai dava as duas por boas.
        """
        self.assertEqual(RESPOSTA_EMOLA["error"], RECUSA_EMOLA["error"])
        pago, _, _ = _interpret_response("EMOLA", 200, RESPOSTA_EMOLA)
        recusado, _, _ = _interpret_response("EMOLA", 200, RECUSA_EMOLA)
        self.assertNotEqual(pago, recusado)

    def test_o_mpesa_continua_a_esperar_confirmacao(self):
        """O M-Pesa e assincrono e TEM consulta: ai o pendente e correcto."""
        resultado, _, _ = _interpret_response("MPESA", 200, {"status": "accepted"})
        self.assertEqual(resultado, "PENDING")


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
