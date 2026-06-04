from __future__ import annotations

import hashlib
import logging
import secrets

from django.conf import settings

logger = logging.getLogger(__name__)

OTP_TTL_MINUTES = getattr(settings, "OTP_TTL_MINUTES", 5)
OTP_MAX_ATTEMPTS = getattr(settings, "OTP_MAX_ATTEMPTS", 5)
MOZAMBIQUE_COUNTRY_CODE = "258"


def normalize_otp_phone(value: str | None) -> str:
    raw = str(value or "").strip().replace(" ", "")
    if raw.startswith("+"):
        raw = raw[1:]
    if raw.startswith("00"):
        raw = raw[2:]
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith(MOZAMBIQUE_COUNTRY_CODE) and len(digits) == 12:
        return digits
    if digits.startswith("0") and len(digits) == 10:
        digits = digits[1:]
    if len(digits) == 9 and digits[0] in "89":
        return f"{MOZAMBIQUE_COUNTRY_CODE}{digits}"
    return digits


def is_valid_otp_phone(value: str | None) -> bool:
    phone = normalize_otp_phone(value)
    return phone.startswith(MOZAMBIQUE_COUNTRY_CODE) and len(phone) == 12 and phone[3] in "89"


def generate_otp() -> tuple[str, str]:
    code = f"{secrets.randbelow(1000000):06d}"
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    return code, code_hash


def send_otp_sms(phone: str, code: str):
    from apps.sms.services.sender import send_sms
    msg = f"BuzUp: O seu codigo de verificacao e {code}. Valido por {OTP_TTL_MINUTES} minutos."
    return send_sms(phone, msg, purpose="OTP")


def verify_otp_hash(code: str, stored_hash: str) -> bool:
    return hashlib.sha256(code.encode()).hexdigest() == stored_hash
