import secrets
import string
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.permissions import ALL_CAPABILITIES, HasCapabilities
from apps.core.viewsets import BaseModelViewSet
from apps.users.api.serializers import (
    AssignRoleSerializer,
    BuzUpTokenObtainPairSerializer,
    ChangePasswordSerializer,
    MeSerializer,
    RoleCreateSerializer,
    RoleSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.cards.models import Card
from apps.packages.models import Package, PassengerPackage
from apps.packages.services import PackageError, subscribe_passenger
from apps.passengers.api.extract import _generate_extract_pdf
from apps.passengers.models import PassengerAccount
from apps.payments.models import PaymentIntent
from apps.payments.services.gateway import get_payment_gateway
from apps.payments.services.processing import confirm_payment_immediately
from apps.users.models import Role, User, UserRole
from apps.wallets.models import Wallet, WalletTransaction
from apps.wallets.services import InsufficientBalanceError, WalletBlockedError


class BuzUpTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = BuzUpTokenObtainPairSerializer


class BuzUpTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


class MeView(APIView):
    def get(self, request):
        return Response(MeSerializer(request.user).data)


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Senha actualizada com sucesso."})


class CapabilitiesListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"capabilities": ALL_CAPABILITIES})


class RoleViewSet(BaseModelViewSet):
    queryset = Role.all_objects.all()
    serializer_class = RoleSerializer
    required_capabilities_by_action = {
        "list": ("roles.read",),
        "retrieve": ("roles.read",),
        "create": ("roles.manage",),
        "update": ("roles.manage",),
        "partial_update": ("roles.manage",),
        "destroy": ("roles.manage",),
    }

    def get_serializer_class(self):
        if self.action in ("create",):
            return RoleCreateSerializer
        return RoleSerializer


class UserViewSet(BaseModelViewSet):
    queryset = User.all_objects.prefetch_related("role_assignments__role").all()
    serializer_class = UserSerializer
    required_capabilities_by_action = {
        "list": ("users.read",),
        "retrieve": ("users.read",),
        "create": ("users.manage",),
        "update": ("users.manage",),
        "partial_update": ("users.manage",),
        "destroy": ("users.manage",),
    }

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserSerializer


class AssignRoleView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("users.manage",)

    def post(self, request):
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(pk=serializer.validated_data["user_id"])
            role = Role.objects.get(pk=serializer.validated_data["role_id"])
        except (User.DoesNotExist, Role.DoesNotExist):
            return Response({"detail": "Utilizador ou role nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        UserRole.objects.get_or_create(user=user, role=role)
        return Response({"detail": f"Role {role.name} atribuida a {user.username}."})

    def delete(self, request):
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        UserRole.objects.filter(
            user_id=serializer.validated_data["user_id"],
            role_id=serializer.validated_data["role_id"],
        ).delete()
        return Response({"detail": "Role removida."})


class PassengerPortalView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        """Allow the passenger to edit their own full_name + email.

        Other fields (phone, document, status) are not editable from the
        mobile app — phone is the auth identity and document changes must go
        through a verification flow.
        """
        passenger = _current_passenger(request.user)
        if not passenger:
            return Response({"detail": "Conta de passageiro nao encontrada."}, status=404)

        new_name = (request.data.get("full_name") or "").strip()
        new_email = (request.data.get("email") or "").strip()

        updates = {}
        if new_name and new_name != passenger.full_name:
            if len(new_name) < 2 or len(new_name) > 255:
                return Response({"detail": "Nome deve ter entre 2 e 255 caracteres."}, status=400)
            updates["full_name"] = new_name
        if new_email != passenger.email:
            # Allow clearing the email by submitting an empty string.
            if new_email and "@" not in new_email:
                return Response({"detail": "Email invalido."}, status=400)
            updates["email"] = new_email

        if updates:
            for k, v in updates.items():
                setattr(passenger, k, v)
            updates["updated_at"] = timezone.now()
            passenger.save(update_fields=list(updates.keys()))

        return self.get(request)

    def get(self, request):
        user = request.user
        passenger = PassengerAccount.objects.filter(
            phone_number=user.phone, deleted_at__isnull=True
        ).first()

        if not passenger:
            return Response(
                {"detail": "Conta de passageiro nao encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        wallet = Wallet.objects.filter(passenger_account=passenger).first()
        cards = Card.objects.filter(passenger_account=passenger, deleted_at__isnull=True)
        packages = PassengerPackage.objects.filter(
            passenger_account=passenger, status="active"
        )
        available_packages = Package.objects.filter(status=Package.Status.ACTIVE).prefetch_related("routes__route")

        digital_card = cards.filter(card_type="digital").first()

        return Response({
            "id": passenger.id,
            "full_name": passenger.full_name,
            "phone": passenger.phone_number,
            "email": passenger.email or "",
            "wallet_uuid": str(wallet.uuid) if wallet else "",
            "balance": str(wallet.balance_cached) if wallet else "0.00",
            "currency": wallet.currency if wallet else "MZN",
            "card_number": digital_card.card_number if digital_card else None,
            "qr_token": digital_card.qr_token if digital_card else None,
            "card_id": digital_card.id if digital_card else None,
            "active_packages": [
                {
                    "id": pkg.id,
                    "package_id": pkg.package_id,
                    "package_name": pkg.package.name,
                    "package_description": pkg.package.description,
                    "discount_type": pkg.package.discount_type,
                    "discount_value": str(pkg.package.discount_value),
                    "package_price": str(pkg.package.price),
                    "validity_days": pkg.package.validity_days,
                    "max_trips": pkg.package.max_trips,
                    "trips_used": pkg.trips_used,
                    "trips_remaining": pkg.trips_remaining,
                    "special_balance": str(pkg.special_balance),
                    "expires_at": pkg.expires_at.isoformat() if pkg.expires_at else None,
                    "activated_at": pkg.activated_at.isoformat() if pkg.activated_at else None,
                    "status": pkg.status,
                    "routes": [
                        {
                            "route_id": r.route_id,
                            "route_code": r.route.code,
                            "route_name": r.route.name,
                        }
                        for r in pkg.package.routes.all()
                    ],
                }
                for pkg in packages.select_related("package").prefetch_related("package__routes__route")
            ],
            "available_packages": [_available_package_payload(pkg) for pkg in available_packages],
        })


class PassengerPortalTopupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        passenger = _current_passenger(request.user)
        if not passenger:
            return Response({"detail": "Conta de passageiro nao encontrada."}, status=status.HTTP_404_NOT_FOUND)

        wallet = Wallet.objects.filter(passenger_account=passenger).first()
        if not wallet:
            return Response({"detail": "Carteira nao encontrada."}, status=status.HTTP_404_NOT_FOUND)
        if wallet.status != Wallet.Status.ACTIVE:
            return Response({"detail": "Carteira bloqueada."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(str(request.data.get("amount", "0"))).quantize(Decimal("0.01"))
        except Exception:
            return Response({"detail": "Valor invalido."}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({"detail": "Valor deve ser maior que zero."}, status=status.HTTP_400_BAD_REQUEST)

        payer_phone = str(request.data.get("payer_phone") or passenger.phone_number).strip()
        idempotency_key = request.headers.get("Idempotency-Key") or f"portal-topup-{uuid4().hex}"
        existing = PaymentIntent.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return Response(_topup_response(existing))

        ref = f"TOP-{uuid4().hex[:12].upper()}"
        pi = PaymentIntent.objects.create(
            reference=ref,
            idempotency_key=idempotency_key,
            purpose=PaymentIntent.Purpose.MOBILE_WALLET_TOPUP,
            amount=amount,
            payer_phone=payer_phone,
            wallet=wallet,
            status=PaymentIntent.Status.PENDING,
            created_by=request.user,
        )

        gateway = get_payment_gateway(payer_phone=payer_phone)
        result = gateway.initiate_payment(
            reference=ref,
            amount=amount,
            payer_phone=payer_phone,
            description=f"Recarga BusUp {amount} MZN",
        )
        pi.provider = result.provider
        pi.metadata = {
            "gateway_request": result.request_payload or {},
            "gateway_response": result.response_payload or {},
        }

        if result.success:
            pi.provider_reference = result.provider_reference
            pi.save(update_fields=["provider", "provider_reference", "metadata", "updated_at"])
            confirm_payment_immediately(pi, result.provider_reference)
            pi.refresh_from_db()
        elif result.pending:
            pi.provider_reference = result.provider_reference
            pi.save(update_fields=["provider", "provider_reference", "metadata", "updated_at"])
        else:
            pi.status = PaymentIntent.Status.FAILED
            pi.save(update_fields=["status", "provider", "metadata", "updated_at"])
            return Response({"detail": result.detail_message or result.error or "Falha no pagamento."}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(_topup_response(pi), status=status.HTTP_201_CREATED)


class PassengerPortalTransactionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        passenger = _current_passenger(request.user)
        if not passenger:
            return Response({"detail": "Conta de passageiro nao encontrada."}, status=status.HTTP_404_NOT_FOUND)
        wallet = Wallet.objects.filter(passenger_account=passenger).first()
        if not wallet:
            return Response({"results": []})

        txs = WalletTransaction.objects.filter(wallet=wallet).order_by("-created_at")[:60]
        return Response({
            "results": [
                {
                    "id": tx.id,
                    "uuid": str(tx.uuid),
                    "type": tx.type,
                    "direction": tx.direction,
                    "amount": str(tx.amount),
                    "signed_amount": str(tx.signed_amount),
                    "balance_before": str(tx.balance_before),
                    "balance_after": str(tx.balance_after),
                    "reference": tx.reference,
                    "source": tx.source,
                    "status": tx.status,
                    "created_at": tx.created_at.isoformat(),
                }
                for tx in txs
            ],
        })


class PassengerPortalAdminFeesView(APIView):
    """Lists the public-facing administrative fees (card issuance, card
    recovery, fines, etc.) so the passenger can see ahead of time what the
    operator will charge for non-trip operations.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.fares.models import AdminFee
        rows = AdminFee.objects.filter(is_active=True).order_by("kind", "name")
        return Response({
            "results": [
                {
                    "code": fee.code,
                    "name": fee.name,
                    "kind": fee.kind,
                    "kind_label": fee.get_kind_display(),
                    "amount": str(fee.amount),
                    "currency": fee.currency,
                    "description": fee.description,
                }
                for fee in rows
            ],
        })


class PassengerPortalTransactionDetailView(APIView):
    """Detail of a single wallet transaction owned by the authenticated passenger.

    Enriches the row with channel (m-pesa, e-mola, mock, agent, validation, ...)
    and, when applicable, agent_name + payment_intent metadata. Lookups happen
    only for the single row, so this is cheap.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, tx_id: int):
        passenger = _current_passenger(request.user)
        if not passenger:
            return Response({"detail": "Conta de passageiro nao encontrada."}, status=404)
        wallet = Wallet.objects.filter(passenger_account=passenger).first()
        if not wallet:
            return Response({"detail": "Sem carteira."}, status=404)

        tx = WalletTransaction.objects.filter(wallet=wallet, pk=tx_id).first()
        if not tx:
            return Response({"detail": "Transaccao nao encontrada."}, status=404)

        payload = {
            "id": tx.id,
            "uuid": str(tx.uuid),
            "type": tx.type,
            "direction": tx.direction,
            "amount": str(tx.amount),
            "signed_amount": str(tx.signed_amount),
            "balance_before": str(tx.balance_before),
            "balance_after": str(tx.balance_after),
            "reference": tx.reference,
            "source": tx.source,
            "status": tx.status,
            "created_at": tx.created_at.isoformat(),
            "metadata": tx.metadata or {},
            "channel": None,
            "channel_label": None,
            "agent_name": None,
            "payment_provider": None,
            "payment_provider_label": None,
            "payment_reference": None,
        }

        src = (tx.source or "").strip()
        if src.startswith("payment:"):
            ref = src.split(":", 1)[1]
            pi = PaymentIntent.objects.filter(reference=ref).first()
            if pi:
                payload["payment_provider"] = pi.provider
                payload["payment_provider_label"] = {
                    "mpesa": "M-Pesa",
                    "emola": "E-Mola",
                    "mock": "Teste (MOCK)",
                    "real_test_mode": "Teste (real)",
                }.get((pi.provider or "").lower(), (pi.provider or "").upper() or None)
                payload["payment_reference"] = pi.reference
                payload["channel"] = "wallet_topup"
                payload["channel_label"] = "Recarga carteira movel"
        elif src.startswith("agent:"):
            try:
                from apps.trips.models import Agent
                aid = int(src.split(":", 1)[1])
                ag = Agent.objects.filter(pk=aid).first()
                if ag:
                    payload["agent_name"] = ag.full_name
                payload["channel"] = "agent"
                payload["channel_label"] = "Agente / Cobrador"
            except (ValueError, TypeError):
                pass
        elif src.startswith("validation:"):
            payload["channel"] = "validation"
            payload["channel_label"] = "Validacao a bordo"
        elif src.startswith("package:"):
            payload["channel"] = "package_purchase"
            payload["channel_label"] = "Compra de pacote"
        elif src.startswith("ticket:") or src.startswith("travel_pass:"):
            payload["channel"] = "ticket_purchase"
            payload["channel_label"] = "Compra de bilhete"
        elif src.startswith("admin:"):
            payload["channel"] = "admin"
            payload["channel_label"] = "Ajuste administrativo"

        return Response(payload)


class _QueryTokenJWTAuthentication:
    """Light wrapper: accept JWT in `?token=` so mobile can `launchUrl()` the
    extract PDF without exposing JWT in HTTP headers (which browsers won't
    set for plain link opens). Mirror of the helper in cards/api/views.py.
    """
    def authenticate(self, request):
        from rest_framework_simplejwt.authentication import JWTAuthentication
        jwt_auth = JWTAuthentication()
        result = jwt_auth.authenticate(request)
        if result is not None:
            return result
        token = (
            request.query_params.get("token")
            if hasattr(request, "query_params")
            else request.GET.get("token")
        )
        if not token:
            return None
        validated = jwt_auth.get_validated_token(token)
        return (jwt_auth.get_user(validated), validated)


class PassengerPortalExtractView(APIView):
    # Allow ?token= so the mobile can open the PDF via a browser intent
    # (no Authorization header). Header auth still works for the portal.
    authentication_classes = [_QueryTokenJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        passenger = _current_passenger(request.user)
        if not passenger:
            return Response({"detail": "Conta de passageiro nao encontrada."}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        parsed_from = parse_date(date_from) if date_from else None
        parsed_to = parse_date(date_to) if date_to else None
        dt_from = timezone.make_aware(timezone.datetime.combine(parsed_from, timezone.datetime.min.time())) if parsed_from else now - timedelta(days=30)
        dt_to = timezone.make_aware(timezone.datetime.combine(parsed_to, timezone.datetime.min.time())) + timedelta(days=1) if parsed_to else now + timedelta(days=1)

        wallet = Wallet.objects.filter(passenger_account=passenger).first()
        txs = []
        if wallet:
            txs = list(WalletTransaction.objects.filter(
                wallet=wallet,
                created_at__gte=dt_from,
                created_at__lt=dt_to,
            ).order_by("-created_at")[:200])

        pdf = _generate_extract_pdf(passenger, wallet, txs, dt_from, dt_to)
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="extracto_passageiro.pdf"'
        return response


class PassengerPortalPackageSubscribeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        passenger = _current_passenger(request.user)
        if not passenger:
            return Response({"detail": "Conta de passageiro nao encontrada."}, status=status.HTTP_404_NOT_FOUND)

        try:
            package_id = int(request.data.get("package_id"))
        except (TypeError, ValueError):
            return Response({"detail": "Pacote invalido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            package = Package.objects.get(pk=package_id, status=Package.Status.ACTIVE)
        except Package.DoesNotExist:
            return Response({"detail": "Pacote nao encontrado ou inactivo."}, status=status.HTTP_404_NOT_FOUND)

        try:
            subscription = subscribe_passenger(passenger, package, pay_from_wallet=True)
        except InsufficientBalanceError:
            return Response({"detail": "Saldo insuficiente para comprar este pacote."}, status=status.HTTP_400_BAD_REQUEST)
        except WalletBlockedError:
            return Response({"detail": "Carteira bloqueada."}, status=status.HTTP_400_BAD_REQUEST)
        except PackageError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(_subscription_payload(subscription), status=status.HTTP_201_CREATED)


def _current_passenger(user):
    return PassengerAccount.objects.filter(
        phone_number=user.phone,
        deleted_at__isnull=True,
    ).first()


def _available_package_payload(package: Package) -> dict:
    return {
        "id": package.id,
        "uuid": str(package.uuid),
        "name": package.name,
        "description": package.description,
        "discount_type": package.discount_type,
        "discount_value": str(package.discount_value),
        "price": str(package.price),
        "validity_days": package.validity_days,
        "max_trips": package.max_trips,
        "routes": [
            {
                "route_id": route.route_id,
                "route_code": route.route.code,
                "route_name": route.route.name,
            }
            for route in package.routes.all()
        ],
    }


def _subscription_payload(subscription: PassengerPackage) -> dict:
    return {
        "id": subscription.id,
        "uuid": str(subscription.uuid),
        "package_id": subscription.package_id,
        "package_name": subscription.package.name,
        "discount_type": subscription.package.discount_type,
        "special_balance": str(subscription.special_balance),
        "trips_used": subscription.trips_used,
        "trips_remaining": subscription.trips_remaining,
        "status": subscription.status,
        "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
    }


class PassengerPortalPaymentStatusView(APIView):
    """Lets a passenger poll the status of their own pending PaymentIntent.

    Ownership is enforced via wallet → passenger_account: if the PI's wallet
    doesn't belong to the requesting user's passenger account, we 403.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, reference: str):
        pi = PaymentIntent.objects.select_related("wallet__passenger_account").filter(
            reference=reference,
        ).first()
        if not pi:
            return Response({"detail": "Pagamento nao encontrado."}, status=404)

        passenger = _current_passenger(request.user)
        if not passenger or not pi.wallet or pi.wallet.passenger_account_id != passenger.id:
            return Response({"detail": "Sem permissao."}, status=403)

        return Response(_topup_response(pi))


def _travel_pass_payload(tp) -> dict:
    """Serializes a DigitalTravelPass for the passenger mobile app.

    Includes the raw token so the app can render a QR code locally — safe to
    return because the request is authenticated and ownership-checked.

    Also includes `reference` (human-readable, ex: GC-AB12-01) and `short_code`
    (4-char alphanum, shown big below the QR) so the agent can validate by
    typing the short code when the QR scan fails.
    """
    from apps.guest_checkouts.ticket_codes import ticket_reference, ticket_short_code

    reference = ticket_reference(tp)
    return {
        "id": tp.id,
        "uuid": str(tp.uuid),
        "status": tp.status,
        "route_code": tp.route_code,
        "route_name": tp.route_name,
        "origin_stop": tp.origin_stop,
        "destination_stop": tp.destination_stop,
        "fare_amount": str(tp.fare_amount),
        "trip_id": tp.trip_id,
        "valid_from": tp.valid_from.isoformat() if tp.valid_from else None,
        "valid_until": tp.valid_until.isoformat() if tp.valid_until else None,
        "used_at": tp.used_at.isoformat() if tp.used_at else None,
        "delivery_channel": tp.delivery_channel,
        "token": tp.token,
        "reference": reference,
        "short_code": ticket_short_code(reference),
        "created_at": tp.created_at.isoformat(),
    }


class PassengerPortalTicketsView(APIView):
    """List travel passes for the authenticated passenger, newest first.

    Query params:
    - `status_filter`: comma-separated subset of {active, used, expired, cancelled}.
      Omit to return all statuses.
    - `limit`: defaults to 50.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.guest_checkouts.models import DigitalTravelPass

        passenger = _current_passenger(request.user)
        if not passenger:
            return Response({"detail": "Conta de passageiro nao encontrada."}, status=404)

        qs = DigitalTravelPass.objects.filter(passenger_account=passenger)

        status_filter = (request.query_params.get("status_filter") or "").strip()
        if status_filter:
            wanted = {s.strip().lower() for s in status_filter.split(",") if s.strip()}
            valid = {c[0] for c in DigitalTravelPass.Status.choices}
            qs = qs.filter(status__in=(wanted & valid))

        try:
            limit = max(1, min(int(request.query_params.get("limit", 50)), 200))
        except (TypeError, ValueError):
            limit = 50

        qs = qs.order_by("-created_at")[:limit]
        return Response({
            "results": [_travel_pass_payload(tp) for tp in qs],
        })


class PassengerPortalTicketDetailView(APIView):
    """Detail of a single travel pass owned by the authenticated passenger."""
    permission_classes = [IsAuthenticated]

    def get(self, request, ticket_id: int):
        from apps.guest_checkouts.models import DigitalTravelPass

        passenger = _current_passenger(request.user)
        if not passenger:
            return Response({"detail": "Conta de passageiro nao encontrada."}, status=404)

        tp = DigitalTravelPass.objects.filter(pk=ticket_id, passenger_account=passenger).first()
        if not tp:
            return Response({"detail": "Bilhete nao encontrado."}, status=404)

        return Response(_travel_pass_payload(tp))


def _topup_response(payment_intent: PaymentIntent) -> dict:
    wallet = payment_intent.wallet
    return {
        "payment_intent": str(payment_intent.uuid),
        "reference": payment_intent.reference,
        "status": payment_intent.status,
        "amount": str(payment_intent.amount),
        "detail_message": "Recarga confirmada." if payment_intent.status == PaymentIntent.Status.CONFIRMED else "Confirme a recarga na carteira movel.",
        "balance": str(wallet.balance_cached) if wallet else "0.00",
    }


def _generate_temp_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


class PublicPasswordResetView(APIView):
    """Generate a temporary password and send via SMS. Public endpoint."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        from apps.users.otp import normalize_otp_phone
        from apps.sms.services.sender import send_sms
        phone = normalize_otp_phone(request.data.get("phone", ""))
        if not phone:
            return Response({"detail": "Telefone invalido."}, status=400)
        user = User.objects.filter(phone=phone, is_active=True).first()
        if not user:
            # Return 200 to avoid leaking which phones exist
            return Response({"detail": "Se o telefone estiver associado a uma conta, enviaremos uma senha temporaria."})
        temp = _generate_temp_password()
        user.set_password(temp)
        user.save(update_fields=["password", "updated_at"])
        send_sms(phone, f"BusUp: senha temporaria {temp}. Altere apos o login.", purpose="PASSWORD_RESET")
        return Response({"detail": "Se o telefone estiver associado a uma conta, enviaremos uma senha temporaria."})


class AdminUserPasswordResetView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("users.manage",)

    def post(self, request, pk):
        from apps.sms.services.sender import send_sms
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "Utilizador nao encontrado."}, status=404)
        if not user.phone:
            return Response({"detail": "Utilizador nao tem telefone registado."}, status=400)
        temp = _generate_temp_password()
        user.set_password(temp)
        user.save(update_fields=["password", "updated_at"])
        send_sms(user.phone, f"BusUp: senha temporaria {temp}. Altere apos o login.", purpose="ADMIN_PASSWORD_RESET")
        return Response({"detail": f"Senha temporaria enviada para {user.phone}.", "phone": user.phone})


class AdminUserToggleActiveView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("users.manage",)

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "Utilizador nao encontrado."}, status=404)
        user.is_active = not user.is_active
        user.save(update_fields=["is_active", "updated_at"])
        return Response({"id": user.id, "username": user.username, "is_active": user.is_active})


class MeProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        updated_fields = []
        for field in ("first_name", "last_name", "email", "phone"):
            if field in request.data:
                value = str(request.data[field] or "").strip()
                if field == "phone":
                    from apps.users.otp import normalize_otp_phone
                    value = normalize_otp_phone(value) or value
                setattr(user, field, value)
                updated_fields.append(field)
        new_password = request.data.get("new_password")
        if new_password:
            current_password = request.data.get("current_password", "")
            if not user.check_password(current_password):
                return Response({"detail": "Senha actual incorrecta."}, status=400)
            if len(str(new_password)) < 6:
                return Response({"detail": "Nova senha deve ter pelo menos 6 caracteres."}, status=400)
            user.set_password(new_password)
            updated_fields.append("password")
        if updated_fields:
            updated_fields.append("updated_at")
            user.save(update_fields=updated_fields)
        from apps.users.api.serializers import MeSerializer
        return Response(MeSerializer(user).data)
