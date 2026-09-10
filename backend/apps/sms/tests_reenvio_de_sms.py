"""Que SMS falhados vale a pena reenviar — e quais nunca.

2026-09-10, em produção: `candidatos=100 reenviados=100 entregues=0
permanentes=0`, de 10 em 10 minutos, indefinidamente. Seiscentas tentativas
por hora, nenhuma entregue, e a fila não drenava.

Três defeitos encadeados:

* a lista de erros definitivos era `("missing_phone", "invalid_msisdn")`, e o
  `invalid_msisdn` **não era escrito em lado nenhum** — nunca batia certo;
* olhava para `metadata["error"]`, que só existe nas falhas ANTERIORES ao
  pedido. Quando o provedor recusa, o que fica é o `response_body` dele — e a
  Bluteki responde em português e com HTTP 500, não 400:
  `{"success":false,"message":"Internal error: Número de telefone inválido"}`;
* cada reenvio falhado criava um registo NOVO com `attempts=0`, que voltava a
  ser candidato. A fila alimentava-se a si própria.
"""

from __future__ import annotations

from django.test import TestCase
from django.utils import timezone

from apps.sms.management.commands.retry_failed_sms import falha_definitiva
from apps.sms.models import SmsMessage


def _sms(numero="841234567", **metadata) -> SmsMessage:
    return SmsMessage(phone_number=numero, body="x", metadata=metadata)


class ClassificacaoDaFalhaTests(TestCase):
    # --- o que NÃO se repete -------------------------------------------

    def test_a_resposta_em_portugues_da_bluteki_e_definitiva(self):
        """O caso real. Repare que vem em HTTP 500, e mesmo assim é definitivo."""
        s = _sms(response_status=500, response_body=(
            '{"success":false,"message":"Internal error: '
            'N\\u00famero de telefone inv\\u00e1lido: 078229722"}'))
        s.phone_number = "078229722"
        definitiva, motivo = falha_definitiva(s)
        self.assertTrue(definitiva)
        self.assertEqual(motivo, "msisdn_invalido")

    def test_numero_que_nunca_podia_ter_sido_enviado(self):
        for mau in ("078229722", "12345", "8412345678901", "0", ""):
            with self.subTest(numero=mau):
                self.assertTrue(falha_definitiva(_sms(mau))[0], mau)

    def test_provedor_recusa_o_destino_com_numero_valido(self):
        s = _sms("841234567", response_status=500,
                 response_body='{"message":"invalid recipient"}')
        self.assertEqual(falha_definitiva(s)[1], "destino_recusado")

    def test_erro_nosso_antes_de_haver_pedido(self):
        s = _sms("841234567", error="missing_phone")
        self.assertEqual(falha_definitiva(s)[1], "missing_phone")

    def test_4xx_e_pedido_mal_feito(self):
        s = _sms("841234567", response_status=401, response_body="unauthorized")
        self.assertEqual(falha_definitiva(s)[1], "http_401")

    # --- o que SE repete ------------------------------------------------

    def test_500_generico_repete_se(self):
        """A operadora engasgou-se. Daqui a dez minutos pode passar."""
        s = _sms("841234567", response_status=500, response_body="Internal Server Error")
        self.assertFalse(falha_definitiva(s)[0])

    def test_sem_resposta_nenhuma_repete_se(self):
        s = _sms("841234567", response_status=0, response_body="timed out")
        self.assertFalse(falha_definitiva(s)[0])

    def test_408_e_429_sao_convites_a_tentar_de_novo(self):
        for estado in (408, 429):
            with self.subTest(estado=estado):
                s = _sms("841234567", response_status=estado, response_body="slow down")
                self.assertFalse(falha_definitiva(s)[0], estado)

    def test_todos_os_prefixos_mocambicanos_passam(self):
        for n in ("841234567", "851234567", "861234567", "871234567", "258841234567"):
            with self.subTest(numero=n):
                s = _sms(n, response_status=500, response_body="Internal Server Error")
                self.assertFalse(falha_definitiva(s)[0], n)


class AFilaTemDeDrenarTests(TestCase):
    """O reenvio não pode criar trabalho para si próprio."""

    def _falhado(self, **metadata) -> SmsMessage:
        return SmsMessage.objects.create(
            phone_number="841234567", body="x",
            status=SmsMessage.Status.FAILED,
            metadata={"response_status": 500, "response_body": "Internal Server Error", **metadata},
        )

    def test_uma_tentativa_de_reenvio_nao_volta_a_ser_candidata(self):
        from django.core.management import call_command
        from io import StringIO

        self._falhado()                      # original
        self._falhado(retry_of=1)            # já é um reenvio
        saida = StringIO()
        call_command("retry_failed_sms", "--dry-run", stdout=saida)
        # Só o original conta. Sem isto, cada passagem duplicava a fila.
        self.assertIn("candidatos=1", saida.getvalue())

    def test_o_numero_invalido_sai_da_fila_a_primeira(self):
        from django.core.management import call_command
        from io import StringIO

        mau = SmsMessage.objects.create(
            phone_number="078229722", body="x", status=SmsMessage.Status.FAILED,
            metadata={"response_status": 500, "response_body": "Numero de telefone invalido"},
        )
        saida = StringIO()
        call_command("retry_failed_sms", stdout=saida)
        self.assertIn("permanentes=1", saida.getvalue())
        mau.refresh_from_db()
        self.assertEqual(mau.metadata.get("falha_definitiva"), "msisdn_invalido")
        # E na passagem seguinte já nem é candidato.
        saida2 = StringIO()
        call_command("retry_failed_sms", "--dry-run", stdout=saida2)
        self.assertIn("candidatos=0", saida2.getvalue())
