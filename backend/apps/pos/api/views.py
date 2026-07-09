from __future__ import annotations

from uuid import uuid4

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cards.models import Card
from apps.devices.models import Device
from apps.packages.models import Package
from apps.packages.services import PackageError, subscribe_passenger
from apps.payments.models import PaymentIntent
from apps.payments.services.gateway import get_payment_gateway
from apps.payments.services.processing import confirm_payment_immediately
from apps.pos.api.serializers import (
    OpenSessionSerializer,
    PosCardTopupSerializer,
    PosCardValidateSerializer,
    PosPackageTopupSerializer,
    PosQrValidateSerializer,
    PosSessionSerializer,
)
from apps.pos.models import PosSession
from apps.routes.models import Route
from apps.validations.api.serializers import ValidationEventSerializer
from apps.validations.services import validate_card, validate_qr_pass
from apps.wallets.services import InsufficientBalanceError


class OpenSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OpenSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            device = Device.objects.get(serial_number=data["device_serial"])
        except Device.DoesNotExist:
            return Response({"detail": "Dispositivo nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if device.status != Device.Status.ACTIVE:
            return Response({"detail": "Dispositivo nao activo."}, status=status.HTTP_403_FORBIDDEN)

        PosSession.objects.filter(agent=request.user, status=PosSession.Status.ACTIVE).update(
            status=PosSession.Status.CLOSED, closed_at=timezone.now(),
        )

        route = None
        if data.get("route_id"):
            route = Route.objects.filter(pk=data["route_id"]).first()

        session = PosSession.objects.create(
            agent=request.user,
            device=device,
            allocated_route=route,
        )

        return Response(PosSessionSerializer(session).data, status=status.HTTP_201_CREATED)


class CloseSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = PosSession.objects.filter(
            agent=request.user, status=PosSession.Status.ACTIVE,
        ).update(status=PosSession.Status.CLOSED, closed_at=timezone.now())
        return Response({"closed": updated})


class ActiveSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session = PosSession.objects.select_related(
            "device", "allocated_route",
        ).filter(agent=request.user, status=PosSession.Status.ACTIVE).first()
        if not session:
            return Response({"detail": "Sem sessao activa."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PosSessionSerializer(session).data)


class PosCardValidateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PosCardValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        session = PosSession.objects.select_related("device", "allocated_route").filter(
            agent=request.user, status=PosSession.Status.ACTIVE,
        ).first()
        if not session:
            return Response({"detail": "Sem sessao activa."}, status=status.HTTP_403_FORBIDDEN)

        route_id = session.allocated_route_id
        if not route_id:
            return Response({"detail": "Sessao sem rota alocada."}, status=status.HTTP_400_BAD_REQUEST)

        event = validate_card(
            card_uid=data["card_uid"],
            route_id=route_id,
            device_serial=session.device.serial_number,
            idempotency_key=data["idempotency_key"],
        )

        return Response(ValidationEventSerializer(event).data)


class PosQrValidateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PosQrValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        session = PosSession.objects.select_related("device", "allocated_route").filter(
            agent=request.user, status=PosSession.Status.ACTIVE,
        ).first()
        if not session:
            return Response({"detail": "Sem sessao activa."}, status=status.HTTP_403_FORBIDDEN)

        event = validate_qr_pass(
            token=data["token"],
            route_id=session.allocated_route_id,
            device_serial=session.device.serial_number,
            idempotency_key=data["idempotency_key"],
        )

        return Response(ValidationEventSerializer(event).data)


class PosCardTopupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PosCardTopupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        session = PosSession.objects.filter(
            agent=request.user, status=PosSession.Status.ACTIVE,
        ).first()
        if not session:
            return Response({"detail": "Sem sessao activa."}, status=status.HTTP_403_FORBIDDEN)

        try:
            card = Card.objects.select_related("wallet").get(card_uid=data["card_uid"])
        except Card.DoesNotExist:
            return Response({"detail": "Cartao nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if card.status != Card.Status.ACTIVE:
            return Response({"detail": "Cartao nao activo."}, status=status.HTTP_400_BAD_REQUEST)

        if not card.wallet:
            return Response({"detail": "Cartao sem carteira."}, status=status.HTTP_400_BAD_REQUEST)

        amount = data["amount"]
        payer_phone = data["payer_phone"]
        ref = f"POS-{uuid4().hex[:12].upper()}"
        idempotency_key = f"pos-topup-{ref}"

        pi = PaymentIntent.objects.create(
            reference=ref,
            idempotency_key=idempotency_key,
            purpose=PaymentIntent.Purpose.POS_CARD_TOPUP,
            amount=amount,
            payer_phone=payer_phone,
            wallet=card.wallet,
            status=PaymentIntent.Status.PENDING,
            created_by=request.user,
        )

        gateway = get_payment_gateway(payer_phone=payer_phone)
        result = gateway.initiate_payment(
            reference=ref, amount=amount, payer_phone=payer_phone,
            description=f"Recarga BusUp Cartao {data['card_uid'][:8]}",
        )

        pi.provider = result.provider
        pi.metadata = {"gateway_request": result.request_payload or {}, "gateway_response": result.response_payload or {}}

        if result.success:
            pi.provider_reference = result.provider_reference
            pi.save(update_fields=["provider", "provider_reference", "metadata", "updated_at"])
            confirm_payment_immediately(pi, result.provider_reference)
            pi.refresh_from_db()
            card.wallet.refresh_from_db()
        elif result.pending:
            pi.provider_reference = result.provider_reference
            pi.save(update_fields=["provider", "provider_reference", "metadata", "updated_at"])
        else:
            pi.status = PaymentIntent.Status.FAILED
            pi.save(update_fields=["status", "provider", "metadata", "updated_at"])
            return Response({"detail": result.detail_message or "Falha."}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({
            "payment_reference": pi.reference,
            "payment_status": pi.status,
            "card_uid": card.card_uid,
            "balance": str(card.wallet.balance_cached),
            "detail_message": result.detail_message,
        }, status=status.HTTP_201_CREATED)


class PosPackageSubscribeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PosPackageTopupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        session = PosSession.objects.filter(
            agent=request.user, status=PosSession.Status.ACTIVE,
        ).first()
        if not session:
            return Response({"detail": "Sem sessao activa."}, status=status.HTTP_403_FORBIDDEN)

        try:
            card = Card.objects.select_related("wallet", "passenger_account").get(card_uid=data["card_uid"])
        except Card.DoesNotExist:
            return Response({"detail": "Cartao nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if not card.passenger_account:
            return Response({"detail": "Cartao sem conta de passageiro."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            package = Package.objects.get(pk=data["package_id"], status=Package.Status.ACTIVE)
        except Package.DoesNotExist:
            return Response({"detail": "Pacote nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        try:
            sub = subscribe_passenger(card.passenger_account, package, pay_from_wallet=True)
        except (PackageError, InsufficientBalanceError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "subscription_id": sub.id,
            "package_name": package.name,
            "special_balance": str(sub.special_balance),
            "trips_remaining": sub.trips_remaining,
            "expires_at": sub.expires_at.isoformat(),
        }, status=status.HTTP_201_CREATED)
