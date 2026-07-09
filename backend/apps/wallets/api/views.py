from uuid import uuid4

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import HasCapabilities
from apps.core.viewsets import BaseModelViewSet
from apps.payments.models import PaymentIntent
from apps.payments.services.gateway import get_payment_gateway
from apps.payments.services.processing import confirm_payment_immediately
from apps.wallets.api.serializers import TopupRequestSerializer, WalletSerializer, WalletTransactionSerializer
from apps.wallets.models import Wallet, WalletTransaction


class WalletViewSet(BaseModelViewSet):
    queryset = Wallet.all_objects.select_related("passenger_account").all()
    serializer_class = WalletSerializer
    http_method_names = ["get", "head", "options"]
    required_capabilities_by_action = {
        "list": ("wallets.read",),
        "retrieve": ("wallets.read",),
    }


class WalletTransactionViewSet(BaseModelViewSet):
    queryset = WalletTransaction.all_objects.all()
    serializer_class = WalletTransactionSerializer
    http_method_names = ["get", "head", "options"]
    required_capabilities_by_action = {
        "list": ("wallets.read",),
        "retrieve": ("wallets.read",),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        wallet_uuid = self.request.query_params.get("wallet")
        if wallet_uuid:
            qs = qs.filter(wallet__uuid=wallet_uuid)
        return qs


class TopupView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("wallets.manage",)

    def post(self, request):
        serializer = TopupRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            wallet = Wallet.objects.get(uuid=serializer.validated_data["wallet_uuid"])
        except Wallet.DoesNotExist:
            return Response({"detail": "Carteira nao encontrada."}, status=status.HTTP_404_NOT_FOUND)

        if wallet.status != Wallet.Status.ACTIVE:
            return Response({"detail": "Carteira bloqueada."}, status=status.HTTP_400_BAD_REQUEST)

        amount = serializer.validated_data["amount"]
        payer_phone = serializer.validated_data["payer_phone"]
        idempotency_key = request.headers.get("Idempotency-Key", uuid4().hex)

        existing = PaymentIntent.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return Response({
                "payment_intent": str(existing.uuid),
                "reference": existing.reference,
                "status": existing.status,
            })

        ref = f"TOP-{uuid4().hex[:12].upper()}"
        pi = PaymentIntent.objects.create(
            reference=ref,
            idempotency_key=idempotency_key,
            purpose=PaymentIntent.Purpose.MOBILE_WALLET_TOPUP,
            amount=amount,
            payer_phone=payer_phone,
            wallet=wallet,
            status=PaymentIntent.Status.PENDING,
            created_by=request.user,
        )

        gateway = get_payment_gateway(payer_phone=payer_phone)
        result = gateway.initiate_payment(
            reference=ref,
            amount=amount,
            payer_phone=payer_phone,
            description=f"Recarga BusUp {amount} MZN",
        )

        pi.provider = result.provider
        pi.metadata = {
            "gateway_request": result.request_payload or {},
            "gateway_response": result.response_payload or {},
        }

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
            return Response({
                "detail": result.detail_message or result.error or "Falha no pagamento.",
            }, status=status.HTTP_502_BAD_GATEWAY)

        return Response({
            "payment_intent": str(pi.uuid),
            "reference": pi.reference,
            "status": pi.status,
            "detail_message": result.detail_message,
        }, status=status.HTTP_201_CREATED)
