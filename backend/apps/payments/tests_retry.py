"""Repeticao de um pedido de pagamento que morreu do lado da operadora.

O M-Pesa devolve `{"message": "Server Error"}` de forma intermitente: em
2026-08-04, quatro de cinco recargas identicas falharam assim em dois minutos e
a quinta passou. Desistir a primeira tentativa transformava uma falha da
operadora numa recarga falhada para o passageiro.

**O que torna a repeticao segura** e a referencia enviada ser DERIVADA da
nossa: o repetido chega a operadora como o mesmo pagamento e ela deduplica.
Com a referencia aleatoria de antes, repetir podia cobrar duas vezes — e por
isso e que esta suite comeca por fixar a referencia.
"""

from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from apps.payments.services.gateway import (
    PAYMENT_MAX_ATTEMPTS,
    _compact_reference,
    _interpret_response,
    _is_transient_gateway_failure,
)


class ReferenciaDerivadaTests(SimpleTestCase):
    def test_mesma_referencia_nossa_da_sempre_a_mesma_da_operadora(self):
        # A base de tudo: sem isto, repetir um pedido cria uma segunda
        # transacao na operadora e o passageiro paga duas vezes.
        a = _compact_reference("BZ", "TOP-E1DF17AA531C4510A5")
        b = _compact_reference("BZ", "TOP-E1DF17AA531C4510A5")
        self.assertEqual(a, b)

    def test_referencias_diferentes_nao_colidem(self):
        a = _compact_reference("BZ", "TOP-E1DF17AA531C4510A5")
        b = _compact_reference("BZ", "TOP-CCED8D1DAC5A4BF8B3")
        self.assertNotEqual(a, b)

    def test_cabe_no_limite_da_operadora_e_e_alfanumerica(self):
        for ref in ["TOP-E1DF17AA531C4510A5", "PAY-GC-998D0A36AC0A4CF181",
                    "PAY-AS-B8E89914232443A68E", "S-1"]:
            saida = _compact_reference("BZ", ref)
            self.assertLessEqual(len(saida), 20, msg=ref)
            self.assertTrue(saida.isalnum(), msg=saida)
            self.assertTrue(saida.startswith("BZ"), msg=saida)

    def test_da_para_voltar_a_nossa_referencia(self):
        # Reconciliacao: uma linha do extracto tem de poder ser ligada ao
        # pagamento que a originou. Antes era impossivel — a referencia
        # enviada era timestamp + aleatorio.
        nossa = "TOP-E1DF17AA531C4510A5"
        enviada = _compact_reference("BZ", nossa)
        self.assertIn(enviada[2:], nossa.replace("-", ""))

    def test_sem_referencia_nossa_nao_rebenta(self):
        self.assertTrue(_compact_reference("BZ", "").startswith("BZ"))


class QuandoRepetirTests(SimpleTestCase):
    def test_repete_o_que_morreu_do_lado_da_operadora(self):
        casos = [
            (500, {"message": "Server Error"}),
            (502, {"detail": "Bad Gateway"}),
            (503, {"message": "Service Unavailable"}),
            (408, {"detail": "Request timed out."}),
            (200, {"message": "Server Error"}),   # 200 com corpo de erro
        ]
        for status, corpo in casos:
            self.assertTrue(_is_transient_gateway_failure(status, corpo),
                            msg=f"{status} {corpo}")

    def test_NAO_repete_uma_resposta_da_operadora(self):
        # Estas sao decisoes sobre o pagamento. Repetir seria pedir o PIN ao
        # passageiro uma segunda vez por uma coisa que ja foi respondida.
        casos = [
            (200, {"responseCode": "INS-0", "responseDescription": "Request processed successfully"}),
            (200, {"message": "Customer did not enter PIN", "errorCode": "11"}),
            (400, {"message": "Insufficient balance"}),
            (401, {"message": "Unauthorized"}),
        ]
        for status, corpo in casos:
            self.assertFalse(_is_transient_gateway_failure(status, corpo),
                             msg=f"{status} {corpo}")


class DuplicadoTests(SimpleTestCase):
    def test_duplicado_e_pedido_aceite_e_nao_falha(self):
        # So chega aqui numa repeticao, e a repeticao vai com a MESMA
        # referencia — o que esta do outro lado e o nosso pagamento a espera
        # do PIN. Marcar como falha recusava um pagamento em curso.
        for corpo in [{"message": "Duplicate transaction"},
                      {"responseCode": "INS-10"},
                      {"responseCode": "2005"}]:
            resultado, detalhe, _ = _interpret_response("MPESA", 200, corpo)
            self.assertEqual(resultado, "PENDING", msg=corpo)
            self.assertTrue(detalhe)


class MensagemAoPassageiroTests(SimpleTestCase):
    def test_erro_cru_da_operadora_nao_chega_ao_ecra(self):
        _, detalhe, _ = _interpret_response("MPESA", 500, {"message": "Server Error"})
        self.assertNotIn("server error", detalhe.lower())
        self.assertIn("M-Pesa", detalhe)


@override_settings(
    MPESA_TRANSPORT="PAYLESS",
    PAYLESS_MPESA_BEARER_TOKEN="token-de-teste",
    MPESA_C2B_URL="https://payless.bluteki.com/api/v2.0/c2b",
    # Um shortcode de PRODUCAO de proposito. Estes testes sao sobre repeticao,
    # nao sobre o simulador — e usar o `171717` aqui era testar o caminho que
    # producao nunca deve percorrer (ver `tests_sandbox_em_producao`).
    MPESA_SHORTCODE="901913",
    PAYMENT_MOBILE_WALLET_TIMEOUT_SECONDS=5,
)
class RepeticaoRealTests(TestCase):
    """O comportamento ponta a ponta, com a rede substituida."""

    def _gateway(self):
        from apps.payments.services.gateway import MobileWalletGateway

        return MobileWalletGateway("MPESA")

    def test_falha_transitoria_seguida_de_sucesso_confirma(self):
        respostas = [
            (500, {"message": "Server Error"}),
            (200, {"responseCode": "INS-0", "transactionID": "CeuB6Cp8A1pr",
                   "responseDescription": "Request processed successfully"}),
        ]
        enviados = []

        def fake(*, url, method, headers, timeout_seconds, body=None):
            enviados.append(body)
            return respostas[len(enviados) - 1]

        with patch("apps.payments.services.gateway._http_json_request", side_effect=fake), \
                patch("apps.payments.services.gateway.time.sleep"):
            r = self._gateway().initiate_payment(
                reference="TOP-TESTE1234567890AB",
                amount=Decimal("1000.00"), payer_phone="851576568",
            )

        self.assertTrue(r.success, msg=r.error)
        self.assertEqual(len(enviados), 2)
        # O ponto que importa: as duas tentativas foram o MESMO pagamento aos
        # olhos da operadora. Se as referencias diferissem, o passageiro podia
        # ter sido cobrado duas vezes.
        self.assertEqual(enviados[0]["thirdPartyReference"],
                         enviados[1]["thirdPartyReference"])
        self.assertEqual(enviados[0], enviados[1])

    def test_desiste_depois_do_limite_e_nao_insiste_para_sempre(self):
        chamadas = []

        def fake(*, url, method, headers, timeout_seconds, body=None):
            chamadas.append(body)
            return 500, {"message": "Server Error"}

        with patch("apps.payments.services.gateway._http_json_request", side_effect=fake), \
                patch("apps.payments.services.gateway.time.sleep"):
            r = self._gateway().initiate_payment(
                reference="TOP-TESTE1234567890AB",
                amount=Decimal("1000.00"), payer_phone="851576568",
            )

        self.assertEqual(len(chamadas), PAYMENT_MAX_ATTEMPTS)
        self.assertFalse(r.success)
        self.assertIn("M-Pesa", r.detail_message)

    def test_recusa_do_cliente_nao_e_repetida(self):
        chamadas = []

        def fake(*, url, method, headers, timeout_seconds, body=None):
            chamadas.append(body)
            return 200, {"message": "Customer did not enter PIN", "errorCode": "11"}

        with patch("apps.payments.services.gateway._http_json_request", side_effect=fake), \
                patch("apps.payments.services.gateway.time.sleep"):
            r = self._gateway().initiate_payment(
                reference="TOP-TESTE1234567890AB",
                amount=Decimal("1000.00"), payer_phone="851576568",
            )

        self.assertEqual(len(chamadas), 1,
                         "pediu o PIN outra vez por uma recusa que ja era resposta")
        self.assertFalse(r.success)
