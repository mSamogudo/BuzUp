"""A tentativa anterior do MESMO comprador nao lhe pode tapar o lugar.

O caso: o passageiro escolhe o lugar 2C, o M-Pesa manda o pedido de PIN, ele
engana-se no PIN (ou nem chega a introduzi-lo). Tenta outra vez — e o sistema
diz-lhe que o lugar 2C esta ocupado. Esta: por ele proprio.

Um lugar fica reservado enquanto a compra espera pagamento, o que e certo — sem
isso dois compradores levavam o mesmo lugar. So que a reserva vale contra
TERCEIROS, nao contra quem a fez.

Duas situacoes, e so uma delas se resolve sozinha:

**Tentativa morta** (o pagamento falhou, expirou ou foi revertido): nao ha nada
a espera de dinheiro, e a reserva pode cair. Cai aqui, e a compra nova segue.

**Tentativa viva** (o pedido de PIN ainda esta de pe): pode ainda ser paga. Nao
se liberta — libertar seria deixar entrar uma segunda cobranca pelo mesmo
lugar, e o passageiro arriscava pagar duas vezes. O que muda e a MENSAGEM: em
vez de "lugar ocupado", diz-se-lhe que ja tem um pagamento a decorrer e que
basta confirmar o PIN.
"""

from __future__ import annotations

from django.utils import timezone

from apps.guest_checkouts.models import GuestCheckout
from apps.payments.models import PaymentIntent

#: Estados de pagamento sem nada a espera: a reserva que os acompanha e lixo.
PAGAMENTOS_MORTOS = (
    PaymentIntent.Status.FAILED,
    PaymentIntent.Status.EXPIRED,
    PaymentIntent.Status.REVERSED,
)


def _reservas_do_comprador(trip, payer_phone: str):
    telefone = "".join(c for c in str(payer_phone or "") if c.isdigit())
    if not trip or not telefone:
        return GuestCheckout.objects.none()
    # Compara so os digitos: o mesmo numero chega ora com 258 a frente ora sem.
    return GuestCheckout.objects.filter(
        trip=trip, status=GuestCheckout.Status.PAYMENT_PENDING,
    ).filter(payer_phone__endswith=telefone[-9:])


def libertar_tentativas_mortas(trip, payer_phone: str) -> int:
    """Cancela as reservas do comprador cujo pagamento ja morreu."""
    libertadas = 0
    for gc in _reservas_do_comprador(trip, payer_phone):
        intents = list(PaymentIntent.objects.filter(guest_checkout=gc))
        # Sem pagamento nenhum, ou todos mortos: nao ha nada a espera.
        if intents and not all(pi.status in PAGAMENTOS_MORTOS for pi in intents):
            continue
        gc.status = GuestCheckout.Status.CANCELLED
        gc.save(update_fields=["status", "updated_at"])
        libertadas += 1
    return libertadas


def pagamento_a_decorrer(trip, payer_phone: str, lugares: list) -> GuestCheckout | None:
    """A compra viva do proprio comprador que ocupa um destes lugares."""
    pedidos = {str(s).strip().upper() for s in lugares if s}
    agora = timezone.now()
    for gc in _reservas_do_comprador(trip, payer_phone):
        if gc.expires_at and gc.expires_at < agora:
            continue  # ja nao segura nada
        ocupados = {
            str((p or {}).get("seat") or "").strip().upper()
            for p in (gc.passengers or [])
        }
        if not pedidos or (ocupados & pedidos):
            return gc
    return None
