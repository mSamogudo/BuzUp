from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import HasCapabilities
from apps.core.viewsets import BaseModelViewSet
from apps.packages.api.serializers import (
    PackageCreateSerializer,
    PackageSerializer,
    PassengerPackageSerializer,
    SubscribeSerializer,
    TopupPackageSerializer,
)
from apps.packages.models import Package, PackageRoute, PassengerPackage
from apps.packages.services import PackageError, subscribe_passenger, topup_package
from apps.passengers.models import PassengerAccount
from apps.wallets.services import InsufficientBalanceError

from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response


class PackageViewSet(BaseModelViewSet):
    queryset = Package.all_objects.prefetch_related("routes__route").all()
    serializer_class = PackageSerializer
    required_capabilities_by_action = {
        "list": ("fares.read",),
        "retrieve": ("fares.read",),
        "create": ("fares.manage",),
        "update": ("fares.manage",),
        "partial_update": ("fares.manage",),
        "destroy": ("fares.manage",),
    }

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return PackageCreateSerializer
        return PackageSerializer

    def perform_create(self, serializer):
        route_ids = serializer.validated_data.pop("route_ids", [])
        pkg = serializer.save()
        for rid in route_ids:
            PackageRoute.objects.create(package=pkg, route_id=rid)

    def perform_update(self, serializer):
        route_ids = serializer.validated_data.pop("route_ids", None)
        pkg = serializer.save()
        if route_ids is not None:
            pkg.routes.all().delete()
            for rid in route_ids:
                PackageRoute.objects.create(package=pkg, route_id=rid)


class PassengerPackageViewSet(BaseModelViewSet):
    queryset = PassengerPackage.all_objects.select_related(
        "passenger_account", "package",
    ).all()
    serializer_class = PassengerPackageSerializer
    http_method_names = ["get", "head", "options"]
    required_capabilities_by_action = {
        "list": ("passengers.read",),
        "retrieve": ("passengers.read",),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        passenger_id = self.request.query_params.get("passenger")
        if passenger_id:
            qs = qs.filter(passenger_account_id=passenger_id)
        pkg_status = self.request.query_params.get("status")
        if pkg_status:
            qs = qs.filter(status=pkg_status)
        return qs


class SubscribeView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("passengers.read",)

    def post(self, request):
        serializer = SubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            passenger = PassengerAccount.objects.get(pk=data["passenger_id"])
        except PassengerAccount.DoesNotExist:
            return Response({"detail": "Passageiro nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        try:
            package = Package.objects.get(pk=data["package_id"])
        except Package.DoesNotExist:
            return Response({"detail": "Pacote nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        try:
            sub = subscribe_passenger(passenger, package, pay_from_wallet=data["pay_from_wallet"])
        except (PackageError, InsufficientBalanceError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PassengerPackageSerializer(sub).data, status=status.HTTP_201_CREATED)


class TopupPackageView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("wallets.manage",)

    def post(self, request):
        serializer = TopupPackageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            sub = PassengerPackage.objects.get(pk=data["subscription_id"])
        except PassengerPackage.DoesNotExist:
            return Response({"detail": "Subscricao nao encontrada."}, status=status.HTTP_404_NOT_FOUND)

        try:
            sub = topup_package(sub, data["amount"])
        except PackageError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PassengerPackageSerializer(sub).data)
