from __future__ import annotations

from dataclasses import dataclass

from apps.routes.models import Route, RouteStop


class RouteSegmentError(ValueError):
    pass


@dataclass(frozen=True)
class RouteSegment:
    route_id: int
    direction: str
    origin_sequence: int
    destination_sequence: int
    distance_km: str


def resolve_route_segment(route: Route, origin_stop_id: int | str | None, destination_stop_id: int | str | None) -> RouteSegment | None:
    if not origin_stop_id and not destination_stop_id:
        return None
    if not origin_stop_id or not destination_stop_id:
        raise RouteSegmentError("Origem e destino sao obrigatorios.")

    origin_id = int(origin_stop_id)
    destination_id = int(destination_stop_id)
    if origin_id == destination_id:
        raise RouteSegmentError("Destino deve ser diferente da origem.")

    origins = list(
        RouteStop.objects.filter(route=route, stop_id=origin_id)
        .order_by("direction", "sequence")
    )
    destinations = list(
        RouteStop.objects.filter(route=route, stop_id=destination_id)
        .order_by("direction", "sequence")
    )
    if not origins or not destinations:
        raise RouteSegmentError("Origem ou destino nao pertence a rota seleccionada.")

    for origin_link in origins:
        for destination_link in destinations:
            if destination_link.direction != origin_link.direction:
                continue
            if destination_link.sequence <= origin_link.sequence:
                continue
            distance = destination_link.distance_from_start_km - origin_link.distance_from_start_km
            return RouteSegment(
                route_id=route.id,
                direction=origin_link.direction,
                origin_sequence=origin_link.sequence,
                destination_sequence=destination_link.sequence,
                distance_km=str(distance),
            )

    raise RouteSegmentError("Destino deve estar depois da origem na mesma direccao da rota.")


def route_segments_for_stop_pair(
    origin_stop_id: int | str,
    destination_stop_id: int | str,
    route_id: int | str | None = None,
) -> dict[int, RouteSegment]:
    if int(origin_stop_id) == int(destination_stop_id):
        raise RouteSegmentError("Destino deve ser diferente da origem.")

    routes = Route.objects.filter(status=Route.Status.ACTIVE)
    if route_id:
        routes = routes.filter(pk=route_id)

    routes = routes.filter(
        route_stops__stop_id=origin_stop_id,
    ).filter(
        route_stops__stop_id=destination_stop_id,
    ).distinct()

    result: dict[int, RouteSegment] = {}
    for route in routes:
        try:
            segment = resolve_route_segment(route, origin_stop_id, destination_stop_id)
        except RouteSegmentError:
            continue
        if segment:
            result[route.id] = segment
    return result
