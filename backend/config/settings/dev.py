from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True

# Em desenvolvimento simula-se sempre: ninguem quer cobrar de verdade ao correr
# a aplicacao na propria maquina.
PAYMENTS_ALLOW_SANDBOX = True
