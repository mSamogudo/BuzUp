from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.viewsets import BaseModelViewSet
from apps.guest_checkouts.api.serializers import (
    GuestCheckoutCreateSerializer,
    GuestCheckoutPublicSerializer,
    GuestCheckoutSerializer,
)
from apps.guest_checkouts.models import GuestCheckout
from apps.fares.services import NoFareFoundError, quote_fare
from apps.payments.models import PaymentIntent
from apps.payments.services.gateway import get_payment_gateway
from apps.payments.services.processing import confirm_payment_immediately
from apps.routes.models import Route, Stop
from apps.routes.services import RouteSegmentError, resolve_route_segment, route_segments_for_stop_pair
from apps.trips.models import Trip


class GuestCheckoutViewSet(BaseModelViewSet):
    queryset = GuestCheckout.all_objects.all()
    serializer_class = GuestCheckoutSerializer
    http_method_names = ["get", "head", "options"]
    required_capabilities_by_action = {
        "list": ("passengers.read",),
        "retrieve": ("passengers.read",),
    }


class GuestCheckoutCreateView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = GuestCheckoutCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        origin = Stop.objects.filter(pk=data.get("origin_stop_id")).first() if data.get("origin_stop_id") else None
        destination = Stop.objects.filter(pk=data.get("destination_stop_id")).first() if data.get("destination_stop_id") else None
        trip = None
        if data.get("trip_id"):
            trip = Trip.objects.select_related("route").filter(
                pk=data["trip_id"],
                status__in=[Trip.Status.BOARDING, Trip.Status.DEPARTED],
            ).first()
            if trip is None:
                return Response({"detail": "Autocarro nao esta disponivel para compra."}, status=status.HTTP_404_NOT_FOUND)
            if trip.route.code != data["route_code"]:
                return Response({"detail": "A viagem nao pertence a rota seleccionada."}, status=status.HTTP_400_BAD_REQUEST)

        route = trip.route if trip else Route.objects.filter(code=data["route_code"], status=Route.Status.ACTIVE).first()
        if route and (origin or destination):
            try:
                resolve_route_segment(route, origin.id if origin else None, destination.id if destination else None)
            except RouteSegmentError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        unit_amount = data.get("unit_amount") or 0
        if route and origin and destination:
            try:
                unit_amount = quote_fare(route=route, origin_stop=origin, destination_stop=destination).amount
            except NoFareFoundError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        if not unit_amount or unit_amount <= 0:
            return Response(
                {"detail": "Nao foi possivel calcular o preco para esta viagem. Tente novamente ou contacte o agente."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total = unit_amount * data["quantity"]
        ref = f"GC-{uuid4().hex[:12].upper()}"
        gc = GuestCheckout.objects.create(
            reference=ref,
            payer_phone=data["payer_phone"],
            buyer_name=data.get("buyer_name", ""),
            route_code=data["route_code"],
            route_name=data.get("route_name", ""),
            origin_stop=origin.name if origin else data["origin_stop"],
            destination_stop=destination.name if destination else data["destination_stop"],
            origin_stop_ref=origin,
            destination_stop_ref=destination,
            quantity=data["quantity"],
            unit_amount=unit_amount,
            total_amount=total,
            status=GuestCheckout.Status.PAYMENT_PENDING,
            expires_at=timezone.now() + timedelta(minutes=30),
            trip=trip,
        )

        idempotency_key = f"gc-{ref}"
        pi = PaymentIntent.objects.create(
            reference=f"PAY-{ref}",
            idempotency_key=idempotency_key,
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
            amount=total,
            payer_phone=data["payer_phone"],
            guest_checkout=gc,
            status=PaymentIntent.Status.PENDING,
            expires_at=gc.expires_at,
        )

        gateway = get_payment_gateway(payer_phone=data["payer_phone"])
        result = gateway.initiate_payment(
            reference=pi.reference,
            amount=total,
            payer_phone=data["payer_phone"],
            description=f"BuzUp bilhete {data['route_code']}",
        )

        pi.provider = result.provider
        pi.metadata = {
            "gateway_request": result.request_payload or {},
            "gateway_response": result.response_payload or {},
        }

        if result.success:
            pi.provider_reference = result.provider_reference
            pi.save(update_fields=["provider", "provider_reference", "metadata", "updated_at"])
            confirm_payment_immediately(pi, result.provider_reference)
            pi.refresh_from_db()
            gc.refresh_from_db()
        elif result.pending:
            pi.provider_reference = result.provider_reference
            pi.save(update_fields=["provider", "provider_reference", "metadata", "updated_at"])
        else:
            gc.status = GuestCheckout.Status.CANCELLED
            gc.save(update_fields=["status", "updated_at"])
            pi.status = PaymentIntent.Status.FAILED
            pi.save(update_fields=["status", "provider", "metadata", "updated_at"])
            return Response({
                "detail": result.detail_message or "Falha ao iniciar pagamento.",
            }, status=status.HTTP_502_BAD_GATEWAY)

        first_pass = gc.travel_passes.order_by("created_at").first() if gc.status == GuestCheckout.Status.ISSUED else None
        return Response({
            "checkout_reference": gc.reference,
            "payment_reference": pi.reference,
            "total_amount": str(total),
            "status": gc.status,
            "payment_status": pi.status,
            "detail_message": result.detail_message,
            "ticket_url": _public_ticket_url(first_pass.token) if first_pass else "",
        }, status=status.HTTP_201_CREATED)


class PublicTripSearchView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        from apps.routes.models import RouteStop
        from datetime import timedelta

        route_id = request.query_params.get("route")
        origin_id = request.query_params.get("origin")
        destination_id = request.query_params.get("destination")
        date_str = request.query_params.get("date")

        if origin_id and destination_id and origin_id == destination_id:
            return Response({"detail": "Destino deve ser diferente da origem."}, status=status.HTTP_400_BAD_REQUEST)

        segments_by_route: dict[int, object] = {}
        if origin_id and destination_id:
            try:
                segments_by_route = route_segments_for_stop_pair(origin_id, destination_id, route_id)
            except RouteSegmentError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            if route_id and not segments_by_route:
                return Response({"detail": "Nao existe direccao valida entre a origem e o destino nesta rota."}, status=status.HTTP_400_BAD_REQUEST)

        qs = Trip.objects.select_related("route", "vehicle", "driver").filter(
            status__in=[Trip.Status.BOARDING, Trip.Status.DEPARTED],
            vehicle__isnull=False,
        )

        if route_id:
            qs = qs.filter(route_id=route_id)
        if origin_id and destination_id:
            qs = qs.filter(route_id__in=segments_by_route.keys())

        if date_str:
            from django.utils.dateparse import parse_date
            day = parse_date(date_str)
            if day:
                day_start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
                qs = qs.filter(planned_departure_at__gte=day_start, planned_departure_at__lt=day_start + timedelta(days=1))

        qs = qs.order_by("route__code", "vehicle__registration", "planned_departure_at")[:20]

        results = []
        for trip in qs:
            fare_amount = None
            origin = Stop.objects.filter(pk=origin_id).first() if origin_id else None
            dest = Stop.objects.filter(pk=destination_id).first() if destination_id else None
            try:
                q = quote_fare(route=trip.route, origin_stop=origin, destination_stop=dest)
                fare_amount = str(q.amount)
            except NoFareFoundError:
                pass

            segment = segments_by_route.get(trip.route_id)
            results.append({
                "trip_id": trip.id,
                "route_id": trip.route_id,
                "route_code": trip.route.code,
                "route_name": trip.route.name,
                "vehicle": trip.vehicle.registration if trip.vehicle else None,
                "driver": trip.driver.full_name if trip.driver else None,
                "departure": trip.planned_departure_at.isoformat() if trip.planned_departure_at else None,
                "started_at": trip.activity_started_at.isoformat() if trip.activity_started_at else None,
                "direction": segment.direction if segment else "",
                "status": trip.status,
                "fare_amount": fare_amount,
            })

        routes_list = list(Route.objects.filter(status="active").values("id", "code", "name"))
        if route_id:
            stops_list = []
            seen_stop_ids = set()
            route_stops = RouteStop.objects.select_related("stop").filter(
                route_id=route_id,
                stop__status="active",
            ).order_by("direction", "sequence")
            for route_stop in route_stops:
                if route_stop.stop_id in seen_stop_ids:
                    continue
                seen_stop_ids.add(route_stop.stop_id)
                stops_list.append({
                    "id": route_stop.stop_id,
                    "code": route_stop.stop.code,
                    "name": route_stop.stop.name,
                })
        else:
            stops_list = list(Stop.objects.filter(status="active").values("id", "code", "name"))

        return Response({
            "routes": routes_list,
            "stops": stops_list,
            "trips": results,
        })


class PublicBusInfoView(APIView):
    """Lookup info for a bus QR code scan: vehicle + active trips + stops + fares."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, vehicle_uuid):
        from apps.trips.models import Vehicle
        from apps.routes.models import RouteStop

        vehicle = Vehicle.objects.filter(uuid=vehicle_uuid).first()
        if not vehicle:
            return Response({"detail": "Autocarro nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        trips = Trip.objects.select_related("route", "driver").filter(
            vehicle=vehicle,
            status__in=[Trip.Status.BOARDING, Trip.Status.DEPARTED, Trip.Status.SCHEDULED],
        ).order_by("planned_departure_at")[:5]

        trips_payload = []
        for trip in trips:
            stops = list(
                RouteStop.objects.select_related("stop")
                .filter(route=trip.route, stop__status="active")
                .order_by("direction", "sequence")
            )
            stops_seen = {}
            for rs in stops:
                key = rs.stop_id
                if key not in stops_seen:
                    stops_seen[key] = {
                        "id": rs.stop_id,
                        "code": rs.stop.code,
                        "name": rs.stop.name,
                    }
            trips_payload.append({
                "trip_id": trip.id,
                "route_id": trip.route_id,
                "route_code": trip.route.code,
                "route_name": trip.route.name,
                "driver": trip.driver.full_name if trip.driver else "",
                "departure": trip.planned_departure_at.isoformat() if trip.planned_departure_at else None,
                "started_at": trip.activity_started_at.isoformat() if trip.activity_started_at else None,
                "status": trip.status,
                "stops": list(stops_seen.values()),
            })

        return Response({
            "vehicle": {
                "uuid": str(vehicle.uuid),
                "registration": vehicle.registration,
                "make": vehicle.make,
                "model_name": vehicle.model_name,
                "status": vehicle.status,
            },
            "active_trips": trips_payload,
        })


class TicketPdfView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        from apps.guest_checkouts.models import DigitalTravelPass
        from apps.guest_checkouts.ticket_pdf import generate_tickets_pdf
        import hashlib

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            tp = DigitalTravelPass.objects.select_related("guest_checkout").get(token_hash=token_hash)
        except DigitalTravelPass.DoesNotExist:
            return Response({"detail": "Bilhete nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if tp.guest_checkout_id:
            travel_passes = list(
                DigitalTravelPass.objects.select_related("guest_checkout").filter(
                    guest_checkout_id=tp.guest_checkout_id,
                ).order_by("created_at", "id")
            )
        else:
            travel_passes = [tp]

        pdf_bytes = generate_tickets_pdf(travel_passes)
        from django.http import HttpResponse as DjangoHttpResponse
        response = DjangoHttpResponse(pdf_bytes, content_type="application/pdf")
        ref = tp.guest_checkout.reference if tp.guest_checkout else str(tp.uuid)[:8]
        filename_prefix = "bilhetes" if len(travel_passes) > 1 else "bilhete"
        response["Content-Disposition"] = f'inline; filename="{filename_prefix}-{ref}.pdf"'
        return response


class GuestCheckoutLookupView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, reference):
        try:
            gc = GuestCheckout.objects.prefetch_related("travel_passes").get(reference=reference)
        except GuestCheckout.DoesNotExist:
            return Response({"detail": "Checkout nao encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return Response(GuestCheckoutPublicSerializer(gc).data)


def _public_ticket_url(token: str) -> str:
    base = str(getattr(settings, "PUBLIC_BASE_URL", "") or "").rstrip("/")
    return f"{base}/api/public/ticket/{token}/" if base else f"/api/public/ticket/{token}/"
