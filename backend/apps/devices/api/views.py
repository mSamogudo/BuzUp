from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.app_releases.models import AppRelease
from apps.core.permissions import HasCapabilities
from apps.core.viewsets import BaseModelViewSet
from apps.devices.api.serializers import (
    DeviceActivationRequestSerializer,
    DeviceApproveSerializer,
    DeviceConfigurationSerializer,
    DeviceRejectSerializer,
    DeviceSerializer,
    HeartbeatSerializer,
    SelfOnboardSerializer,
)
from apps.devices.models import Device, DeviceActivationRequest


class DeviceViewSet(BaseModelViewSet):
    queryset = Device.all_objects.select_related("assigned_agent").all()
    serializer_class = DeviceSerializer
    http_method_names = ["get", "head", "options"]
    required_capabilities_by_action = {
        "list": ("devices.read",),
        "retrieve": ("devices.read",),
    }


class DeviceActivationRequestViewSet(BaseModelViewSet):
    queryset = DeviceActivationRequest.all_objects.select_related("device", "reviewed_by").all()
    serializer_class = DeviceActivationRequestSerializer
    http_method_names = ["get", "head", "options"]
    required_capabilities_by_action = {
        "list": ("devices.read",),
        "retrieve": ("devices.read",),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        req_status = self.request.query_params.get("status")
        if req_status:
            qs = qs.filter(status=req_status)
        return qs


class SelfOnboardView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = SelfOnboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        existing = Device.objects.filter(serial_number=data["serial_number"]).first()
        if existing:
            if existing.status in (Device.Status.REJECTED, Device.Status.BLOCKED):
                return Response(
                    {"detail": "Dispositivo rejeitado ou bloqueado. Contacte o administrador."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if existing.status == Device.Status.ACTIVE:
                return Response({
                    "activation_code": existing.activation_code,
                    "status": existing.status,
                })

            return Response({
                "activation_code": existing.activation_code,
                "status": existing.status,
            })

        activation_code = Device.generate_activation_code()
        device = Device.objects.create(
            serial_number=data["serial_number"],
            device_type=data["device_type"],
            model_name=data.get("model_name", ""),
            manufacturer=data.get("manufacturer", ""),
            imei=data.get("imei", ""),
            android_id=data.get("android_id", ""),
            capabilities=data.get("capabilities", []),
            app_version=data.get("app_version", ""),
            activation_code=activation_code,
            status=Device.Status.SELF_ONBOARDED,
        )

        DeviceActivationRequest.objects.create(
            device=device,
            activation_code=activation_code,
            requested_serial_number=data["serial_number"],
            requested_model=data.get("model_name", ""),
            requested_manufacturer=data.get("manufacturer", ""),
            requested_imei=data.get("imei", ""),
            requested_android_id=data.get("android_id", ""),
            requested_capabilities=data.get("capabilities", []),
            app_version=data.get("app_version", ""),
        )

        return Response({
            "activation_code": activation_code,
            "status": device.status,
        }, status=status.HTTP_201_CREATED)


class ActivationStatusView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, activation_code):
        try:
            device = Device.objects.get(activation_code=activation_code)
        except Device.DoesNotExist:
            return Response({"detail": "Codigo nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        data = {
            "activation_code": device.activation_code,
            "status": device.status,
        }
        if device.status == Device.Status.ACTIVE:
            data["configuration"] = device.configuration
        return Response(data)


class DeviceApproveView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("devices.manage",)

    def post(self, request, pk):
        try:
            device = Device.objects.get(pk=pk)
        except Device.DoesNotExist:
            return Response({"detail": "Dispositivo nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if device.status not in (Device.Status.SELF_ONBOARDED, Device.Status.PENDING_ACTIVATION, Device.Status.PENDING_CONFIGURATION):
            return Response({"detail": f"Dispositivo em estado {device.status}, nao pode ser aprovado."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DeviceApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        device.status = Device.Status.ACTIVE
        device.activated_at = timezone.now()
        if data.get("capabilities"):
            device.capabilities = data["capabilities"]
        if data.get("configuration"):
            device.configuration = data["configuration"]
        if data.get("assigned_agent_id"):
            device.assigned_agent_id = data["assigned_agent_id"]
        device.save(update_fields=[
            "status", "activated_at", "capabilities", "configuration",
            "assigned_agent_id", "updated_at",
        ])

        pending = device.activation_requests.filter(status=DeviceActivationRequest.Status.PENDING).first()
        if pending:
            pending.status = DeviceActivationRequest.Status.APPROVED
            pending.reviewed_by = request.user
            pending.reviewed_at = timezone.now()
            pending.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])

        return Response(DeviceSerializer(device).data)


class DeviceAllocateAgentView(APIView):
    """Admin allocates a self-onboarded POS to an agent.

    Status moves to PENDING_ACTIVATION. The device only becomes ACTIVE after
    the agent enters the activation_code on the POS terminal.
    """
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("devices.manage",)

    def post(self, request, pk):
        try:
            device = Device.objects.get(pk=pk)
        except Device.DoesNotExist:
            return Response({"detail": "Dispositivo nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if device.status == Device.Status.BLOCKED:
            return Response({"detail": "Dispositivo bloqueado."}, status=status.HTTP_400_BAD_REQUEST)

        agent_user_id = request.data.get("agent_user_id") or request.data.get("assigned_agent_id")
        if not agent_user_id:
            return Response({"detail": "Forneca agent_user_id."}, status=status.HTTP_400_BAD_REQUEST)

        from apps.trips.models import Agent as AgentModel
        agent = AgentModel.objects.filter(user_id=agent_user_id, status=AgentModel.Status.ACTIVE).select_related("user").first()
        if not agent or not agent.user:
            return Response({"detail": "Agente nao encontrado ou inactivo."}, status=status.HTTP_404_NOT_FOUND)

        # Rotate the activation code so each allocation produces a fresh
        # single-use code (admin-driven generation).
        for _ in range(5):
            new_code = Device.generate_activation_code()
            if not Device.objects.filter(activation_code=new_code).exclude(pk=device.pk).exists():
                device.activation_code = new_code
                break

        device.assigned_agent = agent.user
        if device.status in (Device.Status.SELF_ONBOARDED, Device.Status.PENDING_CONFIGURATION):
            device.status = Device.Status.PENDING_ACTIVATION
        device.save(update_fields=["assigned_agent", "activation_code", "status", "updated_at"])

        return Response({
            "id": device.id,
            "serial_number": device.serial_number,
            "status": device.status,
            "activation_code": device.activation_code,
            "agent": {"id": agent.id, "name": agent.full_name, "phone": agent.phone},
        })


class DeviceRegenerateActivationCodeView(APIView):
    """Admin generates a fresh activation code (security rotation)."""
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("devices.manage",)

    def post(self, request, pk):
        try:
            device = Device.objects.get(pk=pk)
        except Device.DoesNotExist:
            return Response({"detail": "Dispositivo nao encontrado."}, status=status.HTTP_404_NOT_FOUND)
        if device.status == Device.Status.BLOCKED:
            return Response({"detail": "Dispositivo bloqueado."}, status=status.HTTP_400_BAD_REQUEST)

        for _ in range(5):
            new_code = Device.generate_activation_code()
            if not Device.objects.filter(activation_code=new_code).exclude(pk=device.pk).exists():
                device.activation_code = new_code
                break

        # Rotating the code revokes any prior activation: device must re-enter the new code.
        if device.status == Device.Status.ACTIVE:
            device.status = Device.Status.PENDING_ACTIVATION
            device.activated_at = None
        device.save(update_fields=["activation_code", "status", "activated_at", "updated_at"])
        return Response({
            "id": device.id,
            "serial_number": device.serial_number,
            "status": device.status,
            "activation_code": device.activation_code,
        })


class DeviceRejectView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("devices.manage",)

    def post(self, request, pk):
        try:
            device = Device.objects.get(pk=pk)
        except Device.DoesNotExist:
            return Response({"detail": "Dispositivo nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        serializer = DeviceRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device.status = Device.Status.REJECTED
        device.save(update_fields=["status", "updated_at"])

        pending = device.activation_requests.filter(status=DeviceActivationRequest.Status.PENDING).first()
        if pending:
            pending.status = DeviceActivationRequest.Status.REJECTED
            pending.reviewed_by = request.user
            pending.reviewed_at = timezone.now()
            pending.rejection_reason = serializer.validated_data.get("rejection_reason", "")
            pending.save(update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at"])

        return Response(DeviceSerializer(device).data)


class DeviceConfigurationView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("devices.manage",)

    def patch(self, request, pk):
        try:
            device = Device.objects.get(pk=pk)
        except Device.DoesNotExist:
            return Response({"detail": "Dispositivo nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        serializer = DeviceConfigurationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        update_fields = ["updated_at"]
        if "configuration" in data:
            device.configuration = data["configuration"]
            update_fields.append("configuration")
        if "capabilities" in data:
            device.capabilities = data["capabilities"]
            update_fields.append("capabilities")
        if "assigned_agent_id" in data:
            device.assigned_agent_id = data["assigned_agent_id"]
            update_fields.append("assigned_agent_id")

        device.save(update_fields=update_fields)
        return Response(DeviceSerializer(device).data)


class DeviceHeartbeatView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = HeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            device = Device.objects.get(serial_number=data["serial_number"])
        except Device.DoesNotExist:
            return Response({"detail": "Dispositivo nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        device.last_seen_at = timezone.now()
        update_fields = ["last_seen_at", "updated_at"]
        if data.get("app_version"):
            device.app_version = data["app_version"]
            update_fields.append("app_version")
        if data.get("app_version_code"):
            device.app_version_code = data["app_version_code"]
            update_fields.append("app_version_code")
        device.save(update_fields=update_fields)

        response = {"status": device.status}

        pending_release = AppRelease.objects.filter(
            app_type=AppRelease.AppType.POS,
            status=AppRelease.Status.PUBLISHED,
            version_code__gt=device.app_version_code,
        ).order_by("-version_code").first()

        if pending_release:
            response["update_available"] = {
                "version_name": pending_release.version_name,
                "version_code": pending_release.version_code,
                "is_mandatory": pending_release.is_mandatory,
                "release_notes": pending_release.release_notes,
                "download_url": pending_release.apk_url or "",
                "checksum": pending_release.checksum,
            }

        return Response(response)


class DeviceLocationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serial = request.data.get("serial_number", "")
        lat = request.data.get("latitude")
        lng = request.data.get("longitude")
        speed = request.data.get("speed")
        heading = request.data.get("heading")

        if not serial or lat is None or lng is None:
            return Response({"detail": "serial_number, latitude, longitude obrigatorios."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = Device.objects.get(serial_number=serial)
        except Device.DoesNotExist:
            return Response({"detail": "Dispositivo nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        device.last_latitude = lat
        device.last_longitude = lng
        device.last_speed = speed
        device.last_heading = heading
        device.last_location_at = timezone.now()
        device.last_seen_at = timezone.now()
        device.save(update_fields=["last_latitude", "last_longitude", "last_speed", "last_heading", "last_location_at", "last_seen_at", "updated_at"])

        return Response({"status": "ok"})
