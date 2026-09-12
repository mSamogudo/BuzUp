import os
import sys
from datetime import timedelta
from pathlib import Path

from decouple import config


def csv_config(value):
    return [item.strip() for item in value.split(",") if item.strip()]


BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY", default="buzup-dev-secret-key")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=csv_config)

# Security gate: in production agents cannot bulk-register card UIDs from the
# POS. Set to True only in staging/test envs (or for staff users).
ALLOW_AGENT_CARD_CAPTURE = config("ALLOW_AGENT_CARD_CAPTURE", default=False, cast=bool)

# Aceitar o token de acesso no URL (`?token=<JWT>`) era a forma antiga de
# descarregar um ficheiro protegido, porque um link nao envia o cabecalho
# `Authorization`. So que o URL fica gravado no log do servidor e no historico
# do browser — e o que la ficava era o token COMPLETO, que da acesso a tudo o
# que o utilizador pode fazer.
#
# Desligado por omissao a 2026-08-05, depois de confirmar que ja ninguem o usa:
# o portal descarrega com `fetch` + blob (`apiDownload`) e a app do passageiro
# pede um bilhete de curta duracao (`/api/auth/download-ticket/`). Fica a
# variavel de ambiente para se voltar a ligar se aparecer um cliente antigo.
ALLOW_JWT_IN_QUERY_STRING = config("ALLOW_JWT_IN_QUERY_STRING", default=False, cast=bool)

# Default issuance fee charged to a passenger when they receive a new card
# on the POS. Configurable so commercial can change without code release.
CARD_ISSUE_FEE = config("CARD_ISSUE_FEE", default="50.00")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    "apps.core.apps.CoreConfig",
    "apps.users.apps.UsersConfig",
    "apps.audit.apps.AuditConfig",
    "apps.passengers.apps.PassengersConfig",
    "apps.wallets.apps.WalletsConfig",
    "apps.payments.apps.PaymentsConfig",
    "apps.guest_checkouts.apps.GuestCheckoutsConfig",
    "apps.sms.apps.SmsConfig",
    "apps.cards.apps.CardsConfig",
    "apps.devices.apps.DevicesConfig",
    "apps.app_releases.apps.AppReleasesConfig",
    "apps.branding.apps.BrandingConfig",
    "apps.routes.apps.RoutesConfig",
    "apps.fares.apps.FaresConfig",
    "apps.trips.apps.TripsConfig",
    "apps.validations.apps.ValidationsConfig",
    "apps.reports.apps.ReportsConfig",
    "apps.packages.apps.PackagesConfig",
    "apps.pos.apps.PosConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.leads.apps.LeadsConfig",
    "apps.agent_api.apps.AgentApiConfig",
    "apps.mobile_api.apps.MobileApiConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB", default="buzup_dev"),
        "USER": config("POSTGRES_USER", default="postgres"),
        "PASSWORD": config("POSTGRES_PASSWORD", default="postgres"),
        "HOST": config("POSTGRES_HOST", default="127.0.0.1"),
        "PORT": config("POSTGRES_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt"
TIME_ZONE = "Africa/Maputo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Ficheiros grandes (APKs) entregues pelo nginx em vez do gunicorn — ver
# `apps/core/file_serving.py`. Fica FALSE por omissao para o runserver e os
# testes continuarem a servir o ficheiro directamente; staging e producao
# ligam-no, porque so aí existe o nginx que honra o cabecalho.
USE_X_ACCEL_REDIRECT = config("USE_X_ACCEL_REDIRECT", default=False, cast=bool)
PUBLIC_BASE_URL = config("PUBLIC_BASE_URL", default="https://buzup.updigital.co.mz").rstrip("/")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=False, cast=bool)
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=csv_config)
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=csv_config)

PAYMENT_GATEWAY_PROVIDER = config("PAYMENT_GATEWAY_PROVIDER", default="AUTO")
PAYMENT_GATEWAY_WEBHOOK_SECRET = config("PAYMENT_GATEWAY_WEBHOOK_SECRET", default="")
# Quando True, um webhook de pagamento sem segredo configurado e recusado
# (fail-closed). Default False para nao quebrar dev/test; forcado True em prod.
PAYMENT_WEBHOOK_REQUIRE_SIGNATURE = config("PAYMENT_WEBHOOK_REQUIRE_SIGNATURE", default=False, cast=bool)
PAYMENT_MOBILE_WALLET_METHODS = config("PAYMENT_MOBILE_WALLET_METHODS", default="MPESA,EMOLA")
# ---------------------------------------------------------------------------
# A CADEIA DE TIMEOUTS. Quem mexer num destes numeros mexe nos outros.
#
#   cobranca 45-60s  <  nginx 75s  <  POS 80s  <  gunicorn 200s
#   (aqui)              (nginx.conf)  (pos_app)   (docker-compose.prod.yml)
#
# A regra e uma so: **quem espera pela resposta tem de desistir DEPOIS de
# quem a produz**. O POS e o ultimo a desistir de proposito — assim um 504 do
# nginx chega-lhe como resposta, e nao como silencio.
#
# Ja falhou nos dois sentidos:
#
#  - invertida ao contrario (gateway 180s): o POS recebia 504 do nginx aos
#    60s, o agente repetia, o gunicorn matava o worker aos 120s levando
#    consigo as validacoes em voo, e a resposta do gateway (que chegaria aos
#    150s) perdia-se deixando o pagamento PENDING para sempre;
#  - invertida deste lado (POS 25s, cobranca 60s), a 2026-09-12 as 06:32: a
#    operadora respondeu aos 30,6s, o POS tinha desistido aos 25, e o agente
#    viu um erro enquanto o passageiro recebia o bilhete e era debitado.
#
# `test_cadeia_de_timeouts.py` trava a regra. Ver tambem
# `pos_app/lib/core/config.dart`, docker/prod/nginx.conf e
# docker-compose.prod.yml.
# Prazo que o passageiro tem para confirmar na carteira. E o valor que a
# aplicacao mostra, nao o tempo que o servidor fica a segurar a ligacao.
PAYMENT_MOBILE_WALLET_TIMEOUT_SECONDS = config("PAYMENT_MOBILE_WALLET_TIMEOUT_SECONDS", default=25, cast=int)
# Quanto tempo o pedido de cobranca espera pela operadora antes de desistir. O
# worker do gunicorn fica preso todo esse tempo — e a espera inclui o passageiro
# a digitar o PIN. Em producao isto estava em 180s, e com ate 3 tentativas dava
# 9 minutos por pagamento.
#
#  - MPESA tem consulta de estado (/search/mpesa/c2b), logo o desfecho e sempre
#    recuperavel depois pela reconciliacao.
#  - EMOLA nao tem consulta. A resposta sincrona e o unico sitio onde se aprende
#    o desfecho, por isso nao se pode largar cedo. Medido na producao do
#    ETICKETING: maximo de 43,5s em 111 pagamentos.
#
# O M-Pesa esteve em 15s, a contar com a reconciliacao para o resto. Em 14 dias
# (25/08-08/09) deu 9 pagamentos "falhados" em 12 — o PIN demora mais do que
# isso — e, depois de o timeout passar a "pendente", um bilhete que so saia 6
# minutos depois, com o agente e o passageiro a espera no balcao. 45s cabe na
# maioria dos PINs e fica abaixo dos 75s do nginx (docker/prod/nginx.conf);
# com o volume actual, uma thread presa 45s nao custa nada.
#
# **Nao encurtar o EMOLA a contar com a reconciliacao.** Para o M-Pesa isso
# funciona, porque ha `/search/mpesa/c2b`. Para o e-Mola nao ha para onde
# perguntar — `/search/emola/c2b` da 404, `EMOLA_QUERY_URL` esta vazio, e a
# operadora nao nos chama de volta (os 18 `PaymentCallback` em producao dizem
# todos `source: immediate_confirm`, i.e. fomos nos a escreve-los). Largar
# cedo aqui nao adia o desfecho: perde-o.
PAYMENT_WALLET_CHARGE_TIMEOUT_MPESA = config("PAYMENT_WALLET_CHARGE_TIMEOUT_MPESA", default=45, cast=int)
PAYMENT_WALLET_CHARGE_TIMEOUT_EMOLA = config("PAYMENT_WALLET_CHARGE_TIMEOUT_EMOLA", default=60, cast=int)
# A consulta de estado e um GET, nao espera por ninguem.
PAYMENT_WALLET_QUERY_TIMEOUT_SECONDS = config("PAYMENT_WALLET_QUERY_TIMEOUT_SECONDS", default=15, cast=int)
PAYLESS_BASE_URL = config("PAYLESS_BASE_URL", default="https://payless.bluteki.com/api/v2.0")
PAYLESS_BEARER_TOKEN = config("PAYLESS_BEARER_TOKEN", default="")

MPESA_TRANSPORT = config("MPESA_TRANSPORT", default="PAYLESS")
MPESA_C2B_URL = config("MPESA_C2B_URL", default="")
MPESA_API_URL = config("MPESA_API_URL", default="")
MPESA_QUERY_URL = config("MPESA_QUERY_URL", default="")
MPESA_BEARER_TOKEN = config("MPESA_BEARER_TOKEN", default="")
MPESA_API_KEY = config("MPESA_API_KEY", default="")
MPESA_API_SECRET = config("MPESA_API_SECRET", default="")
MPESA_SERVICE_PROVIDER_CODE = config("MPESA_SERVICE_PROVIDER_CODE", default="")
MPESA_SHORTCODE = config("MPESA_SHORTCODE", default="")
MPESA_SERVICE = config("MPESA_SERVICE", default="buzup")
MPESA_DESCRIPTION = config("MPESA_DESCRIPTION", default="Pagamento BuzUp")
MPESA_CALLBACK_URL = config("MPESA_CALLBACK_URL", default="")

EMOLA_TRANSPORT = config("EMOLA_TRANSPORT", default="PAYLESS")
EMOLA_C2B_URL = config("EMOLA_C2B_URL", default="")
EMOLA_API_URL = config("EMOLA_API_URL", default="")
EMOLA_QUERY_URL = config("EMOLA_QUERY_URL", default="")
EMOLA_BEARER_TOKEN = config("EMOLA_BEARER_TOKEN", default="")
EMOLA_API_KEY = config("EMOLA_API_KEY", default="")
EMOLA_API_SECRET = config("EMOLA_API_SECRET", default="")
EMOLA_WALLET_CODE = config("EMOLA_WALLET_CODE", default="")
EMOLA_SMS_CONTENT = config("EMOLA_SMS_CONTENT", default="Confirme o pagamento BuzUp na sua carteira E-Mola.")
EMOLA_SERVICE = config("EMOLA_SERVICE", default="buzup")
EMOLA_DESCRIPTION = config("EMOLA_DESCRIPTION", default="Pagamento BuzUp")

# Cartao (Visa/Mastercard) pelo DPO Pay. Sem CompanyToken e ServiceType o
# metodo nao aparece ao comprador. Sandbox: DPO_BASE_URL=https://secure1.sandbox.directpay.online
# — e, tal como no M-Pesa, so cobra pelo sandbox onde PAYMENTS_ALLOW_SANDBOX=True.
DPO_COMPANY_TOKEN = config("DPO_COMPANY_TOKEN", default="")
DPO_SERVICE_TYPE = config("DPO_SERVICE_TYPE", default="")
DPO_BASE_URL = config("DPO_BASE_URL", default="https://secure.3gdirectpay.com")
DPO_CURRENCY = config("DPO_CURRENCY", default="MZN")
DPO_PTL_MINUTES = config("DPO_PTL_MINUTES", default=25, cast=int)
DPO_TIMEOUT_SECONDS = config("DPO_TIMEOUT_SECONDS", default=20, cast=int)

BLUTEKI_BASE_URL = config("BLUTEKI_BASE_URL", default="")
BLUTEKI_API_KEY = config("BLUTEKI_API_KEY", default="")
BLUTEKI_SENDER_ID = config("BLUTEKI_SENDER_ID", default="UpDigital")
BLUTEKI_CUSTOMER_KEY = config("BLUTEKI_CUSTOMER_KEY", default="")
BLUTEKI_USERNAME = config("BLUTEKI_USERNAME", default="")
BLUTEKI_PASSWORD = config("BLUTEKI_PASSWORD", default="")
BLUTEKI_DEFAULT_CAMPAIGN_ID = config("BLUTEKI_DEFAULT_CAMPAIGN_ID", default="")
BLUTEKI_DEFAULT_MESSAGE_TYPE = config("BLUTEKI_DEFAULT_MESSAGE_TYPE", default="AUTO")
BLUTEKI_USE_GET = config("BLUTEKI_USE_GET", default=False, cast=bool)
BLUTEKI_VERIFY_SSL = config("BLUTEKI_VERIFY_SSL", default=True, cast=bool)

SMS_PROVIDER = config("SMS_PROVIDER", default="BLUTEKI")

# Numeros que recebem alertas de infraestrutura (separados por virgula), usados
# pelo vigia do servidor (`/usr/local/bin/buzup-vigia`). Um monitor externo
# exigiria uma conta noutro servico; isto usa o gateway de SMS que a operacao
# ja tem. Nao substitui um monitor de fora — se a maquina inteira cair ninguem
# manda o SMS — mas apanha o caso comum: um contentor morto, um certificado a
# expirar, um dominio a servir outra coisa.
ALERT_SMS_NUMBERS = config("ALERT_SMS_NUMBERS", default="")

OTP_TTL_MINUTES = config("OTP_TTL_MINUTES", default=5, cast=int)
OTP_MAX_ATTEMPTS = config("OTP_MAX_ATTEMPTS", default=5, cast=int)
OTP_REQUEST_WINDOW_SECONDS = config("OTP_REQUEST_WINDOW_SECONDS", default=300, cast=int)
OTP_MAX_REQUESTS_PER_PHONE = config("OTP_MAX_REQUESTS_PER_PHONE", default=3, cast=int)
OTP_MAX_REQUESTS_PER_IP = config("OTP_MAX_REQUESTS_PER_IP", default=20, cast=int)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # Nao e a do SimpleJWT: esta recusa um token emitido antes da ultima
        # mudanca de senha. Sem ela, repor a senha de uma conta comprometida
        # nao expulsa ninguem durante 30 minutos. Ver `apps.users.tokens`.
        "apps.users.authentication.JWTComMarcaDeSenha",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Traduz as excepcoes do nosso dominio (terminal bloqueado, partida
    # esgotada, colisao de unicidade) em respostas legiveis em vez de 500 —
    # e registra as inesperadas, que antes desapareciam sem rasto.
    "EXCEPTION_HANDLER": "apps.core.exception_handler.buzup_exception_handler",
    # Paginação por omissão. Sem isto, `/api/validations/` devolvia a tabela
    # inteira num só JSON: com um milhão de linhas o worker esgotava a memória
    # do contentor e morria — e como há poucos workers, isso derrubava o
    # backend para todos os terminais. Um clique no portal chegava.
    # Os clientes já leem `results` (o frontend faz `d.results || d`).
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultPagination",
    # Tecto global: um cliente sem limite é um cliente que pode saturar as
    # threads todas. Endpoints com `throttle_scope` próprio continuam a mandar.
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        # Generosos de propósito: um terminal em hora de ponta faz muitos
        # pedidos legítimos. Isto trava abuso, não trabalho.
        "anon": "120/min",
        "user": "600/min",
        "vehicle-locations": "12/min",
        "service-request": "6/hour",
        "password-reset": "5/hour",
        # Login: travar força bruta de senha e de OTP.
        "agent-login": "10/min",
        # Portal: a senha é o 1.º passo e o código o 2.º — ambos por este balde.
        "auth": "12/min",
        "guest-checkout": "10/hour",
    },
    # O IP vem do proxy; sem isto o `X-Forwarded-For` do cliente é aceite como
    # verdade e qualquer limite por IP é contornável acrescentando um header.
    "NUM_PROXIES": config("NUM_PROXIES", default=1, cast=int),
}

# Telefone que recebe aviso de novos pedidos de contacto da landing.
SALES_NOTIFY_PHONE = os.environ.get("BUZUP_SALES_NOTIFY_PHONE", "")

SPECTACULAR_SETTINGS = {
    "TITLE": "BuzUp API",
    "DESCRIPTION": "Cashless online platform for public transport mobility.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# Não havia configuração nenhuma. Com DEBUG=False, o handler de consola do
# Django está atrás do filtro `require_debug_true`, portanto TODOS os
# logger.info/warning do código (pagamentos, SMS, validações) iam para o vazio;
# e os 500 iam para `mail_admins` com ADMINS vazio, ou seja, desapareciam.
# Resultado prático: com a operação parada não havia uma única linha para ler.
# Aqui tudo vai para stdout, que é onde `docker logs` e qualquer agregador
# esperam encontrá-lo.
LOG_LEVEL = config("LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        # Os 500 têm de aparecer no stdout com stack trace, não só num email
        # que ninguém configurou.
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        # As nossas apps ao nível configurado; o resto do Django mais calado
        # para o ruído não esconder o que importa.
        "apps": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# Ligações à base de dados reutilizadas entre pedidos. Estava em 0 (o default),
# o que abria uma ligação TCP + autenticação nova em CADA pedido — com ~15
# queries por validação e um Postgres com pouca memória, é latência pura na
# hora de ponta.
DATABASES["default"]["CONN_MAX_AGE"] = config("CONN_MAX_AGE", default=60, cast=int)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

# Limites de upload: sem eles, um ficheiro grande na importação Excel enche a
# memória do worker e mata o processo — e com ele a operação de todos.
DATA_UPLOAD_MAX_MEMORY_SIZE = config("DATA_UPLOAD_MAX_MEMORY_SIZE", default=10 * 1024 * 1024, cast=int)
FILE_UPLOAD_MAX_MEMORY_SIZE = config("FILE_UPLOAD_MAX_MEMORY_SIZE", default=10 * 1024 * 1024, cast=int)


# Este ambiente pode usar o SIMULADOR de pagamentos?
#
# O simulador (shortcode 171717 do M-Pesa) aceita qualquer PIN e da tudo por
# pago. Em desenvolvimento e em staging isso e exactamente o que se quer; em
# producao e uma porta aberta para levantar bilhetes sem pagar — e esteve
# aberta quatro dias, ate 19/08/2026.
#
# O default e False de proposito: um ambiente novo nasce protegido, e quem o
# quiser em modo de teste tem de o dizer. O contrario — assumir que se pode
# simular e exigir que producao o negue — poe o peso da prova no sitio errado.
#
# Nao se usa `DEBUG` para isto: staging tambem corre com `DEBUG=False`, e
# confundir os dois faz uma guarda de producao bloquear os testes (foi o que
# aconteceu na primeira versao desta guarda).
PAYMENTS_ALLOW_SANDBOX = config("PAYMENTS_ALLOW_SANDBOX", default=False, cast=bool)

# A correr a suite de testes?
#
# Nao havia forma nenhuma de saber. `send_sms` ja perguntava por
# `settings.TESTING` para nao contactar o provedor — mas a flag nunca existiu,
# logo `getattr(..., False)` respondia sempre False e CADA execucao da suite
# enviava SMS a serio, pagos, para os numeros das fixtures. O mesmo valia para o
# gateway de pagamentos.
#
# Fica em `base.py` de proposito: assim vale para qualquer modulo de definicoes
# com que a suite seja corrida, e nao apenas para `config.settings.test`.
TESTING = "test" in sys.argv or "pytest" in os.path.basename(sys.argv[0] if sys.argv else "")

if TESTING:
    # Nada de dinheiro nem de mensagens reais a partir de um teste.
    PAYMENT_GATEWAY_PROVIDER = "MOCK"
    SMS_PROVIDER = "MOCK"
    PAYMENTS_ALLOW_SANDBOX = True
