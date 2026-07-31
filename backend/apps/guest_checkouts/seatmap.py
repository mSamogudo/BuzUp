"""Mapa de lugares por partida.

Duas decisões vivem aqui:

**Se há planta.** Numa carreira urbana ninguém escolhe assento — entra, valida
e senta-se onde houver. Obrigar a escolher seria um passo inútil numa compra
que tem de ser rápida. Numa viagem interprovincial ou internacional, de várias
horas, o lugar é do passageiro e tem de ser escolhido. Quem decide é o tipo de
serviço da rota (`Route.service_type`), não uma pergunta ao passageiro: ele diz
apenas de onde para onde quer ir, e o resto é o sistema que sabe.

**Que planta.** A disposição dos bancos varia com o autocarro: 2+2 clássico,
1+2 nos interprovinciais com bancos individuais de um lado, 3+2 nos de maior
lotação. Uma planta 2+2 aplicada a um autocarro 1+2 mostraria lugares que não
existem — e o passageiro escolheria um assento que não vai encontrar a bordo.
"""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout

DEFAULT_LAYOUT = "2+2"
# Letras por posição, da janela esquerda à janela direita. Um 3+2 usa A..E.
_LETTERS = "ABCDEFGH"


def parse_layout(layout: str) -> tuple[int, int]:
    """"2+2" -> (2, 2). Aceita lixo e cai no layout por omissão."""
    try:
        left, right = str(layout or DEFAULT_LAYOUT).split("+")
        left_n, right_n = int(left), int(right)
        if left_n < 1 or right_n < 1 or left_n + right_n > len(_LETTERS):
            raise ValueError
        return left_n, right_n
    except (ValueError, AttributeError):
        return 2, 2


def seat_rows(capacity: int, layout: str = DEFAULT_LAYOUT, last_row_seats: int = 0) -> list[dict]:
    """Filas prontas a desenhar, com o corredor no sítio certo.

    Cada fila traz `left` e `right`; quem desenha põe o corredor entre os dois
    sem ter de saber o layout. A última fila pode ser corrida (sem corredor),
    como é comum no fundo do autocarro.
    """
    left_n, right_n = parse_layout(layout)
    per_row = left_n + right_n
    if capacity <= 0 or per_row <= 0:
        return []

    body_capacity = max(capacity - last_row_seats, 0) if last_row_seats else capacity
    rows: list[dict] = []
    placed = 0
    row_number = 0

    while placed < body_capacity:
        row_number += 1
        remaining = body_capacity - placed
        take = min(per_row, remaining)
        letters = _LETTERS[:per_row]
        seats = [f"{row_number}{letters[i]}" for i in range(take)]
        rows.append({
            "row": row_number,
            "left": seats[:left_n],
            "right": seats[left_n:],
            "full_width": False,
        })
        placed += take

    if last_row_seats:
        row_number += 1
        letters = _LETTERS[:last_row_seats]
        rows.append({
            "row": row_number,
            "left": [f"{row_number}{letters[i]}" for i in range(last_row_seats)],
            "right": [],
            # Fila corrida: sem corredor a meio.
            "full_width": True,
        })
    return rows


def seat_labels(capacity: int, layout: str = DEFAULT_LAYOUT, last_row_seats: int = 0) -> list[str]:
    """Todas as etiquetas de lugar, por ordem."""
    labels: list[str] = []
    for row in seat_rows(capacity, layout, last_row_seats):
        labels.extend(row["left"])
        labels.extend(row["right"])
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


def trip_requires_seat_selection(trip) -> bool:
    """A rota desta partida marca lugar?"""
    route = getattr(trip, "route", None)
    if route is None:
        return False
    return bool(getattr(route, "requires_seat_selection", False))


def seat_map(trip) -> dict:
    """Planta pronta a desenhar. `has_seat_map=False` quando não se escolhe."""
    route = getattr(trip, "route", None)
    empty = {
        "has_seat_map": False,
        "seat_selection": False,
        "layout": DEFAULT_LAYOUT,
        "rows": [],
        "occupied": [],
        "available": None,
        "service_type": getattr(route, "service_type", ""),
    }

    if not trip_requires_seat_selection(trip):
        # Urbano: sem escolha de lugar. O site e as apps saltam a etapa.
        return {**empty, "reason": "Nesta carreira o lugar nao e marcado."}

    vehicle = getattr(trip, "vehicle", None)
    capacity = (getattr(vehicle, "seated_capacity", 0) or 0) if vehicle else 0
    layout = (getattr(vehicle, "seat_layout", "") or DEFAULT_LAYOUT) if vehicle else DEFAULT_LAYOUT
    last_row = (getattr(vehicle, "last_row_seats", 0) or 0) if vehicle else 0
    if not capacity:
        # Rota com lugar marcado mas viatura sem lotação registada: melhor
        # vender sem planta do que bloquear a venda.
        return {
            **empty,
            "seat_selection": True,
            "reason": "Viatura sem lotacao registada.",
        }

    taken = occupied_seats(trip)
    rows = []
    for row in seat_rows(capacity, layout, last_row):
        rows.append({
            "row": row["row"],
            "full_width": row["full_width"],
            "left": [{"label": s, "occupied": s in taken} for s in row["left"]],
            "right": [{"label": s, "occupied": s in taken} for s in row["right"]],
            # Compatibilidade com quem lia `seats` numa lista única.
            "seats": [
                {"label": s, "occupied": s in taken}
                for s in row["left"] + row["right"]
            ],
        })

    return {
        "has_seat_map": True,
        "seat_selection": True,
        "service_type": getattr(route, "service_type", ""),
        "layout": layout,
        "capacity": capacity,
        "rows": rows,
        "occupied": sorted(taken),
        "available": max(capacity - len(taken), 0),
    }
