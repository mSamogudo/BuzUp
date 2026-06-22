from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.viewsets import BaseModelViewSet
from apps.passengers.api.serializers import (
    PassengerAccountCreateAccessSerializer,
    PassengerAccountCreateSerializer,
    PassengerAccountDetailSerializer,
    PassengerAccountSerializer,
)
from apps.passengers.models import PassengerAccount
from apps.passengers.services import ensure_passenger_access_account
from apps.wallets.models import Wallet


class PassengerAccountViewSet(BaseModelViewSet):
    queryset = PassengerAccount.all_objects.all()
    serializer_class = PassengerAccountSerializer
    required_capabilities_by_action = {
        "list": ("passengers.read",),
        "retrieve": ("passengers.read",),
        "create": ("passengers.manage",),
        "update": ("passengers.manage",),
        "partial_update": ("passengers.manage",),
        "destroy": ("passengers.manage",),
        "block": ("passengers.manage",),
        "activate": ("passengers.manage",),
        "create_account": ("passengers.manage",),
    }

    def get_serializer_class(self):
        if self.action == "create":
            return PassengerAccountCreateSerializer
        if self.action == "retrieve":
            return PassengerAccountDetailSerializer
        return PassengerAccountSerializer

    def perform_create(self, serializer):
        create_account = serializer.validated_data.pop("create_account", False)
        notify_by_sms = serializer.validated_data.pop("notify_by_sms", True)
        passenger = serializer.save()
        Wallet.objects.get_or_create(passenger_account=passenger)
        if create_account:
            ensure_passenger_access_account(passenger, notify_by_sms=notify_by_sms)

    @action(detail=True, methods=["post"])
    def block(self, request, *args, **kwargs):
        passenger = self.get_object()
        passenger.status = PassengerAccount.Status.BLOCKED
        passenger.save(update_fields=["status", "updated_at"])
        if hasattr(passenger, "wallet"):
            passenger.wallet.status = Wallet.Status.BLOCKED
            passenger.wallet.save(update_fields=["status", "updated_at"])
        return Response(PassengerAccountSerializer(passenger).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, *args, **kwargs):
        passenger = self.get_object()
        passenger.status = PassengerAccount.Status.ACTIVE
        passenger.save(update_fields=["status", "updated_at"])
        if hasattr(passenger, "wallet"):
            passenger.wallet.status = Wallet.Status.ACTIVE
            passenger.wallet.save(update_fields=["status", "updated_at"])
        return Response(PassengerAccountSerializer(passenger).data)

    @action(detail=True, methods=["post"], url_path="create-account")
    def create_account(self, request, *args, **kwargs):
        passenger = self.get_object()
        serializer = PassengerAccountCreateAccessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user, wallet, digital_card = ensure_passenger_access_account(
                passenger,
                notify_by_sms=serializer.validated_data["notify_by_sms"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "detail": "Conta de passageiro criada com sucesso.",
            "username": user.username,
            "wallet_id": wallet.id,
            "digital_card_number": digital_card.card_number,
        })
