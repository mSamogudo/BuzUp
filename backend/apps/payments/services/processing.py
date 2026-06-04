from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from apps.payments.models import PaymentCallback, PaymentIntent
from apps.payments.services.gateway import _extract_value, _interpret_response
from apps.wallets.models import WalletTransaction
from apps.wallets.services import credit_wallet

logger = logging.getLogger(__name__)


def process_payment_callback(
    payment_intent: PaymentIntent,
    raw_payload: dict,
    provider: str = "",
) -> PaymentCallback:
    provider_ref = _extract_value(raw_payload, (
        "provider_reference", "providerReference",
        "output_TransactionID", "data.output_TransactionID",
        "transaction_id", "transactionId", "reference",
    ))
    logger.info(
        "[PAY][callback] ref=%s provider=%s intent_status=%s amount=%s provider_ref=%s",
        payment_intent.reference, provider or payment_intent.provider,
        payment_intent.status, payment_intent.amount, provider_ref,
    )

    callback = PaymentCallback.objects.create(
        payment_intent=payment_intent,
        provider_reference=provider_ref,
        raw_payload=raw_payload,
        signature_valid=True,
        processing_status="received",
    )

    if payment_intent.status == PaymentIntent.Status.CONFIRMED:
        logger.info("[PAY][callback_dup] ref=%s already CONFIRMED, skipping", payment_intent.reference)
        callback.processing_status = "duplicate"
        callback.save(update_fields=["processing_status", "updated_at"])
        return callback

    resolved_provider = provider or payment_intent.provider or ""
    result, detail, ext_ref = _resolve_callback_result(resolved_provider, raw_payload)
    logger.info(
        "[PAY][callback_result] ref=%s result=%s detail=%s ext_ref=%s",
        payment_intent.reference, result, detail, ext_ref,
    )

    if ext_ref and not callback.provider_reference:
        callback.provider_reference = ext_ref
        callback.save(update_fields=["provider_reference", "updated_at"])

    if result == "SUCCESS":
        _confirm_payment(payment_intent, callback, ext_ref)
    elif result in ("FAILED", "TIMEOUT"):
        _fail_payment(payment_intent, callback)
        logger.warning("[PAY][failed] ref=%s reason=%s", payment_intent.reference, result)
    else:
        callback.processing_status = "pending"
        callback.save(update_fields=["processing_status", "updated_at"])
        logger.info("[PAY][pending] ref=%s awaiting next callback", payment_intent.reference)

    return callback


def _resolve_callback_result(provider: str, payload: dict) -> tuple[str, str, str]:
    simple_status = str(payload.get("status", "")).lower()
    if simple_status == "confirmed":
        return "SUCCESS", "Pagamento confirmado.", payload.get("provider_reference", "")
    if simple_status == "failed":
        return "FAILED", "Pagamento falhado.", ""

    status_code = int(_extract_value(payload, ("http_status", "status_code", "statusCode")) or "200")
    return _interpret_response(provider, status_code, payload)


def confirm_payment_immediately(payment_intent: PaymentIntent, provider_reference: str = ""):
    if payment_intent.status == PaymentIntent.Status.CONFIRMED:
        return

    callback = PaymentCallback.objects.create(
        payment_intent=payment_intent,
        provider_reference=provider_reference,
        raw_payload={"source": "immediate_confirm", "provider": payment_intent.provider},
        signature_valid=True,
        processing_status="received",
    )
    _confirm_payment(payment_intent, callback, provider_reference)


def _confirm_payment(payment_intent: PaymentIntent, callback: PaymentCallback, provider_ref: str = ""):
    with transaction.atomic():
        pi = PaymentIntent.objects.select_for_update().get(pk=payment_intent.pk)
        if pi.status == PaymentIntent.Status.CONFIRMED:
            callback.processing_status = "duplicate"
            callback.save(update_fields=["processing_status", "updated_at"])
            return

        pi.status = PaymentIntent.Status.CONFIRMED
        pi.confirmed_at = timezone.now()
        if provider_ref:
            pi.provider_reference = provider_ref
        pi.save(update_fields=["status", "confirmed_at", "provider_reference", "updated_at"])
        logger.info(
            "[PAY][confirmed] ref=%s amount=%s purpose=%s provider=%s provider_ref=%s",
            pi.reference, pi.amount, pi.purpose, pi.provider, provider_ref or "-",
        )

        if pi.wallet and pi.purpose in (
            PaymentIntent.Purpose.MOBILE_WALLET_TOPUP,
            PaymentIntent.Purpose.POS_CARD_TOPUP,
        ):
            credit_wallet(
                wallet=pi.wallet,
                amount=pi.amount,
                tx_type=WalletTransaction.Type.TOPUP,
                source=f"payment:{pi.reference}",
                reference=f"TOP-{pi.reference}",
                metadata={"payment_intent": str(pi.uuid)},
            )
            logger.info(
                "[PAY][wallet_credit] ref=%s wallet=%s amount=%s",
                pi.reference, pi.wallet_id, pi.amount,
            )

        # Hook: card recovery flow — block the passenger's old physical
        # cards and send the credentials SMS only AFTER payment confirms.
        if (pi.metadata or {}).get("kind") == "card_recovery":
            try:
                from apps.agent_api.recovery_views import finalize_card_recovery
                finalize_card_recovery(pi)
            except Exception:
                # Recovery finalisation must never fail the webhook — the
                # PaymentIntent is already CONFIRMED at this point.
                from apps.audit.services import audit as _a
                _a("CARD_RECOVERY_FINALISE_FAILED",
                   actor=pi.created_by,
                   entity_type="payment_intent", entity_id=str(pi.id))

        if pi.guest_checkout and pi.purpose == PaymentIntent.Purpose.GUEST_TRAVEL_PASS:
            from apps.guest_checkouts.services import issue_guest_pass
            from apps.audit.services import audit
            from apps.notifications.services import notify_by_phone
            passes = issue_guest_pass(pi.guest_checkout)
            for tp in passes:
                audit(
                    "TICKET_ISSUED",
                    actor=pi.created_by,
                    entity_type="travel_pass", entity_id=str(tp.id),
                    after={
                        "guest_checkout_reference": pi.guest_checkout.reference,
                        "payment_reference": pi.reference,
                    },
                )
            notify_by_phone(
                pi.payer_phone,
                "ticket_issued",
                f"{len(passes)} bilhete(s) emitido(s)",
                f"Pagamento {pi.reference} confirmado.",
                data={"payment_reference": pi.reference, "guest_checkout_reference": pi.guest_checkout.reference},
            )

        from apps.audit.services import audit as _audit
        _audit(
            "PAYMENT_CONFIRMED",
            actor=pi.created_by,
            entity_type="payment_intent", entity_id=str(pi.id),
            after={"amount": str(pi.amount), "provider": pi.provider, "reference": pi.reference},
        )

        from apps.audit.services import audit as _audit_dup
        _audit_dup(
            "WEBHOOK_RECEIVED",
            actor=pi.created_by,
            entity_type="payment_callback", entity_id=str(callback.id),
            after={"reference": pi.reference, "processing_status": "processed"},
        )
        callback.processing_status = "processed"
        callback.save(update_fields=["processing_status", "updated_at"])


def _fail_payment(payment_intent: PaymentIntent, callback: PaymentCallback):
    with transaction.atomic():
        pi = PaymentIntent.objects.select_for_update().get(pk=payment_intent.pk)
        if pi.status in (PaymentIntent.Status.CONFIRMED, PaymentIntent.Status.FAILED):
            callback.processing_status = "duplicate"
            callback.save(update_fields=["processing_status", "updated_at"])
            return

        pi.status = PaymentIntent.Status.FAILED
        pi.save(update_fields=["status", "updated_at"])

        if pi.guest_checkout:
            from apps.guest_checkouts.models import GuestCheckout
            gc = pi.guest_checkout
            if gc.status not in (GuestCheckout.Status.ISSUED, GuestCheckout.Status.CANCELLED):
                gc.status = GuestCheckout.Status.CANCELLED
                gc.save(update_fields=["status", "updated_at"])

        callback.processing_status = "processed"
        callback.save(update_fields=["processing_status", "updated_at"])
