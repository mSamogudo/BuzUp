"""As regras de recurso do portal nao podem ser mais frouxas do que as reais.

O portal traz uma copia das regras dos documentos para usar enquanto
`/api/public/document-types/` nao responde. Estavam todas em "4 a 32 caracteres"
com ajuda vazia — mais permissivas do que as do servidor. O campo aceitava 13
digitos num BI (que precisa de 12 mais uma letra), deixava avancar, e a compra
rebentava no fim com um erro que o comprador nem via.

Um recurso mais frouxo do que a regra real nao e um recurso: e uma armadilha
que so aparece quando a rede esta lenta.

Este teste le o ficheiro do portal e compara-o com a fonte da verdade. Se
alguem mudar um formato num lado e esquecer o outro, falha aqui — que e o unico
sitio onde a divergencia se ve antes de chegar a um passageiro.
"""

from __future__ import annotations

import re
from pathlib import Path

from unittest import skipUnless

from django.test import SimpleTestCase

from apps.guest_checkouts.documents import DOCUMENT_RULES

PORTAL = (Path(__file__).resolve().parents[3]
          / "frontend" / "src" / "public" / "booking" / "BookingPage.tsx")


def _regras_do_portal() -> dict[str, dict]:
    texto = PORTAL.read_text(encoding="utf-8")
    inicio = texto.index("const DOC_FALLBACK")
    bloco = texto[inicio:texto.index("];", inicio)]
    achadas: dict[str, dict] = {}
    padrao = re.compile(
        r'value:\s*"(?P<value>\w+)".*?pattern:\s*"(?P<pattern>[^"]+)".*?'
        r'max_length:\s*(?P<max>\d+)',
        re.S,
    )
    for m in padrao.finditer(bloco):
        achadas[m.group("value")] = {
            # No ficheiro TypeScript a barra vem duplicada; o valor em memoria
            # tem uma so.
            "pattern": m.group("pattern").replace("\\\\", "\\"),
            "max_length": int(m.group("max")),
        }
    return achadas


# O contentor do backend nao tem a arvore do portal. Ali este teste salta, e
# diz porque: e melhor uma falta declarada do que uma verificacao que finge
# passar. Corre nas maquinas de desenvolvimento e em qualquer CI com o
# repositorio inteiro — que e onde a divergencia se introduz.
@skipUnless(PORTAL.is_file(), f"sem a arvore do portal em {PORTAL}")
class RegrasDoPortalTests(SimpleTestCase):
    def test_o_portal_conhece_os_mesmos_tipos(self):
        self.assertEqual(set(_regras_do_portal()), set(DOCUMENT_RULES))

    def test_os_formatos_sao_os_mesmos(self):
        portal = _regras_do_portal()
        for tipo, regra in DOCUMENT_RULES.items():
            with self.subTest(tipo=tipo):
                self.assertEqual(
                    portal[tipo]["pattern"], regra["pattern"],
                    f"o portal aceita '{portal[tipo]['pattern']}' e o servidor "
                    f"exige '{regra['pattern']}' — o comprador preenche o campo "
                    f"e leva com a recusa no fim",
                )

    def test_os_limites_sao_os_mesmos(self):
        portal = _regras_do_portal()
        for tipo, regra in DOCUMENT_RULES.items():
            with self.subTest(tipo=tipo):
                self.assertEqual(portal[tipo]["max_length"], regra["max_length"])
