"""Passenger onboarding flow run from the POS.

Endpoint:
    POST /api/agent/passengers/onboard/

Flow (all atomic):
  1. Agent submits passenger data + the card UID they're about to hand over.
  2. We create the PassengerAccount + Wallet + assigns the card to that
     passenger (status → ACTIVE).
  3. We open a PaymentIntent for the card issuance fee. Today we only support
     mobile money (M-Pesa / E-Mola); the agent provides the payer phone.
  4. If the gateway confirms immediately, we credit the wallet... actually we
     DON'T credit it — the fee is for issuance. Instead we just mark the PI as
     CONFIRMED. The agent collected the money for the company.
  5. We provision the User account (passenger_<phone>) and send the SMS with
     instructions (existing helper).
  6. Return everything to the POS so it can print a receipt + show success.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from django.conf import settings as django_settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agent_api.permissions import IsActiveAgent
from apps.audit.services import audit, client_ip
from apps.cards.models import Card
from apps.cards.services import assign_card_to_passenger, CardError
from apps.fares.models import AdminFee
from apps.passengers.models import PassengerAccount
from apps.passengers.services import ensure_passenger_access_account
from apps.payments.models import PaymentIntent
from apps.payments.services.gateway import get_payment_gateway
from apps.payments.services.processing import confirm_payment_immediately
from apps.users.otp import normalize_otp_phone
from apps.wallets.models import Wallet


def _mask_phone(phone: str) -> str:
    p = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(p) < 4:
        return p
    return f"***{p[-4:]}"


class PassengerOnboardSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True)
    document_type = serializers.ChoiceField(
        choices=PassengerAccount.DocumentType.choices,
        required=False, allow_blank=True,
    )
    document_number = serializers.CharField(max_length=64, required=False, allow_blank=True)
    # Card the agent is handing over (must be INACTIVE & not yet linked)
    card_uid = serializers.CharField(max_length=64, required=False, allow_blank=True)
    qr_token = serializers.CharField(max_length=256, required=False, allow_blank=True)
    # Mobile money charge for the issuance fee
    payer_phone = serializers.CharField(max_length=20)
    fee = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True,
    )
    notify_sms = serializers.BooleanField(default=True)
    device_serial = serializers.CharField(max_length=128, required=False, allow_blank=True)

    def validate(self, attrs):
        if not (attrs.get("card_uid") or attrs.get("qr_token")):
            raise serializers.ValidationError(
                "Indique card_uid ou qr_token do cartao a entregar."
            )
        return attrs


class AgentPassengerOnboardView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request):
        serializer = PassengerOnboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        phone = normalize_otp_phone(data["phone"])
        if not phone:
            return Response({"detail": "Telefone do passageiro invalido."}, status=400)

        # Idempotency: if a passenger already exists for this phone, prevent
        # double-creation (uniqueness on PhoneAccount.phone_number is partial
        # active, but we still guard against re-running with same data).
        if PassengerAccount.objects.filter(phone_number=phone, deleted_at__isnull=True).exists():
            return Response(
                {"detail": "Ja existe uma conta de passageiro com este telefone."},
                status=409,
            )

        # Resolve the card. Must be INACTIVE so it can be assigned.
        import hashlib
        if data.get("card_uid"):
            card = Card.objects.filter(card_uid=data["card_uid"].strip().upper()).first()
        else:
            token_hash = hashlib.sha256(data["qr_token"].strip().encode()).hexdigest()
            card = Card.objects.filter(qr_token_hash=token_hash).first()
        if not card:
            return Response({"detail": "Cartao nao encontrado no inventario."}, status=404)
        if card.status != Card.Status.INACTIVE:
            return Response(
                {"detail": f"Cartao {card.card_number} esta {card.status}. Use um cartao novo."},
                status=400,
            )
        if card.passenger_account_id:
            return Response({"detail": "Cartao ja esta vinculado a outro passageiro."}, status=400)

        fee = data.get("fee")
        if fee is None or fee <= Decimal("0.00"):
            # AdminFee resolves from DB (commercial can change without code
            # deploy). Falls back to the historical settings constant if no
            # active fee row exists.
            default = Decimal(str(getattr(django_settings, "CARD_ISSUE_FEE", "50.00")))
            fee = AdminFee.resolve(AdminFee.Kind.CARD_ISSUANCE, default=default)

        # Atomic block: create passenger + assign card + create PI. If gateway
        # initiation fails, everything rolls back.
        ref = f"ISS-{uuid4().hex[:12].upper()}"
        with transaction.atomic():
            passenger = PassengerAccount.objects.create(
                full_name=data["full_name"].strip(),
                phone_number=phone,
                email=(data.get("email") or "").strip(),
                document_type=data.get("document_type") or "",
                document_number=data.get("document_number") or "",
                status=PassengerAccount.Status.ACTIVE,
            )
            try:
                assign_card_to_passenger(card, passenger)
            except CardError as e:
                raise serializers.ValidationError(str(e))

            pi = PaymentIntent.objects.create(
                reference=f"PAY-{ref}",
                idempotency_key=f"card-issue-{ref}",
                purpose=PaymentIntent.Purpose.POS_CARD_TOPUP,
                amount=fee,
                payer_phone=data["payer_phone"].strip(),
                wallet=passenger.wallet if hasattr(passenger, "wallet") else None,
                status=PaymentIntent.Status.PENDING,
                created_by=request.user,
                metadata={
                    "agent_user_id": request.user.id,
                    "device_serial": data.get("device_serial", ""),
                    "kind": "card_issuance",
                    "card_id": card.id,
                    "card_uid": card.card_uid,
                    "passenger_id": passenger.id,
                    "channel": "POS",
                },
            )

            gateway = get_payment_gateway(payer_phone=data["payer_phone"])
            result = gateway.initiate_payment(
                reference=ref,
                amount=fee,
                payer_phone=data["payer_phone"],
                description=f"BuzUp: emissao cartao {card.card_number}",
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
                # Roll back the passenger + card assignment via raising
                raise serializers.ValidationError(
                    result.detail_message or result.error or "Falha no pagamento."
                )

        # Provision user account + send SMS (separate from the atomic block —
        # if SMS fails the passenger still exists and can be re-fetched).
        try:
            user, wallet, digital_card = ensure_passenger_access_account(
                passenger, notify_by_sms=bool(data.get("notify_sms", True)),
            )
        except Exception as e:
            user, wallet, digital_card = (None, None, None)
            audit("PASSENGER_ONBOARD_ACCESS_FAILED", actor=request.user,
                  entity_type="passenger", entity_id=str(passenger.id),
                  after={"error": str(e)})

        audit(
            "PASSENGER_ONBOARDED",
            actor=request.user,
            entity_type="passenger", entity_id=str(passenger.id),
            ip=client_ip(request),
            after={
                "phone": _mask_phone(phone),
                "card_uid": card.card_uid,
                "card_number": card.card_number,
                "fee": str(fee),
                "payment_status": pi.status,
                "payment_reference": pi.reference,
            },
        )

        return Response({
            "passenger": {
                "id": passenger.id,
                "uuid": str(passenger.uuid),
                "full_name": passenger.full_name,
                "phone_masked": _mask_phone(passenger.phone_number),
            },
            "card": {
                "id": card.id,
                "card_number": card.card_number,
                "card_uid": card.card_uid,
            },
            "digital_card": {
                "card_number": digital_card.card_number if digital_card else None,
            } if digital_card else None,
            "wallet": {
                "uuid": str(wallet.uuid) if wallet else None,
                "balance": str(wallet.balance_cached) if wallet else "0.00",
            } if wallet else None,
            "user_account": {
                "username": user.username if user else None,
                "sms_sent": bool(data.get("notify_sms", True)) and user is not None,
            },
            "payment": {
                "reference": pi.reference,
                "status": pi.status,
                "amount": str(pi.amount),
                "provider": pi.provider,
                "detail_message": result.detail_message,
            },
        }, status=201)
