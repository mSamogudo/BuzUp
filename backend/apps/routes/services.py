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


# Segmentos sao praticamente estaticos: as paragens de uma rota mudam quando um
# administrador as edita, o que e raro. Sem cache, esta funcao corria TRES vezes
# por validacao (uma directa, uma dentro de `quote_fare` e outra em
# `_safe_distance_km`), a 2 queries cada — 6 queries desperdicadas no caminho
# mais quente do sistema, o do embarque. O TTL e curto e ha invalidacao
# explicita quando as paragens sao alteradas (ver `invalidate_route_segments`).
_SEGMENT_CACHE_TTL = 300


def _segment_cache_key(route_id: int, origin_id: int, destination_id: int) -> str:
    return f"routeseg:{route_id}:{origin_id}:{destination_id}"


def invalidate_route_segments(route_id: int) -> None:
    """Esquece os segmentos em cache de uma rota.

    Chamar sempre que as paragens da rota mudam, senao as tarifas por distancia
    podem usar sequencias antigas durante o TTL.
    """
    from django.core.cache import cache

    # Sem enumerar pares: uma marca de versao por rota invalida tudo de uma vez.
    try:
        cache.incr(f"routeseg:ver:{route_id}")
    except ValueError:
        cache.set(f"routeseg:ver:{route_id}", 1, None)


def _route_version(route_id: int) -> int:
    from django.core.cache import cache

    return cache.get(f"routeseg:ver:{route_id}") or 0


def resolve_route_segment(route: Route, origin_stop_id: int | str | None, destination_stop_id: int | str | None) -> RouteSegment | None:
    """Wrapper com cache. A resolucao propria esta em `_resolve_route_segment`."""
    from django.core.cache import cache

    if not origin_stop_id or not destination_stop_id:
        return _resolve_route_segment(route, origin_stop_id, destination_stop_id)

    try:
        key = (
            f"{_segment_cache_key(route.id, int(origin_stop_id), int(destination_stop_id))}"
            f":v{_route_version(route.id)}"
        )
    except (TypeError, ValueError):
        # Input invalido: deixa a validacao normal levantar o erro legivel.
        return _resolve_route_segment(route, origin_stop_id, destination_stop_id)

    cached = cache.get(key)
    if cached is not None:
        # `False` guarda o facto de "este par nao forma segmento nesta rota",
        # que tambem custa 2 queries a descobrir.
        if cached is False:
            raise RouteSegmentError("Origem ou destino nao pertence a rota seleccionada.")
        return cached or None

    try:
        segment = _resolve_route_segment(route, origin_stop_id, destination_stop_id)
    except RouteSegmentError:
        cache.set(key, False, _SEGMENT_CACHE_TTL)
        raise
    cache.set(key, segment or "", _SEGMENT_CACHE_TTL)
    return segment


def _resolve_route_segment(route: Route, origin_stop_id: int | str | None, destination_stop_id: int | str | None) -> RouteSegment | None:
    if not origin_stop_id and not destination_stop_id:
        return None
    if not origin_stop_id or not destination_stop_id:
        raise RouteSegmentError("Origem e destino sao obrigatorios.")

    # Vinha `int()` cru sobre query-params do site publico: `?origin=abc`
    # levantava ValueError e devolvia 500 em vez de um pedido invalido.
    try:
        origin_id = int(origin_stop_id)
        destination_id = int(destination_stop_id)
    except (TypeError, ValueError):
        raise RouteSegmentError("Origem e destino invalidos.") from None
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
    # Os ids chegam de query-params do site publico (`?origin=abc`): `int()` cru
    # levantava ValueError e devolvia 500 em vez de "pedido invalido".
    try:
        origin_id = int(origin_stop_id)
        destination_id = int(destination_stop_id)
    except (TypeError, ValueError):
        raise RouteSegmentError("Origem e destino invalidos.") from None
    if origin_id == destination_id:
        raise RouteSegmentError("Destino deve ser diferente da origem.")

    routes = Route.objects.filter(status=Route.Status.ACTIVE)
    if route_id:
        routes = routes.filter(pk=route_id)

    routes = routes.filter(
        route_stops__stop_id=origin_id,
    ).filter(
        route_stops__stop_id=destination_id,
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


def paragens_no_sentido(route, direction: str = "") -> list:
    """As paragens da rota pela ordem em que o autocarro as vai encontrar.

    Uma rota tem duas listas — `outbound` e `inbound` — e sao a mesma estrada ao
    contrario. Quem listava paragens ordenava por `("direction", "sequence")` e
    ficava-se pela primeira ocorrencia de cada paragem: como "inbound" vem antes
    de "outbound" por ordem alfabetica, o percurso saia SEMPRE na ordem da
    volta. Na ida, o passageiro via o destino em primeiro lugar e a origem no
    fim — exactamente o percurso contrario ao que ia fazer.

    Com o sentido conhecido, mostra-se o dele. Sem sentido declarado (partidas
    anteriores ao campo existir), fica a ida — que e a leitura natural da rota,
    e a mesma que o portal ja usa para o nome dela.
    """
    from apps.routes.models import RouteStop

    escolhido = direction or RouteStop.Direction.OUTBOUND
    paragens = list(
        RouteStop.objects.select_related("stop")
        .filter(route=route, direction=escolhido, stop__status="active")
        .order_by("sequence")
    )
    if not paragens:
        # Rota so definida no outro sentido: mais vale mostrar o que existe do
        # que devolver um percurso vazio.
        paragens = list(
            RouteStop.objects.select_related("stop")
            .filter(route=route, stop__status="active")
            .order_by("direction", "sequence")
        )
    vistas: dict = {}
    for rs in paragens:
        vistas.setdefault(rs.stop_id, {"id": rs.stop_id, "code": rs.stop.code, "name": rs.stop.name})
    return list(vistas.values())
