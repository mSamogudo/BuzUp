from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.viewsets import BaseModelViewSet
from apps.fares.api.serializers import (
    AdminFeeSerializer,
    FareProductSerializer,
    FareQuoteRequestSerializer,
    FareRuleSerializer,
)
from apps.fares.models import AdminFee, FareProduct, FareRule


class AdminFeeViewSet(BaseModelViewSet):
    queryset = AdminFee.all_objects.all()
    serializer_class = AdminFeeSerializer
    required_capabilities_by_action = {
        "list": ("fares.read",),
        "retrieve": ("fares.read",),
        "create": ("fares.manage",),
        "update": ("fares.manage",),
        "partial_update": ("fares.manage",),
        "destroy": ("fares.manage",),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        kind = self.request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        return qs
from apps.fares.services import FareConflictError, NoFareFoundError, quote_fare
from apps.routes.models import Route, Stop


class FareProductViewSet(BaseModelViewSet):
    queryset = FareProduct.all_objects.all()
    serializer_class = FareProductSerializer
    required_capabilities_by_action = {
        "list": ("fares.read",),
        "retrieve": ("fares.read",),
        "create": ("fares.manage",),
        "update": ("fares.manage",),
        "partial_update": ("fares.manage",),
        "destroy": ("fares.manage",),
    }


class FareRuleViewSet(BaseModelViewSet):
    queryset = FareRule.all_objects.select_related(
        "fare_product", "route", "origin_stop", "destination_stop",
    ).all()
    serializer_class = FareRuleSerializer
    required_capabilities_by_action = {
        "list": ("fares.read",),
        "retrieve": ("fares.read",),
        "create": ("fares.manage",),
        "update": ("fares.manage",),
        "partial_update": ("fares.manage",),
        "destroy": ("fares.manage",),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        route_id = self.request.query_params.get("route")
        if route_id:
            qs = qs.filter(route_id=route_id)
        return qs


class FareQuoteView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = FareQuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            route = Route.objects.get(pk=data["route_id"])
        except Route.DoesNotExist:
            return Response({"detail": "Rota nao encontrada."}, status=status.HTTP_404_NOT_FOUND)

        origin = None
        destination = None
        if data.get("origin_stop_id"):
            try:
                origin = Stop.objects.get(pk=data["origin_stop_id"])
            except Stop.DoesNotExist:
                return Response({"detail": "Paragem de origem nao encontrada."}, status=status.HTTP_404_NOT_FOUND)
        if data.get("destination_stop_id"):
            try:
                destination = Stop.objects.get(pk=data["destination_stop_id"])
            except Stop.DoesNotExist:
                return Response({"detail": "Paragem de destino nao encontrada."}, status=status.HTTP_404_NOT_FOUND)

        try:
            result = quote_fare(
                route=route,
                origin_stop=origin,
                destination_stop=destination,
                passenger_class=data.get("passenger_class", FareRule.PassengerClass.STANDARD),
            )
        except NoFareFoundError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except FareConflictError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)

        return Response({
            "amount": str(result.amount),
            "currency": "MZN",
            "method": result.method,
            "route_code": route.code,
            "origin": origin.name if origin else None,
            "destination": destination.name if destination else None,
        })
