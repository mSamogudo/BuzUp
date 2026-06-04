from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.passengers.models import PassengerAccount
from apps.passengers.services import ensure_passenger_access_account
from apps.users.models import OtpChallenge
from apps.users.otp import (
    OTP_MAX_ATTEMPTS,
    OTP_TTL_MINUTES,
    generate_otp,
    is_valid_otp_phone,
    normalize_otp_phone,
    send_otp_sms,
    verify_otp_hash,
)


def _client_ip(request) -> str:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _rate_limit_exceeded(key: str, limit: int, window_seconds: int) -> bool:
    if limit <= 0 or window_seconds <= 0:
        return False
    if cache.add(key, 1, timeout=window_seconds):
        return False
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        return False
    return count > limit


class PhoneCheckView(APIView):
    """Tells the mobile app whether a phone already has an account.

    Used before sending an OTP so a brand-new passenger can be shown a quick
    registration form. Does NOT send SMS, so it is cheap and rate-limit-light.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        phone = normalize_otp_phone(request.data.get("phone", ""))
        if not is_valid_otp_phone(phone):
            return Response({"detail": "Telefone invalido."}, status=status.HTTP_400_BAD_REQUEST)

        # Throttle to blunt account-enumeration: this endpoint reveals whether a
        # phone has an account, so cap it per IP (and per phone).
        window = getattr(settings, "OTP_REQUEST_WINDOW_SECONDS", 300)
        client_ip = _client_ip(request)
        if client_ip and _rate_limit_exceeded(f"check:ip:{client_ip}", getattr(settings, "PHONE_CHECK_MAX_PER_IP", 30), window):
            return Response({"detail": "Muitas tentativas. Tente novamente mais tarde."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        if _rate_limit_exceeded(f"check:phone:{phone}", getattr(settings, "PHONE_CHECK_MAX_PER_PHONE", 8), window):
            return Response({"detail": "Muitas tentativas. Tente novamente mais tarde."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        from apps.trips.models import Agent as AgentModel
        from apps.trips.models import Driver as DriverModel

        # Only disclose existence (not the role) — the app just needs to decide
        # between login and registration.
        exists = (
            DriverModel.objects.filter(phone=phone, status=DriverModel.Status.ACTIVE).exists()
            or AgentModel.objects.filter(phone=phone, status=AgentModel.Status.ACTIVE).exists()
            or PassengerAccount.objects.filter(phone_number=phone).exists()
        )
        return Response({"exists": exists})


class OtpRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        phone = normalize_otp_phone(request.data.get("phone", ""))
        if not is_valid_otp_phone(phone):
            return Response({"detail": "Telefone invalido."}, status=status.HTTP_400_BAD_REQUEST)

        window_seconds = getattr(settings, "OTP_REQUEST_WINDOW_SECONDS", 300)
        max_phone_requests = getattr(settings, "OTP_MAX_REQUESTS_PER_PHONE", 3)
        max_ip_requests = getattr(settings, "OTP_MAX_REQUESTS_PER_IP", 20)
        if _rate_limit_exceeded(f"otp:request:phone:{phone}", max_phone_requests, window_seconds):
            return Response({"detail": "Muitas tentativas. Tente novamente mais tarde."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        client_ip = _client_ip(request)
        if client_ip and _rate_limit_exceeded(f"otp:request:ip:{client_ip}", max_ip_requests, window_seconds):
            return Response({"detail": "Muitas tentativas. Tente novamente mais tarde."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        OtpChallenge.objects.filter(
            phone=phone, status=OtpChallenge.Status.PENDING,
        ).update(status=OtpChallenge.Status.EXPIRED)

        code, code_hash = generate_otp()
        challenge = OtpChallenge.objects.create(
            phone=phone,
            code_hash=code_hash,
            expires_at=timezone.now() + timedelta(minutes=OTP_TTL_MINUTES),
        )

        sms = send_otp_sms(phone, code)
        if sms.status == sms.Status.FAILED:
            challenge.status = OtpChallenge.Status.EXPIRED
            challenge.save(update_fields=["status", "updated_at"])
            return Response(
                {"detail": "Nao foi possivel enviar o codigo por SMS."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({
            "challenge_id": str(challenge.uuid),
            "expires_in": OTP_TTL_MINUTES * 60,
            "phone": phone,
        })


class OtpVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        challenge_id = request.data.get("challenge_id", "")
        code = str(request.data.get("code", "")).strip()
        phone = normalize_otp_phone(request.data.get("phone", ""))
        full_name = str(request.data.get("full_name", "")).strip()[:255]
        email = str(request.data.get("email", "")).strip()[:254]

        if not code or not phone:
            return Response({"detail": "Codigo e telefone obrigatorios."}, status=status.HTTP_400_BAD_REQUEST)
        if not code.isdigit() or len(code) != 6:
            return Response({"detail": "Codigo invalido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            challenge = OtpChallenge.objects.get(
                uuid=challenge_id,
                phone=phone,
                status=OtpChallenge.Status.PENDING,
            )
        except OtpChallenge.DoesNotExist:
            return Response({"detail": "Codigo expirado ou invalido."}, status=status.HTTP_400_BAD_REQUEST)

        if timezone.now() > challenge.expires_at:
            challenge.status = OtpChallenge.Status.EXPIRED
            challenge.save(update_fields=["status", "updated_at"])
            return Response({"detail": "Codigo expirado."}, status=status.HTTP_400_BAD_REQUEST)

        if challenge.attempts >= OTP_MAX_ATTEMPTS:
            challenge.status = OtpChallenge.Status.EXPIRED
            challenge.save(update_fields=["status", "updated_at"])
            return Response({"detail": "Tentativas excedidas."}, status=status.HTTP_400_BAD_REQUEST)

        if not verify_otp_hash(code, challenge.code_hash):
            challenge.attempts += 1
            update_fields = ["attempts", "updated_at"]
            detail = "Codigo incorreto."
            if challenge.attempts >= OTP_MAX_ATTEMPTS:
                challenge.status = OtpChallenge.Status.EXPIRED
                update_fields.append("status")
                detail = "Tentativas excedidas."
            challenge.save(update_fields=update_fields)
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        challenge.status = OtpChallenge.Status.VERIFIED
        challenge.verified_at = timezone.now()
        challenge.save(update_fields=["status", "verified_at", "updated_at"])

        from apps.trips.models import Agent as AgentModel
        from apps.trips.models import Driver as DriverModel

        driver = DriverModel.objects.filter(phone=phone, status=DriverModel.Status.ACTIVE).select_related("user").first()
        if driver and driver.user:
            user = driver.user
            user.is_active = True
            if full_name and not (user.first_name or "").strip():
                user.first_name = full_name
            user.save(update_fields=["is_active", "first_name", "updated_at"])

            refresh = RefreshToken.for_user(user)
            refresh["driver_id"] = driver.id
            refresh["phone"] = phone
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "driver_id": driver.id,
                "is_new": False,
            })

        agent = AgentModel.objects.filter(phone=phone, status=AgentModel.Status.ACTIVE).select_related("user").first()
        if agent and agent.user:
            user = agent.user
            user.is_active = True
            if full_name and not (user.first_name or "").strip():
                user.first_name = full_name
            user.save(update_fields=["is_active", "first_name", "updated_at"])

            refresh = RefreshToken.for_user(user)
            refresh["agent_id"] = agent.id
            refresh["phone"] = phone
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "agent_id": agent.id,
                "is_new": False,
            })

        with transaction.atomic():
            passenger, created = PassengerAccount.objects.select_for_update().get_or_create(
                phone_number=phone,
                defaults={"full_name": full_name, "email": email, "status": PassengerAccount.Status.ACTIVE},
            )
            if passenger.status != PassengerAccount.Status.ACTIVE:
                return Response({"detail": "Conta de passageiro bloqueada ou suspensa."}, status=status.HTTP_403_FORBIDDEN)

            profile_fields = []
            if full_name and not passenger.full_name.strip():
                passenger.full_name = full_name
                profile_fields.append("full_name")
            if email and not passenger.email.strip():
                passenger.email = email
                profile_fields.append("email")
            if profile_fields:
                passenger.save(update_fields=profile_fields + ["updated_at"])

        user, _wallet, _digital_card = ensure_passenger_access_account(passenger, notify_by_sms=created)

        refresh = RefreshToken.for_user(user)
        refresh["passenger_id"] = passenger.id
        refresh["phone"] = phone

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "passenger_id": passenger.id,
            "is_new": created,
        })
