"""Definições para correr a suite de testes sem infra-estrutura.

A suite dependia de um Postgres a correr, o que na prática significava que
quase ninguém a corria. Com SQLite em memória, `manage.py test` funciona em
qualquer máquina e em CI. Os testes que dependam de comportamento específico
do Postgres (ex.: `select_for_update`) devem dizê-lo explicitamente.
"""

from .base import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = ["*", "testserver"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Testes não devem enviar SMS nem falar com gateways reais.
SMS_PROVIDER = "MOCK"
PAYMENT_GATEWAY_PROVIDER = "MOCK"

# Hasher rápido: a suite não valida força de password.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Cache local — evita depender do Redis.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
