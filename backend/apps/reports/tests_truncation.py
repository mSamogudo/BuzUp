"""O corte dos relatorios tem de ser visivel.

Cada relatorio le no maximo 5000 linhas, porque o documento e construido
inteiro em memoria antes de sair. O problema nao era o tecto — era o silencio:
um relatorio financeiro com 7000 movimentos saia com 5000 e com ar de completo,
e quem reconciliava so dava pela diferenca ao nao bater certo com a
contabilidade.
"""

from __future__ import annotations

import csv
from io import StringIO

from django.test import TestCase

from apps.reports.api.views import _warn_if_truncated
from apps.reports.builder import MAX_ROWS, RowSet, _capped


class RowSetTests(TestCase):
    def test_exactly_the_cap_is_not_truncated(self):
        """5000 linhas exactas nao sao um corte — nao ha aviso a dar."""
        rows = _capped([{"i": i} for i in range(MAX_ROWS)])
        self.assertEqual(len(rows), MAX_ROWS)
        self.assertFalse(rows.truncated)

    def test_one_row_over_the_cap_is_reported(self):
        """Os construtores pedem MAX_ROWS+1 a base de dados justamente para
        distinguir 'sao mesmo 5000' de 'sao mais de 5000'."""
        rows = _capped([{"i": i} for i in range(MAX_ROWS + 1)])
        self.assertEqual(len(rows), MAX_ROWS)
        self.assertTrue(rows.truncated)

    def test_short_report_is_untouched(self):
        rows = _capped([{"i": 1}, {"i": 2}])
        self.assertEqual(len(rows), 2)
        self.assertFalse(rows.truncated)

    def test_rowset_behaves_like_a_list(self):
        """Os renderizadores e o `aggregate_totals` tratam isto como uma lista."""
        rows = _capped([{"i": 1}, {"i": 2}])
        self.assertIsInstance(rows, list)
        self.assertEqual(rows[0], {"i": 1})
        self.assertEqual([r["i"] for r in rows], [1, 2])
        self.assertEqual(len(list(rows)), 2)


class CsvWarningTests(TestCase):
    def _csv(self, truncated: bool) -> str:
        out = StringIO()
        writer = csv.writer(out)
        writer.writerow(["Data", "Valor"])
        writer.writerow(["2026-07-31", "100.00"])
        _warn_if_truncated(writer, truncated)
        return out.getvalue()

    def test_complete_file_carries_no_warning(self):
        self.assertNotIn("ATENCAO", self._csv(False))

    def test_truncated_file_says_so_inside_the_file(self):
        """Um cabecalho HTTP nao sobrevive a um ficheiro guardado e reenviado;
        o aviso tem de estar no proprio CSV."""
        content = self._csv(True)
        self.assertIn("ATENCAO", content)
        self.assertIn(str(MAX_ROWS), content)
        # E na ultima linha, para nao desalinhar as colunas dos dados.
        self.assertTrue(content.rstrip().splitlines()[-1].startswith("ATENCAO"))
