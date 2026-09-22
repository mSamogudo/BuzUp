# -*- coding: utf-8 -*-
"""O que sai nos documentos, e nao o que esta na base.

Estes testes nasceram de um relatorio que o cliente devolveu com cinco
queixas. Nenhuma era um erro de calculo — eram todas de apresentacao, que e
precisamente o que ninguem testa e toda a gente ve.
"""
from __future__ import annotations

from datetime import datetime, timezone as utc
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.reports.exporters import (
    _apresentar, _dinheiro, _e_intocavel, _larguras_das_colunas,
    _rotulo_de_coluna, _rotulo_de_total, _stringify,
)


class ADataEHoraDeMaputo(TestCase):
    """O PDF mostrava a partida das 05:00 como «03:00».

    O Django guarda tudo em UTC e o `strftime` escreve o fuso que a data
    traz. O horario inteiro saia com duas horas de atraso, num documento que
    o operador usa para saber a que horas sai o autocarro.
    """

    def test_uma_data_utc_sai_em_hora_local(self):
        partida = datetime(2026, 9, 25, 3, 0, tzinfo=utc.utc)   # 05:00 em Maputo
        self.assertEqual(_stringify(partida), "25/09/2026 05:00")

    def test_a_da_tarde_tambem(self):
        partida = datetime(2026, 9, 25, 13, 30, tzinfo=utc.utc)  # 15:30 em Maputo
        self.assertEqual(_stringify(partida), "25/09/2026 15:30")

    def test_uma_data_sem_fuso_nao_rebenta(self):
        self.assertEqual(_stringify(datetime(2026, 9, 25, 5, 0)), "25/09/2026 05:00")

    def test_o_dia_vem_a_frente_do_mes(self):
        """Em Mocambique le-se 25/09. «09/25» num relatorio de fronteira e um
        engano a espera de acontecer."""
        self.assertTrue(_stringify(datetime(2026, 9, 25, 5, 0)).startswith("25/09"))


class ODinheiro(TestCase):
    def test_le_se_como_em_mocambique(self):
        self.assertEqual(_dinheiro("68650.00"), "68 650,00 MZN")
        self.assertEqual(_dinheiro("1650"), "1 650,00 MZN")
        self.assertEqual(_dinheiro(Decimal("1234567.5")), "1 234 567,50 MZN")

    def test_o_separador_e_um_espaco_que_o_pdf_sabe_desenhar(self):
        """O espaco fino inquebravel (U+202F) nao existe no Helvetica: saiu um
        quadrado preto no meio do total — «68<quadrado>650,00»."""
        self.assertNotIn(" ", _dinheiro("68650.00"))
        self.assertNotIn(" ", _dinheiro("68650.00"))

    def test_o_que_nao_e_numero_passa_intacto(self):
        self.assertEqual(_dinheiro("—"), "—")

    def test_na_tabela_vai_sem_a_moeda(self):
        """A moeda esta no cabecalho da coluna. Repetida em 62 linhas so
        rouba largura ao numero."""
        self.assertEqual(_apresentar("amount", "1650.00"), "1 650,00")
        self.assertEqual(_rotulo_de_coluna("amount", "Valor"), "Valor (MZN)")

    def test_no_excel_vai_como_NUMERO(self):
        """Formatar o dinheiro em texto deixava a folha bonita e impossivel
        de somar — e somar a coluna e a primeira coisa que quem a recebe faz."""
        valor = _apresentar("amount", "1650.00", para="xlsx")
        self.assertIsInstance(valor, float)
        self.assertEqual(valor, 1650.0)


class OsEstados(TestCase):
    def test_saem_por_escrito(self):
        self.assertEqual(_apresentar("status", "confirmed"), "Confirmado")
        self.assertEqual(_apresentar("status", "failed"), "Falhado")

    def test_um_estado_desconhecido_ainda_se_le(self):
        self.assertEqual(_apresentar("status", "meio_pago"), "Meio pago")

    def test_vazio_nao_se_confunde_com_zero(self):
        """Uma celula em branco le-se como «nao houve». Aqui quer dizer «nao
        soubemos dizer», e o documento tem de o distinguir."""
        self.assertEqual(_apresentar("status", ""), "—")


class OsRotulosDosCartoes(TestCase):
    def test_estao_em_portugues(self):
        """Sairam «COUNT» e «CONFIRMED COUNT» — nomes das chaves do
        dicionario, no primeiro sitio que se le no documento."""
        self.assertEqual(_rotulo_de_total("count"), "Linhas")
        self.assertEqual(_rotulo_de_total("confirmed_count"), "Confirmadas")
        self.assertEqual(_rotulo_de_total("total_amount"), "Total")

    def test_uma_chave_nova_nao_sai_com_underscores(self):
        self.assertEqual(_rotulo_de_total("algo_novo"), "Algo novo")


class AsLarguras(TestCase):
    """«1650…» num relatorio financeiro nao e um numero mais curto — e outro
    numero."""

    class TelaFalsa:
        @staticmethod
        def stringWidth(txt, font, size):
            return len(txt or "") * size * 0.5

    def test_o_dinheiro_e_as_datas_sao_intocaveis(self):
        for key in ("amount", "fare_amount", "created_at", "ida_at", "status"):
            self.assertTrue(_e_intocavel(key), key)
        for key in ("reference", "route_code", "passageiro"):
            self.assertFalse(_e_intocavel(key), key)

    def test_a_coluna_do_dinheiro_recebe_o_que_precisa(self):
        """Mesmo ao lado de referencias longas, que antes lhe comiam a
        largura toda."""
        colunas = [
            ("reference", "Pagamento"), ("sale_reference", "Venda"),
            ("route_code", "Rota"), ("amount", "Valor"),
        ]
        linhas = [{
            "reference": "PAY-AS-57735E7CA2914B2C3D4E5F6A7B8C9D",
            "sale_reference": "AS-57735E7CA2914B2C3D4E5F6A7B8C9D",
            "route_code": "RT-MAPUTO-X-NELSPRUIT",
            "amount": "1650.00",
        }]
        c = self.TelaFalsa()
        larguras = _larguras_das_colunas(c, colunas, linhas, 800.0)

        i = [k for k, _ in colunas].index("amount")
        texto = _apresentar("amount", "1650.00")
        precisa = c.stringWidth(texto, "Helvetica", 8)
        self.assertGreaterEqual(larguras[i], precisa,
                                "a coluna do dinheiro tem de caber sem cortar")

    def test_a_soma_das_larguras_cabe_na_pagina(self):
        colunas = [(f"c{i}", f"Coluna {i}") for i in range(8)] + [("amount", "Valor")]
        linhas = [{f"c{i}": "x" * 20 for i in range(8)} | {"amount": "1650.00"}]
        larguras = _larguras_das_colunas(self.TelaFalsa(), colunas, linhas, 800.0)
        self.assertLessEqual(sum(larguras), 800.0 + 0.5)
