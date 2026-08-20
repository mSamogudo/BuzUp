#!/usr/bin/env python
"""Ponto de entrada dos comandos de gestão.

**Não há módulo de definições por omissão, de propósito.**

Antes assumia-se `config.settings.dev` quando `DJANGO_SETTINGS_MODULE` não
estava definido. Parece conveniente — e é, até ao dia em que um comando corre
num servidor sem essa variável: nesse caso apanha silenciosamente `DEBUG=True`,
`ALLOWED_HOSTS=["*"]`, CORS aberto a toda a gente e o simulador de pagamentos
permitido. Tudo isso sem um aviso, e a executar contra a base de dados real.

Um valor por omissão que escolhe o ambiente MAIS permissivo está ao contrário:
o que falta deve travar, não abrir. Aqui falta e trava, com uma mensagem que
diz o que fazer.

`wsgi.py` e `asgi.py` mantêm um valor por omissão, mas o deles é
`config.settings.prod` — o mais restritivo. Aí a escolha é segura: se alguém
esquecer a variável, o servidor arranca protegido em vez de exposto.
"""
import os
import sys

AJUDA = """
DJANGO_SETTINGS_MODULE não está definido.

Indique o ambiente de forma explícita — não há valor por omissão, porque
adivinhar mal significaria correr com DEBUG ligado e pagamentos simulados
contra dados reais:

  desenvolvimento   export DJANGO_SETTINGS_MODULE=config.settings.dev
  testes            export DJANGO_SETTINGS_MODULE=config.settings.test
  staging           export DJANGO_SETTINGS_MODULE=config.settings.staging
  produção          export DJANGO_SETTINGS_MODULE=config.settings.prod

Ou de uma vez só:

  DJANGO_SETTINGS_MODULE=config.settings.dev python manage.py runserver
"""


def main():
    if not os.environ.get("DJANGO_SETTINGS_MODULE", "").strip():
        sys.stderr.write(AJUDA)
        raise SystemExit(2)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
