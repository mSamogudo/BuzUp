from datetime import timedelta

from django.http import HttpResponse
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.download_auth import DownloadTicketAuthentication
from apps.core.download_scopes import TRIP_MANIFEST
from apps.core.permissions import HasCapabilities
from apps.core.viewsets import BaseModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from apps.routes.services import RouteSegmentError, route_segments_for_stop_pair
from apps.trips.activity import (
    depart_trip_activity,
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
    ProgramarPartidasSerializer,
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


class VehicleSeatPreviewView(APIView):
    """Como fica a planta com esta lotacao e esta disposicao.

    O operador escolhia "2+2" numa lista e nunca via o resultado — tinha de
    imaginar. Num autocarro de 50 lugares engana-se pouco; num minibus de 15,
    a diferenca entre 2+2 e 1+2 e a diferenca entre uma planta que existe e uma
    que o passageiro nao vai encontrar a bordo.

    Calculada aqui e nao no browser de proposito: a regra da planta e uma so, e
    escreve-la outra vez em JavaScript era garantir que um dia deixavam de
    concordar.
    """

    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("vehicles.read",)

    def get(self, request):
        from apps.guest_checkouts.seatmap import DEFAULT_LAYOUT, seat_rows

        try:
            capacidade = int(request.query_params.get("capacity") or 0)
            ultima = int(request.query_params.get("last_row") or 0)
        except (TypeError, ValueError):
            return Response({"detail": "Lotacao invalida."}, status=status.HTTP_400_BAD_REQUEST)

        # Um tecto: isto e uma pre-visualizacao, nao um gerador de plantas de
        # comboio. Sem ele, um engano num campo devolvia mil filas.
        if capacidade < 0 or capacidade > 120 or ultima < 0 or ultima > 10:
            return Response({"detail": "Valores fora do razoavel."},
                            status=status.HTTP_400_BAD_REQUEST)

        layout = request.query_params.get("layout") or DEFAULT_LAYOUT
        filas = seat_rows(capacidade, layout, ultima)
        return Response({
            "layout": layout,
            "capacity": capacidade,
            "rows": filas,
            "seats": sum(len(f["left"]) + len(f["right"]) for f in filas),
        })


class ProgramarPartidasView(APIView):
    """Partidas marcadas no calendario, sem passar por um horario recorrente.

    O assistente antigo exigia um `RouteSchedule` — e criar um obrigava a
    inventar hora de fim e cadencia para uma carreira que sai uma vez por dia.
    Sem nenhum horario criado, o assistente abria com a lista vazia e nao havia
    caminho nenhum a partir dali.
    """

    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("trips.manage",)

    def post(self, request):
        from apps.routes.models import Route
        from apps.trips.services import programar_partidas

        serializer = ProgramarPartidasSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        route = Route.objects.filter(pk=data["route_id"], status=Route.Status.ACTIVE).first()
        if not route:
            return Response({"detail": "Rota nao encontrada ou inactiva."},
                            status=status.HTTP_404_NOT_FOUND)

        def _opcional(modelo, chave):
            pk = data.get(chave)
            return modelo.objects.filter(pk=pk).first() if pk else None

        resultado = programar_partidas(
            route=route,
            dates=data["dates"],
            times=data["times"],
            vehicle=_opcional(Vehicle, "vehicle_id"),
            driver=_opcional(Driver, "driver_id"),
            agent=_opcional(Agent, "agent_id"),
            duration_minutes=data.get("duration_minutes"),
            direction=data.get("direction") or "",
            preview=data["preview"],
        )
        criadas = resultado.pop("trips")
        resultado["route_code"] = route.code
        resultado["route_name"] = route.name
        if not data["preview"]:
            resultado["trip_ids"] = [t.id for t in criadas]

        return Response(
            resultado,
            status=status.HTTP_200_OK if data["preview"] else status.HTTP_201_CREATED,
        )


class TripViewSet(BaseModelViewSet):
    queryset = Trip.all_objects.select_related("route", "vehicle", "driver", "agent").all()
    serializer_class = TripSerializer
    required_capabilities_by_action = {
        "list": ("trips.read",), "retrieve": ("trips.read",),
        "create": ("trips.manage",), "update": ("trips.manage",),
        "partial_update": ("trips.manage",), "destroy": ("trips.manage",),
        "summary": ("trips.read",),
    }

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TripDetailSerializer
        return TripSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Os filtros sao da LISTA. Quando se pede uma viagem pelo numero, ela ja
        # esta identificada — nao ha nada para filtrar.
        #
        # Aplicados a tudo, escondiam do proprio `retrieve` as partidas que ja
        # tinham saido: abrir, editar, apagar ou ver o manifesto de uma viagem
        # de ontem respondia "No Trip matches the given query". Em producao eram
        # quatro das seis viagens — e sao precisamente as que se vao consultar
        # depois de acontecerem.
        if self.action != "list":
            return qs
        route_id = self.request.query_params.get("route")
        if route_id:
            qs = qs.filter(route_id=route_id)
        trip_status = self.request.query_params.get("status")
        if trip_status:
            qs = qs.filter(status=trip_status)
        return self._por_periodo(qs, self.request.query_params.get("when"))

    @staticmethod
    def _por_periodo(qs, periodo):
        """Recorta por periodo E ordena de acordo.

        Sem isto, a ordenacao do modelo (`-planned_departure_at`) punha a
        partida MAIS DISTANTE em primeiro: com milhares de viagens geradas por
        horario, a primeira pagina do portal era so futuro longinquo — todas
        "agendadas" — e a operacao de hoje nao aparecia em lado nenhum.
        """
        agora = timezone.now()
        if periodo == "hoje":
            inicio = timezone.localtime(agora).replace(hour=0, minute=0, second=0, microsecond=0)
            return qs.filter(
                planned_departure_at__gte=inicio,
                planned_departure_at__lt=inicio + timedelta(days=1),
            ).order_by("planned_departure_at")
        if periodo == "passadas":
            return qs.filter(planned_departure_at__lt=agora).order_by("-planned_departure_at")
        if periodo == "todas":
            return qs.order_by("-planned_departure_at")
        # Por omissao: o que ainda esta para acontecer, do mais proximo primeiro.
        return qs.filter(
            Q(planned_departure_at__gte=agora) | Q(planned_departure_at__isnull=True)
        ).order_by("planned_departure_at")

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """Contadores calculados na base de dados.

        O portal contava em cima da pagina que recebia — com 200 de 7 500
        linhas, os numeros do cabecalho estavam simplesmente errados.
        """
        agora = timezone.now()
        inicio = timezone.localtime(agora).replace(hour=0, minute=0, second=0, microsecond=0)
        base = Trip.objects.all()
        return Response({
            "hoje": base.filter(planned_departure_at__gte=inicio,
                                planned_departure_at__lt=inicio + timedelta(days=1)).count(),
            "circulacao": base.filter(status__in=[Trip.Status.BOARDING, Trip.Status.DEPARTED]).count(),
            "agendadas": base.filter(status=Trip.Status.SCHEDULED,
                                     planned_departure_at__gte=agora).count(),
            "repouso": base.filter(status=Trip.Status.PAUSED).count(),
            "total": base.count(),
        })


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
            if self.action == "depart":
                trip = depart_trip_activity(trip, driver, request.user)
            elif self.action == "start":
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


class _ManifestMixin:
    """Manifesto de uma partida, ao vivo ou fotografado.

    Depois do fecho devolve a FOTOGRAFIA guardada, nao um recalculo: e isso
    que faz do manifesto um documento e nao um relatorio que muda sozinho.
    """

    def _manifest_for(self, trip) -> dict:
        closure = getattr(trip, "revenue_closure", None)
        if closure is not None and closure.manifest:
            return closure.manifest
        from apps.trips.manifest import build_manifest
        return build_manifest(trip, final=trip.status in {
            Trip.Status.COMPLETED, Trip.Status.CANCELLED,
        })


class DriverTripManifestView(_ManifestMixin, APIView):
    """Manifesto da viagem do proprio motorista."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        driver = resolve_driver_for_user(request.user)
        if not driver:
            return Response({"detail": "Motorista nao associado ao utilizador autenticado."},
                            status=status.HTTP_404_NOT_FOUND)
        trip = Trip.objects.select_related("route", "vehicle", "driver").filter(pk=pk).first()
        if not trip:
            return Response({"detail": "Viagem nao encontrada."}, status=status.HTTP_404_NOT_FOUND)
        if trip.driver_id != driver.id:
            # Nao dizer "existe mas nao e tua": o manifesto tem nomes e
            # documentos de passageiros.
            return Response({"detail": "Viagem nao encontrada."}, status=status.HTTP_404_NOT_FOUND)
        return Response(self._manifest_for(trip))


class TripManifestView(_ManifestMixin, APIView):
    """Manifesto visto do portal (quem tem leitura de viagens)."""

    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("trips.read",)

    def get(self, request, pk: int):
        trip = Trip.objects.select_related("route", "vehicle", "driver").filter(pk=pk).first()
        if not trip:
            return Response({"detail": "Viagem nao encontrada."}, status=status.HTTP_404_NOT_FOUND)
        return Response(self._manifest_for(trip))


class TripManifestPdfView(_ManifestMixin, APIView):
    """Manifesto em PDF, para fiscalizacao, seguradora e arquivo."""

    permission_classes = [IsAuthenticated, HasCapabilities]
    authentication_classes = [JWTAuthentication, DownloadTicketAuthentication]
    download_scope = TRIP_MANIFEST
    required_capabilities = ("trips.read",)

    def get(self, request, pk: int):
        trip = Trip.objects.select_related("route", "vehicle", "driver").filter(pk=pk).first()
        if not trip:
            return Response({"detail": "Viagem nao encontrada."}, status=status.HTTP_404_NOT_FOUND)
        from apps.trips.manifest_pdf import render_manifest_pdf

        data = self._manifest_for(trip)
        pdf = render_manifest_pdf(data)
        resp = HttpResponse(pdf, content_type="application/pdf")
        nome = f"manifesto-{data.get('route_code') or trip.pk}-{trip.pk}.pdf"
        resp["Content-Disposition"] = f'inline; filename="{nome}"'
        return resp
