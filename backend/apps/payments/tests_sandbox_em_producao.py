"""Producao nao pode cobrar pelo simulador.

O que aconteceu a 19/08/2026: o M-Pesa de producao estava a apontar ao
shortcode `171717` — o simulador. Ele aceita QUALQUER PIN e responde sempre
"Request processed successfully". Uma venda de 1650 MZN deu-se por paga, o
bilhete foi emitido e o lugar ficou ocupado, sem dinheiro nenhum ter saido da
conta de ninguem.

A causa nao foi a configuracao estar errada — o ficheiro ja tinha o shortcode
certo desde o dia 15. Foi o contentor ter sido criado ANTES de o ficheiro ser
corrigido: `docker restart` nao rele o `env_file`, so a recriacao o faz. Quer
dizer que uma configuracao correcta em disco nao garante nada; o que conta e o
que o processo tem em memoria.

Por isso a guarda vive no codigo e olha para a configuracao EFECTIVA, e nao
para o ficheiro. Em producao, apontar ao simulador nao e um defeito de
configuracao: e uma porta aberta para levantar bilhetes sem pagar.
"""

from __future__ import annotations

from decimal import Decimal
from unittest import mock

from django.test import SimpleTestCase, override_settings

from apps.payments.services.gateway import (
    MPESA_SANDBOX_SHORTCODE,
    MobileWalletGateway,
    usando_sandbox,
)


class DeteccaoDoSandboxTests(SimpleTestCase):
    def test_reconhece_o_shortcode_do_simulador(self):
        self.assertTrue(usando_sandbox({"shortcode": "171717"}))

    def test_o_shortcode_de_producao_nao_e_sandbox(self):
        self.assertFalse(usando_sandbox({"shortcode": "901913"}))

    def test_sem_shortcode_nao_e_sandbox(self):
        self.assertFalse(usando_sandbox({}))
        self.assertFalse(usando_sandbox({"shortcode": ""}))

    def test_a_constante_e_a_que_o_incidente_usou(self):
        self.assertEqual(MPESA_SANDBOX_SHORTCODE, "171717")


class DefinicaoDoAmbienteTests(SimpleTestCase):
    """Um ambiente novo nasce protegido."""

    def test_por_omissao_nao_se_simula(self):
        from config.settings import base

        self.assertIs(
            base.config("PAYMENTS_ALLOW_SANDBOX", default=False, cast=bool), False,
            "o default tem de ser 'nao simular': quem quiser simular que o diga",
        )

    def test_producao_nao_declara_que_pode_simular(self):
        """Se prod.py um dia o declarar, este teste avisa."""
        from pathlib import Path

        prod = Path(__file__).resolve().parents[2] / "config" / "settings" / "prod.py"
        self.assertNotIn("PAYMENTS_ALLOW_SANDBOX", prod.read_text(encoding="utf-8"))


@override_settings(PAYMENTS_ALLOW_SANDBOX=False, PAYMENT_GATEWAY_PROVIDER="AUTO")
class RecusaEmProducaoTests(SimpleTestCase):
    """A venda para aqui, e diz porque."""

    def _gateway(self, shortcode):
        gw = MobileWalletGateway("MPESA")
        gw.config = {**gw.config, "shortcode": shortcode}
        return gw

    def test_com_o_simulador_a_venda_e_recusada(self):
        gw = self._gateway("171717")
        with mock.patch("apps.payments.services.gateway._provider_is_configured", return_value=True):
            r = gw.initiate_payment("PAY-1", Decimal("1650.00"), "841234567")
        self.assertFalse(r.success)
        self.assertFalse(r.pending)
        self.assertIn("simulador", r.error)

    def test_nao_chega_a_contactar_o_gateway(self):
        """Recusar depois de contactar ja seria tarde: o dinheiro podia mexer-se."""
        gw = self._gateway("171717")
        with mock.patch("apps.payments.services.gateway._provider_is_configured", return_value=True), \
             mock.patch("apps.payments.services.gateway._post_with_retry") as chamada:
            gw.initiate_payment("PAY-2", Decimal("1650.00"), "841234567")
        chamada.assert_not_called()

    @override_settings(PAYMENTS_ALLOW_SANDBOX=True)
    def test_onde_o_simulador_e_permitido_ele_funciona(self):
        """Staging e desenvolvimento simulam — e para isso que o simulador existe.

        A primeira versao desta guarda olhava para `DEBUG`, e staging tambem
        corre com `DEBUG=False`: bloqueou os pagamentos de teste durante uma
        hora. Quem decide agora e uma definicao propria, que cada ambiente
        declara — e cujo default e "nao simular", para um ambiente novo nascer
        protegido.
        """
        gw = self._gateway("171717")
        with mock.patch("apps.payments.services.gateway._provider_is_configured", return_value=True), \
             mock.patch("apps.payments.services.gateway._post_with_retry",
                        return_value=(200, {"responseCode": "INS-0"}, 1)):
            r = gw.initiate_payment("PAY-3", Decimal("10.00"), "841234567")
        self.assertTrue(r.success)
