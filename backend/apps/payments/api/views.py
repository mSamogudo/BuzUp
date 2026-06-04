from __future__ import annotations

import json
import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.viewsets import BaseModelViewSet
from apps.payments.api.serializers import (
    PaymentCallbackIngestSerializer,
    PaymentIntentSerializer,
)
from apps.payments.models import PaymentIntent
from apps.payments.services.gateway import _extract_value
from apps.payments.services.processing import process_payment_callback

logger = logging.getLogger(__name__)


class PaymentIntentViewSet(BaseModelViewSet):
    queryset = (
        PaymentIntent.all_objects
        .select_related("wallet__passenger_account", "guest_checkout", "created_by")
        .all()
    )
    serializer_class = PaymentIntentSerializer
    http_method_names = ["get", "head", "options"]
    required_capabilities_by_action = {
        "list": ("payments.read",),
        "retrieve": ("payments.read",),
    }

    _SOURCE_FILTERS = {
        "MOBILE": ["mobile_wallet_topup", "app_travel_pass_purchase"],
        "POS": ["pos_card_topup", "direct_trip_payment"],
        "PORTAL": ["guest_travel_pass_purchase", "refund"],
    }

    def get_queryset(self):
        qs = super().get_queryset()
        payer = self.request.query_params.get("payer_phone")
        if payer:
            qs = qs.filter(payer_phone=payer)
        pi_status = self.request.query_params.get("status")
        if pi_status:
            statuses = [s.strip() for s in pi_status.split(",") if s.strip()]
            qs = qs.filter(status__in=statuses)
        purpose = self.request.query_params.get("purpose")
        if purpose:
            purposes = [item.strip() for item in purpose.split(",") if item.strip()]
            qs = qs.filter(purpose__in=purposes)
        provider = self.request.query_params.get("provider")
        if provider:
            providers = [p.strip().lower() for p in provider.split(",") if p.strip()]
            qs = qs.filter(provider__in=providers)
        source = self.request.query_params.get("source")
        if source:
            sources = {s.strip().upper() for s in source.split(",") if s.strip()}
            purposes = []
            for s in sources:
                purposes.extend(self._SOURCE_FILTERS.get(s, []))
            if purposes:
                qs = qs.filter(purpose__in=purposes)
        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs


class PaymentCallbackView(APIView):
    """Simple callback for testing and mock provider."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, provider):
        serializer = PaymentCallbackIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reference = serializer.validated_data["reference"]
        try:
            payment_intent = PaymentIntent.objects.get(reference=reference)
        except PaymentIntent.DoesNotExist:
            return Response(
                {"detail": "Payment intent not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        raw_payload = {
            "provider": provider,
            **serializer.validated_data,
        }

        callback = process_payment_callback(payment_intent, raw_payload, provider=provider)
        payment_intent.refresh_from_db()

        return Response({
            "callback_id": callback.pk,
            "processing_status": callback.processing_status,
            "payment_status": payment_intent.status,
        })


class MobileWalletWebhookView(APIView):
    """Webhook endpoint for real MPESA/EMOLA callbacks from Payless."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, provider):
        normalized_provider = str(provider or "").upper()
        if normalized_provider not in ("MPESA", "EMOLA"):
            return Response({"detail": "Unsupported provider."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if isinstance(request.data, dict):
                payload = request.data
            else:
                raw = request.body.decode("utf-8", errors="replace")
                payload = json.loads(raw) if raw else {}
        except (json.JSONDecodeError, Exception):
            return Response({"detail": "Invalid payload."}, status=status.HTTP_400_BAD_REQUEST)

        payload_body = payload.get("data", payload) if isinstance(payload.get("data"), dict) else payload

        reference = _extract_value(payload_body, (
            "thirdPartyReference", "third_party_reference",
            "transactionReference", "transaction_reference",
            "requestReference", "request_reference",
            "reference",
        ))
        provider_reference = _extract_value(payload_body, (
            "output_TransactionID", "data.output_TransactionID",
            "transaction_id", "transactionId", "transaction",
            "provider_reference", "providerReference",
        ))

        payment_intent = _resolve_payment_intent(reference, provider_reference, normalized_provider)
        if not payment_intent:
            logger.warning(
                "Webhook %s: no payment intent found for ref=%s provider_ref=%s",
                normalized_provider, reference, provider_reference,
            )
            return Response({"detail": "Payment intent not found."}, status=status.HTTP_404_NOT_FOUND)

        callback = process_payment_callback(payment_intent, payload, provider=normalized_provider)
        payment_intent.refresh_from_db()

        return Response({
            "callback_id": callback.pk,
            "processing_status": callback.processing_status,
            "payment_status": payment_intent.status,
        })


def _resolve_payment_intent(reference: str, provider_reference: str, provider: str) -> PaymentIntent | None:
    if reference:
        pi = PaymentIntent.objects.filter(reference=reference).first()
        if pi:
            return pi
        pi = PaymentIntent.objects.filter(
            metadata__gateway_response__transactionReference=reference,
        ).first()
        if pi:
            return pi
        pi = PaymentIntent.objects.filter(
            metadata__gateway_response__thirdPartyReference=reference,
        ).first()
        if pi:
            return pi

    if provider_reference:
        pi = PaymentIntent.objects.filter(provider_reference=provider_reference).first()
        if pi:
            return pi

    return None
