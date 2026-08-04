from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import HasCapabilities
from apps.core.viewsets import BaseModelViewSet
from apps.routes.services import RouteSegmentError, route_segments_for_stop_pair
from apps.trips.activity import (
    TripActivityError,
    close_trip_activity,
    pause_trip_activity,
    resolve_driver_for_user,
    resume_trip_activity,
    start_trip_activity,
)
from apps.trips.api.serializers import (
    AgentSerializer,
    DriverSerializer,
    GenerateTripsSerializer,
    RouteScheduleSerializer,
    TripSearchSerializer,
    TripDetailSerializer,
    TripSerializer,
    VehicleSerializer,
)
from apps.trips.models import Agent, Driver, RouteSchedule, Trip, Vehicle
from apps.trips.services import generate_daily_trips


class VehicleViewSet(BaseModelViewSet):
    queryset = Vehicle.all_objects.all()
    serializer_class = VehicleSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    required_capabilities_by_action = {
        "list": ("vehicles.read",), "retrieve": ("vehicles.read",),
        "create": ("vehicles.manage",), "update": ("vehicles.manage",),
        "partial_update": ("vehicles.manage",), "destroy": ("vehicles.manage",),
    }


class DriverViewSet(BaseModelViewSet):
    queryset = Driver.all_objects.all()
    serializer_class = DriverSerializer
    required_capabilities_by_action = {
        "list": ("drivers.read",), "retrieve": ("drivers.read",),
        "create": ("drivers.manage",), "update": ("drivers.manage",),
        "partial_update": ("drivers.manage",), "destroy": ("drivers.manage",),
    }


class AgentViewSet(BaseModelViewSet):
    queryset = Agent.all_objects.all()
    serializer_class = AgentSerializer
    required_capabilities_by_action = {
        "list": ("agents.read",), "retrieve": ("agents.read",),
        "create": ("agents.manage",), "update": ("agents.manage",),
        "partial_update": ("agents.manage",), "destroy": ("agents.manage",),
    }


class RouteScheduleViewSet(BaseModelViewSet):
    queryset = RouteSchedule.all_objects.select_related("route", "vehicle", "driver", "agent").all()
    serializer_class = RouteScheduleSerializer
    required_capabilities_by_action = {
        "list": ("trips.read",), "retrieve": ("trips.read",),
        "create": ("trips.manage",), "update": ("trips.manage",),
        "partial_update": ("trips.manage",), "destroy": ("trips.manage",),
    }


class GenerateTripsView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("trips.manage",)

    def post(self, request):
        from datetime import timedelta

        from apps.trips.services import count_daily_trips

        serializer = GenerateTripsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        schedule_id = data.get("schedule_id")
        if schedule_id:
            schedules = list(RouteSchedule.objects.filter(pk=schedule_id))
            if not schedules:
                return Response({"detail": "Programacao nao encontrada."},
                                status=status.HTTP_404_NOT_FOUND)
        else:
            # Sem horario indicado: todos os activos.
            schedules = list(
                RouteSchedule.objects.filter(status=RouteSchedule.Status.ACTIVE)
                .select_related("route", "vehicle", "driver")
            )

        date_from = data.get("date_from") or timezone.now().date()
        days = data.get("days") or 1
        preview = data.get("preview", False)

        per_day = []
        per_schedule = {}
        total = 0
        for offset in range(days):
            day = date_from + timedelta(days=offset)
            day_total = 0
            for schedule in schedules:
                n = (count_daily_trips(schedule, day) if preview
                     else len(generate_daily_trips(schedule, day)))
                if n:
                    day_total += n
                    key = schedule.pk
                    entry = per_schedule.setdefault(key, {
                        "schedule_id": key,
                        "route_code": schedule.route.code if schedule.route_id else "",
                        "route_name": schedule.route.name if schedule.route_id else "",
                        "count": 0,
                    })
                    entry["count"] += n
            per_day.append({"date": day.isoformat(), "count": day_total})
            total += day_total

        return Response(
            {
                "generated": 0 if preview else total,
                "preview": preview,
                # `would_generate` responde sempre, para o assistente poder
                # mostrar o numero antes e depois de confirmar.
                "would_generate": total,
                "days": days,
                "date_from": date_from.isoformat(),
                "date_to": (date_from + timedelta(days=days - 1)).isoformat(),
                "schedules_considered": len(schedules),
                "by_day": per_day,
                "by_schedule": sorted(per_schedule.values(), key=lambda e: -e["count"]),
            },
            status=status.HTTP_200_OK if preview else status.HTTP_201_CREATED,
        )


class TripViewSet(BaseModelViewSet):
    queryset = Trip.all_objects.select_related("route", "vehicle", "driver", "agent").all()
    serializer_class = TripSerializer
    required_capabilities_by_action = {
        "list": ("trips.read",), "retrieve": ("trips.read",),
        "create": ("trips.manage",), "update": ("trips.manage",),
        "partial_update": ("trips.manage",), "destroy": ("trips.manage",),
    }

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TripDetailSerializer
        return TripSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        route_id = self.request.query_params.get("route")
        if route_id:
            qs = qs.filter(route_id=route_id)
        trip_status = self.request.query_params.get("status")
        if trip_status:
            qs = qs.filter(status=trip_status)
        return qs


class TripSearchView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = TripSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        origin_id = data.get("origin_stop_id")
        destination_id = data.get("destination_stop_id")
        segments_by_route = {}
        if origin_id and destination_id:
            try:
                segments_by_route = route_segments_for_stop_pair(origin_id, destination_id, data.get("route_id"))
            except RouteSegmentError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            if data.get("route_id") and not segments_by_route:
                return Response({"detail": "Nao existe direccao valida entre a origem e o destino nesta rota."}, status=status.HTTP_400_BAD_REQUEST)

        qs = Trip.objects.select_related("route", "vehicle", "driver").filter(
            status__in=[Trip.Status.BOARDING, Trip.Status.DEPARTED],
            vehicle__isnull=False,
        )

        if data.get("route_id"):
            qs = qs.filter(route_id=data["route_id"])

        if origin_id and destination_id:
            qs = qs.filter(route_id__in=segments_by_route.keys())

        if data.get("date"):
            day_start = timezone.make_aware(timezone.datetime.combine(data["date"], timezone.datetime.min.time()))
            day_end = day_start + timedelta(days=1)
            qs = qs.filter(planned_departure_at__gte=day_start, planned_departure_at__lt=day_end)

        qs = qs.order_by("route__code", "vehicle__registration", "planned_departure_at")[:20]
        return Response(TripSerializer(qs, many=True).data)


class DriverTripsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        driver = resolve_driver_for_user(request.user)
        if not driver:
            return Response({"detail": "Motorista nao associado ao utilizador autenticado."}, status=status.HTTP_404_NOT_FOUND)

        trips = Trip.objects.select_related("route", "vehicle", "driver").filter(
            driver=driver,
            status__in=[Trip.Status.SCHEDULED, Trip.Status.BOARDING, Trip.Status.DEPARTED, Trip.Status.PAUSED],
        ).order_by("planned_departure_at", "route__code")
        return Response(TripSerializer(trips, many=True).data)


class DriverTripActionView(APIView):
    permission_classes = [IsAuthenticated]

    action = ""

    def post(self, request, pk: int):
        driver = resolve_driver_for_user(request.user)
        if not driver:
            return Response({"detail": "Motorista nao associado ao utilizador autenticado."}, status=status.HTTP_404_NOT_FOUND)

        try:
            trip = Trip.objects.select_related("route", "vehicle", "driver").get(pk=pk)
        except Trip.DoesNotExist:
            return Response({"detail": "Viagem nao encontrada."}, status=status.HTTP_404_NOT_FOUND)

        try:
            if self.action == "start":
                trip = start_trip_activity(trip, driver, request.user)
                # Dispositivos livres: o terminal que inicia a viagem passa a
                # ser a fonte da posicao do autocarro no mapa dos passageiros.
                serial = (request.data.get("device_serial") or "").strip()
                if serial:
                    from apps.devices.models import Device
                    device = Device.objects.filter(serial_number=serial).exclude(
                        status=Device.Status.BLOCKED,
                    ).first()
                    if device:
                        trip.device = device
                        trip.save(update_fields=["device", "updated_at"])
            elif self.action == "pause":
                trip = pause_trip_activity(trip, driver, request.user)
            elif self.action == "resume":
                trip = resume_trip_activity(trip, driver, request.user)
            elif self.action == "close":
                trip = close_trip_activity(trip, driver, request.user)
            else:
                return Response({"detail": "Accao invalida."}, status=status.HTTP_400_BAD_REQUEST)
        except TripActivityError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(TripDetailSerializer(trip).data)
