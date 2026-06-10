from __future__ import annotations

import json
import logging

from django.conf import settings
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
from apps.payments.services.webhook_security import verify_webhook_signature

logger = logging.getLogger(__name__)


def _check_webhook_auth(request) -> tuple[bool, Response | None]:
    """Autentica um callback de pagamento de fonte externa.

    Devolve ``(signature_valid, reject)``. Se ``reject`` nao for None, a view
    deve devolve-lo imediatamente (callback recusado, NADA e processado).

    Regra:
      - segredo configurado -> exige HMAC/token valido, senao 401;
      - sem segredo + PAYMENT_WEBHOOK_REQUIRE_SIGNATURE (prod) -> 503 fail-closed;
      - sem segredo + nao obrigatorio (dev/test) -> aceita mas signature_valid=False.
    """
    secret = getattr(settings, "PAYMENT_GATEWAY_WEBHOOK_SECRET", "") or ""
    require = getattr(settings, "PAYMENT_WEBHOOK_REQUIRE_SIGNATURE", False)

    if secret:
        ok, method = verify_webhook_signature(request, secret)
        if not ok:
            logger.warning("[PAY][webhook_auth] recusado: assinatura/token invalido (metodo=%s)", method)
            return False, Response({"detail": "Assinatura invalida."}, status=status.HTTP_401_UNAUTHORIZED)
        logger.info("[PAY][webhook_auth] aceite via %s", method)
        return True, None

    if require:
        logger.error(
            "[PAY][webhook_auth] PAYMENT_GATEWAY_WEBHOOK_SECRET nao configurado e "
            "assinatura obrigatoria — a recusar callback.",
        )
        return False, Response({"detail": "Webhook nao configurado."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    logger.warning("[PAY][webhook_auth] sem segredo configurado — callback aceite SEM verificacao (apenas dev/test).")
    return False, None


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
        signature_valid, reject = _check_webhook_auth(request)
        if reject is not None:
            return reject

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

        callback = process_payment_callback(
            payment_intent, raw_payload, provider=provider, signature_valid=signature_valid,
        )
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

        signature_valid, reject = _check_webhook_auth(request)
        if reject is not None:
            return reject

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

        callback = process_payment_callback(
            payment_intent, payload, provider=normalized_provider, signature_valid=signature_valid,
        )
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
