from decouple import config

from .base import *  # noqa: F401, F403

DEBUG = False
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=lambda v: [s.strip() for s in v.split(",") if s.strip()])

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=True, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
