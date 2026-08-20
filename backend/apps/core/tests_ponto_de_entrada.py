"""O `manage.py` nao pode adivinhar o ambiente.

Assumia `config.settings.dev` quando `DJANGO_SETTINGS_MODULE` nao estava
definido. Num servidor isso significa correr com `DEBUG=True`,
`ALLOWED_HOSTS=["*"]`, CORS aberto e o simulador de pagamentos permitido —
contra a base de dados real, e sem um aviso.

Um valor por omissao que escolhe o ambiente MAIS permissivo esta ao contrario.
O `wsgi.py` mostra como deve ser: o valor por omissao dele e `prod`, o mais
restritivo, e por isso esquecer a variavel deixa o servidor protegido em vez de
exposto.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

RAIZ = Path(__file__).resolve().parents[2]
MANAGE = RAIZ / "manage.py"


class PontoDeEntradaTests(SimpleTestCase):
    def test_sem_a_variavel_recusa_correr(self):
        r = subprocess.run(
            [sys.executable, str(MANAGE), "check"],
            capture_output=True, text=True, cwd=str(RAIZ),
            env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"},
        )
        self.assertNotEqual(r.returncode, 0, "correu sem saber em que ambiente estava")
        self.assertIn("DJANGO_SETTINGS_MODULE", r.stderr)

    def test_a_mensagem_diz_o_que_fazer(self):
        r = subprocess.run(
            [sys.executable, str(MANAGE), "check"],
            capture_output=True, text=True, cwd=str(RAIZ),
            env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"},
        )
        for ambiente in ("dev", "staging", "prod"):
            self.assertIn(f"config.settings.{ambiente}", r.stderr,
                          "quem tropeca nisto tem de saber logo o que escrever")

    def test_nao_ha_omissao_escondida_no_ficheiro(self):
        texto = MANAGE.read_text(encoding="utf-8")
        self.assertNotIn('setdefault("DJANGO_SETTINGS_MODULE"', texto)

    def test_o_servidor_por_omissao_arranca_no_ambiente_MAIS_restritivo(self):
        """Se um dia alguem trocar isto por `dev`, o teste avisa."""
        for ficheiro in ("wsgi.py", "asgi.py"):
            texto = (RAIZ / "config" / ficheiro).read_text(encoding="utf-8")
            with self.subTest(ficheiro=ficheiro):
                self.assertIn("config.settings.prod", texto)
                self.assertNotIn("config.settings.dev", texto)
