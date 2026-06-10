"""Hardened settings for the buzup.updigital.co.mz PRODUCTION environment.

Use config.settings.staging for the test/staging stack (buzup-test) instead.
"""
from decouple import config

from .base import *  # noqa: F401, F403

DEBUG = False

# Fail loud if SECRET_KEY is not provided in prod (never fall back to the dev key).
SECRET_KEY = config("SECRET_KEY")

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=lambda v: [s.strip() for s in v.split(",") if s.strip()])

# TLS / security hardening. Default ON in prod (env can still override).
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=True, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True, cast=bool)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=True, cast=bool)
SECURE_CONTENT_TYPE_NOSNIFF = True

# Webhooks de pagamento: fail-closed. Em producao um callback sem segredo
# valido (HMAC/token) e SEMPRE recusado — nunca creditar carteira sem prova.
PAYMENT_WEBHOOK_REQUIRE_SIGNATURE = config("PAYMENT_WEBHOOK_REQUIRE_SIGNATURE", default=True, cast=bool)

# Shared Redis cache (OTP rate-limiting consistent across workers).
REDIS_URL = config("REDIS_URL", default="redis://redis:6379/1")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}
