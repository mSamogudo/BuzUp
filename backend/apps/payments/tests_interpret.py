"""Interpretação da resposta do gateway — o ponto onde se decide se houve dinheiro.

Estes casos existem porque a versão anterior comparava `json.dumps(payload)`
inteiro por substring: `{"status": "unpaid"}` contém "paid" e a chave
`amountPaid` também — pagamentos falhados eram confirmados, emitindo bilhete
e creditando carteiras sem entrada de dinheiro.
"""

from django.test import SimpleTestCase

from apps.payments.services.gateway import _interpret_response


class InterpretResponseTests(SimpleTestCase):
    def _result(self, payload, provider="MPESA", status_code=200):
        return _interpret_response(provider, status_code, payload)[0]

    # --- o bug que motivou o teste ---
    def test_unpaid_nao_e_sucesso(self):
        self.assertEqual(self._result({"status": "unpaid"}), "FAILED")

    def test_chave_amount_paid_nao_e_sucesso(self):
        # "amountPaid" como CHAVE não pode confirmar nada
        self.assertEqual(self._result({"amountPaid": 0, "status": "error"}), "FAILED")

    def test_negacao_nao_e_sucesso(self):
        self.assertNotEqual(self._result({"message": "payment not completed"}), "SUCCESS")

    # --- sucessos legítimos ---
    def test_codigo_mpesa_confirma(self):
        self.assertEqual(self._result({"output_ResponseCode": "INS-0"}), "SUCCESS")

    def test_estado_success_confirma(self):
        self.assertEqual(self._result({"status": "SUCCESS"}), "SUCCESS")

    def test_estado_pago_confirma(self):
        self.assertEqual(self._result({"status": "paid"}), "SUCCESS")

    # --- falhas e estados intermédios ---
    def test_saldo_insuficiente_falha(self):
        self.assertEqual(self._result({"message": "Insufficient balance"}), "FAILED")

    def test_cancelado_pelo_cliente_falha(self):
        self.assertEqual(self._result({"status": "cancelled"}), "FAILED")

    def test_timeout_mpesa(self):
        self.assertEqual(self._result({"output_ResponseCode": "INS-9"}), "TIMEOUT")

    def test_timeout_emola(self):
        self.assertEqual(self._result({"code": "2007"}, provider="EMOLA"), "TIMEOUT")

    def test_sem_estado_fica_pendente(self):
        self.assertEqual(self._result({"data": {"requestId": "abc123"}}), "PENDING")

    def test_http_erro_falha(self):
        self.assertEqual(self._result({"status": "success"}, status_code=500), "FAILED")
