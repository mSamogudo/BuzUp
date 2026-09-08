from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.branding.api.serializers import BrandingSettingsSerializer
from apps.branding.models import BrandingSettings
from apps.core.permissions.base import has_capabilities


class BrandingView(APIView):
    """GET publico (apps/login carregam a marca ao arrancar); PATCH exige a
    capacidade ``settings.manage``. Aceita multipart para upload dos logos."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request):
        obj = BrandingSettings.load()
        data = BrandingSettingsSerializer(obj, context={"request": request}).data
        # O botao "Cartao" na compra publica so aparece quando ha operador de
        # cartoes configurado. Nao e da marca, e do ambiente — mas e aqui que
        # a pagina de compra vai buscar o que precisa de saber antes de mostrar
        # seja o que for, e uma chamada a mais so para isto era pior.
        from apps.payments.services.card_gateway import _config as _dpo

        data["card_payments_enabled"] = _dpo().configured
        return Response(data)

    def patch(self, request):
        if not has_capabilities(request.user, ("settings.manage",)):
            return Response(
                {"detail": "Sem permissao para alterar a marca."},
                status=status.HTTP_403_FORBIDDEN,
            )
        obj = BrandingSettings.load()
        serializer = BrandingSettingsSerializer(
            obj, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
