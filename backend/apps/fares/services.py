from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.fares.models import FareProduct, FareRule
from apps.routes.models import Route, Stop
from apps.routes.services import RouteSegmentError, resolve_route_segment


class NoFareFoundError(Exception):
    pass


class FareConflictError(Exception):
    """Multiplas regras igualmente aplicaveis. Sistema nao desconta."""


@dataclass
class FareQuoteResult:
    amount: Decimal
    fare_rule: FareRule | None = None
    method: str = ""
    distance_km: Decimal | None = None


PRIORITY_TIERS = (
    "OD_SPECIFIC",
    "OD_GENERIC",
    "FIXED_SPECIFIC",
    "FIXED_GENERIC",
    "DISTANCE_SPECIFIC",
    "DISTANCE_GENERIC",
)


def quote_fare(
    route: Route,
    origin_stop: Stop | None = None,
    destination_stop: Stop | None = None,
    passenger_class: str = FareRule.PassengerClass.STANDARD,
) -> FareQuoteResult:
    """Resolve a tarifa correcta usando a ordem de prioridade. Falha de forma
    segura se houver ambiguidade ou se nao existirem regras."""

    _validate_route_stops(route, origin_stop, destination_stop)
    now = timezone.now()

    base_qs = _active_rules_qs(now, route)
    distance_km = _safe_distance_km(route, origin_stop, destination_stop)

    for tier in PRIORITY_TIERS:
        rules = _candidates_for_tier(base_qs, tier, route, origin_stop, destination_stop, passenger_class, distance_km)
        if len(rules) == 0:
            continue
        if len(rules) > 1:
            raise FareConflictError(
                f"Conflito de tarifas para a rota {route.code}: {len(rules)} regras igualmente aplicaveis "
                f"({tier}). Reveja a configuracao."
            )
        rule = rules[0]
        amount = _calculate_amount(rule, origin_stop, destination_stop, distance_km)
        return FareQuoteResult(
            amount=amount,
            fare_rule=rule,
            method=rule.calculation_method,
            distance_km=distance_km,
        )

    raise NoFareFoundError(
        f"Nenhuma tarifa configurada para a rota {route.code}"
        + (f" entre {origin_stop.code} e {destination_stop.code}" if origin_stop and destination_stop else "")
        + f" (categoria {passenger_class})."
    )


def _active_rules_qs(now, route: Route) -> QuerySet[FareRule]:
    return FareRule.objects.filter(
        route=route,
        fare_product__status=FareProduct.Status.ACTIVE,
        fare_product__product_type=FareProduct.ProductType.SINGLE_TRIP,
    ).filter(
        (Q(valid_from__isnull=True) | Q(valid_from__lte=now))
        & (Q(valid_until__isnull=True) | Q(valid_until__gte=now))
    )


def _candidates_for_tier(
    base_qs: QuerySet[FareRule],
    tier: str,
    route: Route,
    origin_stop: Stop | None,
    destination_stop: Stop | None,
    passenger_class: str,
    distance_km: Decimal | None,
) -> list[FareRule]:
    if tier == "OD_SPECIFIC":
        if not (origin_stop and destination_stop):
            return []
        return list(base_qs.filter(
            calculation_method=FareRule.CalculationMethod.ORIGIN_DESTINATION,
            origin_stop=origin_stop, destination_stop=destination_stop,
            passenger_class=passenger_class,
        ))
    if tier == "OD_GENERIC":
        if not (origin_stop and destination_stop) or passenger_class == FareRule.PassengerClass.STANDARD:
            return []
        return list(base_qs.filter(
            calculation_method=FareRule.CalculationMethod.ORIGIN_DESTINATION,
            origin_stop=origin_stop, destination_stop=destination_stop,
            passenger_class=FareRule.PassengerClass.STANDARD,
        ))
    if tier == "FIXED_SPECIFIC":
        return list(base_qs.filter(
            calculation_method=FareRule.CalculationMethod.FIXED,
            passenger_class=passenger_class,
        ))
    if tier == "FIXED_GENERIC":
        if passenger_class == FareRule.PassengerClass.STANDARD:
            return []
        return list(base_qs.filter(
            calculation_method=FareRule.CalculationMethod.FIXED,
            passenger_class=FareRule.PassengerClass.STANDARD,
        ))
    if tier == "DISTANCE_SPECIFIC":
        if distance_km is None:
            return []
        return _filter_distance(base_qs, passenger_class, distance_km)
    if tier == "DISTANCE_GENERIC":
        if distance_km is None or passenger_class == FareRule.PassengerClass.STANDARD:
            return []
        return _filter_distance(base_qs, FareRule.PassengerClass.STANDARD, distance_km)
    return []


def _filter_distance(base_qs: QuerySet[FareRule], passenger_class: str, distance_km: Decimal) -> list[FareRule]:
    qs = base_qs.filter(
        calculation_method=FareRule.CalculationMethod.DISTANCE,
        passenger_class=passenger_class,
    )
    return [
        r for r in qs
        if r.distance_min_km is None or r.distance_min_km <= distance_km
        if r.distance_max_km is None or r.distance_max_km >= distance_km
    ]


def _safe_distance_km(route: Route, origin_stop: Stop | None, destination_stop: Stop | None) -> Decimal | None:
    if not (origin_stop and destination_stop):
        return None
    try:
        segment = resolve_route_segment(route, origin_stop.pk, destination_stop.pk)
    except RouteSegmentError:
        return None
    return Decimal(segment.distance_km) if segment else None


def _calculate_amount(
    rule: FareRule, origin_stop: Stop | None, destination_stop: Stop | None, distance_km: Decimal | None
) -> Decimal:
    if rule.calculation_method == FareRule.CalculationMethod.DISTANCE and distance_km is not None:
        if rule.amount_per_km and rule.amount_per_km > 0:
            amount = distance_km * rule.amount_per_km
            if rule.min_amount and amount < rule.min_amount:
                amount = rule.min_amount
            if rule.max_amount and amount > rule.max_amount:
                amount = rule.max_amount
            return amount.quantize(Decimal("0.01"))
    return rule.fixed_amount.quantize(Decimal("0.01"))


def find_conflicts(rule: FareRule, exclude_pk: int | None = None) -> list[FareRule]:
    """Devolve regras activas que cobrem o mesmo cenario que a regra fornecida."""

    base = FareRule.objects.filter(
        route=rule.route,
        calculation_method=rule.calculation_method,
        passenger_class=rule.passenger_class,
        deleted_at__isnull=True,
    )
    if exclude_pk:
        base = base.exclude(pk=exclude_pk)

    now = timezone.now()
    base = base.filter(
        (Q(valid_from__isnull=True) | Q(valid_from__lte=(rule.valid_until or now)))
        & (Q(valid_until__isnull=True) | Q(valid_until__gte=(rule.valid_from or now)))
    )

    if rule.calculation_method == FareRule.CalculationMethod.ORIGIN_DESTINATION:
        base = base.filter(origin_stop=rule.origin_stop, destination_stop=rule.destination_stop)
        return list(base)
    if rule.calculation_method == FareRule.CalculationMethod.FIXED:
        return list(base)
    if rule.calculation_method == FareRule.CalculationMethod.DISTANCE:
        return [c for c in base if _distance_ranges_overlap(rule, c)]
    return list(base)


def _distance_ranges_overlap(a: FareRule, b: FareRule) -> bool:
    a_min = a.distance_min_km if a.distance_min_km is not None else Decimal("-Infinity")
    a_max = a.distance_max_km if a.distance_max_km is not None else Decimal("Infinity")
    b_min = b.distance_min_km if b.distance_min_km is not None else Decimal("-Infinity")
    b_max = b.distance_max_km if b.distance_max_km is not None else Decimal("Infinity")
    return a_min <= b_max and b_min <= a_max


def _validate_route_stops(route: Route, origin_stop: Stop | None, destination_stop: Stop | None) -> None:
    if not origin_stop and not destination_stop:
        return
    if not origin_stop or not destination_stop:
        raise NoFareFoundError("Origem e destino sao obrigatorios para esta rota.")
    if origin_stop.pk == destination_stop.pk:
        raise NoFareFoundError("Destino deve ser diferente da origem.")

    requested_ids = [origin_stop.pk, destination_stop.pk]
    linked_ids = set(route.route_stops.filter(stop_id__in=requested_ids).values_list("stop_id", flat=True))
    missing = [
        stop.code or stop.name
        for stop in (origin_stop, destination_stop)
        if stop.pk not in linked_ids
    ]
    if missing:
        raise NoFareFoundError(f"Paragem fora da rota {route.code}: {', '.join(missing)}.")

    try:
        resolve_route_segment(route, origin_stop.pk, destination_stop.pk)
    except RouteSegmentError as e:
        raise NoFareFoundError(str(e)) from e
