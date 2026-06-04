from __future__ import annotations

import json
import logging
import ssl
import uuid
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from apps.sms.models import SmsMessage

logger = logging.getLogger(__name__)

MOZAMBIQUE_COUNTRY_CODE = "258"
BLUTEKI_SMS_HUB_V1_BASE_URL = "https://smshub.bluteki.com/api/v1"
BLUTEKI_SMS_ENDPOINT_SUFFIXES = (
    "/sms/send/personalized-bulk",
    "/sms/send/bulk",
    "/sms/send",
    "/sender-ids",
    "/estimate-cost",
    "/balance",
    "/sendsms",
    "/sendmessage",
)
BLUTEKI_SUPPORTED_MESSAGE_TYPES = {"TEXT", "UNICODE", "FLASH"}


@dataclass
class SmsDispatchResult:
    recipient: str
    ok: bool
    detail: str


def _normalize_phone_digits(value: str) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _normalize_msisdn(value: str | None) -> str:
    raw = str(value or "").strip().replace(" ", "")
    if raw.startswith("+"):
        raw = raw[1:]
    if raw.startswith("00"):
        raw = raw[2:]
    digits = _normalize_phone_digits(raw)
    if digits.startswith(MOZAMBIQUE_COUNTRY_CODE) and len(digits) == 12:
        return digits
    if digits.startswith("0") and len(digits) == 10:
        digits = digits[1:]
    if len(digits) == 9 and digits[0] in "89":
        return f"{MOZAMBIQUE_COUNTRY_CODE}{digits}"
    return digits


def _normalize_provider_base_url(value: str | None) -> str:
    base_url = str(value or "").strip().rstrip("/")
    for suffix in BLUTEKI_SMS_ENDPOINT_SUFFIXES:
        if base_url.endswith(suffix):
            base_url = base_url[: -len(suffix)]
    return base_url


def _resolve_message_type(message: str) -> str:
    configured = str(getattr(settings, "BLUTEKI_DEFAULT_MESSAGE_TYPE", "AUTO") or "").strip().upper()
    if configured in BLUTEKI_SUPPORTED_MESSAGE_TYPES:
        return configured
    return "TEXT" if str(message or "").isascii() else "UNICODE"


def _dispatch_sms_via_sms_hub_v1(
    *,
    base_url: str,
    api_key: str,
    sender_id: str,
    msisdn: str,
    message: str,
    verify_ssl: bool,
) -> tuple[int, str]:
    payload = {
        "destination": msisdn,
        "message": message,
        "sender": sender_id,
        "type": _resolve_message_type(message),
    }
    request = Request(
        f"{base_url}/sms/send",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/json",
            "Accept-Charset": "utf-8",
            "Content-Type": "application/json; charset=utf-8",
            "X-API-KEY": api_key,
        },
    )
    context = None if verify_ssl else ssl._create_unverified_context()
    with urlopen(request, timeout=20, context=context) as response:
        body = response.read().decode("utf-8", errors="replace")
        return getattr(response, "status", 200), body


def _dispatch_sms_via_legacy_bluteki(
    *,
    base_url: str,
    customer_key: str,
    username: str,
    password: str,
    campaign_id: str,
    msisdn: str,
    message: str,
    use_get: bool,
    verify_ssl: bool,
) -> tuple[int, str]:
    request_id = str(uuid.uuid4())
    context = None if verify_ssl else ssl._create_unverified_context()

    if use_get:
        params: dict = {
            "customerKey": customer_key,
            "number": msisdn,
            "message": message,
            "id": request_id,
        }
        if campaign_id:
            params["campaignID"] = campaign_id
        if username:
            params["username"] = username
        if password:
            params["password"] = password
        request = Request(
            f"{base_url}/sendsms?{urlencode(params)}",
            headers={"Accept-Charset": "utf-8"},
        )
    else:
        payload: dict = {
            "customerKey": customer_key,
            "messageRequestList": [
                {
                    "number": msisdn,
                    "message": message,
                    "id": request_id,
                    **({"campaignID": campaign_id} if campaign_id else {}),
                }
            ],
        }
        if username:
            payload["username"] = username
        if password:
            payload["password"] = password
        request = Request(
            f"{base_url}/sendmessage",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Accept-Charset": "utf-8",
                "Content-Type": "application/json; charset=utf-8",
            },
        )

    with urlopen(request, timeout=20, context=context) as response:
        body = response.read().decode("utf-8", errors="replace")
        return getattr(response, "status", 200), body


def send_sms(
    phone_number: str,
    body: str,
    purpose: str = "",
    metadata: dict | None = None,
) -> SmsMessage:
    logger.info(
        "[SMS][dispatch] phone=%s purpose=%s body_len=%s metadata=%s",
        phone_number, purpose, len(body or ""), metadata or {},
    )
    msisdn = _normalize_msisdn(phone_number)
    if not msisdn:
        logger.warning(
            "[SMS][reject] reason=missing_phone raw=%s purpose=%s",
            phone_number, purpose,
        )
        sms = SmsMessage.objects.create(
            phone_number=str(phone_number or ""),
            body=body,
            purpose=purpose,
            status=SmsMessage.Status.FAILED,
            metadata={**(metadata or {}), "error": "missing_phone"},
        )
        return sms

    api_key = str(getattr(settings, "BLUTEKI_API_KEY", "") or "").strip()
    sender_id = str(getattr(settings, "BLUTEKI_SENDER_ID", "") or "").strip()
    default_base_url = BLUTEKI_SMS_HUB_V1_BASE_URL if api_key else ""
    configured_base_url = getattr(settings, "BLUTEKI_BASE_URL", "") or default_base_url
    base_url = _normalize_provider_base_url(configured_base_url)
    customer_key = str(getattr(settings, "BLUTEKI_CUSTOMER_KEY", "") or "").strip()
    username = str(getattr(settings, "BLUTEKI_USERNAME", "") or "").strip()
    password = str(getattr(settings, "BLUTEKI_PASSWORD", "") or "").strip()
    use_get = getattr(settings, "BLUTEKI_USE_GET", False)
    verify_ssl = getattr(settings, "BLUTEKI_VERIFY_SSL", True)
    default_campaign = str(getattr(settings, "BLUTEKI_DEFAULT_CAMPAIGN_ID", "") or "").strip()

    sms_provider = str(getattr(settings, "SMS_PROVIDER", "MOCK") or "MOCK").strip().upper()
    testing = getattr(settings, "TESTING", False)

    if testing or sms_provider == "MOCK" or not base_url or (not api_key and not customer_key):
        logger.info(
            "[SMS][mock] msisdn=%s purpose=%s body=%r reason=%s",
            msisdn, purpose, body[:120],
            "TESTING" if testing else ("provider=MOCK" if sms_provider == "MOCK" else "no_credentials"),
        )
        sms = SmsMessage.objects.create(
            phone_number=msisdn,
            body=body,
            purpose=purpose,
            status=SmsMessage.Status.SENT,
            sent_at=timezone.now(),
            provider_reference=f"MOCK-{msisdn}",
            metadata={**(metadata or {}), "provider": "mock"},
        )
        return sms

    provider_name = "bluteki_sms_hub_v1" if api_key else ("bluteki_legacy_get" if use_get else "bluteki_legacy_post")
    response_status = 0
    response_body = ""
    logger.info(
        "[SMS][provider_call] provider=%s base_url=%s sender_id=%s msisdn=%s purpose=%s",
        provider_name, base_url, sender_id or "-", msisdn, purpose,
    )

    try:
        if api_key:
            if not sender_id:
                logger.warning(
                    "[SMS][reject] reason=missing_sender_id provider=%s msisdn=%s",
                    provider_name, msisdn,
                )
                sms = SmsMessage.objects.create(
                    phone_number=msisdn,
                    body=body,
                    purpose=purpose,
                    status=SmsMessage.Status.FAILED,
                    metadata={**(metadata or {}), "error": "missing_sender_id", "provider": provider_name},
                )
                return sms

            response_status, response_body = _dispatch_sms_via_sms_hub_v1(
                base_url=base_url,
                api_key=api_key,
                sender_id=sender_id,
                msisdn=msisdn,
                message=body,
                verify_ssl=verify_ssl,
            )
        else:
            response_status, response_body = _dispatch_sms_via_legacy_bluteki(
                base_url=base_url,
                customer_key=customer_key,
                username=username,
                password=password,
                campaign_id=default_campaign,
                msisdn=msisdn,
                message=body,
                use_get=use_get,
                verify_ssl=verify_ssl,
            )
    except HTTPError as exc:
        response_status = exc.code
        response_body = exc.read().decode("utf-8", errors="replace")
        logger.warning("[SMS][http_error] provider=%s status=%s body=%r", provider_name, response_status, response_body[:200])
    except Exception as exc:
        response_status = 0
        response_body = str(exc)
        logger.exception("[SMS][exception] provider=%s msisdn=%s err=%s", provider_name, msisdn, exc)

    ok = 200 <= response_status < 300
    logger.log(
        logging.INFO if ok else logging.WARNING,
        "[SMS][result] provider=%s msisdn=%s status=%s response=%r",
        provider_name, msisdn, response_status, response_body[:200],
    )

    sms = SmsMessage.objects.create(
        phone_number=msisdn,
        body=body,
        purpose=purpose,
        status=SmsMessage.Status.SENT if ok else SmsMessage.Status.FAILED,
        sent_at=timezone.now() if ok else None,
        provider_reference=response_body[:128] if ok else "",
        metadata={
            **(metadata or {}),
            "provider": provider_name,
            "response_status": response_status,
            "response_body": response_body[:2000],
        },
    )
    return sms
