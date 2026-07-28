"""Mapa de lugares por partida.

O passageiro escolhe o lugar como escolheria num autocarro real: ve a planta,
os lugares ocupados e os livres. A planta e derivada da capacidade da viatura
(2+2 com corredor, ultima fila corrida), pelo que nao exige configuracao por
viatura — quando for preciso um layout especifico, basta guardar o desenho na
viatura e substituir `seat_labels`.
"""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout

COLUMNS = ("A", "B", "C", "D")  # A|B [corredor] C|D


def seat_labels(capacity: int) -> list[str]:
    """Etiquetas de lugar: 1A,1B,1C,1D,2A... ate a capacidade."""
    labels = []
    row = 1
    while len(labels) < capacity:
        for col in COLUMNS:
            if len(labels) >= capacity:
                break
            labels.append(f"{row}{col}")
        row += 1
    return labels


def occupied_seats(trip) -> set[str]:
    """Lugares ja vendidos ou reservados (pagamento em curso, nao expirado)."""
    taken: set[str] = set()

    passes = DigitalTravelPass.objects.filter(trip=trip).exclude(
        status__in=[DigitalTravelPass.Status.CANCELLED, DigitalTravelPass.Status.REFUNDED],
    ).values_list("seat_number", flat=True)
    taken.update(s for s in passes if s)

    holds = GuestCheckout.objects.filter(
        trip=trip,
        status__in=[GuestCheckout.Status.PAYMENT_PENDING, GuestCheckout.Status.PAID],
    ).exclude(
        Q(status=GuestCheckout.Status.PAYMENT_PENDING) & Q(expires_at__lt=timezone.now()),
    ).values_list("passengers", flat=True)
    for people in holds:
        for person in people or []:
            seat = (person or {}).get("seat")
            if seat:
                taken.add(seat)

    return taken


def seat_map(trip) -> dict:
    """Planta pronta a desenhar no site."""
    vehicle = getattr(trip, "vehicle", None)
    capacity = (getattr(vehicle, "seated_capacity", 0) or 0) if vehicle else 0
    if not capacity:
        return {"has_seat_map": False, "columns": list(COLUMNS), "rows": [], "occupied": [], "available": None}

    labels = seat_labels(capacity)
    taken = occupied_seats(trip)
    rows: list[dict] = []
    for i in range(0, len(labels), len(COLUMNS)):
        chunk = labels[i:i + len(COLUMNS)]
        rows.append({
            "row": i // len(COLUMNS) + 1,
            "seats": [{"label": s, "occupied": s in taken} for s in chunk],
        })
    return {
        "has_seat_map": True,
        "columns": list(COLUMNS),
        "capacity": capacity,
        "rows": rows,
        "occupied": sorted(taken),
        "available": max(capacity - len(taken), 0),
    }
