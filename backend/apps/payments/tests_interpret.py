"""Interpretação da resposta do gateway — o ponto onde se decide se houve dinheiro.

Estes casos existem porque a versão anterior comparava `json.dumps(payload)`
inteiro por substring: `{"status": "unpaid"}` contém "paid" e a chave
`amountPaid` também — pagamentos falhados eram confirmados, emitindo bilhete
e creditando carteiras sem entrada de dinheiro.
"""

from django.test import SimpleTestCase

from apps.payments.services.gateway import _desembrulhar_pesquisa, _interpret_response


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


# Respostas REAIS do `/search/mpesa/c2b` da Payless, copiadas a 2026-09-03.
PESQUISA_PAGO = {"data": [{
    "msisdn": "258843923574", "amount": "6600", "responseCode": "INS-0",
    "transactionID": "DI35LFZBWZL", "conversationID": "ca6b4b0147444dca91788edd8d30f970",
    "responseDescription": "Request processed successfully",
    "transactionReference": "MPBC49262D46054E1DB9", "thirdPartyReference": "BZBC49262D46054E1DB9",
    "transactionStatus": 200, "environment": "production",
}]}
PESQUISA_SEM_PIN = {"data": [{
    "msisdn": "258843923574", "amount": "6600", "responseCode": "INS-9",
    "transactionID": "N/A", "conversationID": "5316765a69de4160b34520c26c302d71",
    "responseDescription": "Request timeout",
    "transactionReference": "MPF5D074EC3DF84B96BD", "thirdPartyReference": "BZF5D074EC3DF84B96BD",
    "transactionStatus": 408, "environment": "production",
}]}
PESQUISA_DESCONHECIDA = {"data": []}


class PesquisaDaPaylessTests(SimpleTestCase):
    """A pesquisa devolve `data` como LISTA — e a interpretacao so lia dicionarios.

    A 2026-09-03 a reconciliacao tinha na mao `INS-0` e o `transactionID` da
    operadora e leu "pendente": 6.600 MT ficaram sem bilhete ate alguem olhar.
    """

    def _lido(self, payload, ref):
        return _interpret_response("MPESA", 200, _desembrulhar_pesquisa(payload, ref))

    def test_pago_na_lista_e_sucesso_com_a_referencia_da_operadora(self):
        resultado, _, ext = self._lido(PESQUISA_PAGO, "MPBC49262D46054E1DB9")
        self.assertEqual(resultado, "SUCCESS")
        self.assertEqual(ext, "DI35LFZBWZL")

    def test_sem_pin_na_lista_e_timeout_da_operadora(self):
        resultado, _, ext = self._lido(PESQUISA_SEM_PIN, "MPF5D074EC3DF84B96BD")
        self.assertEqual(resultado, "TIMEOUT")
        self.assertEqual(ext, "", "'N/A' nao e uma referencia")

    def test_referencia_desconhecida_fica_pendente(self):
        # `data: []`: a operadora nao conhece o pedido. Nao ha por onde decidir.
        resultado, _, _ = self._lido(PESQUISA_DESCONHECIDA, "MPXXXX")
        self.assertEqual(resultado, "PENDING")

    def test_escolhe_o_elemento_da_nossa_referencia(self):
        # Duas transaccoes na lista: fica a nossa, nao a primeira.
        dois = {"data": [PESQUISA_SEM_PIN["data"][0], PESQUISA_PAGO["data"][0]]}
        resultado, _, ext = self._lido(dois, "MPBC49262D46054E1DB9")
        self.assertEqual((resultado, ext), ("SUCCESS", "DI35LFZBWZL"))

    def test_sem_a_desembrulhar_lia_se_pendente(self):
        """O defeito, fixado para nao voltar por 'simplificacao'."""
        resultado, _, _ = _interpret_response("MPESA", 200, PESQUISA_PAGO)
        self.assertEqual(resultado, "PENDING")
