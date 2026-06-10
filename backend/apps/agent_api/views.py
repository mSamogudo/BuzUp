"""All /api/agent/* endpoints consumed by the Flutter POS app.

Endpoints provided:
    POST   /api/agent/auth/login/                   -> issue JWT for agent
    POST   /api/agent/auth/logout/                  -> blacklist refresh token
    GET    /api/agent/me/                           -> agent profile + session + device

    POST   /api/agent/devices/register/             -> POS device self-register
    GET    /api/agent/devices/current/              -> device currently linked to agent
    POST   /api/agent/devices/heartbeat/            -> heartbeat + location update

    GET    /api/agent/trips/                        -> available trips for selling
    GET    /api/agent/trips/<id>/                   -> trip detail
    POST   /api/agent/trips/<id>/fare/              -> compute fare for trip+stops

    POST   /api/agent/sales/                        -> create sale + initiate payment
    GET    /api/agent/payments/<ref>/status/        -> poll payment status
    GET    /api/agent/sales/history/                -> sales made by this agent
    GET    /api/agent/sales/summary/                -> daily summary

    GET    /api/agent/tickets/                      -> tickets sold by this agent
    GET    /api/agent/tickets/<ref>/                -> ticket detail
    GET    /api/agent/tickets/<ref>/pdf/            -> ticket pdf
    POST   /api/agent/tickets/verify/               -> validate a QR token
    POST   /api/agent/tickets/<ref>/mark-used/      -> mark ticket used
"""
from __future__ import annotations

import hashlib
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.http import HttpResponse as DjangoHttpResponse
from django.conf import settings as django_settings
from django.utils import timezone
from rest_framework import status as drf_status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.services import audit, client_ip
from apps.agent_api.permissions import IsActiveAgent, get_agent_profile, get_authorized_device
from apps.agent_api.sales import SaleError, create_pos_sale, request_payment
from apps.agent_api.serializers import (
    AgentDeviceHeartbeatSerializer,
    AgentDeviceRegisterSerializer,
    AgentFareSerializer,
    AgentLoginSerializer,
    AgentSaleSerializer,
    AgentTicketVerifySerializer,
)
from apps.devices.models import Device
from apps.fares.services import NoFareFoundError, quote_fare
from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.guest_checkouts.ticket_pdf import generate_tickets_pdf
from apps.payments.models import PaymentIntent
from apps.payments.services.processing import confirm_payment_immediately
from apps.pos.models import PosSession
from apps.routes.models import Route, Stop
from apps.trips.models import Trip


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _mask_phone(phone: str) -> str:
    p = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(p) < 4:
        return p
    return f"***{p[-4:]}"


def _trip_payload(trip: Trip) -> dict:
    return {
        "id": trip.id,
        "uuid": str(trip.uuid),
        "route_code": trip.route.code,
        "route_name": trip.route.name,
        "vehicle": trip.vehicle.registration if trip.vehicle else "",
        "driver": trip.driver.full_name if trip.driver else "",
        "planned_departure_at": trip.planned_departure_at.isoformat() if trip.planned_departure_at else None,
        "status": trip.status,
    }


def _ticket_payload(tp: DigitalTravelPass) -> dict:
    return {
        "id": tp.id,
        "uuid": str(tp.uuid),
        "reference": tp.guest_checkout.reference if tp.guest_checkout else str(tp.uuid)[:12].upper(),
        "route_code": tp.route_code,
        "route_name": tp.route_name,
        "origin_stop": tp.origin_stop,
        "destination_stop": tp.destination_stop,
        "fare_amount": str(tp.fare_amount),
        "payer_phone_masked": _mask_phone(tp.payer_phone),
        "status": tp.status,
        "valid_from": tp.valid_from.isoformat() if tp.valid_from else None,
        "valid_until": tp.valid_until.isoformat() if tp.valid_until else None,
        "used_at": tp.used_at.isoformat() if tp.used_at else None,
        "token": tp.token,
        "trip_id": tp.trip_id,
    }


# ----------------------------------------------------------------------------
# Auth
# ----------------------------------------------------------------------------

class AgentLoginView(APIView):
    """Agent login by phone+OTP code (reuses OtpChallenge).

    For development convenience, when the agent has a usable password set,
    username/password is also accepted.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = AgentLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = None
        if data.get("password"):
            from django.contrib.auth import authenticate
            user = authenticate(request, username=data["username"], password=data["password"])
        elif data.get("phone") and data.get("otp_code"):
            from apps.users.models import OtpChallenge
            from apps.users.otp import OTP_MAX_ATTEMPTS, verify_otp_hash, normalize_otp_phone
            phone = normalize_otp_phone(data["phone"])
            challenge = OtpChallenge.objects.filter(
                uuid=data.get("challenge_id"),
                phone=phone,
                status=OtpChallenge.Status.PENDING,
            ).first()
            if not challenge or timezone.now() > challenge.expires_at:
                return Response({"detail": "Codigo invalido ou expirado."}, status=400)
            # Limite de tentativas: sem isto, o OTP de 6 digitos era brute-forcavel
            # dentro do TTL (ao contrario de OtpVerifyView, que ja o impunha).
            if challenge.attempts >= OTP_MAX_ATTEMPTS:
                challenge.status = OtpChallenge.Status.EXPIRED
                challenge.save(update_fields=["status", "updated_at"])
                return Response({"detail": "Tentativas excedidas."}, status=400)
            if not verify_otp_hash(data["otp_code"], challenge.code_hash):
                challenge.attempts += 1
                update_fields = ["attempts", "updated_at"]
                detail = "Codigo incorreto."
                if challenge.attempts >= OTP_MAX_ATTEMPTS:
                    challenge.status = OtpChallenge.Status.EXPIRED
                    update_fields.append("status")
                    detail = "Tentativas excedidas."
                challenge.save(update_fields=update_fields)
                return Response({"detail": detail}, status=400)
            challenge.status = OtpChallenge.Status.VERIFIED
            challenge.verified_at = timezone.now()
            challenge.save(update_fields=["status", "verified_at", "updated_at"])

            from apps.trips.models import Agent as AgentModel
            agent = AgentModel.objects.filter(phone=phone, status=AgentModel.Status.ACTIVE).select_related("user").first()
            user = agent.user if agent else None

        if not user or not user.is_active:
            return Response({"detail": "Credenciais invalidas."}, status=401)

        agent = get_agent_profile(user)
        if not agent:
            return Response({"detail": "Utilizador nao tem perfil de agente activo."}, status=403)

        # Optional: bind login to an active POS device
        serial = (request.data.get("device_serial") or "").strip()
        if serial:
            device = Device.objects.filter(serial_number=serial).first()
            if not device:
                return Response({"detail": "Dispositivo nao registado no sistema."}, status=403)
            if device.status != Device.Status.ACTIVE:
                return Response({"detail": "Dispositivo nao esta activo. Aguarde activacao pelo administrador.", "device_status": device.status}, status=403)
            if device.assigned_agent_id and device.assigned_agent_id != user.id:
                return Response({"detail": "Dispositivo nao esta alocado a este agente."}, status=403)

        refresh = RefreshToken.for_user(user)
        refresh["agent_id"] = agent.id
        refresh["phone"] = user.phone

        audit(
            "AGENT_LOGIN",
            actor=user,
            entity_type="agent", entity_id=str(agent.id),
            ip=client_ip(request),
            after={"username": user.username},
        )
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "agent_id": agent.id,
            "agent_name": agent.full_name,
        })


class AgentLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("refresh")
        if token:
            try:
                RefreshToken(token).blacklist()
            except Exception:
                pass
        audit("AGENT_LOGOUT", actor=request.user, ip=client_ip(request))
        return Response({"detail": "Sessao encerrada."})


class AgentMeView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def get(self, request):
        agent = get_agent_profile(request.user)
        device = Device.objects.filter(assigned_agent=request.user).exclude(status=Device.Status.BLOCKED).first()
        session = PosSession.objects.filter(agent=request.user, status=PosSession.Status.ACTIVE).select_related("device", "allocated_route").first()
        return Response({
            "agent": {
                "id": agent.id,
                "full_name": agent.full_name,
                "phone": agent.phone,
                "status": agent.status,
            },
            "user": {
                "username": request.user.username,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "email": request.user.email,
            },
            "device": {
                "id": device.id,
                "serial_number": device.serial_number,
                "device_type": device.device_type,
                "model_name": device.model_name,
                "status": device.status,
            } if device else None,
            "session": {
                "id": session.id,
                "opened_at": session.opened_at.isoformat(),
                "allocated_route_id": session.allocated_route_id,
                "allocated_route_code": session.allocated_route.code if session.allocated_route else "",
            } if session else None,
            "features": {
                # POS-level feature flags. The Flutter app uses these to hide
                # menus / icons that the user shouldn't be able to even reach.
                "card_capture": (
                    bool(getattr(django_settings, "ALLOW_AGENT_CARD_CAPTURE", False))
                    or request.user.is_staff
                    or request.user.is_superuser
                ),
            },
        })


# ----------------------------------------------------------------------------
# Devices
# ----------------------------------------------------------------------------

class PosDeviceSelfRegisterView(APIView):
    """POS self-onboarding. No auth required.

    Returns the device's activation_code which the admin will give to the
    agent to enter and unlock the app.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = AgentDeviceRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        serial = data["serial_number"].strip()

        # Use all_objects so a soft-deleted device with the same serial is
        # found and reused. The DB unique constraint on serial_number counts
        # soft-deleted rows, so a blind create() on a previously-deleted
        # serial would raise IntegrityError (500).
        device = Device.all_objects.filter(serial_number=serial).first()
        created = False
        if device is None:
            device = Device.objects.create(
                serial_number=serial,
                device_type=data.get("device_type") or Device.DeviceType.SUNMI_V2S_POS,
                model_name=data.get("model_name", ""),
                manufacturer=data.get("manufacturer", ""),
                imei=data.get("imei", ""),
                android_id=data.get("android_id", ""),
                capabilities=data.get("capabilities", []),
                app_version=data.get("app_version", ""),
                app_version_code=data.get("app_version_code", 0),
                status=Device.Status.SELF_ONBOARDED,
                activation_code=Device.generate_activation_code(),
                last_seen_at=timezone.now(),
            )
            created = True
        else:
            if device.status == Device.Status.BLOCKED:
                return Response({"detail": "Dispositivo bloqueado pelo administrador."}, status=403)
            update_fields = ["last_seen_at", "updated_at"]
            # A previously soft-deleted device re-onboarding: restore it and
            # reset to the self-onboarded state so the admin can re-approve.
            if device.deleted_at is not None:
                device.deleted_at = None
                device.status = Device.Status.SELF_ONBOARDED
                device.assigned_agent = None
                if not device.activation_code:
                    device.activation_code = Device.generate_activation_code()
                update_fields += ["deleted_at", "status", "assigned_agent", "activation_code"]
                created = True  # treat as a fresh onboard for audit + 201
            if data.get("app_version"):
                device.app_version = data["app_version"]
                update_fields.append("app_version")
            if data.get("app_version_code"):
                device.app_version_code = data["app_version_code"]
                update_fields.append("app_version_code")
            device.last_seen_at = timezone.now()
            device.save(update_fields=list(set(update_fields)))

        audit(
            "AGENT_DEVICE_SELF_ONBOARDED" if created else "AGENT_DEVICE_PING",
            entity_type="device", entity_id=str(device.id),
            ip=client_ip(request), device=serial,
            after={"serial": serial, "status": device.status},
        )
        # Note: activation_code is NEVER returned to the device. The admin
        # generates the code in the portal and hands it to the agent verbally
        # / by SMS. The device only knows whether it's awaiting activation.
        return Response({
            "id": device.id,
            "serial_number": device.serial_number,
            "status": device.status,
            "assigned_agent_id": device.assigned_agent_id,
            "created": created,
        }, status=201 if created else 200)


class PosDeviceStatusView(APIView):
    """Poll endpoint for the POS to check whether admin has approved + assigned an agent."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, serial_number: str):
        device = Device.objects.filter(serial_number=serial_number).select_related("assigned_agent").first()
        if not device:
            return Response({"detail": "Dispositivo nao registado."}, status=404)
        agent_profile = None
        if device.assigned_agent_id:
            from apps.trips.models import Agent as AgentModel
            agent_profile = AgentModel.objects.filter(user=device.assigned_agent).first()
        # activation_code is intentionally OMITTED — only visible to admin in portal.
        return Response({
            "serial_number": device.serial_number,
            "status": device.status,
            "is_active": device.status == Device.Status.ACTIVE,
            "has_agent": device.assigned_agent_id is not None,
            "agent_name": agent_profile.full_name if agent_profile else "",
            "activated_at": device.activated_at.isoformat() if device.activated_at else None,
        })


class PosDeviceActivateView(APIView):
    """Agent enters the activation code on the device after admin approval.

    Validates that:
      - Device is in SELF_ONBOARDED / PENDING_ACTIVATION status
      - Activation code matches
      - Device has an assigned_agent (admin already did the allocation)
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serial = (request.data.get("serial_number") or "").strip()
        code = (request.data.get("activation_code") or "").strip().upper()
        if not serial or not code:
            return Response({"detail": "serial_number e activation_code obrigatorios."}, status=400)

        device = Device.objects.filter(serial_number=serial).first()
        if not device:
            return Response({"detail": "Dispositivo nao registado."}, status=404)
        if device.status == Device.Status.BLOCKED:
            return Response({"detail": "Dispositivo bloqueado."}, status=403)
        if device.status == Device.Status.ACTIVE:
            return Response({"detail": "Dispositivo ja activo.", "status": device.status}, status=200)
        if device.activation_code != code:
            audit(
                "AGENT_DEVICE_ACTIVATION_FAILED",
                entity_type="device", entity_id=str(device.id),
                ip=client_ip(request), device=serial,
                after={"reason": "wrong_code"},
            )
            return Response({"detail": "Codigo de activacao incorrecto."}, status=400)
        if not device.assigned_agent_id:
            return Response({"detail": "Aguarde o administrador alocar o dispositivo a um agente."}, status=409)

        device.status = Device.Status.ACTIVE
        device.activated_at = timezone.now()
        device.last_seen_at = timezone.now()
        device.save(update_fields=["status", "activated_at", "last_seen_at", "updated_at"])

        audit(
            "AGENT_DEVICE_ACTIVATED",
            actor=device.assigned_agent,
            entity_type="device", entity_id=str(device.id),
            ip=client_ip(request), device=serial,
            after={"serial": serial, "agent_user_id": device.assigned_agent_id},
        )

        from apps.trips.models import Agent as AgentModel
        agent = AgentModel.objects.filter(user=device.assigned_agent).first()
        return Response({
            "serial_number": device.serial_number,
            "status": device.status,
            "agent_name": agent.full_name if agent else "",
            "agent_phone": agent.phone if agent else "",
            "activated_at": device.activated_at.isoformat(),
        })


class AgentCurrentDeviceView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def get(self, request):
        device = get_authorized_device(request.user)
        if not device:
            return Response({"detail": "Nenhum dispositivo activo associado."}, status=404)
        return Response({
            "id": device.id,
            "serial_number": device.serial_number,
            "device_type": device.device_type,
            "model_name": device.model_name,
            "manufacturer": device.manufacturer,
            "status": device.status,
            "app_version": device.app_version,
            "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
        })


class AgentDeviceHeartbeatView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request):
        serializer = AgentDeviceHeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        device = get_authorized_device(request.user, serial_number=data.get("serial_number"))
        if not device:
            return Response({"detail": "Dispositivo nao encontrado."}, status=404)
        if device.status == Device.Status.BLOCKED:
            return Response({"detail": "Dispositivo bloqueado."}, status=403)

        device.last_seen_at = timezone.now()
        if data.get("app_version"):
            device.app_version = data["app_version"]
        if data.get("latitude") is not None:
            device.last_latitude = data["latitude"]
            device.last_longitude = data.get("longitude")
            device.last_location_at = timezone.now()
        device.save(update_fields=[
            "last_seen_at", "last_latitude", "last_longitude", "last_location_at",
            "app_version", "updated_at",
        ])

        audit(
            "AGENT_DEVICE_HEARTBEAT",
            actor=request.user,
            entity_type="device", entity_id=str(device.id),
            device=device.serial_number,
        )
        return Response({"detail": "ok", "last_seen_at": device.last_seen_at.isoformat()})


# ----------------------------------------------------------------------------
# Trips
# ----------------------------------------------------------------------------

class AgentTripListView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def get(self, request):
        qs = Trip.objects.select_related("route", "vehicle", "driver").filter(
            status__in=[Trip.Status.BOARDING, Trip.Status.DEPARTED],
        )
        route_id = request.query_params.get("route")
        if route_id:
            qs = qs.filter(route_id=route_id)
        return Response([_trip_payload(t) for t in qs.order_by("planned_departure_at")[:50]])


class AgentTripDetailView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def get(self, request, trip_id: int):
        from apps.routes.models import RouteStop
        trip = Trip.objects.select_related("route", "vehicle", "driver").filter(pk=trip_id).first()
        if not trip:
            return Response({"detail": "Viagem nao encontrada."}, status=404)
        stops = list(
            RouteStop.objects.select_related("stop").filter(route=trip.route, stop__status="active")
            .order_by("direction", "sequence")
        )
        seen = {}
        for rs in stops:
            seen.setdefault(rs.stop_id, {"id": rs.stop_id, "code": rs.stop.code, "name": rs.stop.name})
        payload = _trip_payload(trip)
        payload["stops"] = list(seen.values())
        return Response(payload)


class AgentFareQuoteView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request, trip_id: int):
        serializer = AgentFareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        trip = Trip.objects.select_related("route").filter(pk=trip_id).first()
        if not trip:
            return Response({"detail": "Viagem nao encontrada."}, status=404)
        if trip.status not in [Trip.Status.BOARDING, Trip.Status.DEPARTED]:
            return Response({"detail": "Viagem nao esta em circulacao."}, status=400)

        origin = Stop.objects.filter(pk=data["origin_stop_id"]).first()
        destination = Stop.objects.filter(pk=data["destination_stop_id"]).first()
        if not origin or not destination:
            return Response({"detail": "Origem ou destino nao encontrados."}, status=400)

        try:
            q = quote_fare(route=trip.route, origin_stop=origin, destination_stop=destination)
        except NoFareFoundError as e:
            return Response({"detail": str(e)}, status=400)

        return Response({
            "trip_id": trip.id,
            "route_code": trip.route.code,
            "origin": origin.name,
            "destination": destination.name,
            "fare_amount": str(q.amount),
            "currency": "MZN",
            "method": q.method,
        })


# ----------------------------------------------------------------------------
# Sales / Payments
# ----------------------------------------------------------------------------

class AgentSaleCreateView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request):
        from apps.agent_api.sales import create_card_sale
        serializer = AgentSaleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        agent = get_agent_profile(request.user)
        device = get_authorized_device(request.user, serial_number=data.get("device_serial"))
        method = data.get("payment_method", "mobile_money")

        # Honour Idempotency-Key: if a sale with the same key was already
        # processed for this agent, return the existing record instead of
        # double-charging the wallet / opening a second M-Pesa request.
        idem = request.headers.get("Idempotency-Key", "").strip()
        if idem:
            existing_pi = PaymentIntent.objects.filter(
                idempotency_key=f"agent-idem-{request.user.id}-{idem}",
            ).select_related("guest_checkout").first()
            if existing_pi:
                egc = existing_pi.guest_checkout
                return Response({
                    "sale_reference": egc.reference if egc else "",
                    "payment": {
                        "status": existing_pi.status,
                        "reference": existing_pi.reference,
                        "provider": existing_pi.provider,
                        "duplicate": True,
                    },
                    "amount": str(existing_pi.amount),
                    "quantity": egc.quantity if egc else 0,
                    "status": egc.status if egc else "",
                    "duplicate": True,
                }, status=200)

        idem_full = f"agent-idem-{request.user.id}-{idem}" if idem else ""

        try:
            if method == "card":
                gc, pi, passes = create_card_sale(
                    agent=agent,
                    device=device,
                    trip_id=data.get("trip_id"),
                    route_id=data.get("route_id"),
                    origin_stop_id=data["origin_stop_id"],
                    destination_stop_id=data["destination_stop_id"],
                    card_uid=data.get("card_uid", ""),
                    qr_token=data.get("qr_token", ""),
                    quantity=data.get("quantity", 1),
                    idempotency_key=idem_full,
                )
                # Card payment is confirmed synchronously; return final state.
                return Response({
                    "sale_reference": gc.reference,
                    "payment": {
                        "status": pi.status,
                        "reference": pi.reference,
                        "provider": pi.provider,
                        "detail": "Pagamento via cartao confirmado.",
                    },
                    "amount": str(gc.total_amount),
                    "quantity": gc.quantity,
                    "status": gc.status,
                    "tickets": [_ticket_payload(tp) for tp in passes],
                }, status=201)

            gc, pi = create_pos_sale(
                agent=agent,
                device=device,
                trip_id=data.get("trip_id"),
                route_id=data.get("route_id"),
                origin_stop_id=data["origin_stop_id"],
                destination_stop_id=data["destination_stop_id"],
                passenger_phone=data["passenger_phone"],
                quantity=data.get("quantity", 1),
                idempotency_key=idem_full,
            )
        except SaleError as e:
            return Response({"detail": str(e)}, status=400)

        if data.get("auto_request_payment", True):
            payment_status = request_payment(gc, pi)
        else:
            payment_status = {"status": pi.status, "reference": pi.reference}

        return Response({
            "sale_reference": gc.reference,
            "payment": payment_status,
            "amount": str(gc.total_amount),
            "quantity": gc.quantity,
            "status": gc.status,
        }, status=201)


class AgentPaymentStatusView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def get(self, request, payment_reference: str):
        pi = (
            PaymentIntent.objects
            .select_related("guest_checkout", "created_by")
            .filter(reference=payment_reference)
            .first()
        )
        if not pi:
            return Response({"detail": "Pagamento nao encontrado."}, status=404)
        # Defense in depth: an agent may see this payment only if ANY of these
        # ownership signals points back to them. Relying solely on `metadata`
        # would let a row with empty metadata be read by any agent.
        meta_owner = (pi.metadata or {}).get("agent_user_id") == request.user.id
        creator_owner = pi.created_by_id == request.user.id
        sale_owner = False
        if pi.guest_checkout_id:
            sale_owner = PaymentIntent.objects.filter(
                guest_checkout_id=pi.guest_checkout_id,
                metadata__agent_user_id=request.user.id,
            ).exists()
        if not (meta_owner or creator_owner or sale_owner):
            audit(
                "PERMISSION_DENIED",
                actor=request.user,
                entity_type="payment_intent", entity_id=str(pi.id),
                after={"reason": "not_owner", "endpoint": "payment_status"},
            )
            return Response({"detail": "Sem permissao."}, status=403)

        gc = pi.guest_checkout
        passes = list(gc.travel_passes.all()) if gc else []
        return Response({
            "payment_reference": pi.reference,
            "status": pi.status,
            "amount": str(pi.amount),
            "provider": pi.provider,
            "confirmed_at": pi.confirmed_at.isoformat() if pi.confirmed_at else None,
            "sale_reference": gc.reference if gc else "",
            "sale_status": gc.status if gc else "",
            "tickets": [_ticket_payload(tp) for tp in passes],
        })


class AgentSalesHistoryView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def get(self, request):
        # History covers BOTH sales (guest_travel_pass) and top-ups
        # (pos_card_topup) for the agent. Front-end uses `kind` to render.
        kind = request.query_params.get("kind")  # optional filter
        purposes = [
            PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
            PaymentIntent.Purpose.POS_CARD_TOPUP,
        ]
        if kind == "sale":
            purposes = [PaymentIntent.Purpose.GUEST_TRAVEL_PASS]
        elif kind == "topup":
            purposes = [PaymentIntent.Purpose.POS_CARD_TOPUP]

        qs = PaymentIntent.objects.filter(
            metadata__agent_user_id=request.user.id,
            purpose__in=purposes,
        ).order_by("-created_at").select_related("guest_checkout")

        since = request.query_params.get("since")
        if since:
            from django.utils.dateparse import parse_date
            d = parse_date(since)
            if d:
                qs = qs.filter(created_at__date__gte=d)

        results = []
        for pi in qs[:200]:
            gc = pi.guest_checkout
            row_kind = "sale" if pi.purpose == PaymentIntent.Purpose.GUEST_TRAVEL_PASS else "topup"
            label = ""
            if row_kind == "topup":
                meta = pi.metadata or {}
                if meta.get("kind") == "package":
                    label = f"Pacote: {meta.get('package_name', '')}"
                else:
                    label = "Recarga de carteira"
            results.append({
                "kind": row_kind,
                "payment_reference": pi.reference,
                "sale_reference": gc.reference if gc else "",
                "status": pi.status,
                "amount": str(pi.amount),
                "quantity": gc.quantity if gc else 0,
                "route_code": gc.route_code if gc else "",
                "origin": gc.origin_stop if gc else "",
                "destination": gc.destination_stop if gc else "",
                "payer_phone_masked": _mask_phone(pi.payer_phone),
                "label": label,
                "provider": pi.provider,
                "channel": pi.channel,
                "created_at": pi.created_at.isoformat(),
            })
        return Response({"count": len(results), "results": results})


class AgentDayCloseView(APIView):
    """Returns the full daily breakdown and (POST) closes the agent session.

    GET  /api/agent/day-close/        -> preview of today's activity
    POST /api/agent/day-close/        -> closes any active PosSession + audits the closure
    """
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def get(self, request):
        return Response(self._build_payload(request.user))

    def post(self, request):
        from datetime import datetime as _dt
        from apps.agent_api.models import AgentDayClose
        from apps.trips.models import Agent as AgentModel

        payload = self._build_payload(request.user)

        sessions = PosSession.objects.filter(agent=request.user, status=PosSession.Status.ACTIVE)
        closed = 0
        for s in sessions:
            s.status = PosSession.Status.CLOSED
            s.closed_at = timezone.now()
            s.metadata = {**(s.metadata or {}), "day_close": payload}
            s.save(update_fields=["status", "closed_at", "metadata", "updated_at"])
            closed += 1

        totals = payload["totals"]
        record = AgentDayClose.objects.create(
            agent_user=request.user,
            agent_profile=AgentModel.objects.filter(user=request.user).first(),
            date=_dt.fromisoformat(payload["date"]).date(),
            total_revenue=Decimal(str(totals.get("revenue", "0.00"))),
            sales_total=Decimal(str(totals.get("sales", "0.00"))),
            topups_total=Decimal(str(totals.get("topups", "0.00"))),
            validations_revenue=Decimal(str(totals.get("validations_revenue", "0.00"))),
            tickets_count=int(totals.get("tickets", 0) or 0),
            validations_count=int(totals.get("validations", 0) or 0),
            confirmed_count=int(totals.get("confirmed_count", 0) or 0),
            pending_count=int(totals.get("pending_count", 0) or 0),
            failed_count=int(totals.get("failed_count", 0) or 0),
            sessions_closed=closed,
            payload=payload,
        )
        audit(
            "AGENT_DAY_CLOSED",
            actor=request.user,
            entity_type="agent_day_close", entity_id=str(record.id),
            after={
                "total_revenue": str(record.total_revenue),
                "tickets": record.tickets_count,
                "validations": record.validations_count,
                "sessions_closed": closed,
            },
        )
        payload["sessions_closed"] = closed
        payload["record_id"] = record.id
        return Response(payload, status=201)

    def _build_payload(self, user) -> dict:
        from apps.agent_api.models import AgentDayClose
        from apps.validations.models import ValidationEvent
        day = timezone.now().date()
        day_start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
        day_end = day_start + timedelta(days=1)

        # Use the last day-close as the lower bound. After a fecho, the new
        # session starts from zero — totals do not roll over the previous one.
        last_close = AgentDayClose.objects.filter(agent_user=user).order_by("-closed_at").first()
        since = last_close.closed_at if last_close and last_close.closed_at else day_start
        # Defensive: clamp `since` to today's midnight if the close was on a
        # previous day OR if a corrupt timestamp pushes it into the future.
        if since < day_start or since > day_end:
            since = day_start

        sales_qs = PaymentIntent.objects.filter(
            metadata__agent_user_id=user.id,
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
            created_at__gte=since, created_at__lt=day_end,
        ).select_related("guest_checkout").order_by("-created_at")

        topup_qs = PaymentIntent.objects.filter(
            metadata__agent_user_id=user.id,
            purpose=PaymentIntent.Purpose.POS_CARD_TOPUP,
            created_at__gte=since, created_at__lt=day_end,
        ).order_by("-created_at")

        device_ids = list(
            Device.objects.filter(assigned_agent=user).values_list("id", flat=True)
        )
        validations_qs = ValidationEvent.objects.filter(
            device_id__in=device_ids,
            created_at__gte=since, created_at__lt=day_end,
        ).order_by("-created_at")

        sales_total = sales_qs.filter(status=PaymentIntent.Status.CONFIRMED).aggregate(s=Sum("amount"))["s"] or Decimal("0.00")
        topup_total = topup_qs.filter(status=PaymentIntent.Status.CONFIRMED).aggregate(s=Sum("amount"))["s"] or Decimal("0.00")
        valid_total = validations_qs.filter(status="approved").aggregate(s=Sum("amount_debited"))["s"] or Decimal("0.00")

        tickets_issued = sales_qs.filter(
            status=PaymentIntent.Status.CONFIRMED, guest_checkout__status="issued",
        ).aggregate(t=Sum("guest_checkout__quantity"))["t"] or 0

        # Revenue = ONLY cash/mobile-money the agent collected (sales + topups).
        # Validations are wallet debits between passenger and system — they are
        # tracked separately (count + value) and must NOT be added to revenue.
        return {
            "date": day.isoformat(),
            "session_since": since.isoformat(),
            "session_started_after_close": last_close is not None and last_close.closed_at >= day_start,
            "totals": {
                "revenue": str(sales_total + topup_total),
                "sales": str(sales_total),
                "topups": str(topup_total),
                "validations_revenue": str(valid_total),
                "tickets": tickets_issued,
                "validations": validations_qs.filter(status="approved").count(),
            },
            "sales": [{
                "reference": pi.reference,
                "sale_reference": pi.guest_checkout.reference if pi.guest_checkout else "",
                "amount": str(pi.amount),
                "quantity": pi.guest_checkout.quantity if pi.guest_checkout else 0,
                "status": pi.status,
                "payer_phone_masked": _mask_phone(pi.payer_phone),
                "created_at": pi.created_at.isoformat(),
            } for pi in sales_qs[:200]],
            "topups": [{
                "reference": pi.reference,
                "amount": str(pi.amount),
                "status": pi.status,
                "payer_phone_masked": _mask_phone(pi.payer_phone),
                "created_at": pi.created_at.isoformat(),
            } for pi in topup_qs[:100]],
            "validations": [{
                "id": v.id,
                "validation_type": v.validation_type,
                "amount_debited": str(v.amount_debited),
                "status": v.status,
                "route": v.route.code if v.route_id else "",
                "device_serial": v.device.serial_number if v.device_id else "",
                "created_at": v.created_at.isoformat(),
            } for v in validations_qs[:200]],
        }


class AgentSalesSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def get(self, request):
        from apps.agent_api.models import AgentDayClose
        from django.utils.dateparse import parse_date
        date_str = request.query_params.get("date")
        day = parse_date(date_str) if date_str else timezone.now().date()
        day_start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
        day_end = day_start + timedelta(days=1)

        # Use last day-close as lower bound so KPIs zero out after a fecho.
        last_close = AgentDayClose.objects.filter(agent_user=request.user).order_by("-closed_at").first()
        since = last_close.closed_at if last_close and last_close.closed_at else day_start
        if since < day_start or since > day_end:
            since = day_start

        # Sales (guest_travel_pass)
        sales_qs = PaymentIntent.objects.filter(
            metadata__agent_user_id=request.user.id,
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
            created_at__gte=since, created_at__lt=day_end,
        )
        # Top-ups (wallet + package)
        topup_qs = PaymentIntent.objects.filter(
            metadata__agent_user_id=request.user.id,
            purpose=PaymentIntent.Purpose.POS_CARD_TOPUP,
            created_at__gte=since, created_at__lt=day_end,
        )

        sales_total = sales_qs.filter(status=PaymentIntent.Status.CONFIRMED).aggregate(s=Sum("amount"))["s"] or Decimal("0.00")
        topups_total = topup_qs.filter(status=PaymentIntent.Status.CONFIRMED).aggregate(s=Sum("amount"))["s"] or Decimal("0.00")

        sales_confirmed = sales_qs.filter(status=PaymentIntent.Status.CONFIRMED).count()
        sales_pending = sales_qs.filter(status=PaymentIntent.Status.PENDING).count()
        sales_failed = sales_qs.filter(status=PaymentIntent.Status.FAILED).count()

        topups_confirmed = topup_qs.filter(status=PaymentIntent.Status.CONFIRMED).count()
        topups_pending = topup_qs.filter(status=PaymentIntent.Status.PENDING).count()
        topups_failed = topup_qs.filter(status=PaymentIntent.Status.FAILED).count()

        tickets = GuestCheckout.objects.filter(
            payment_intents__metadata__agent_user_id=request.user.id,
            status=GuestCheckout.Status.ISSUED,
            updated_at__gte=since, updated_at__lt=day_end,
        ).aggregate(t=Sum("quantity"))["t"] or 0

        return Response({
            "date": day.isoformat(),
            "session_since": since.isoformat(),
            # Total cash collected by the agent (sales + topups). Validations
            # are wallet debits between passenger and system and not counted.
            "total_revenue": str(sales_total + topups_total),
            "currency": "MZN",
            "sales_total": str(sales_total),
            "topups_total": str(topups_total),
            "tickets_issued": tickets,
            "topups_count": topups_confirmed,
            "confirmed_count": sales_confirmed + topups_confirmed,
            "pending_count": sales_pending + topups_pending,
            "failed_count": sales_failed + topups_failed,
            # Keep the old breakdown for any consumers still using it
            "sales_confirmed_count": sales_confirmed,
            "sales_pending_count": sales_pending,
            "sales_failed_count": sales_failed,
        })


# ----------------------------------------------------------------------------
# Tickets
# ----------------------------------------------------------------------------

class AgentTicketListView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def get(self, request):
        qs = DigitalTravelPass.objects.select_related("guest_checkout").filter(
            guest_checkout__payment_intents__metadata__agent_user_id=request.user.id,
        ).distinct().order_by("-created_at")[:100]
        return Response({"count": qs.count(), "results": [_ticket_payload(tp) for tp in qs]})


def _ticket_visible_to(user, tp: DigitalTravelPass) -> bool:
    """An agent can only see tickets that came from a sale he initiated."""
    if tp.guest_checkout_id is None:
        return False
    return PaymentIntent.objects.filter(
        guest_checkout_id=tp.guest_checkout_id,
        metadata__agent_user_id=user.id,
    ).exists()


def _sale_visible_to(user, gc: GuestCheckout) -> bool:
    return PaymentIntent.objects.filter(
        guest_checkout=gc, metadata__agent_user_id=user.id,
    ).exists()


class AgentTicketDetailView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def get(self, request, ref: str):
        tp = DigitalTravelPass.objects.select_related("guest_checkout").filter(
            Q(guest_checkout__reference=ref) | Q(token_hash=hashlib.sha256(ref.encode()).hexdigest()),
        ).first()
        if not tp:
            return Response({"detail": "Bilhete nao encontrado."}, status=404)
        if not _ticket_visible_to(request.user, tp):
            audit(
                "PERMISSION_DENIED",
                actor=request.user,
                entity_type="travel_pass", entity_id=str(tp.id),
                after={"reason": "not_owner", "endpoint": "ticket_detail"},
            )
            return Response({"detail": "Sem permissao para ver este bilhete."}, status=403)
        return Response(_ticket_payload(tp))


class AgentTicketPdfView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def get(self, request, ref: str):
        gc = GuestCheckout.objects.filter(reference=ref).first()
        if not gc:
            return Response({"detail": "Venda nao encontrada."}, status=404)
        if not _sale_visible_to(request.user, gc):
            audit(
                "PERMISSION_DENIED",
                actor=request.user,
                entity_type="guest_checkout", entity_id=str(gc.id),
                after={"reason": "not_owner", "endpoint": "ticket_pdf"},
            )
            return Response({"detail": "Sem permissao para ver este bilhete."}, status=403)
        passes = list(gc.travel_passes.order_by("created_at", "id"))
        if not passes:
            return Response({"detail": "Sem bilhetes emitidos."}, status=404)
        pdf_bytes = generate_tickets_pdf(passes)
        response = DjangoHttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="bilhetes-{gc.reference}.pdf"'
        return response


class AgentTicketVerifyView(APIView):
    """Verify a QR token OR a shortcode (last 4 chars of reference) and
    (by default) consume the ticket.

    Body:
      - token: full QR token string, OR
      - shortcode: 4-char (last) of the GuestCheckout reference (case-insensitive)

    Pass `consume=false` to only check status without marking used.
    """
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request):
        token = (request.data.get("token") or "").strip()
        shortcode = (request.data.get("shortcode") or "").strip().upper()
        consume = bool(request.data.get("consume", True))

        tp = None
        lookup_kind = ""
        if token:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            tp = (DigitalTravelPass.objects
                  .select_related("guest_checkout")
                  .filter(token_hash=token_hash)
                  .first())
            lookup_kind = "qr"
        elif shortcode:
            # 4-char shortcode matches the last 4 chars of GuestCheckout.reference
            if len(shortcode) != 4:
                return Response({"valid": False, "reason": "Shortcode deve ter 4 caracteres."}, status=400)
            matches = list(
                DigitalTravelPass.objects
                .select_related("guest_checkout")
                .filter(guest_checkout__reference__iendswith=shortcode)
                .filter(status=DigitalTravelPass.Status.ACTIVE)
                .order_by("-created_at")[:5]
            )
            if not matches:
                audit("TICKET_VERIFIED", actor=request.user, entity_type="travel_pass",
                      after={"valid": False, "reason": "shortcode_not_found", "shortcode": shortcode})
                return Response({"valid": False, "reason": "Codigo nao encontrado.", "consumed": False}, status=404)
            if len(matches) > 1:
                audit("TICKET_VERIFY_REJECTED", actor=request.user, entity_type="travel_pass",
                      after={"reason": "shortcode_ambiguous", "shortcode": shortcode, "count": len(matches)})
                return Response({
                    "valid": False,
                    "reason": "Codigo ambiguo. Use QR Code ou pergunte a referencia completa.",
                    "consumed": False,
                    "candidates": [_ticket_payload(t) for t in matches],
                }, status=409)
            tp = matches[0]
            lookup_kind = "shortcode"
        else:
            return Response({"valid": False, "reason": "Indique token (QR) ou shortcode."}, status=400)

        if not tp:
            audit("TICKET_VERIFIED", actor=request.user, entity_type="travel_pass",
                  after={"valid": False, "reason": "not_found", "lookup": lookup_kind})
            return Response({"valid": False, "reason": "Bilhete nao encontrado.", "consumed": False}, status=404)

        # Already-used must NOT be consumed again (prevents double validation)
        if tp.status == DigitalTravelPass.Status.USED:
            audit("TICKET_VERIFY_REJECTED", actor=request.user,
                  entity_type="travel_pass", entity_id=str(tp.id),
                  after={"reason": "already_used", "used_at": tp.used_at.isoformat() if tp.used_at else ""})
            return Response({
                "valid": False,
                "reason": "Bilhete ja utilizado.",
                "ticket": _ticket_payload(tp),
                "consumed": False,
            }, status=409)

        valid = (tp.status == DigitalTravelPass.Status.ACTIVE and
                 (not tp.valid_until or tp.valid_until >= timezone.now()))

        if not valid:
            audit("TICKET_VERIFY_REJECTED", actor=request.user,
                  entity_type="travel_pass", entity_id=str(tp.id),
                  after={"reason": _verify_reason(tp), "status": tp.status})
            return Response({
                "valid": False,
                "reason": _verify_reason(tp),
                "ticket": _ticket_payload(tp),
                "consumed": False,
            })

        consumed = False
        if consume:
            tp.status = DigitalTravelPass.Status.USED
            tp.used_at = timezone.now()
            tp.save(update_fields=["status", "used_at", "updated_at"])
            consumed = True
            audit("TICKET_USED", actor=request.user,
                  entity_type="travel_pass", entity_id=str(tp.id),
                  after={"reference": tp.guest_checkout.reference if tp.guest_checkout else "", "via": "qr_verify"})

            from apps.validations.models import ValidationEvent
            try:
                ValidationEvent.objects.create(
                    validation_type=ValidationEvent.ValidationType.GUEST_DIGITAL_TRAVEL_PASS,
                    status=ValidationEvent.Status.APPROVED,
                    passenger_account=tp.passenger_account,
                    digital_travel_pass=tp,
                    route=tp.trip.route if tp.trip_id else None,
                    trip=tp.trip if tp.trip_id else None,
                    amount_debited=tp.fare_amount,
                    idempotency_key=f"verify-{tp.id}-{tp.used_at.timestamp()}",
                    device=Device.objects.filter(assigned_agent=request.user).first(),
                )
            except Exception:
                pass  # ValidationEvent is bookkeeping; never blocks the validation success

        audit("TICKET_VERIFIED", actor=request.user, entity_type="travel_pass",
              entity_id=str(tp.id),
              after={"valid": True, "consumed": consumed})
        return Response({
            "valid": True,
            "reason": "",
            "consumed": consumed,
            "ticket": _ticket_payload(tp),
        })


def _verify_reason(tp: DigitalTravelPass) -> str:
    if tp.status == DigitalTravelPass.Status.USED:
        return "Bilhete ja utilizado."
    if tp.status == DigitalTravelPass.Status.EXPIRED:
        return "Bilhete expirado."
    if tp.status == DigitalTravelPass.Status.CANCELLED:
        return "Bilhete cancelado."
    if tp.valid_until and tp.valid_until < timezone.now():
        return "Bilhete expirado."
    return "Bilhete inactivo."


class AgentCardValidationView(APIView):
    """Pay-as-you-go validation via NFC card or digital QR token.

    Body: { card_uid OR qr_token, route_id OR trip_id, [origin_stop_id],
            [destination_stop_id], [device_serial] }

    Backend locks the canonical wallet, applies the fare (with package
    fallback if the passenger has one), and emits a ValidationEvent. The
    response is shaped like the QR `tickets/verify/` endpoint so the Flutter
    feedback UI can be reused.
    """
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request):
        import hashlib
        from apps.cards.models import Card
        from apps.validations.services import validate_card

        card_uid = (request.data.get("card_uid") or "").strip().upper()
        qr_token = (request.data.get("qr_token") or "").strip()
        if not card_uid and not qr_token:
            return Response({"valid": False, "reason": "Indique card_uid ou qr_token."}, status=400)

        # If the agent gave us a QR token, resolve it to the card's UID so we
        # reuse the same pay-as-you-go service (which keys off card_uid).
        if not card_uid and qr_token:
            token_hash = hashlib.sha256(qr_token.encode()).hexdigest()
            card = Card.objects.filter(qr_token_hash=token_hash).first()
            if not card:
                return Response({"valid": False, "reason": "Cartao nao encontrado."}, status=404)
            card_uid = card.card_uid

        route_id = request.data.get("route_id")
        trip_id = request.data.get("trip_id")
        if not route_id and not trip_id:
            return Response({"valid": False, "reason": "Indique route_id ou trip_id."}, status=400)
        if not route_id and trip_id:
            from apps.trips.models import Trip
            trip = Trip.objects.filter(pk=trip_id).first()
            if not trip:
                return Response({"valid": False, "reason": "Viagem nao encontrada."}, status=404)
            route_id = trip.route_id

        origin_stop_id = request.data.get("origin_stop_id")
        destination_stop_id = request.data.get("destination_stop_id")
        device = get_authorized_device(request.user, serial_number=request.data.get("device_serial"))
        idem = (
            request.headers.get("Idempotency-Key")
            or f"card-{card_uid}-{trip_id or 'rt'}-{int(timezone.now().timestamp())}"
        )

        try:
            event = validate_card(
                card_uid=card_uid,
                route_id=int(route_id),
                origin_stop_id=int(origin_stop_id) if origin_stop_id else None,
                destination_stop_id=int(destination_stop_id) if destination_stop_id else None,
                trip_id=int(trip_id) if trip_id else None,
                device_serial=device.serial_number if device else "",
                idempotency_key=str(idem),
            )
        except Exception as e:
            return Response({"valid": False, "reason": str(e)}, status=400)

        approved = event.status == "approved"
        return Response({
            "valid": approved,
            "consumed": approved,
            "reason": event.get_failure_reason_display() if not approved else "",
            "validation_id": event.id,
            "amount_debited": str(event.amount_debited),
            "validation_type": event.validation_type,
            "wallet_tx_ref": event.wallet_transaction_ref,
            "card_uid": card_uid,
            "passenger": ({
                "full_name": event.passenger_account.full_name,
                "phone_masked": _mask_phone(event.passenger_account.phone_number),
            } if event.passenger_account_id else None),
        }, status=200 if approved else 402)


class AgentTicketMarkUsedView(APIView):
    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request, ref: str):
        tp = DigitalTravelPass.objects.select_related("guest_checkout").filter(
            Q(guest_checkout__reference=ref) | Q(token_hash=hashlib.sha256(ref.encode()).hexdigest()),
        ).first()
        if not tp:
            return Response({"detail": "Bilhete nao encontrado."}, status=404)
        if tp.status == DigitalTravelPass.Status.USED:
            return Response({"detail": "Bilhete ja foi utilizado.", "used_at": tp.used_at.isoformat() if tp.used_at else None}, status=409)
        if tp.status != DigitalTravelPass.Status.ACTIVE:
            return Response({"detail": "Bilhete nao esta activo."}, status=400)
        if tp.valid_until and tp.valid_until < timezone.now():
            return Response({"detail": "Bilhete expirado."}, status=400)

        tp.status = DigitalTravelPass.Status.USED
        tp.used_at = timezone.now()
        tp.save(update_fields=["status", "used_at", "updated_at"])
        audit(
            "TICKET_USED",
            actor=request.user,
            entity_type="travel_pass", entity_id=str(tp.id),
            after={"reference": tp.guest_checkout.reference if tp.guest_checkout else ""},
        )
        return Response({"detail": "Bilhete marcado como utilizado.", "used_at": tp.used_at.isoformat()})
