"""Lotacao por partida.

O lugar e reservado no momento do checkout (nao na emissao do passe): entre
iniciar o pagamento e o gateway confirmar podem passar minutos, e nesse
intervalo o lugar nao pode ser vendido a outra pessoa. Checkouts pendentes que
expiram libertam o lugar automaticamente.
"""

from __future__ import annotations

from django.db.models import Q, Sum
from django.utils import timezone

from apps.guest_checkouts.models import GuestCheckout

# Estados que ocupam lugar na viagem.
BLOCKING_STATUSES = (
    GuestCheckout.Status.PAYMENT_PENDING,
    GuestCheckout.Status.PAID,
    GuestCheckout.Status.ISSUED,
)


def trip_capacity(trip) -> int | None:
    """Lugares vendaveis da viagem, ou None quando nao ha viatura alocada."""
    vehicle = getattr(trip, "vehicle", None)
    if vehicle is None:
        return None
    return (vehicle.seated_capacity or 0) or None


def seats_taken(trip) -> int:
    qs = GuestCheckout.objects.filter(trip=trip, status__in=BLOCKING_STATUSES).exclude(
        Q(status=GuestCheckout.Status.PAYMENT_PENDING) & Q(expires_at__lt=timezone.now()),
    )
    return qs.aggregate(n=Sum("quantity"))["n"] or 0


def seats_available(trip) -> int | None:
    """None = sem limite conhecido (viagem sem viatura alocada)."""
    capacity = trip_capacity(trip)
    if capacity is None:
        return None
    return max(capacity - seats_taken(trip), 0)


# A venda fecha pouco antes da partida (derivado, nunca configurado por
# partida — com centenas de partidas seria insustentavel).
SALE_CLOSES_MINUTES_BEFORE = 15

# Estados de viagem em que ainda se pode comprar: agendada (venda antecipada)
# ou ja em embarque/em curso (compra a bordo, caso urbano).
SELLABLE_TRIP_STATUSES = ("scheduled", "boarding", "departed")


def sale_state(trip) -> tuple[bool, str]:
    """(pode_vender, motivo_legivel_quando_nao).

    Devolver o motivo em texto — e nao um booleano — permite ao site dizer
    "Venda encerrada 15 min antes da partida" em vez de mostrar um botao morto.
    """
    from django.utils import timezone as tz

    if trip.status not in SELLABLE_TRIP_STATUSES:
        return False, "Esta partida ja nao esta disponivel."

    departure = trip.planned_departure_at
    if trip.status == "scheduled" and departure:
        from datetime import timedelta

        if tz.now() > departure - timedelta(minutes=SALE_CLOSES_MINUTES_BEFORE):
            return False, (
                f"A venda encerra {SALE_CLOSES_MINUTES_BEFORE} minutos antes da partida."
            )

    available = seats_available(trip)
    if available is not None and available <= 0:
        return False, "Partida esgotada."

    return True, ""
