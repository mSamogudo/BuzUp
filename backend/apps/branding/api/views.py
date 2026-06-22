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
        return Response(BrandingSettingsSerializer(obj, context={"request": request}).data)

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
