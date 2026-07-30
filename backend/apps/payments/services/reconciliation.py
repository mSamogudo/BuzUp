"""Reconciliação de pagamentos pendentes com o gateway.

O problema que isto resolve: a confirmação de um pagamento chega por webhook.
Com a rede móvel a oscilar — e é a norma no terreno — uma parte dos webhooks
nunca chega. O passageiro pagou no M-Pesa, o dinheiro saiu da conta dele, e o
`PaymentIntent` fica `PENDING` para sempre: nunca recebe bilhete, e nada no
sistema deteta que isso aconteceu. A reclamação chega ao balcão dias depois,
sem forma de provar o que se passou.

`query_payment` já existia no gateway e nunca era chamado por ninguém. Este
módulo é o chamador que faltava: pergunta ao gateway o que aconteceu de facto a
cada pagamento pendente e alinha o nosso estado com a resposta.

Uma decisão importante está aqui: quando o gateway confirma um pagamento cujo
checkout **já expirou**, NÃO emitimos o bilhete automaticamente. O lugar pode
ter sido libertado e revendido a outra pessoa, e emitir criaria dois
passageiros com o mesmo lugar — um problema pior do que o original. Esses casos
são marcados para revisão humana (com o dinheiro reconhecido como recebido),
porque a decisão entre reemitir e reembolsar depende de haver ou não lugar.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from django.utils import timezone

from apps.audit.services import audit
from apps.payments.models import PaymentCallback, PaymentIntent
from apps.payments.services.gateway import get_payment_gateway
from apps.payments.services.processing import _confirm_payment, _fail_payment

logger = logging.getLogger(__name__)

# Margem antes de perguntar ao gateway: um pagamento acabado de iniciar está
# legitimamente pendente enquanto o passageiro digita o PIN.
DEFAULT_MIN_AGE_MINUTES = 5


@dataclass
class ReconcileReport:
    checked: int = 0
    confirmed: int = 0
    failed: int = 0
    still_pending: int = 0
    needs_review: int = 0
    unsupported: int = 0
    errors: list[str] = field(default_factory=list)

    def as_line(self) -> str:
        return (
            f"verificados={self.checked} confirmados={self.confirmed} "
            f"falhados={self.failed} pendentes={self.still_pending} "
            f"revisao_manual={self.needs_review} sem_consulta={self.unsupported} "
            f"erros={len(self.errors)}"
        )


def _checkout_still_usable(payment_intent: PaymentIntent) -> bool:
    """O bilhete deste pagamento ainda pode ser emitido em segurança?

    Se o checkout expirou, o lugar já foi devolvido à lotação (ver
    `guest_checkouts/capacity.py`) e pode estar vendido a outra pessoa.
    """
    from apps.guest_checkouts.models import GuestCheckout

    gc = payment_intent.guest_checkout
    if gc is None:
        # Recargas de carteira não têm lugar associado: creditar é sempre seguro.
        return True
    if gc.status in (GuestCheckout.Status.EXPIRED, GuestCheckout.Status.CANCELLED):
        return False
    if gc.expires_at and gc.expires_at < timezone.now():
        return False
    return True


def _mark_for_review(payment_intent: PaymentIntent, provider_reference: str, detail: str) -> None:
    """Dinheiro recebido que não pode ser transformado em bilhete sozinho."""
    metadata = dict(payment_intent.metadata or {})
    metadata["reconciliation"] = {
        "needs_manual_review": True,
        "reason": detail,
        "provider_reference": provider_reference,
        "detected_at": timezone.now().isoformat(),
    }
    payment_intent.metadata = metadata
    payment_intent.save(update_fields=["metadata", "updated_at"])
    audit(
        "PAYMENT_NEEDS_REVIEW",
        entity_type="payment_intent",
        entity_id=str(payment_intent.id),
        after={
            "reference": payment_intent.reference,
            "amount": str(payment_intent.amount),
            "payer_phone": payment_intent.payer_phone,
            "reason": detail,
        },
    )
    logger.warning(
        "reconciliacao: pagamento %s confirmado pelo gateway mas o checkout ja expirou (%s)",
        payment_intent.reference, detail,
    )


def reconcile_payment(payment_intent: PaymentIntent, report: ReconcileReport) -> None:
    """Alinha um pagamento com o que o gateway diz ter acontecido."""
    report.checked += 1
    gateway = get_payment_gateway(
        provider=payment_intent.provider or None,
        payer_phone=payment_intent.payer_phone,
    )

    # Sem referência do provedor não há nada para consultar: o pedido pode nem
    # ter chegado ao gateway. Fica para o `expire_stale` fechar pela validade.
    lookup_ref = payment_intent.provider_reference or payment_intent.reference
    if not lookup_ref:
        report.unsupported += 1
        return

    try:
        result = gateway.query_payment(lookup_ref)
    except Exception as exc:  # rede, timeout, resposta ilegível
        report.errors.append(f"{payment_intent.reference}: {exc}")
        logger.warning("reconciliacao: consulta falhou para %s: %s", payment_intent.reference, exc)
        return

    if not result.success and not result.pending and result.error and "not supported" in result.error.lower():
        report.unsupported += 1
        return

    if result.pending:
        report.still_pending += 1
        return

    if result.success:
        if not _checkout_still_usable(payment_intent):
            report.needs_review += 1
            _mark_for_review(
                payment_intent,
                result.provider_reference or lookup_ref,
                "pagamento confirmado apos a expiracao do checkout — o lugar pode ter sido revendido",
            )
            return

        callback = PaymentCallback.objects.create(
            payment_intent=payment_intent,
            provider_reference=result.provider_reference or lookup_ref,
            raw_payload={
                "source": "reconciliation",
                "provider": payment_intent.provider,
                "gateway_response": result.response_payload or {},
            },
            signature_valid=True,
            processing_status="received",
        )
        _confirm_payment(payment_intent, callback, result.provider_reference or lookup_ref)
        report.confirmed += 1
        logger.info(
            "reconciliacao: pagamento %s confirmado a partir do gateway (webhook perdido)",
            payment_intent.reference,
        )
        return

    # O gateway diz que falhou: fechar o pagamento e libertar o lugar.
    callback = PaymentCallback.objects.create(
        payment_intent=payment_intent,
        provider_reference=result.provider_reference or lookup_ref,
        raw_payload={
            "source": "reconciliation",
            "provider": payment_intent.provider,
            "gateway_response": result.response_payload or {},
        },
        signature_valid=True,
        processing_status="received",
    )
    _fail_payment(payment_intent, callback)
    report.failed += 1


def reconcile_pending_payments(
    *,
    min_age_minutes: int = DEFAULT_MIN_AGE_MINUTES,
    limit: int = 200,
) -> ReconcileReport:
    """Consulta o gateway sobre os pagamentos pendentes e alinha o estado.

    `limit` existe para uma execução não crescer sem controlo: cada consulta é
    uma chamada HTTP a terceiros, e é preferível processar 200 por passagem de
    cinco em cinco minutos do que prender um worker durante muito tempo.
    """
    report = ReconcileReport()
    cutoff = timezone.now() - timedelta(minutes=min_age_minutes)

    pending = (
        PaymentIntent.objects
        .select_related("guest_checkout", "wallet")
        .filter(status=PaymentIntent.Status.PENDING, created_at__lt=cutoff)
        .order_by("created_at")[:limit]
    )

    for payment_intent in pending:
        try:
            reconcile_payment(payment_intent, report)
        except Exception as exc:
            # Um pagamento problemático não pode parar a reconciliação dos
            # outros — é exactamente o caso em que mais precisamos dela.
            report.errors.append(f"{payment_intent.reference}: {exc}")
            logger.exception("reconciliacao: erro inesperado em %s", payment_intent.reference)

    return report
