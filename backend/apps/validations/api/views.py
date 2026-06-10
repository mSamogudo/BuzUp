from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agent_api.permissions import IsActiveAgent, get_authorized_device
from apps.core.viewsets import BaseModelViewSet
from apps.guest_checkouts.api.serializers import DigitalTravelPassSerializer
from apps.guest_checkouts.purchase import PurchaseError, purchase_travel_pass, quote_for_passenger
from apps.fares.services import NoFareFoundError
from apps.routes.models import Route, Stop
from apps.routes.services import RouteSegmentError, route_segments_for_stop_pair
from apps.passengers.models import PassengerAccount


def _resolve_route_id(data) -> int | None:
    """Returns the route id to use for a purchase/quote.

    The mobile passenger only picks origin + destination — they cannot be
    expected to know route codes. When ``route_id`` is omitted we infer it
    from the stop pair. If several corridors share the pair we prefer one with
    an active trip, otherwise the lowest route id (deterministic).
    """
    route_id = data.get("route_id")
    if route_id:
        return route_id
    origin_id = data.get("origin_stop_id")
    destination_id = data.get("destination_stop_id")
    if not (origin_id and destination_id):
        return None
    try:
        segments = route_segments_for_stop_pair(origin_id, destination_id)
    except RouteSegmentError:
        return None
    route_ids = sorted(segments.keys())
    if not route_ids:
        return None
    if len(route_ids) == 1:
        return route_ids[0]
    from apps.trips.models import Trip
    active = (
        Trip.objects.filter(
            route_id__in=route_ids,
            status__in=[Trip.Status.BOARDING, Trip.Status.DEPARTED],
        )
        .values_list("route_id", flat=True)
        .first()
    )
    return active or route_ids[0]
from apps.validations.api.serializers import (
    PurchaseTravelPassSerializer,
    ValidateCardSerializer,
    ValidateGuestPassSerializer,
    ValidateQrSerializer,
    ValidationEventSerializer,
)
from apps.validations.models import ValidationEvent
from apps.validations.services import validate_card, validate_qr_account, validate_qr_pass
from apps.wallets.services import InsufficientBalanceError, WalletBlockedError


class ValidationEventViewSet(BaseModelViewSet):
    queryset = ValidationEvent.all_objects.select_related(
        "route", "device", "passenger_account",
    ).all()
    serializer_class = ValidationEventSerializer
    http_method_names = ["get", "head", "options"]
    required_capabilities_by_action = {
        "list": ("validations.read",),
        "retrieve": ("validations.read",),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        route_id = self.request.query_params.get("route")
        if route_id:
            qs = qs.filter(route_id=route_id)
        device_id = self.request.query_params.get("device")
        if device_id:
            qs = qs.filter(device_id=device_id)
        v_status = self.request.query_params.get("status")
        if v_status:
            qs = qs.filter(status=v_status)
        v_type = self.request.query_params.get("type")
        if v_type:
            qs = qs.filter(validation_type=v_type)
        return qs


class ValidateCardView(APIView):
    # Debita a carteira do passageiro: SO um agente activo pode validar.
    # (era AllowAny -> qualquer um podia drenar saldo). O endpoint canonico do
    # POS e /api/agent/validations/card/; este fica protegido do mesmo modo.
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request):
        serializer = ValidateCardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # O device tem de pertencer ao agente autenticado — nunca confiar no
        # serial cru do corpo (so um device ACTIVE atribuido conta).
        device = get_authorized_device(request.user, serial_number=data.get("device_serial") or None)
        event = validate_card(
            card_uid=data["card_uid"],
            route_id=data["route_id"],
            origin_stop_id=data.get("origin_stop_id"),
            destination_stop_id=data.get("destination_stop_id"),
            trip_id=data.get("trip_id"),
            device_serial=device.serial_number if device else "",
            idempotency_key=data["idempotency_key"],
        )

        return Response(ValidationEventSerializer(event).data)


class ValidateQrView(APIView):
    # Queima um passe digital: so um agente activo pode validar.
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request):
        serializer = ValidateQrSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        device = get_authorized_device(request.user, serial_number=data.get("device_serial") or None)
        event = validate_qr_pass(
            token=data["token"],
            route_id=data.get("route_id"),
            trip_id=data.get("trip_id"),
            device_serial=device.serial_number if device else "",
            idempotency_key=data["idempotency_key"],
        )

        return Response(ValidationEventSerializer(event).data)


class ValidateGuestPassView(APIView):
    # Queima um passe de convidado: so um agente activo pode validar.
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request):
        serializer = ValidateGuestPassSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        device = get_authorized_device(request.user, serial_number=data.get("device_serial") or None)
        event = validate_qr_pass(
            token=data["token"],
            route_id=data.get("route_id"),
            trip_id=data.get("trip_id"),
            device_serial=device.serial_number if device else "",
            idempotency_key=data["idempotency_key"],
        )

        return Response(ValidationEventSerializer(event).data)


class PurchaseTravelPassView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PurchaseTravelPassSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        passenger = PassengerAccount.objects.filter(
            phone_number=request.user.phone,
            status=PassengerAccount.Status.ACTIVE,
        ).first()

        if not passenger:
            return Response(
                {"detail": "Conta de passageiro nao encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        route_id = _resolve_route_id(data)
        if not route_id:
            return Response(
                {"detail": "Nao existe rota entre a origem e o destino seleccionados."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            travel_pass = purchase_travel_pass(
                passenger=passenger,
                route_id=route_id,
                origin_stop_id=data.get("origin_stop_id"),
                destination_stop_id=data.get("destination_stop_id"),
                trip_id=data.get("trip_id"),
                passenger_package_id=data.get("passenger_package_id"),
                use_package=data.get("use_package", True),
            )
        except (PurchaseError, InsufficientBalanceError, WalletBlockedError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        result = DigitalTravelPassSerializer(travel_pass).data
        result["token"] = getattr(travel_pass, "_raw_token", "")
        pkg = getattr(travel_pass, "_package_used", None)
        if pkg:
            result["used_package"] = {
                "id": pkg.id,
                "name": pkg.package.name,
                "discount_type": pkg.package.discount_type,
            }
            result["wallet_amount_charged"] = str(getattr(travel_pass, "_wallet_amount", "0.00"))
        return Response(result, status=status.HTTP_201_CREATED)


class TravelPassQuoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PurchaseTravelPassSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        passenger = PassengerAccount.objects.filter(
            phone_number=request.user.phone, status=PassengerAccount.Status.ACTIVE,
        ).first()
        if not passenger:
            return Response({"detail": "Conta de passageiro nao encontrada."}, status=status.HTTP_404_NOT_FOUND)

        route_id = _resolve_route_id(data)
        if not route_id:
            return Response(
                {"detail": "Nao existe rota entre a origem e o destino seleccionados."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            route = Route.objects.get(pk=route_id)
        except Route.DoesNotExist:
            return Response({"detail": "Rota nao encontrada."}, status=status.HTTP_404_NOT_FOUND)

        origin = Stop.objects.filter(pk=data.get("origin_stop_id")).first() if data.get("origin_stop_id") else None
        destination = Stop.objects.filter(pk=data.get("destination_stop_id")).first() if data.get("destination_stop_id") else None

        try:
            quote = quote_for_passenger(
                passenger=passenger, route=route,
                origin=origin, destination=destination,
                passenger_package_id=data.get("passenger_package_id"),
                use_package=data.get("use_package", True),
            )
        except NoFareFoundError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(quote)
