"""Arredondamento do valor exibido em moeda estrangeira.

Uma divisao por uma taxa quase nunca da um numero redondo: 1000 MZN a 3,87 sao
258,398... rands. O passageiro ficava a olhar para centavos que ninguem no
balcao consegue dar em troco.

Arredonda-se sempre PARA CIMA, pela mesma razao que a taxa e posta abaixo do
mercado: a cobranca e em meticais e a conversao real acontece na carteira do
passageiro. Mostrar-lhe MENOS rands do que lhe vao sair da conta e uma surpresa
negativa e uma queixa; mostrar ligeiramente mais e uma surpresa positiva.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from apps.fares.models import ExchangeRate


class ArredondamentoTests(TestCase):
    def _taxa(self, passo="1.00", valor="3.8700"):
        ExchangeRate.objects.all().delete()
        return ExchangeRate.objects.create(
            currency="ZAR", rate_to_mzn=Decimal(valor),
            rounding_step=Decimal(passo), is_active=True,
        )

    def test_unidade_inteira_elimina_os_centavos(self):
        self._taxa("1.00")
        valor, taxa = ExchangeRate.convert_from_mzn(Decimal("1000.00"), "ZAR")
        self.assertEqual(valor, Decimal("259.00"))  # 258,398... para cima
        self.assertEqual(taxa, Decimal("3.8700"))

    def test_arredonda_sempre_para_cima(self):
        """Para baixo mostraria menos rands do que saem da conta do passageiro."""
        self._taxa("1.00")
        valor, _ = ExchangeRate.convert_from_mzn(Decimal("1200.00"), "ZAR")
        self.assertEqual(valor, Decimal("311.00"))  # 310,077... para cima

    def test_valor_ja_redondo_nao_sobe(self):
        self._taxa("1.00", valor="4.0000")
        valor, _ = ExchangeRate.convert_from_mzn(Decimal("1200.00"), "ZAR")
        self.assertEqual(valor, Decimal("300.00"))

    def test_multiplos_de_cinco(self):
        self._taxa("5.00")
        valor, _ = ExchangeRate.convert_from_mzn(Decimal("1000.00"), "ZAR")
        self.assertEqual(valor, Decimal("260.00"))  # 258,398... -> 260

    def test_multiplos_de_dez(self):
        self._taxa("10.00")
        valor, _ = ExchangeRate.convert_from_mzn(Decimal("1000.00"), "ZAR")
        self.assertEqual(valor, Decimal("260.00"))

    def test_ao_centavo_mantem_o_comportamento_antigo(self):
        self._taxa("0.01")
        valor, _ = ExchangeRate.convert_from_mzn(Decimal("1000.00"), "ZAR")
        self.assertEqual(valor, Decimal("258.40"))

    def test_o_bilhete_congela_o_valor_arredondado(self):
        """O que o passageiro viu e o que fica impresso — nao dois numeros."""
        from apps.fares.services import display_snapshot

        self._taxa("1.00")
        moeda, valor, taxa = display_snapshot(Decimal("1000.00"), "ZAR")
        self.assertEqual(moeda, "ZAR")
        self.assertEqual(valor, Decimal("259.00"))
        self.assertEqual(taxa, Decimal("3.8700"))

    def test_sem_taxa_configurada_fica_em_meticais(self):
        from apps.fares.services import display_snapshot

        ExchangeRate.objects.all().delete()
        self.assertEqual(display_snapshot(Decimal("1000.00"), "ZAR"), ("MZN", None, None))
