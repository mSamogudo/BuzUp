"""Settings for the buzup-test (staging) environment.

Mirrors what the staging stack has always used: DEBUG off, but the security
knobs are env-driven and tolerant (so a missing var doesn't take staging down).
Production hardening lives in prod.py instead.
"""
from decouple import config

from .base import *  # noqa: F401, F403

DEBUG = False
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=lambda v: [s.strip() for s in v.split(",") if s.strip()])

# Webhooks de pagamento tambem sao fail-closed aqui. Staging herdava o default
# False de base.py, o que deixava qualquer pessoa confirmar um pagamento
# inventado (`POST /api/payments/callbacks/mock/` com status=confirmed) e
# receber bilhetes e saldo de graca. Staging aponta ao gateway REAL e tem dados
# que usamos para validar contas — nao pode ser mais aberto que producao.
PAYMENT_WEBHOOK_REQUIRE_SIGNATURE = config("PAYMENT_WEBHOOK_REQUIRE_SIGNATURE", default=True, cast=bool)

# O SECRET_KEY e o pepper dos hashes de OTP (apps/users/otp.py). Herdar o
# default de desenvolvimento tornava os codigos reversiveis por tabela.
SECRET_KEY = config("SECRET_KEY")

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=True, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Shared Redis cache (OTP rate-limiting consistent across workers).
REDIS_URL = config("REDIS_URL", default="redis://redis:6379/1")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# O gateway nginx monta o volume de media e tem a location `/protected-media/`:
# os APKs sao entregues por ele, nao pelo gunicorn (ver apps/core/file_serving.py).
USE_X_ACCEL_REDIRECT = config("USE_X_ACCEL_REDIRECT", default=True, cast=bool)
