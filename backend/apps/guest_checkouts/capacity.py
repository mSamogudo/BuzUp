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


def seats_taken_bulk(trips) -> dict[int, int]:
    """Lugares ocupados de VARIAS partidas num unico agregado.

    A pesquisa publica listava 40 partidas e chamava `seats_taken` por cada
    uma — e `sale_state` chamava-o outra vez, dando 80 queries so para contar
    lugares. Aqui e um `GROUP BY`.
    """
    trip_ids = [t.pk for t in trips]
    if not trip_ids:
        return {}
    rows = (
        GuestCheckout.objects
        .filter(trip_id__in=trip_ids, status__in=BLOCKING_STATUSES)
        .exclude(Q(status=GuestCheckout.Status.PAYMENT_PENDING) & Q(expires_at__lt=timezone.now()))
        .values("trip_id")
        .annotate(n=Sum("quantity"))
    )
    return {row["trip_id"]: row["n"] or 0 for row in rows}


def seats_available(trip, taken: int | None = None) -> int | None:
    """None = sem limite conhecido (viagem sem viatura alocada).

    `taken` permite reaproveitar uma contagem feita em bloco por
    `seats_taken_bulk`, evitando um agregado por partida.
    """
    capacity = trip_capacity(trip)
    if capacity is None:
        return None
    used = seats_taken(trip) if taken is None else taken
    return max(capacity - used, 0)


# A venda fecha pouco antes da partida (derivado, nunca configurado por
# partida — com centenas de partidas seria insustentavel).
SALE_CLOSES_MINUTES_BEFORE = 15

# Estados de viagem em que ainda se pode comprar: agendada (venda antecipada)
# ou ja em embarque/em curso (compra a bordo, caso urbano).
SELLABLE_TRIP_STATUSES = ("scheduled", "boarding", "departed")


def sale_state(trip, taken: int | None = None) -> tuple[bool, str]:
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

    available = seats_available(trip, taken=taken)
    if available is not None and available <= 0:
        return False, "Partida esgotada."

    return True, ""


class SeatsUnavailable(Exception):
    """Lotacao esgotada ou venda encerrada, com motivo legivel."""


def lock_trip_for_sale(trip, quantity: int = 1):
    """Bloqueia a partida e confirma que ha lugar — devolve a Trip bloqueada.

    Tem de ser chamado DENTRO de um `transaction.atomic()`: o lock so vale ate
    ao fim da transacao. Contar lugares sem bloquear a linha da viagem nao
    impede sobrevenda — dois vendedores contam 49 de 50 ao mesmo tempo e ambos
    aceitam. `of=("self",)` porque a viatura e nullable (LEFT JOIN) e o
    Postgres recusa FOR UPDATE sobre o lado nullable de um outer join.
    """
    from apps.trips.models import Trip

    locked = (Trip.objects.select_related("route", "vehicle")
              .select_for_update(of=("self",))
              .filter(pk=getattr(trip, "pk", trip))
              .first())
    if locked is None:
        raise SeatsUnavailable("Partida nao encontrada.")

    can_sell, reason = sale_state(locked)
    if not can_sell:
        raise SeatsUnavailable(reason)

    available = seats_available(locked)
    if available is not None and quantity > available:
        raise SeatsUnavailable(
            f"Restam apenas {available} lugares nesta partida."
            if available else "Partida esgotada."
        )
    return locked
