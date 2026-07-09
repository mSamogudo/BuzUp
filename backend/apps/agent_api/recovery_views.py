"""Card recovery flow run by the agent on the POS.

    POST /api/agent/passengers/recover-card/request-otp/   → opens session
    POST /api/agent/passengers/recover-card/verify-otp/    → mints recovery_token
    POST /api/agent/passengers/recover-card/associate/     → swaps card + charges fee
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agent_api.models import RecoverySession
from apps.agent_api.permissions import IsActiveAgent
from apps.audit.services import audit, client_ip
from apps.cards.models import Card
from apps.cards.services import assign_card_to_passenger, CardError
from apps.fares.models import AdminFee
from apps.passengers.models import PassengerAccount
from apps.payments.models import PaymentIntent
from apps.payments.services.gateway import get_payment_gateway
from apps.payments.services.processing import confirm_payment_immediately
from apps.users.otp import generate_otp, normalize_otp_phone, send_otp_sms, verify_otp_hash


def _mask_phone(phone: str) -> str:
    p = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(p) < 4:
        return p
    return f"***{p[-4:]}"


class _OtpStartSerializer(serializers.Serializer):
    passenger_phone = serializers.CharField(max_length=20)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)


class _OtpVerifySerializer(serializers.Serializer):
    challenge_id = serializers.CharField(max_length=64)
    otp_code = serializers.CharField(max_length=8)


class _AssociateSerializer(serializers.Serializer):
    recovery_token = serializers.CharField(max_length=64)
    new_card_uid = serializers.CharField(max_length=64, required=False, allow_blank=True)
    new_qr_token = serializers.CharField(max_length=256, required=False, allow_blank=True)
    payer_phone = serializers.CharField(max_length=20)
    fee_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True,
    )

    def validate(self, attrs):
        if not (attrs.get("new_card_uid") or attrs.get("new_qr_token")):
            raise serializers.ValidationError("Indique new_card_uid ou new_qr_token.")
        return attrs


class AgentRecoverCardRequestOtpView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request):
        ser = _OtpStartSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = normalize_otp_phone(ser.validated_data["passenger_phone"])
        if not phone:
            return Response({"detail": "Telefone invalido."}, status=400)

        passenger = PassengerAccount.objects.filter(
            phone_number=phone, deleted_at__isnull=True,
        ).first()
        if not passenger:
            audit("RECOVERY_OTP_REQUEST_FAILED",
                  actor=request.user, entity_type="passenger", entity_id="",
                  ip=client_ip(request),
                  after={"reason": "no_passenger", "phone_masked": _mask_phone(phone)})
            return Response({"detail": "Nao existe conta para este telefone."}, status=404)
        if passenger.status != PassengerAccount.Status.ACTIVE:
            return Response(
                {"detail": f"Conta {passenger.status}. Contacte o administrador."},
                status=400,
            )

        code, code_hash = generate_otp()
        challenge_id = uuid4().hex
        session = RecoverySession.objects.create(
            challenge_id=challenge_id,
            agent_user=request.user,
            passenger=passenger,
            phone=phone,
            reason=ser.validated_data.get("reason", ""),
            code_hash=code_hash,
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        try:
            send_otp_sms(phone, code)
        except Exception:
            # SMS failure shouldn't crash the flow; agent can retry
            pass

        audit("RECOVERY_OTP_REQUESTED",
              actor=request.user, entity_type="passenger", entity_id=str(passenger.id),
              ip=client_ip(request),
              after={"phone_masked": _mask_phone(phone),
                     "reason": session.reason,
                     "challenge_id": challenge_id})

        return Response({
            "challenge_id": challenge_id,
            "expires_in": 300,  # 5 minutes
            "phone_masked": _mask_phone(phone),
        })


class AgentRecoverCardVerifyOtpView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request):
        ser = _OtpVerifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        session = RecoverySession.objects.filter(
            challenge_id=ser.validated_data["challenge_id"],
        ).first()
        if not session:
            return Response({"detail": "Sessao de recuperacao nao encontrada."}, status=404)
        if session.agent_user_id != request.user.id:
            return Response({"detail": "Sessao nao corresponde a este agente."}, status=403)
        if session.status != RecoverySession.Status.PENDING:
            return Response({"detail": f"Sessao {session.get_status_display()}."}, status=409)
        if session.is_expired:
            session.status = RecoverySession.Status.EXPIRED
            session.save(update_fields=["status", "updated_at"])
            return Response({"detail": "Codigo expirado. Inicie de novo."}, status=410)
        if session.attempts >= 5:
            session.status = RecoverySession.Status.EXPIRED
            session.save(update_fields=["status", "updated_at"])
            return Response({"detail": "Demasiadas tentativas. Inicie de novo."}, status=429)

        if not verify_otp_hash(ser.validated_data["otp_code"], session.code_hash):
            session.attempts += 1
            session.save(update_fields=["attempts", "updated_at"])
            return Response(
                {"detail": "Codigo invalido.",
                 "attempts_left": max(0, 5 - session.attempts)},
                status=400,
            )

        token = secrets.token_hex(16)
        session.status = RecoverySession.Status.VERIFIED
        session.recovery_token = token
        session.verified_at = timezone.now()
        # Extend lifetime so the agent has time to scan + initiate payment
        session.expires_at = timezone.now() + timedelta(minutes=10)
        session.save(update_fields=["status", "recovery_token", "verified_at", "expires_at", "updated_at"])

        passenger = session.passenger
        cards = passenger.cards.filter(card_type=Card.CardType.PHYSICAL).order_by("-created_at")[:5]

        audit("RECOVERY_OTP_VERIFIED",
              actor=request.user, entity_type="passenger", entity_id=str(passenger.id),
              ip=client_ip(request), after={"recovery_token_id": token[:8]})

        return Response({
            "recovery_token": token,
            "expires_in": 600,
            "passenger": {
                "id": passenger.id,
                "full_name": passenger.full_name,
                "phone_masked": _mask_phone(passenger.phone_number),
                "email": passenger.email or "",
                "document": f"{passenger.document_type or ''} {passenger.document_number or ''}".strip(),
            },
            "existing_physical_cards": [{
                "id": c.id,
                "card_number": c.card_number,
                "status": c.status,
                "activated_at": c.activated_at.isoformat() if c.activated_at else None,
            } for c in cards],
        })


class AgentRecoverCardAssociateView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request):
        ser = _AssociateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        session = RecoverySession.objects.filter(
            recovery_token=data["recovery_token"],
            status=RecoverySession.Status.VERIFIED,
        ).select_related("passenger").first()
        if not session:
            return Response({"detail": "Token de recuperacao invalido ou ja usado."}, status=403)
        if session.agent_user_id != request.user.id:
            return Response({"detail": "Token nao corresponde a este agente."}, status=403)
        if session.is_expired:
            session.status = RecoverySession.Status.EXPIRED
            session.save(update_fields=["status", "updated_at"])
            return Response({"detail": "Sessao expirada. Inicie de novo."}, status=410)

        passenger = session.passenger

        # Resolve the new card
        if data.get("new_card_uid"):
            new_card = Card.objects.filter(card_uid=data["new_card_uid"].strip().upper()).first()
        else:
            token_hash = hashlib.sha256(data["new_qr_token"].strip().encode()).hexdigest()
            new_card = Card.objects.filter(qr_token_hash=token_hash).first()
        if not new_card:
            return Response({"detail": "Cartao novo nao encontrado no inventario."}, status=404)
        if new_card.status != Card.Status.INACTIVE:
            return Response(
                {"detail": f"Cartao {new_card.card_number} esta {new_card.status}. Use um cartao novo."},
                status=400,
            )
        if new_card.passenger_account_id:
            return Response({"detail": "Este cartao ja esta vinculado a outra conta."}, status=409)

        # Resolve fee
        fee = data.get("fee_amount")
        if fee is None or fee <= Decimal("0.00"):
            fee = AdminFee.resolve(AdminFee.Kind.CARD_RECOVERY, default=Decimal("100.00"))

        ref = f"REC-{uuid4().hex[:12].upper()}"
        idem_key = f"recovery-{session.challenge_id}-{new_card.id}"

        if PaymentIntent.objects.filter(idempotency_key=idem_key).exists():
            return Response(
                {"detail": "Esta recuperacao ja foi processada. Inicie nova solicitacao."},
                status=409,
            )

        # Snapshot the IDs of the passenger's OTHER physical cards. They are
        # NOT blocked yet — only when the payment confirms (synchronously here
        # or via webhook later, see `payments.services.processing`). This
        # avoids leaving the passenger card-less if the payment fails.
        old_card_ids = list(
            passenger.cards
            .filter(card_type=Card.CardType.PHYSICAL,
                    status__in=[Card.Status.ACTIVE, Card.Status.INACTIVE])
            .values_list("id", flat=True)
        )

        with transaction.atomic():
            try:
                # notify_sms=False — we'll send the recovery SMS only once the
                # payment is confirmed (sync below or via webhook later).
                assign_card_to_passenger(new_card, passenger, notify_sms=False)
            except CardError as e:
                raise serializers.ValidationError(str(e))

            pi = PaymentIntent.objects.create(
                reference=f"PAY-{ref}",
                idempotency_key=idem_key,
                purpose=PaymentIntent.Purpose.POS_CARD_TOPUP,
                amount=fee,
                payer_phone=data["payer_phone"].strip(),
                wallet=passenger.wallet if hasattr(passenger, "wallet") else None,
                status=PaymentIntent.Status.PENDING,
                created_by=request.user,
                metadata={
                    "agent_user_id": request.user.id,
                    "kind": "card_recovery",
                    "passenger_id": passenger.id,
                    "card_id": new_card.id,
                    "card_uid": new_card.card_uid,
                    "old_card_ids": old_card_ids,
                    "reason": session.reason,
                    "challenge_id": session.challenge_id,
                    "channel": "POS",
                },
            )

            gateway = get_payment_gateway(payer_phone=data["payer_phone"])
            result = gateway.initiate_payment(
                reference=ref,
                amount=fee,
                payer_phone=data["payer_phone"],
                description=f"BusUp: recuperacao cartao {new_card.card_number}",
            )
            pi.provider = result.provider
            pi.metadata = {**(pi.metadata or {}),
                          "gateway_request": result.request_payload or {},
                          "gateway_response": result.response_payload or {}}
            if result.success:
                pi.provider_reference = result.provider_reference
                pi.save(update_fields=["provider", "provider_reference", "metadata", "updated_at"])
                confirm_payment_immediately(pi, result.provider_reference)
                pi.refresh_from_db()
            elif result.pending:
                pi.provider_reference = result.provider_reference
                pi.save(update_fields=["provider", "provider_reference", "metadata", "updated_at"])
            else:
                pi.status = PaymentIntent.Status.FAILED
                pi.save(update_fields=["status", "provider", "metadata", "updated_at"])
                raise serializers.ValidationError(
                    result.detail_message or result.error or "Falha no pagamento."
                )

            session.status = RecoverySession.Status.CONSUMED
            session.consumed_at = timezone.now()
            session.save(update_fields=["status", "consumed_at", "updated_at"])

        # If the gateway confirmed synchronously, run the finalisation now.
        # For pending payments the same routine is triggered later via the
        # `card_recovery` hook in `payments.services.processing._confirm_payment`.
        blocked_count = 0
        if pi.status == PaymentIntent.Status.CONFIRMED:
            blocked_count = finalize_card_recovery(pi)

        audit("PASSENGER_CARD_RECOVERED",
              actor=request.user, entity_type="passenger", entity_id=str(passenger.id),
              ip=client_ip(request),
              after={"new_card_id": new_card.id,
                     "new_card_number": new_card.card_number,
                     "blocked_now": blocked_count,
                     "pending_block": len(old_card_ids) if pi.status != PaymentIntent.Status.CONFIRMED else 0,
                     "fee": str(fee),
                     "payment_status": pi.status})

        return Response({
            "passenger": {
                "id": passenger.id,
                "full_name": passenger.full_name,
                "phone_masked": _mask_phone(passenger.phone_number),
            },
            "card": {
                "id": new_card.id,
                "card_number": new_card.card_number,
                "card_uid": new_card.card_uid,
                "status": new_card.status,
            },
            "old_card_ids": old_card_ids,
            "blocked_now": blocked_count,
            "payment": {
                "reference": pi.reference,
                "status": pi.status,
                "amount": str(pi.amount),
                "provider": pi.provider,
                "detail_message": result.detail_message,
            },
        }, status=201)


# ---------------------------------------------------------------------------
# Recovery finalisation: block old cards + SMS the new card credentials.
#
# Called in two places:
#   1. Inline in `AgentRecoverCardAssociateView` when the gateway returns
#      success synchronously.
#   2. By `apps.payments.services.processing._confirm_payment` when the
#      webhook flips a previously-pending recovery PaymentIntent to CONFIRMED.
#
# Idempotent on the PaymentIntent — we only finalise once (tracked via
# metadata.finalised_at).
# ---------------------------------------------------------------------------

def finalize_card_recovery(pi) -> int:
    """Block the passenger's old physical cards + send the recovery SMS.

    Returns the number of cards blocked. No-op (returns 0) if already done.
    """
    meta = pi.metadata or {}
    if meta.get("finalised_at"):
        return 0
    if meta.get("kind") != "card_recovery":
        return 0

    from apps.cards.models import Card as CardModel
    from apps.passengers.models import PassengerAccount as PA

    old_card_ids = meta.get("old_card_ids") or []
    blocked = 0
    new_card = CardModel.objects.filter(pk=meta.get("card_id")).first()

    for old in CardModel.objects.filter(pk__in=old_card_ids):
        if old.status in (CardModel.Status.BLOCKED, CardModel.Status.LOST):
            continue
        old.status = CardModel.Status.BLOCKED
        old.blocked_at = timezone.now()
        if new_card:
            old.replaced_by = new_card
        old.save(update_fields=["status", "blocked_at", "replaced_by", "updated_at"])
        blocked += 1

    # Mark PI as finalised before sending the SMS so retried webhooks don't
    # double-text the passenger.
    pi.metadata = {**meta, "finalised_at": timezone.now().isoformat(), "blocked_cards": blocked}
    pi.save(update_fields=["metadata", "updated_at"])

    passenger = PA.objects.filter(pk=meta.get("passenger_id")).first()
    if passenger and passenger.phone_number and new_card:
        try:
            from apps.sms.services.sender import send_sms
            send_sms(
                passenger.phone_number,
                (
                    f"BusUp: Recuperacao concluida. O seu novo cartao {new_card.card_number} "
                    f"esta activo. Os cartoes anteriores foram bloqueados."
                ),
                purpose="CARD_RECOVERY_CONFIRMED",
            )
        except Exception:
            pass

    return blocked
