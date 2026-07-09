"""Agent-facing endpoints for card lookup, wallet top-up and wallet payment.

All endpoints in this module respect agent isolation: an agent's own user.id is
recorded on every PaymentIntent metadata, so revenue/history queries can filter
by `metadata__agent_user_id`.
"""
from __future__ import annotations

import hashlib
from decimal import Decimal
from uuid import uuid4

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agent_api.permissions import IsActiveAgent
from apps.audit.services import audit, client_ip
from apps.cards.models import Card
from apps.packages.models import Package, PassengerPackage
from apps.payments.models import PaymentIntent
from apps.payments.services.gateway import get_payment_gateway
from apps.payments.services.processing import confirm_payment_immediately
from apps.wallets.models import Wallet, WalletTransaction
from apps.wallets.services import credit_wallet, debit_wallet, InsufficientBalanceError, WalletBlockedError


def _mask_phone(phone: str) -> str:
    p = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(p) < 4:
        return p
    return f"***{p[-4:]}"


def _resolve_card(card_uid: str = "", qr_token: str = "") -> Card | None:
    """Find a card by NFC UID or by digital QR token (hashed lookup).

    The UID is stored UPPERCASE (see AgentCardCaptureUidView); we normalise on
    the way in so lowercase tokens from the SDK still match. Tabs/spaces are
    trimmed for the same reason.
    """
    if card_uid:
        return (
            Card.objects.select_related("wallet", "passenger_account")
            .filter(card_uid=card_uid.strip().upper())
            .first()
        )
    if qr_token:
        token_hash = hashlib.sha256(qr_token.strip().encode()).hexdigest()
        return (
            Card.objects.select_related("wallet", "passenger_account")
            .filter(qr_token_hash=token_hash)
            .first()
        )
    return None


def _serialize_card(card: Card) -> dict:
    pa = card.passenger_account
    # Wallet is per-account, not per-card. Both digital and physical cards of
    # the same passenger share the same balance + packages. Prefer the
    # account's wallet, fall back to the card's wallet FK for legacy rows.
    wallet = None
    if pa and hasattr(pa, "wallet"):
        try:
            wallet = pa.wallet
        except Exception:
            wallet = None
    if wallet is None:
        wallet = card.wallet
    active_pkgs = []
    if pa:
        for pp in pa.packages.filter(status=PassengerPackage.Status.ACTIVE).select_related("package"):
            active_pkgs.append({
                "id": pp.id,
                "uuid": str(pp.uuid),
                "package_id": pp.package_id,
                "package_name": pp.package.name,
                "special_balance": str(pp.special_balance),
                "trips_used": pp.trips_used,
                "trips_remaining": pp.trips_remaining,
                "max_trips": pp.package.max_trips,
                "expires_at": pp.expires_at.isoformat() if pp.expires_at else None,
                "activated_at": pp.activated_at.isoformat() if pp.activated_at else None,
            })
    passenger = None
    if pa:
        passenger = {
            "id": pa.id,
            "uuid": str(pa.uuid),
            "full_name": pa.full_name,
            "phone_masked": _mask_phone(pa.phone_number),
            "email": pa.email or "",
            "document_type": pa.document_type or "",
            "document_number": pa.document_number or "",
            "status": pa.status,
            "registered_at": pa.created_at.isoformat() if pa.created_at else None,
        }
    linked_cards = []
    if pa:
        for other in Card.objects.filter(passenger_account=pa).exclude(pk=card.pk):
            linked_cards.append({
                "card_id": other.id,
                "card_uid": other.card_uid,
                "card_number": other.card_number,
                "card_type": other.card_type,
                "status": other.status,
            })

    return {
        "card_id": card.id,
        "card_uid": card.card_uid,
        "card_number": card.card_number,
        "card_type": card.card_type,
        "status": card.status,
        "activated_at": card.activated_at.isoformat() if card.activated_at else None,
        "passenger_name": pa.full_name if pa else "",
        "passenger_phone_masked": _mask_phone(pa.phone_number) if pa else "",
        "passenger": passenger,
        "wallet": {
            "uuid": str(wallet.uuid) if wallet else None,
            "balance": str(wallet.balance_cached) if wallet else "0.00",
            "currency": wallet.currency if wallet else "MZN",
            "status": wallet.status if wallet else None,
        } if wallet else None,
        "active_packages": active_pkgs,
        "linked_cards": linked_cards,
    }


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------

class AgentCardLookupView(APIView):
    """Resolve a card by NFC UID or by digital QR token."""

    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request):
        card_uid = (request.data.get("card_uid") or "").strip()
        qr_token = (request.data.get("qr_token") or "").strip()
        if not card_uid and not qr_token:
            return Response({"detail": "Indique card_uid ou qr_token."}, status=400)

        card = _resolve_card(card_uid=card_uid, qr_token=qr_token)
        if not card:
            audit(
                "AGENT_CARD_LOOKUP_NOT_FOUND",
                actor=request.user,
                entity_type="card", entity_id="",
                ip=client_ip(request),
                after={"card_uid": card_uid, "qr_token_provided": bool(qr_token)},
            )
            return Response({"detail": "Cartao nao encontrado."}, status=404)

        if card.status == Card.Status.BLOCKED:
            return Response({"detail": "Cartao bloqueado.", "card": _serialize_card(card)}, status=403)
        if card.status == Card.Status.LOST:
            return Response({"detail": "Cartao reportado perdido.", "card": _serialize_card(card)}, status=403)

        return Response({"card": _serialize_card(card)})


# ---------------------------------------------------------------------------
# Wallet top-up (cash / m-pesa / e-mola)
# ---------------------------------------------------------------------------

class AgentWalletTopupView(APIView):
    """Agent tops up a passenger wallet.

    Payment methods:
      - cash: confirmed immediately, wallet credited
      - mobile_money: initiates gateway (M-Pesa / E-Mola); webhook confirms
    """

    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request):
        card_uid = (request.data.get("card_uid") or "").strip()
        qr_token = (request.data.get("qr_token") or "").strip()
        try:
            amount = Decimal(str(request.data.get("amount", "0")))
        except Exception:
            return Response({"detail": "Valor invalido."}, status=400)
        if amount <= Decimal("0.00"):
            return Response({"detail": "Valor deve ser positivo."}, status=400)
        method = (request.data.get("method") or "cash").strip().lower()
        payer_phone = (request.data.get("payer_phone") or "").strip()

        card = _resolve_card(card_uid=card_uid, qr_token=qr_token)
        if not card:
            return Response({"detail": "Cartao nao encontrado."}, status=404)
        if card.status not in (Card.Status.ACTIVE,):
            return Response({"detail": f"Cartao {card.card_number} esta {card.status}. Active o cartao primeiro."}, status=400)
        # Resolve the canonical wallet from the passenger account. Both
        # digital and physical cards of the same passenger share it.
        wallet = None
        if card.passenger_account_id:
            try:
                wallet = card.passenger_account.wallet
            except Exception:
                wallet = None
        if wallet is None:
            wallet = card.wallet
        if wallet is None:
            return Response({"detail": "Cartao sem carteira associada. Vincule a um passageiro."}, status=400)
        if wallet.status != Wallet.Status.ACTIVE:
            return Response({"detail": "Carteira bloqueada."}, status=400)

        idem = request.headers.get("Idempotency-Key", uuid4().hex)
        existing = PaymentIntent.objects.filter(idempotency_key=idem).first()
        if existing:
            return Response({
                "payment_intent": str(existing.uuid),
                "reference": existing.reference,
                "status": existing.status,
                "duplicate": True,
            })

        ref = f"TOP-{uuid4().hex[:12].upper()}"
        pi = PaymentIntent.objects.create(
            reference=ref,
            idempotency_key=idem,
            purpose=PaymentIntent.Purpose.POS_CARD_TOPUP,
            amount=amount,
            payer_phone=payer_phone or (card.passenger_account.phone_number if card.passenger_account else ""),
            wallet=wallet,
            status=PaymentIntent.Status.PENDING,
            created_by=request.user,
            metadata={
                "agent_user_id": request.user.id,
                "card_uid": card.card_uid,
                "card_id": card.id,
                "method": method,
                "channel": "POS",
            },
        )

        if method == "cash":
            confirm_payment_immediately(pi, provider_reference=f"CASH-{ref}")
            pi.refresh_from_db()
            audit(
                "AGENT_WALLET_TOPUP_CASH",
                actor=request.user,
                entity_type="payment_intent", entity_id=str(pi.id),
                ip=client_ip(request),
                after={"amount": str(pi.amount), "card_uid": card.card_uid, "reference": pi.reference},
            )
            return Response({
                "payment_intent": str(pi.uuid),
                "reference": pi.reference,
                "status": pi.status,
                "wallet": {
                    "uuid": str(card.wallet.uuid),
                    "balance": str(Wallet.objects.get(pk=card.wallet.pk).balance_cached),
                },
            }, status=201)

        gw_phone = payer_phone or pi.payer_phone
        if not gw_phone:
            pi.status = PaymentIntent.Status.FAILED
            pi.save(update_fields=["status", "updated_at"])
            return Response({"detail": "Telefone do pagador e obrigatorio para Mobile Money."}, status=400)

        gateway = get_payment_gateway(payer_phone=gw_phone)
        result = gateway.initiate_payment(
            reference=ref,
            amount=amount,
            payer_phone=gw_phone,
            description=f"Recarga BusUp {amount} MZN",
        )
        pi.provider = result.provider
        pi.metadata = {
            **(pi.metadata or {}),
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
            return Response({"detail": result.detail_message or result.error or "Falha no pagamento."}, status=502)

        return Response({
            "payment_intent": str(pi.uuid),
            "reference": pi.reference,
            "status": pi.status,
            "detail_message": result.detail_message,
        }, status=201)


# ---------------------------------------------------------------------------
# Package purchase
# ---------------------------------------------------------------------------

class AgentPackagePurchaseView(APIView):
    """Agent activates a package for a passenger card."""

    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request):
        card_uid = (request.data.get("card_uid") or "").strip()
        qr_token = (request.data.get("qr_token") or "").strip()
        package_id = request.data.get("package_id")
        method = (request.data.get("method") or "cash").strip().lower()
        payer_phone = (request.data.get("payer_phone") or "").strip()

        if not package_id:
            return Response({"detail": "package_id obrigatorio."}, status=400)

        card = _resolve_card(card_uid=card_uid, qr_token=qr_token)
        if not card:
            return Response({"detail": "Cartao nao encontrado."}, status=404)
        if card.status != Card.Status.ACTIVE:
            return Response({"detail": "Cartao nao esta activo."}, status=400)
        if not card.passenger_account:
            return Response({"detail": "Cartao nao associado a passageiro."}, status=400)
        if not card.wallet:
            return Response({"detail": "Cartao sem carteira."}, status=400)

        try:
            package = Package.objects.get(pk=package_id, status=Package.Status.ACTIVE)
        except Package.DoesNotExist:
            return Response({"detail": "Pacote indisponivel."}, status=404)

        amount = package.price
        if amount <= Decimal("0.00"):
            return Response({"detail": "Pacote sem preco definido."}, status=400)

        # Business rule: a passenger can only have ONE active package at a
        # time. Recharging the SAME package is allowed (extends validity +
        # resets trips). A different package is rejected with 409 until the
        # current one is exhausted/expired.
        #
        # The check + decision is run under a pessimistic row lock so two
        # parallel POSTs can't both observe "no active package" and end up
        # creating duplicates.
        from django.db import transaction as _tx
        is_recharge = False
        active_pkg = None
        with _tx.atomic():
            existing_active = list(
                card.passenger_account.packages
                .select_for_update()
                .filter(status=PassengerPackage.Status.ACTIVE)
                .select_related("package")
            )
            if existing_active:
                active_pkg = existing_active[0]
                if active_pkg.package_id != package.id:
                    return Response({
                        "detail": (
                            f"O passageiro ja tem o pacote '{active_pkg.package.name}' "
                            f"activo ({active_pkg.trips_remaining} viagens restantes). "
                            f"Aguarde esgotar/expirar ou recarregue o mesmo pacote."
                        ),
                        "code": "PACKAGE_ACTIVE",
                        "active_package": {
                            "id": active_pkg.id,
                            "package_id": active_pkg.package_id,
                            "package_name": active_pkg.package.name,
                            "trips_remaining": active_pkg.trips_remaining,
                            "expires_at": active_pkg.expires_at.isoformat() if active_pkg.expires_at else None,
                        },
                    }, status=409)
                # same package_id → recharge
                is_recharge = True

        idem = request.headers.get("Idempotency-Key", uuid4().hex)
        existing = PaymentIntent.objects.filter(idempotency_key=idem).first()
        if existing:
            # If the previous attempt failed, allow a clean retry (caller
            # should pass a fresh Idempotency-Key, but be defensive).
            if existing.status == PaymentIntent.Status.FAILED:
                return Response({
                    "payment_intent": str(existing.uuid),
                    "reference": existing.reference,
                    "status": existing.status,
                    "duplicate": True,
                    "detail": "Tentativa anterior falhou. Use uma nova chave de idempotencia.",
                }, status=409)
            return Response({
                "payment_intent": str(existing.uuid),
                "reference": existing.reference,
                "status": existing.status,
                "duplicate": True,
            })

        ref = f"PKG-{uuid4().hex[:12].upper()}"
        pi = PaymentIntent.objects.create(
            reference=ref,
            idempotency_key=idem,
            purpose=PaymentIntent.Purpose.POS_CARD_TOPUP,
            amount=amount,
            payer_phone=payer_phone or (card.passenger_account.phone_number or ""),
            wallet=card.wallet,
            status=PaymentIntent.Status.PENDING,
            created_by=request.user,
            metadata={
                "agent_user_id": request.user.id,
                "card_uid": card.card_uid,
                "card_id": card.id,
                "method": method,
                "channel": "POS",
                "kind": "package",
                "package_id": package.id,
                "package_name": package.name,
            },
        )

        def _activate_package():
            from datetime import timedelta as _td
            now = timezone.now()
            if is_recharge and active_pkg is not None:
                # Recharge: top-up the same package. Re-add max_trips and push
                # expiry by validity_days from now (whichever is later).
                ap = active_pkg
                ap.trips_remaining = (ap.trips_remaining or 0) + package.max_trips
                new_expiry = now + _td(days=package.validity_days)
                if not ap.expires_at or ap.expires_at < new_expiry:
                    ap.expires_at = new_expiry
                ap.status = PassengerPackage.Status.ACTIVE
                ap.save(update_fields=["trips_remaining", "expires_at", "status", "updated_at"])
                return ap
            return PassengerPackage.objects.create(
                passenger_account=card.passenger_account,
                package=package,
                wallet=card.passenger_account.wallet if hasattr(card.passenger_account, "wallet") else card.wallet,
                special_balance=Decimal("0.00"),
                trips_used=0,
                trips_remaining=package.max_trips,
                status=PassengerPackage.Status.ACTIVE,
                expires_at=now + _td(days=package.validity_days),
            )

        if method == "cash":
            pi.status = PaymentIntent.Status.CONFIRMED
            pi.confirmed_at = timezone.now()
            pi.provider_reference = f"CASH-{ref}"
            pi.save(update_fields=["status", "confirmed_at", "provider_reference", "updated_at"])
            pp = _activate_package()
            audit(
                "AGENT_PACKAGE_PURCHASE_CASH",
                actor=request.user,
                entity_type="passenger_package", entity_id=str(pp.id),
                ip=client_ip(request),
                after={"package_id": package.id, "amount": str(amount), "reference": ref},
            )
            return Response({
                "payment_intent": str(pi.uuid),
                "reference": pi.reference,
                "status": pi.status,
                "package": {
                    "id": pp.id,
                    "name": package.name,
                    "trips_remaining": pp.trips_remaining,
                    "expires_at": pp.expires_at.isoformat(),
                },
            }, status=201)

        gw_phone = payer_phone or pi.payer_phone
        if not gw_phone:
            pi.status = PaymentIntent.Status.FAILED
            pi.save(update_fields=["status", "updated_at"])
            return Response({"detail": "Telefone do pagador e obrigatorio para Mobile Money."}, status=400)

        gateway = get_payment_gateway(payer_phone=gw_phone)
        result = gateway.initiate_payment(
            reference=ref,
            amount=amount,
            payer_phone=gw_phone,
            description=f"Pacote BusUp: {package.name} ({amount} MZN)",
        )
        pi.provider = result.provider
        pi.metadata = {
            **(pi.metadata or {}),
            "gateway_request": result.request_payload or {},
            "gateway_response": result.response_payload or {},
        }
        if result.success:
            pi.provider_reference = result.provider_reference
            pi.status = PaymentIntent.Status.CONFIRMED
            pi.confirmed_at = timezone.now()
            pi.save(update_fields=["status", "confirmed_at", "provider", "provider_reference", "metadata", "updated_at"])
            pp = _activate_package()
            return Response({
                "payment_intent": str(pi.uuid),
                "reference": pi.reference,
                "status": pi.status,
                "package": {
                    "id": pp.id,
                    "name": package.name,
                    "trips_remaining": pp.trips_remaining,
                    "expires_at": pp.expires_at.isoformat(),
                },
            }, status=201)
        elif result.pending:
            pi.provider_reference = result.provider_reference
            pi.save(update_fields=["provider", "provider_reference", "metadata", "updated_at"])
            return Response({
                "payment_intent": str(pi.uuid),
                "reference": pi.reference,
                "status": pi.status,
                "detail_message": result.detail_message,
            }, status=202)
        else:
            pi.status = PaymentIntent.Status.FAILED
            pi.save(update_fields=["status", "provider", "metadata", "updated_at"])
            return Response({"detail": result.detail_message or result.error or "Falha no pagamento."}, status=502)


# ---------------------------------------------------------------------------
# Wallet payment for a sale (debit wallet directly)
# ---------------------------------------------------------------------------

class AgentWalletPaymentView(APIView):
    """Passenger pays for a trip using their wallet balance (debit).

    Body: card_uid OR qr_token + amount + reason (e.g. trip_id).
    Backend debits wallet and returns the new balance. Caller is then
    responsible for issuing the ticket through the normal sale flow with
    `method=wallet` (handled by AgentSaleCreateView when extended).
    """

    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request):
        card_uid = (request.data.get("card_uid") or "").strip()
        qr_token = (request.data.get("qr_token") or "").strip()
        try:
            amount = Decimal(str(request.data.get("amount", "0")))
        except Exception:
            return Response({"detail": "Valor invalido."}, status=400)
        if amount <= Decimal("0.00"):
            return Response({"detail": "Valor deve ser positivo."}, status=400)

        card = _resolve_card(card_uid=card_uid, qr_token=qr_token)
        if not card:
            return Response({"detail": "Cartao nao encontrado."}, status=404)
        if card.status != Card.Status.ACTIVE:
            return Response({"detail": "Cartao nao esta activo."}, status=400)
        if not card.wallet:
            return Response({"detail": "Cartao sem carteira."}, status=400)

        idem = request.headers.get("Idempotency-Key", uuid4().hex)
        if WalletTransaction.objects.filter(reference=f"PAY-{idem[:16].upper()}").exists():
            tx = WalletTransaction.objects.get(reference=f"PAY-{idem[:16].upper()}")
            return Response({
                "reference": tx.reference,
                "status": tx.status,
                "balance_after": str(tx.balance_after),
                "duplicate": True,
            })

        try:
            tx = debit_wallet(
                wallet=card.wallet,
                amount=amount,
                tx_type=WalletTransaction.Type.FARE_DEBIT,
                source=f"agent:{request.user.id}",
                reference=f"PAY-{idem[:16].upper()}",
                metadata={
                    "agent_user_id": request.user.id,
                    "card_uid": card.card_uid,
                    "card_id": card.id,
                    "channel": "POS",
                },
            )
        except InsufficientBalanceError:
            return Response({"detail": "Saldo insuficiente."}, status=402)
        except WalletBlockedError:
            return Response({"detail": "Carteira bloqueada."}, status=403)

        audit(
            "AGENT_WALLET_DEBIT",
            actor=request.user,
            entity_type="wallet_transaction", entity_id=str(tx.id),
            ip=client_ip(request),
            after={"amount": str(amount), "card_uid": card.card_uid, "balance_after": str(tx.balance_after)},
        )
        return Response({
            "reference": tx.reference,
            "status": tx.status,
            "amount": str(tx.amount),
            "balance_before": str(tx.balance_before),
            "balance_after": str(tx.balance_after),
        }, status=201)


# ---------------------------------------------------------------------------
# Package catalog
# ---------------------------------------------------------------------------

class AgentCardCaptureUidView(APIView):
    """Capture the UID of a brand new physical card.

    Gated for production: only allowed when
      - `settings.ALLOW_AGENT_CARD_CAPTURE = True` (staging / test env), OR
      - the requester is staff/superuser.

    In production the canonical card loading happens via the admin portal
    (Excel import or one-by-one); agents are NOT supposed to have this
    privilege to keep card inventory under tight control.
    """

    permission_classes = [IsAuthenticated, IsActiveAgent]

    def post(self, request):
        from django.conf import settings as _settings
        if not (getattr(_settings, "ALLOW_AGENT_CARD_CAPTURE", False)
                or request.user.is_staff or request.user.is_superuser):
            return Response(
                {"detail": "Operacao restrita ao portal de administracao."},
                status=403,
            )
        uid = (request.data.get("card_uid") or "").strip().upper()
        if not uid:
            return Response({"detail": "card_uid obrigatorio."}, status=400)

        batch = (request.data.get("batch") or "").strip()
        manufacturer = (request.data.get("manufacturer") or "").strip()
        technology = (request.data.get("card_technology") or Card.Technology.NFC_UID).strip()
        if technology not in {c[0] for c in Card.Technology.choices}:
            technology = Card.Technology.NFC_UID

        existing = Card.objects.filter(card_uid=uid).first()
        if existing:
            audit(
                "AGENT_CARD_UID_RESEEN",
                actor=request.user,
                entity_type="card", entity_id=str(existing.id),
                ip=client_ip(request),
                after={"card_uid": uid, "status": existing.status},
            )
            return Response({
                "card_id": existing.id,
                "card_uid": existing.card_uid,
                "card_number": existing.card_number,
                "status": existing.status,
                "card_technology": existing.card_technology,
                "issued_batch": existing.issued_batch,
                "created": False,
                "detail": "Cartao ja registado.",
            })

        card = Card.objects.create(
            card_type=Card.CardType.PHYSICAL,
            card_uid=uid,
            card_technology=technology,
            status=Card.Status.INACTIVE,
            issued_batch=batch,
            manufacturer=manufacturer,
            issued_at=timezone.now(),
        )
        audit(
            "AGENT_CARD_UID_CAPTURED",
            actor=request.user,
            entity_type="card", entity_id=str(card.id),
            ip=client_ip(request),
            after={"card_uid": uid, "batch": batch, "manufacturer": manufacturer},
        )
        return Response({
            "card_id": card.id,
            "card_uid": card.card_uid,
            "card_number": card.card_number,
            "status": card.status,
            "card_technology": card.card_technology,
            "issued_batch": card.issued_batch,
            "created": True,
        }, status=201)


class AgentPackagesListView(APIView):
    """Lists active packages the agent can sell."""

    permission_classes = [IsAuthenticated, IsActiveAgent]

    def get(self, request):
        packages = Package.objects.filter(status=Package.Status.ACTIVE).order_by("name")
        return Response({
            "results": [{
                "id": p.id,
                "uuid": str(p.uuid),
                "name": p.name,
                "description": p.description,
                "price": str(p.price),
                "validity_days": p.validity_days,
                "max_trips": p.max_trips,
                "discount_type": p.discount_type,
                "discount_value": str(p.discount_value),
            } for p in packages]
        })
