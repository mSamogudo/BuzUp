from __future__ import annotations

import json
import logging
import re
import secrets
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class PaymentGatewayResult:
    success: bool
    pending: bool = False
    provider_reference: str = ""
    detail_message: str = ""
    error: str = ""
    request_payload: dict | None = None
    response_payload: dict | None = None
    status_code: int = 0
    provider: str = ""
    timeout_seconds: int = 0
    supports_query: bool = False


class MockPaymentGateway:
    def initiate_payment(self, reference: str, amount, payer_phone: str, description: str = "") -> PaymentGatewayResult:
        return PaymentGatewayResult(
            success=True,
            provider_reference=f"MOCK-{uuid4().hex[:12].upper()}",
            detail_message="Pagamento confirmado (mock).",
            provider="MOCK",
        )

    def query_payment(self, provider_reference: str) -> dict:
        return {
            "provider_reference": provider_reference,
            "status": "confirmed",
            "confirmed_at": timezone.now().isoformat(),
        }


def _payless_base_url() -> str:
    return str(
        getattr(settings, "PAYLESS_BASE_URL", "https://payless.bluteki.com/api/v2.0") or ""
    ).strip().rstrip("/")


def _is_payless_url(url: str) -> bool:
    normalized = str(url or "").strip().lower()
    return "payless.bluteki.com" in normalized and "/api/v2.0" in normalized


def _provider_transport(provider: str, *, direct_url: str, api_url: str) -> str:
    normalized = str(provider or "").upper()
    configured = str(getattr(settings, f"{normalized}_TRANSPORT", "AUTO") or "AUTO").strip().upper()
    if configured in {"PAYLESS", "LEGACY"}:
        return configured

    has_payless_credentials = bool(
        str(getattr(settings, f"PAYLESS_{normalized}_BEARER_TOKEN", "") or "").strip()
        or str(getattr(settings, f"{normalized}_BEARER_TOKEN", "") or "").strip()
        or str(getattr(settings, "PAYLESS_BEARER_TOKEN", "") or "").strip()
    )
    if _is_payless_url(direct_url) or _is_payless_url(api_url):
        return "PAYLESS"
    if normalized in {"MPESA", "EMOLA"} and has_payless_credentials and not direct_url and not api_url:
        return "PAYLESS"
    return "LEGACY"


def _resolve_payless_token(provider: str) -> str:
    normalized = provider.upper()
    for attr in (f"PAYLESS_{normalized}_BEARER_TOKEN", f"{normalized}_BEARER_TOKEN", "PAYLESS_BEARER_TOKEN"):
        token = str(getattr(settings, attr, "") or "").strip()
        if token:
            return token
    return ""


def _resolve_payless_urls(provider: str, direct_url: str) -> tuple[str, str]:
    normalized = provider.upper()
    base_url = _payless_base_url()
    resolved_direct_url = direct_url if _is_payless_url(direct_url) else ""
    if normalized == "MPESA":
        query_url = str(getattr(settings, "MPESA_QUERY_URL", "") or "").strip()
        query_url = query_url if _is_payless_url(query_url) else ""
        return (resolved_direct_url or f"{base_url}/c2b").rstrip("/"), (query_url or f"{base_url}/search/mpesa/c2b").rstrip("/")
    if normalized == "EMOLA":
        query_url = str(getattr(settings, "EMOLA_QUERY_URL", "") or "").strip()
        query_url = query_url if _is_payless_url(query_url) else ""
        return (resolved_direct_url or f"{base_url}/emola/c2b").rstrip("/"), query_url.rstrip("/")
    return direct_url.rstrip("/"), ""


def _get_provider_config(provider: str) -> dict:
    normalized = provider.upper()
    if normalized not in {"MPESA", "EMOLA"}:
        raise ValueError(f"Unsupported provider: {normalized}")

    direct_url = str(getattr(settings, f"{normalized}_C2B_URL", "") or "").strip().rstrip("/")
    api_url = str(getattr(settings, f"{normalized}_API_URL", "") or "").strip().rstrip("/")
    transport = _provider_transport(normalized, direct_url=direct_url, api_url=api_url)
    query_url = ""
    if transport == "PAYLESS":
        c2b_url, query_url = _resolve_payless_urls(normalized, direct_url)
    else:
        c2b_url = direct_url
        if not c2b_url and api_url:
            c2b_url = api_url if api_url.lower().endswith("/c2b") else f"{api_url}/c2b"

    shortcode = str(
        getattr(settings, f"{normalized}_SHORTCODE", "")
        or getattr(settings, f"{normalized}_SERVICE_PROVIDER_CODE", "")
        or ""
    ).strip()
    wallet_code = str(
        getattr(settings, f"{normalized}_WALLET_CODE", "")
        or getattr(settings, f"{normalized}_SERVICE_PROVIDER_CODE", "")
        or ""
    ).strip()

    return {
        "provider": normalized,
        "transport": transport,
        "url": c2b_url,
        "query_url": query_url,
        "api_key": str(getattr(settings, f"{normalized}_API_KEY", "") or "").strip(),
        "api_secret": str(getattr(settings, f"{normalized}_API_SECRET", "") or "").strip(),
        "bearer_token": _resolve_payless_token(normalized),
        "shortcode": shortcode,
        "wallet_code": wallet_code,
        "service": str(getattr(settings, f"{normalized}_SERVICE", "buzup") or "buzup").strip(),
        "description": str(getattr(settings, f"{normalized}_DESCRIPTION", "Pagamento BusUp") or "Pagamento BusUp").strip(),
        "sms_content": str(getattr(settings, "EMOLA_SMS_CONTENT", "") or "").strip(),
        "supports_query": bool(query_url),
    }


def _provider_is_configured(provider: str) -> bool:
    config = _get_provider_config(provider)
    if config["transport"] == "PAYLESS":
        if not config["url"] or not config["bearer_token"]:
            return False
        if config["provider"] == "MPESA":
            return bool(config["shortcode"])
        if config["provider"] == "EMOLA":
            return bool(config["wallet_code"])
        return False
    return bool(config["url"] and config["api_key"] and config["api_secret"])


def _normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if digits.startswith("258") and len(digits) == 12:
        digits = digits[3:]
    if len(digits) != 9:
        raise ValueError("Numero de telefone invalido.")
    return digits


def _provider_msisdn(provider: str, local_phone: str) -> str:
    if provider.upper() == "MPESA":
        return f"258{local_phone}"
    return local_phone


def _serialize_amount(amount: Decimal):
    normalized = Decimal(amount).quantize(Decimal("0.01"))
    return int(normalized) if normalized == normalized.to_integral() else float(normalized)


def _compact_reference(prefix: str, ref: str) -> str:
    timestamp = timezone.now().strftime("%d%H%M%S")
    suffix = secrets.token_hex(3).upper()
    raw = f"{prefix}{timestamp}{suffix}"
    return re.sub(r"[^A-Za-z0-9]", "", raw).upper()[:20]


def _wallet_request_reference() -> str:
    token = "".join(secrets.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(10))
    return f"buz{token}{int(timezone.now().timestamp())}"


def _legacy_wallet_headers(payload_json: str, api_secret: str, api_key: str) -> dict:
    import hashlib
    import hmac

    signature = hmac.new(api_secret.encode("utf-8"), payload_json.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-API-KEY": api_key,
        "X-SIGNATURE": signature,
    }


def _http_json_request(*, url: str, method: str, headers: dict, timeout_seconds: int, body: dict | None = None) -> tuple[int, dict]:
    data = None
    if body is not None:
        data = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"raw_response": raw}
            return int(getattr(response, "status", 200)), payload
    except socket.timeout:
        return 408, {"detail": "Request timed out."}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw_response": raw}
        return int(exc.code or 400), payload
    except urllib.error.URLError as exc:
        return 502, {"detail": str(getattr(exc, "reason", "Unable to reach payment gateway."))}


def _extract_value(payload: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        current = payload
        for part in key.split("."):
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(part)
        if current is not None:
            text = str(current).strip()
            if text:
                return text
    return ""


def _interpret_response(provider: str, status_code: int, payload: dict) -> tuple[str, str, str]:
    payload_text = json.dumps(payload, ensure_ascii=False).lower() if payload else ""

    response_code = _extract_value(payload, (
        "output_ResponseCode", "data.output_ResponseCode", "response_code", "responseCode", "code", "data.code",
    )).upper()
    detail = _extract_value(payload, (
        "output_ResponseDesc", "message", "detail", "description",
        "data.output_ResponseDesc", "data.message", "data.detail",
    ))
    ext_ref = _extract_value(payload, (
        "output_TransactionID", "data.output_TransactionID",
        "transaction_id", "transactionId", "reference", "data.reference",
    ))

    mpesa_success = {"0", "00", "000", "INS-0", "SUCCESS", "OK"}
    emola_success = {"0", "00", "000", "2001", "SUCCESS", "OK"}
    success_codes = mpesa_success if provider == "MPESA" else emola_success

    success_markers = ("success", "approved", "completed", "paid", "confirmado com sucesso")
    failure_markers = ("failed", "failure", "error", "rejected", "insufficient", "declined", "invalid")

    if any(k in payload_text for k in ("cancelled", "canceled", "rejected by customer")):
        result = "FAILED"
        detail = detail or "Transacao cancelada pelo cliente."
    elif provider == "MPESA" and response_code == "INS-9":
        result = "TIMEOUT"
    elif provider == "EMOLA" and response_code == "2007":
        result = "TIMEOUT"
    elif response_code in success_codes or any(m in payload_text for m in success_markers):
        result = "SUCCESS"
    elif any(m in payload_text for m in failure_markers) or status_code >= 400:
        result = "FAILED"
    elif 200 <= status_code < 300:
        result = "PENDING"
    else:
        result = "FAILED"

    if not detail:
        if result == "SUCCESS":
            detail = "Pagamento confirmado."
        elif result == "PENDING":
            detail = "Solicitacao recebida. Aguarde confirmacao na carteira movel."
        elif result == "TIMEOUT":
            detail = "Solicitacao expirou antes da confirmacao."
        else:
            detail = "Nao foi possivel confirmar o pagamento."

    return result, detail, ext_ref


class MobileWalletGateway:
    def __init__(self, provider: str = "MPESA"):
        self.provider = provider.upper()
        self.config = _get_provider_config(self.provider)
        self.timeout = max(30, int(getattr(settings, "PAYMENT_MOBILE_WALLET_TIMEOUT_SECONDS", 180)))

    def initiate_payment(self, reference: str, amount, payer_phone: str, description: str = "") -> PaymentGatewayResult:
        if not _provider_is_configured(self.provider):
            return PaymentGatewayResult(
                success=False,
                error=f"Provider {self.provider} nao esta configurado.",
                provider=self.provider,
            )

        local_phone = _normalize_phone(payer_phone)
        msisdn = _provider_msisdn(self.provider, local_phone)

        if self.config["transport"] == "PAYLESS" and self.provider == "MPESA":
            request_payload = {
                "msisdn": msisdn,
                "amount": _serialize_amount(Decimal(str(amount))),
                "transactionReference": _compact_reference("MP", reference),
                "thirdPartyReference": _compact_reference("BZ", reference),
                "shortcode": str(self.config["shortcode"]),
            }
        elif self.config["transport"] == "PAYLESS" and self.provider == "EMOLA":
            sms_content = self.config["sms_content"] or f"Confirme o pagamento de {amount} MT no BusUp."
            request_payload = {
                "amount": _serialize_amount(Decimal(str(amount))),
                "msisdn": msisdn,
                "sms_content": sms_content,
                "wallet_code": str(self.config["wallet_code"]),
            }
        else:
            request_payload = {
                "phone_number": local_phone,
                "amount": _serialize_amount(Decimal(str(amount))),
                "third_party_reference": _wallet_request_reference(),
                "service": str(self.config["service"]),
                "description": description or str(self.config["description"]),
            }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.config["transport"] == "PAYLESS":
            headers["Authorization"] = f"Bearer {self.config['bearer_token']}"
        else:
            payload_json = json.dumps(request_payload, separators=(",", ":"), ensure_ascii=False)
            headers = _legacy_wallet_headers(
                payload_json,
                str(self.config["api_secret"]),
                str(self.config["api_key"]),
            )

        status_code, response_payload = _http_json_request(
            url=str(self.config["url"]),
            method="POST",
            headers=headers,
            timeout_seconds=self.timeout,
            body=request_payload,
        )

        result, detail, ext_ref = _interpret_response(self.provider, status_code, response_payload)

        return PaymentGatewayResult(
            success=(result == "SUCCESS"),
            pending=(result == "PENDING"),
            provider_reference=ext_ref,
            detail_message=detail,
            error=detail if result == "FAILED" else "",
            request_payload=request_payload,
            response_payload=response_payload,
            status_code=status_code,
            provider=self.provider,
            timeout_seconds=self.timeout,
            supports_query=bool(self.config["supports_query"]),
        )

    def query_payment(self, transaction_reference: str) -> PaymentGatewayResult:
        if self.config["transport"] != "PAYLESS" or not self.config["query_url"]:
            return PaymentGatewayResult(success=False, error="Query not supported.", provider=self.provider)

        url = f"{self.config['query_url']}?{urllib.parse.urlencode({'transactionReference': transaction_reference})}"
        status_code, response_payload = _http_json_request(
            url=url,
            method="GET",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.config['bearer_token']}",
            },
            timeout_seconds=self.timeout,
        )

        result, detail, ext_ref = _interpret_response(self.provider, status_code, response_payload)

        return PaymentGatewayResult(
            success=(result == "SUCCESS"),
            pending=(result == "PENDING"),
            provider_reference=ext_ref,
            detail_message=detail,
            provider=self.provider,
            response_payload=response_payload,
            status_code=status_code,
        )


def _detect_provider(payer_phone: str) -> str:
    digits = "".join(ch for ch in str(payer_phone or "") if ch.isdigit())
    if digits.startswith("258"):
        digits = digits[3:]
    if digits.startswith("84") or digits.startswith("85"):
        return "MPESA"
    if digits.startswith("86") or digits.startswith("87"):
        return "EMOLA"
    methods = str(getattr(settings, "PAYMENT_MOBILE_WALLET_METHODS", "MPESA") or "MPESA")
    return methods.split(",")[0].strip().upper()


def get_payment_gateway(provider: str | None = None, payer_phone: str = "") -> MockPaymentGateway | MobileWalletGateway:
    gateway_provider = str(getattr(settings, "PAYMENT_GATEWAY_PROVIDER", "MOCK") or "MOCK").strip().upper()

    if gateway_provider == "MOCK":
        return MockPaymentGateway()

    resolved_provider = provider or _detect_provider(payer_phone)
    return MobileWalletGateway(resolved_provider)
