from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.core.permissions import HasCapabilities
from apps.core.viewsets import BaseModelViewSet
from apps.leads.api.serializers import ServiceRequestCreateSerializer, ServiceRequestSerializer
from apps.leads.models import ServiceRequest


class ServiceRequestThrottle(AnonRateThrottle):
    scope = "service-request"


class PublicServiceRequestView(APIView):
    """Formulario de pedido de contacto da landing."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ServiceRequestThrottle]

    def post(self, request):
        serializer = ServiceRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lead = serializer.save(source=request.data.get("source") or "landing")

        # Avisa a equipa comercial na hora — um lead que espera esfria.
        target = str(getattr(settings, "SALES_NOTIFY_PHONE", "") or "").strip()
        if target:
            try:
                from apps.sms.services.sender import send_sms

                send_sms(
                    target,
                    f"BusUp: novo pedido de contacto de {lead.name}"
                    f"{f' ({lead.organization})' if lead.organization else ''} - {lead.phone}",
                    purpose="LEAD_NOTIFICATION",
                )
            except Exception:
                pass  # o lead ja esta gravado; a notificacao e best-effort

        return Response(
            {"detail": "Pedido recebido. A nossa equipa entra em contacto."},
            status=status.HTTP_201_CREATED,
        )


class ServiceRequestViewSet(BaseModelViewSet):
    queryset = ServiceRequest.all_objects.all()
    serializer_class = ServiceRequestSerializer
    http_method_names = ["get", "patch", "head", "options"]
    required_capabilities_by_action = {
        "list": ("passengers.read",),
        "retrieve": ("passengers.read",),
        "partial_update": ("passengers.manage",),
    }
    permission_classes = [IsAuthenticated, HasCapabilities]
