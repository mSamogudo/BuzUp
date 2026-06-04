from django.db import transaction
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.viewsets import BaseModelViewSet
from apps.routes.api.serializers import (
    RouteDetailSerializer,
    RouteSerializer,
    RouteStopWriteSerializer,
    StopDetailSerializer,
    StopSerializer,
)
from apps.routes.models import Route, RouteStop, Stop


class RouteViewSet(BaseModelViewSet):
    queryset = Route.all_objects.all()
    serializer_class = RouteSerializer
    required_capabilities_by_action = {
        "list": ("routes.read",),
        "retrieve": ("routes.read",),
        "create": ("routes.manage",),
        "update": ("routes.manage",),
        "partial_update": ("routes.manage",),
        "destroy": ("routes.manage",),
        "stops": ("routes.read",),
        "set_stops": ("routes.manage",),
    }

    def get_serializer_class(self):
        if self.action == "retrieve":
            return RouteDetailSerializer
        return RouteSerializer

    @action(detail=True, methods=["get"], url_path="stops")
    def stops(self, request, *args, **kwargs):
        route = self.get_object()
        qs = route.route_stops.select_related("stop").order_by("direction", "sequence")
        from apps.routes.api.serializers import RouteStopSerializer
        return Response(RouteStopSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="set-stops")
    def set_stops(self, request, *args, **kwargs):
        route = self.get_object()
        serializer = RouteStopWriteSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data

        stop_ids = {item["stop_id"] for item in items}
        existing_stop_ids = set(Stop.objects.filter(id__in=stop_ids).values_list("id", flat=True))
        missing_stop_ids = sorted(stop_ids - existing_stop_ids)
        if missing_stop_ids:
            raise ValidationError({"detail": f"Paragem inexistente: {', '.join(map(str, missing_stop_ids))}."})

        seen_sequences = set()
        seen_stops = set()
        for item in items:
            direction = item.get("direction", RouteStop.Direction.OUTBOUND)
            sequence_key = (direction, item["sequence"])
            stop_key = (direction, item["stop_id"])
            if sequence_key in seen_sequences:
                raise ValidationError({"detail": "Sequencia duplicada na mesma direccao."})
            if stop_key in seen_stops:
                raise ValidationError({"detail": "A mesma paragem nao pode repetir na mesma direccao."})
            seen_sequences.add(sequence_key)
            seen_stops.add(stop_key)

        with transaction.atomic():
            route.route_stops.all().delete()
            for item in items:
                RouteStop.objects.create(
                    route=route,
                    stop_id=item["stop_id"],
                    sequence=item["sequence"],
                    distance_from_start_km=item.get("distance_from_start_km", 0),
                    direction=item.get("direction", RouteStop.Direction.OUTBOUND),
                )

        qs = route.route_stops.select_related("stop").order_by("direction", "sequence")
        from apps.routes.api.serializers import RouteStopSerializer
        return Response(RouteStopSerializer(qs, many=True).data)


class StopViewSet(BaseModelViewSet):
    queryset = Stop.all_objects.all()
    serializer_class = StopSerializer
    required_capabilities_by_action = {
        "list": ("stops.read",),
        "retrieve": ("stops.read",),
        "create": ("stops.manage",),
        "update": ("stops.manage",),
        "partial_update": ("stops.manage",),
        "destroy": ("stops.manage",),
    }

    def get_serializer_class(self):
        if self.action == "retrieve":
            return StopDetailSerializer
        return StopSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        route_id = self.request.query_params.get("route")
        if route_id:
            qs = qs.filter(route_stops__route_id=route_id, route_stops__deleted_at__isnull=True).distinct()
        return qs
