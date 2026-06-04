"""All /api/mobile/* endpoints consumed by the Flutter passenger app.

Re-uses existing services:
    - OTP login (apps.users.api.otp_views)
    - Passenger portal view payload (apps.users.api.views.PassengerPortalView)
    - Wallet topup (apps.users.api.views.PassengerPortalTopupView)
    - Travel pass purchase (apps.validations.api.views.PurchaseTravelPassView)

This module adds the dedicated mobile-namespaced endpoints required by the
Flutter app and a Notifications API.
"""
from __future__ import annotations

import hashlib
from datetime import timedelta

from django.http import HttpResponse as DjangoHttpResponse
from django.utils import timezone
from rest_framework import status as drf_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import audit, client_ip
from apps.cards.models import Card
from apps.guest_checkouts.models import DigitalTravelPass
from apps.guest_checkouts.ticket_pdf import generate_tickets_pdf
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.passengers.models import PassengerAccount
from apps.payments.models import PaymentIntent
from apps.validations.models import ValidationEvent
from apps.wallets.models import Wallet, WalletTransaction


def _passenger(user) -> PassengerAccount | None:
    if not user or not user.is_authenticated:
        return None
    return PassengerAccount.objects.filter(
        phone_number=user.phone or "",
        status=PassengerAccount.Status.ACTIVE,
    ).first()


def _mask_phone(phone: str) -> str:
    p = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(p) < 4:
        return p
    return f"***{p[-4:]}"


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
        "status": tp.status,
        "valid_from": tp.valid_from.isoformat() if tp.valid_from else None,
        "valid_until": tp.valid_until.isoformat() if tp.valid_until else None,
        "used_at": tp.used_at.isoformat() if tp.used_at else None,
        "token": tp.token,
    }


# ----------------------------------------------------------------------------
# Profile / Me
# ----------------------------------------------------------------------------

class MobileMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        passenger = _passenger(request.user)
        if not passenger:
            return Response({"detail": "Conta de passageiro nao encontrada."}, status=404)
        return Response({
            "passenger": {
                "id": passenger.id,
                "uuid": str(passenger.uuid),
                "full_name": passenger.full_name,
                "phone": passenger.phone_number,
                "email": passenger.email,
                "document_type": passenger.document_type,
                "document_number": passenger.document_number,
                "status": passenger.status,
            },
            "user": {
                "username": request.user.username,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "email": request.user.email,
                "phone": request.user.phone,
            },
        })


# ----------------------------------------------------------------------------
# Card / Wallet
# ----------------------------------------------------------------------------

class MobileCardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        passenger = _passenger(request.user)
        if not passenger:
            return Response({"detail": "Conta de passageiro nao encontrada."}, status=404)
        cards = Card.objects.filter(passenger_account=passenger, deleted_at__isnull=True)
        return Response({
            "results": [{
                "id": c.id,
                "uuid": str(c.uuid),
                "card_number": c.card_number,
                "card_type": c.card_type,
                "card_technology": c.card_technology,
                "status": c.status,
                "qr_token": c.qr_token if c.card_type == "digital" else None,
                "issued_at": c.issued_at.isoformat() if c.issued_at else None,
                "activated_at": c.activated_at.isoformat() if c.activated_at else None,
            } for c in cards]
        })


class MobileBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        passenger = _passenger(request.user)
        if not passenger:
            return Response({"detail": "Conta de passageiro nao encontrada."}, status=404)
        wallet = Wallet.objects.filter(passenger_account=passenger).first()
        if not wallet:
            return Response({"balance": "0.00", "currency": "MZN", "status": "missing"})
        return Response({
            "wallet_uuid": str(wallet.uuid),
            "balance": str(wallet.balance_cached),
            "currency": wallet.currency,
            "status": wallet.status,
        })


# ----------------------------------------------------------------------------
# Tickets
# ----------------------------------------------------------------------------

class MobileTicketListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        passenger = _passenger(request.user)
        if not passenger:
            return Response({"detail": "Conta de passageiro nao encontrada."}, status=404)
        phone = request.user.phone or passenger.phone_number
        qs = DigitalTravelPass.objects.select_related("guest_checkout").filter(
            passenger_account=passenger,
        ) | DigitalTravelPass.objects.select_related("guest_checkout").filter(
            passenger_account__isnull=True, payer_phone=phone,
        )
        qs = qs.distinct().order_by("-created_at")[:100]
        return Response({"count": qs.count(), "results": [_ticket_payload(tp) for tp in qs]})


class MobileTicketDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, ref: str):
        passenger = _passenger(request.user)
        phone = request.user.phone or (passenger.phone_number if passenger else "")
        from django.db.models import Q

        token_hash = hashlib.sha256(ref.encode()).hexdigest()
        tp = DigitalTravelPass.objects.select_related("guest_checkout").filter(
            Q(token_hash=token_hash) | Q(guest_checkout__reference=ref) | Q(uuid=ref),
        ).first()
        if not tp:
            return Response({"detail": "Bilhete nao encontrado."}, status=404)
        if tp.passenger_account_id and passenger and tp.passenger_account_id != passenger.id:
            return Response({"detail": "Sem permissao."}, status=403)
        if not tp.passenger_account_id and tp.payer_phone != phone:
            return Response({"detail": "Sem permissao."}, status=403)
        return Response(_ticket_payload(tp))


class MobileTicketPdfView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, ref: str):
        passenger = _passenger(request.user)
        phone = request.user.phone or (passenger.phone_number if passenger else "")
        from django.db.models import Q
        token_hash = hashlib.sha256(ref.encode()).hexdigest()
        tp = DigitalTravelPass.objects.select_related("guest_checkout").filter(
            Q(token_hash=token_hash) | Q(guest_checkout__reference=ref) | Q(uuid=ref),
        ).first()
        if not tp:
            return Response({"detail": "Bilhete nao encontrado."}, status=404)
        if tp.passenger_account_id and passenger and tp.passenger_account_id != passenger.id:
            return Response({"detail": "Sem permissao."}, status=403)
        if not tp.passenger_account_id and tp.payer_phone != phone:
            return Response({"detail": "Sem permissao."}, status=403)

        if tp.guest_checkout_id:
            passes = list(DigitalTravelPass.objects.filter(guest_checkout_id=tp.guest_checkout_id).order_by("created_at", "id"))
        else:
            passes = [tp]
        pdf_bytes = generate_tickets_pdf(passes)
        response = DjangoHttpResponse(pdf_bytes, content_type="application/pdf")
        ref_display = tp.guest_checkout.reference if tp.guest_checkout else str(tp.uuid)[:8]
        response["Content-Disposition"] = f'inline; filename="bilhete-{ref_display}.pdf"'
        return response


# ----------------------------------------------------------------------------
# Payments
# ----------------------------------------------------------------------------

class MobilePaymentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        passenger = _passenger(request.user)
        phone = request.user.phone or (passenger.phone_number if passenger else "")
        if not phone:
            return Response({"detail": "Telefone obrigatorio."}, status=404)
        qs = PaymentIntent.objects.filter(payer_phone=phone).order_by("-created_at")[:100]
        return Response({"count": qs.count(), "results": [{
            "reference": pi.reference,
            "purpose": pi.purpose,
            "amount": str(pi.amount),
            "currency": pi.currency,
            "status": pi.status,
            "provider": pi.provider,
            "confirmed_at": pi.confirmed_at.isoformat() if pi.confirmed_at else None,
            "created_at": pi.created_at.isoformat(),
        } for pi in qs]})


class MobilePaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, reference: str):
        passenger = _passenger(request.user)
        phone = request.user.phone or (passenger.phone_number if passenger else "")
        pi = PaymentIntent.objects.filter(reference=reference, payer_phone=phone).first()
        if not pi:
            return Response({"detail": "Pagamento nao encontrado."}, status=404)
        return Response({
            "reference": pi.reference,
            "purpose": pi.purpose,
            "amount": str(pi.amount),
            "currency": pi.currency,
            "status": pi.status,
            "provider": pi.provider,
            "confirmed_at": pi.confirmed_at.isoformat() if pi.confirmed_at else None,
            "created_at": pi.created_at.isoformat(),
        })


# ----------------------------------------------------------------------------
# Trip history (validations)
# ----------------------------------------------------------------------------

class MobileTripHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        passenger = _passenger(request.user)
        if not passenger:
            return Response({"detail": "Conta de passageiro nao encontrada."}, status=404)
        qs = ValidationEvent.objects.select_related("route").filter(
            passenger_account=passenger,
        ).order_by("-created_at")[:100]
        return Response({"count": qs.count(), "results": [{
            "id": v.id,
            "uuid": str(v.uuid),
            "validation_type": v.validation_type,
            "route_code": v.route.code if v.route else "",
            "amount_debited": str(v.amount_debited),
            "status": v.status,
            "failure_reason": v.failure_reason,
            "created_at": v.created_at.isoformat(),
        } for v in qs]})


# ----------------------------------------------------------------------------
# Notifications
# ----------------------------------------------------------------------------

class MobileNotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(user=request.user).order_by("-created_at")[:100]
        unread = Notification.objects.filter(user=request.user, read_at__isnull=True).count()
        return Response({
            "unread_count": unread,
            "results": [{
                "id": n.id,
                "uuid": str(n.uuid),
                "kind": n.kind,
                "title": n.title,
                "body": n.body,
                "data": n.data,
                "read_at": n.read_at.isoformat() if n.read_at else None,
                "created_at": n.created_at.isoformat(),
            } for n in qs],
        })


class MobileNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id: int):
        notif = Notification.objects.filter(pk=notification_id, user=request.user).first()
        if not notif:
            return Response({"detail": "Notificacao nao encontrada."}, status=404)
        if not notif.read_at:
            notif.read_at = timezone.now()
            notif.save(update_fields=["read_at", "updated_at"])
        return Response({"detail": "ok", "read_at": notif.read_at.isoformat()})


class MobileNotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        n = Notification.objects.filter(user=request.user, read_at__isnull=True).update(read_at=timezone.now())
        return Response({"detail": "ok", "marked": n})
