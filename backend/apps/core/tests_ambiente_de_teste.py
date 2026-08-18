"""Um teste nunca pode gastar dinheiro nem tocar num telemovel de alguem.

`send_sms` sempre perguntou por `settings.TESTING` antes de contactar o
provedor. So que a flag nunca foi definida em lado nenhum: `getattr(settings,
"TESTING", False)` respondia sempre False, e cada execucao da suite enviava SMS
a serio — pagos, pela Bluteki, para os numeros das fixtures. Os registos das
corridas mostravam `status=202 SMS sent successfully` a dezenas.

O gateway de pagamentos tinha o mesmo problema pelo outro lado: corria com
`PAYMENT_GATEWAY_PROVIDER=AUTO` e batia no Payless a cada compra de teste. Nao
moveu dinheiro porque as credenciais de staging estao vazias — o que quer dizer
que a suite dependia de uma chave em falta para ser segura.
"""

from __future__ import annotations

from django.conf import settings
from django.test import TestCase

from apps.sms.models import SmsMessage


class AmbienteDeTesteTests(TestCase):
    def test_a_flag_de_teste_esta_ligada(self):
        self.assertTrue(
            getattr(settings, "TESTING", False),
            "sem esta flag, os testes falam com os provedores a serio",
        )

    def test_o_provedor_de_sms_esta_simulado(self):
        self.assertEqual(settings.SMS_PROVIDER, "MOCK")

    def test_o_gateway_de_pagamentos_esta_simulado(self):
        self.assertEqual(settings.PAYMENT_GATEWAY_PROVIDER, "MOCK")

    def test_enviar_um_sms_num_teste_nao_sai_do_processo(self):
        from apps.sms.services.sender import send_sms

        sms = send_sms("841234567", "isto nunca pode chegar a um telemovel")
        self.assertEqual(sms.status, SmsMessage.Status.SENT)
        self.assertEqual(sms.metadata.get("provider"), "mock")
        self.assertTrue(sms.provider_reference.startswith("MOCK-"))

    def test_o_gateway_devolvido_e_o_simulado(self):
        from apps.payments.services.gateway import MockPaymentGateway, get_payment_gateway

        self.assertIsInstance(get_payment_gateway(payer_phone="841234567"), MockPaymentGateway)
