import os
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
PAYMENT_MOBILE_WALLET_TIMEOUT_SECONDS = config("PAYMENT_MOBILE_WALLET_TIMEOUT_SECONDS", default=180, cast=int)
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

OTP_TTL_MINUTES = config("OTP_TTL_MINUTES", default=5, cast=int)
OTP_MAX_ATTEMPTS = config("OTP_MAX_ATTEMPTS", default=5, cast=int)
OTP_REQUEST_WINDOW_SECONDS = config("OTP_REQUEST_WINDOW_SECONDS", default=300, cast=int)
OTP_MAX_REQUESTS_PER_PHONE = config("OTP_MAX_REQUESTS_PER_PHONE", default=3, cast=int)
OTP_MAX_REQUESTS_PER_IP = config("OTP_MAX_REQUESTS_PER_IP", default=20, cast=int)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

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
