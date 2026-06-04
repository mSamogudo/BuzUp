import io

import qrcode
from django.http import HttpResponse as DjangoHttpResponse
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.cards.api.serializers import CardAssignSerializer, CardLookupSerializer, CardReplaceSerializer, CardSerializer
from apps.cards.models import Card
from apps.cards.services import activate_card, assign_card_to_passenger, block_card, replace_card, CardError
from apps.core.permissions import HasCapabilities
from apps.core.viewsets import BaseModelViewSet
from apps.passengers.models import PassengerAccount


class CardViewSet(BaseModelViewSet):
    queryset = Card.all_objects.select_related("passenger_account", "wallet").all()
    serializer_class = CardSerializer
    http_method_names = ["get", "head", "options"]
    required_capabilities_by_action = {
        "list": ("cards.read",),
        "retrieve": ("cards.read",),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        card_type = self.request.query_params.get("type")
        if card_type:
            qs = qs.filter(card_type=card_type)
        card_status = self.request.query_params.get("status")
        if card_status:
            qs = qs.filter(status=card_status)
        passenger_id = self.request.query_params.get("passenger")
        if passenger_id:
            try:
                qs = qs.filter(passenger_account_id=int(passenger_id))
            except (TypeError, ValueError):
                pass
        return qs


class CardLookupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CardLookupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            card = Card.objects.select_related("passenger_account", "wallet").get(card_uid=serializer.validated_data["card_uid"])
        except Card.DoesNotExist:
            return Response({"detail": "Cartao nao encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return Response(CardSerializer(card).data)


class _QueryTokenJWTAuthentication(JWTAuthentication):
    """Accept JWT in ?token=... so <img src=...> tags work for QR PNGs."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            return result
        token = request.query_params.get("token") if hasattr(request, "query_params") else request.GET.get("token")
        if not token:
            return None
        validated = self.get_validated_token(token)
        return (self.get_user(validated), validated)


class CardQrPngView(APIView):
    """Render the QR code of a digital card as a PNG.

    Authorisation:
      - admin staff with `cards.read` capability, OR
      - the passenger themselves (PassengerAccount.user == request.user)
    The token may come from the standard `Authorization: Bearer` header OR
    from `?token=...` so the image can be embedded via <img src>.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, _QueryTokenJWTAuthentication]

    def get(self, request, card_id: int):
        try:
            card = Card.objects.select_related("passenger_account").get(pk=card_id)
        except Card.DoesNotExist:
            return Response({"detail": "Cartao nao encontrado."}, status=404)
        if card.card_type != Card.CardType.DIGITAL or not card.qr_token:
            return Response({"detail": "Apenas cartoes digitais tem QR."}, status=400)

        # Allow staff/superuser; or the actual passenger (matched by phone).
        user = request.user
        if not (user.is_staff or user.is_superuser):
            owner = False
            pa = card.passenger_account
            user_phone = getattr(user, "phone", "") or ""
            if pa is not None and user_phone and pa.phone_number == user_phone:
                owner = True
            if not owner:
                return Response({"detail": "Sem permissao."}, status=403)

        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=12,
            border=2,
        )
        qr.add_data(card.qr_token)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        resp = DjangoHttpResponse(buf.getvalue(), content_type="image/png")
        resp["Cache-Control"] = "private, no-store"
        return resp


class CardActivateView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("cards.manage",)

    def post(self, request):
        serializer = CardLookupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            card = Card.objects.get(card_uid=serializer.validated_data["card_uid"])
        except Card.DoesNotExist:
            return Response({"detail": "Cartao nao encontrado."}, status=status.HTTP_404_NOT_FOUND)
        try:
            card = activate_card(card)
        except CardError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        card = Card.objects.select_related("passenger_account", "wallet").get(pk=card.pk)
        return Response(CardSerializer(card).data)


class CardBlockView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("cards.manage",)

    def post(self, request):
        serializer = CardLookupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            card = Card.objects.get(card_uid=serializer.validated_data["card_uid"])
        except Card.DoesNotExist:
            return Response({"detail": "Cartao nao encontrado."}, status=status.HTTP_404_NOT_FOUND)
        try:
            card = block_card(card)
        except CardError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CardSerializer(card).data)


class CardAssignView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("cards.manage",)

    def post(self, request):
        serializer = CardAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            card = Card.objects.get(card_uid=serializer.validated_data["card_uid"])
        except Card.DoesNotExist:
            return Response({"detail": "Cartao nao encontrado."}, status=status.HTTP_404_NOT_FOUND)
        try:
            passenger = PassengerAccount.objects.get(pk=serializer.validated_data["passenger_id"])
        except PassengerAccount.DoesNotExist:
            return Response({"detail": "Passageiro nao encontrado."}, status=status.HTTP_404_NOT_FOUND)
        try:
            card = assign_card_to_passenger(card, passenger)
        except CardError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        card = Card.objects.select_related("passenger_account", "wallet").get(pk=card.pk)
        return Response(CardSerializer(card).data)


class CardReplaceView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("cards.manage",)

    def post(self, request):
        serializer = CardReplaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            old_card = Card.objects.get(card_uid=serializer.validated_data["old_card_uid"])
        except Card.DoesNotExist:
            return Response({"detail": "Cartao antigo nao encontrado."}, status=status.HTTP_404_NOT_FOUND)
        try:
            new_card = Card.objects.get(card_uid=serializer.validated_data["new_card_uid"])
        except Card.DoesNotExist:
            return Response({"detail": "Cartao novo nao encontrado."}, status=status.HTTP_404_NOT_FOUND)
        try:
            new_card = replace_card(old_card, new_card)
        except CardError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        new_card = Card.objects.select_related("passenger_account", "wallet").get(pk=new_card.pk)
        return Response(CardSerializer(new_card).data)
