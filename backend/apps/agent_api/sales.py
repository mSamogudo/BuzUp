"""Agent POS sales service.

Reuses the guest_checkouts purchase pipeline to create a sale + payment intent
on behalf of the passenger. Tickets are issued only after the PaymentIntent
transitions to CONFIRMED (idempotent via process_payment_callback).
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from apps.audit.services import audit
from apps.devices.models import Device
from apps.fares.services import FareConflictError, NoFareFoundError, quote_fare
from apps.guest_checkouts.models import GuestCheckout
from apps.notifications.services import notify_by_phone
from apps.packages.services import consume_package_trip, find_active_package_for_route
from apps.payments.models import PaymentIntent
from apps.payments.services.gateway import get_payment_gateway
from apps.payments.services.processing import confirm_payment_immediately
from apps.routes.models import Route, Stop
from apps.routes.services import RouteSegmentError, resolve_route_segment
from apps.trips.models import Trip
from apps.users.otp import normalize_otp_phone


class SaleError(Exception):
    pass


def create_pos_sale(
    *,
    agent,
    device: Device | None,
    trip_id: int | None,
    route_id: int | None,
    origin_stop_id: int,
    destination_stop_id: int,
    passenger_phone: str,
    quantity: int = 1,
    idempotency_key: str = "",
) -> tuple[GuestCheckout, PaymentIntent]:
    """Create a sale + initiate payment for an agent's POS terminal.

    Backend computes the fare. Returns (GuestCheckout, PaymentIntent).
    """
    if device and device.status == Device.Status.BLOCKED:
        raise SaleError("Dispositivo bloqueado. Contacte o administrador.")

    if device and device.assigned_agent_id != getattr(agent, "user_id", None):
        raise SaleError("Dispositivo nao esta atribuido a este agente.")

    phone = normalize_otp_phone(passenger_phone)
    if not phone:
        raise SaleError("Telefone do passageiro invalido.")

    if quantity < 1 or quantity > 10:
        raise SaleError("Quantidade deve estar entre 1 e 10.")

    trip = None
    if trip_id:
        trip = Trip.objects.select_related("route").filter(
            pk=trip_id,
            status__in=[Trip.Status.BOARDING, Trip.Status.DEPARTED],
        ).first()
        if not trip:
            raise SaleError("Viagem nao encontrada ou ja encerrada.")
        route = trip.route
    elif route_id:
        route = Route.objects.filter(pk=route_id, status=Route.Status.ACTIVE).first()
        if not route:
            raise SaleError("Rota nao encontrada.")
    else:
        raise SaleError("Forneca trip_id ou route_id.")

    origin = Stop.objects.filter(pk=origin_stop_id).first()
    destination = Stop.objects.filter(pk=destination_stop_id).first()
    if not origin or not destination:
        raise SaleError("Origem ou destino nao encontrados.")
    if origin.pk == destination.pk:
        raise SaleError("Origem e destino devem ser diferentes.")

    try:
        resolve_route_segment(route, origin.pk, destination.pk)
    except RouteSegmentError as e:
        raise SaleError(str(e))

    try:
        quote = quote_fare(route=route, origin_stop=origin, destination_stop=destination)
    except NoFareFoundError as e:
        audit(
            "FARE_RESOLUTION_FAILED",
            actor=getattr(agent, "user", None),
            entity_type="route", entity_id=str(route.id),
            after={"reason": str(e), "origin": origin.pk, "destination": destination.pk},
        )
        raise SaleError(str(e))
    except FareConflictError as e:
        audit(
            "FARE_RESOLUTION_FAILED",
            actor=getattr(agent, "user", None),
            entity_type="route", entity_id=str(route.id),
            after={"reason": "conflict", "detail": str(e)},
        )
        raise SaleError("Conflito de tarifas. Contacte o administrador.")

    total = quote.amount * quantity
    ref = f"AS-{uuid4().hex[:12].upper()}"

    with transaction.atomic():
        gc = GuestCheckout.objects.create(
            reference=ref,
            payer_phone=phone,
            buyer_name="",
            route_code=route.code,
            route_name=route.name,
            origin_stop=origin.name,
            destination_stop=destination.name,
            origin_stop_ref=origin,
            destination_stop_ref=destination,
            trip=trip,
            quantity=quantity,
            unit_amount=quote.amount,
            total_amount=total,
            status=GuestCheckout.Status.PAYMENT_PENDING,
            expires_at=timezone.now() + timedelta(minutes=15),
        )

        pi = PaymentIntent.objects.create(
            reference=f"PAY-{ref}",
            idempotency_key=idempotency_key or f"agent-sale-{ref}",
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
            amount=total,
            payer_phone=phone,
            guest_checkout=gc,
            status=PaymentIntent.Status.PENDING,
            expires_at=gc.expires_at,
            metadata={
                "agent_id": getattr(agent, "id", None),
                "agent_user_id": getattr(agent, "user_id", None),
                "device_id": device.id if device else None,
                "device_serial": device.serial_number if device else "",
            },
            created_by=getattr(agent, "user", None),
        )

    audit(
        "SALE_CREATED",
        actor=getattr(agent, "user", None),
        entity_type="guest_checkout",
        entity_id=str(gc.id),
        after={
            "reference": gc.reference,
            "amount": str(total),
            "quantity": quantity,
            "trip_id": trip.id if trip else None,
            "device_serial": device.serial_number if device else "",
        },
    )

    return gc, pi


def create_card_sale(
    *,
    agent,
    device: Device | None,
    trip_id: int | None,
    route_id: int | None,
    origin_stop_id: int,
    destination_stop_id: int,
    card_uid: str = "",
    qr_token: str = "",
    quantity: int = 1,
    idempotency_key: str = "",
) -> tuple[GuestCheckout, PaymentIntent, list]:
    """Card-based POS sale: lookup card -> debit wallet -> confirm + issue.

    Returns (GuestCheckout, PaymentIntent, list[DigitalTravelPass]).
    Raises SaleError on validation / insufficient balance / blocked card.
    """
    import hashlib
    from apps.cards.models import Card
    from apps.wallets.models import Wallet, WalletTransaction
    from apps.wallets.services import debit_wallet, InsufficientBalanceError, WalletBlockedError

    if device and device.status == Device.Status.BLOCKED:
        raise SaleError("Dispositivo bloqueado. Contacte o administrador.")
    if device and device.assigned_agent_id != getattr(agent, "user_id", None):
        raise SaleError("Dispositivo nao esta atribuido a este agente.")
    if quantity < 1 or quantity > 10:
        raise SaleError("Quantidade deve estar entre 1 e 10.")

    # Resolve card by UID or QR token
    card = None
    if card_uid:
        card = (
            Card.objects.select_related("passenger_account")
            .filter(card_uid=card_uid.strip().upper())
            .first()
        )
    elif qr_token:
        token_hash = hashlib.sha256(qr_token.strip().encode()).hexdigest()
        card = (
            Card.objects.select_related("passenger_account")
            .filter(qr_token_hash=token_hash)
            .first()
        )
    if not card:
        raise SaleError("Cartao nao encontrado.")
    if card.status != Card.Status.ACTIVE:
        raise SaleError(f"Cartao {card.card_number} esta {card.status}.")
    if not card.passenger_account_id:
        raise SaleError("Cartao nao esta vinculado a um passageiro.")

    pa = card.passenger_account
    try:
        wallet = pa.wallet
    except Exception:
        wallet = None
    if wallet is None:
        raise SaleError("Passageiro sem carteira activa.")
    if wallet.status != Wallet.Status.ACTIVE:
        raise SaleError("Carteira bloqueada.")

    # Resolve trip / route + fare
    trip = None
    if trip_id:
        trip = Trip.objects.select_related("route").filter(
            pk=trip_id,
            status__in=[Trip.Status.BOARDING, Trip.Status.DEPARTED],
        ).first()
        if not trip:
            raise SaleError("Viagem nao encontrada ou ja encerrada.")
        route = trip.route
    elif route_id:
        route = Route.objects.filter(pk=route_id, status=Route.Status.ACTIVE).first()
        if not route:
            raise SaleError("Rota nao encontrada.")
    else:
        raise SaleError("Forneca trip_id ou route_id.")

    origin = Stop.objects.filter(pk=origin_stop_id).first()
    destination = Stop.objects.filter(pk=destination_stop_id).first()
    if not origin or not destination:
        raise SaleError("Origem ou destino nao encontrados.")
    if origin.pk == destination.pk:
        raise SaleError("Origem e destino devem ser diferentes.")

    try:
        resolve_route_segment(route, origin.pk, destination.pk)
    except RouteSegmentError as e:
        raise SaleError(str(e))

    try:
        quote = quote_fare(route=route, origin_stop=origin, destination_stop=destination)
    except NoFareFoundError as e:
        raise SaleError(str(e))
    except FareConflictError:
        raise SaleError("Conflito de tarifas. Contacte o administrador.")

    base_unit = quote.amount
    gross_total = base_unit * quantity  # fare value (shown on the ticket)
    ref = f"AS-{uuid4().hex[:12].upper()}"
    phone = pa.phone_number or ""

    # Single atomic block:
    #   1. Re-read the wallet WITH a row lock (`select_for_update`) so two
    #      concurrent card sales for the same passenger can't both pass the
    #      balance check and overdraw.
    #   2. Create GuestCheckout + PaymentIntent.
    #   3. Debit the wallet (idempotent via the FARE-{ref} reference).
    #   4. Confirm the PaymentIntent (issues tickets via shared processor).
    # If ANY step raises, the whole transaction rolls back and the wallet
    # stays untouched, so no scenario leaves money debited without a ticket.
    from apps.wallets.models import Wallet  # local import to avoid cycle

    with transaction.atomic():
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        if wallet.status != Wallet.Status.ACTIVE:
            raise SaleError("Carteira bloqueada.")

        # Apply the passenger's active package (same rule as the mobile app):
        # consume one trip per unit and only charge the wallet the discounted
        # remainder. Without this the POS overcharged cardholders with a
        # package the full base fare. Consumption happens inside this atomic,
        # so an insufficient-balance abort below rolls it back.
        subscription = find_active_package_for_route(pa, route)
        package_meta: dict = {}
        if subscription:
            charged_total = Decimal("0.00")
            for _ in range(quantity):
                charged_total += consume_package_trip(subscription, base_unit)
            package_meta = {
                "package_id": subscription.package_id,
                "package_name": subscription.package.name,
                "discount_type": subscription.package.discount_type,
                "base_total": str(gross_total),
                "charged_total": str(charged_total),
            }
        else:
            charged_total = gross_total

        if wallet.balance_cached < charged_total:
            raise SaleError(
                f"Saldo insuficiente. Saldo: {wallet.balance_cached} MZN. Necessario: {charged_total} MZN."
            )

        # Issued passes read `unit_amount` as their fare — record the net paid
        # (after package discount) so the ticket shows what was charged, not
        # the gross fare.
        net_unit = (charged_total / quantity).quantize(Decimal("0.01")) if quantity else charged_total
        gc = GuestCheckout.objects.create(
            reference=ref,
            payer_phone=phone,
            buyer_name=pa.full_name or "",
            route_code=route.code,
            route_name=route.name,
            origin_stop=origin.name,
            destination_stop=destination.name,
            origin_stop_ref=origin,
            destination_stop_ref=destination,
            trip=trip,
            quantity=quantity,
            unit_amount=net_unit,
            total_amount=charged_total,
            status=GuestCheckout.Status.PAYMENT_PENDING,
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        pi = PaymentIntent.objects.create(
            reference=f"PAY-{ref}",
            idempotency_key=idempotency_key or f"card-sale-{ref}",
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
            amount=charged_total,
            payer_phone=phone,
            guest_checkout=gc,
            wallet=wallet,
            status=PaymentIntent.Status.PENDING,
            provider="wallet",
            channel="POS_CARD",
            expires_at=gc.expires_at,
            metadata={
                "agent_id": getattr(agent, "id", None),
                "agent_user_id": getattr(agent, "user_id", None),
                "device_id": device.id if device else None,
                "device_serial": device.serial_number if device else "",
                "payment_method": "card",
                "card_uid": card.card_uid,
                "card_id": card.id,
                "passenger_account_id": pa.id,
                **package_meta,
            },
            created_by=getattr(agent, "user", None),
        )

        if charged_total > Decimal("0.00"):
            try:
                debit_wallet(
                    wallet=wallet,
                    amount=charged_total,
                    tx_type=WalletTransaction.Type.FARE_DEBIT,
                    source=f"agent:{getattr(agent, 'user_id', '')}",
                    reference=f"FARE-{ref}",
                    metadata={
                        "agent_user_id": getattr(agent, "user_id", None),
                        "card_uid": card.card_uid,
                        "card_id": card.id,
                        "guest_checkout": gc.reference,
                        "channel": "POS_CARD",
                        **package_meta,
                    },
                    notify=False,
                )
            except InsufficientBalanceError as e:
                raise SaleError(str(e))
            except WalletBlockedError as e:
                raise SaleError(str(e))

        # Confirm + issue tickets inside the same atomic. If issuance fails
        # the wallet debit is rolled back automatically by Django.
        confirm_payment_immediately(pi, provider_reference=f"WALLET-{ref}")

    audit(
        "SALE_CREATED",
        actor=getattr(agent, "user", None),
        entity_type="guest_checkout",
        entity_id=str(gc.id),
        after={
            "reference": gc.reference,
            "amount": str(charged_total),
            "base_amount": str(gross_total),
            "quantity": quantity,
            "trip_id": trip.id if trip else None,
            "device_serial": device.serial_number if device else "",
            "method": "card",
            "card_uid": card.card_uid,
        },
    )

    pi.refresh_from_db()
    gc.refresh_from_db()
    passes = list(gc.travel_passes.all())
    return gc, pi, passes


def request_payment(gc: GuestCheckout, pi: PaymentIntent) -> dict:
    """Trigger the configured payment gateway to ask passenger to confirm.

    Returns dict with payment status info. Idempotent: if PI already CONFIRMED,
    just returns the current status.
    """
    pi.refresh_from_db()
    if pi.status == PaymentIntent.Status.CONFIRMED:
        return {"status": pi.status, "provider": pi.provider, "reference": pi.reference, "detail": "Pagamento ja confirmado."}

    gateway = get_payment_gateway(payer_phone=pi.payer_phone)
    result = gateway.initiate_payment(
        reference=pi.reference,
        amount=pi.amount,
        payer_phone=pi.payer_phone,
        description=f"BuzUp bilhete {gc.route_code}",
    )

    pi.provider = result.provider
    pi.metadata = {
        **(pi.metadata or {}),
        "gateway_request": result.request_payload or {},
        "gateway_response": result.response_payload or {},
    }

    audit(
        "PAYMENT_REQUESTED",
        actor=pi.created_by,
        entity_type="payment_intent", entity_id=str(pi.id),
        after={"provider": result.provider, "amount": str(pi.amount), "success": result.success},
    )

    if result.success:
        pi.provider_reference = result.provider_reference
        pi.save(update_fields=["provider", "provider_reference", "metadata", "updated_at"])
        confirm_payment_immediately(pi, result.provider_reference)
        pi.refresh_from_db()
        notify_by_phone(
            pi.payer_phone,
            "payment_confirmed",
            "Pagamento confirmado",
            f"O seu pagamento de {pi.amount} MZN foi confirmado.",
            data={"payment_reference": pi.reference, "guest_checkout_reference": gc.reference},
        )
        return {"status": pi.status, "provider": pi.provider, "reference": pi.reference, "detail": result.detail_message}

    if result.pending:
        pi.provider_reference = result.provider_reference
        pi.status = PaymentIntent.Status.PENDING
        pi.save(update_fields=["status", "provider", "provider_reference", "metadata", "updated_at"])
        return {"status": pi.status, "provider": pi.provider, "reference": pi.reference, "detail": result.detail_message}

    gc.status = GuestCheckout.Status.CANCELLED
    gc.save(update_fields=["status", "updated_at"])
    pi.status = PaymentIntent.Status.FAILED
    pi.save(update_fields=["status", "provider", "metadata", "updated_at"])
    audit(
        "PAYMENT_FAILED",
        actor=pi.created_by,
        entity_type="payment_intent", entity_id=str(pi.id),
        after={"reason": result.error or result.detail_message},
    )
    notify_by_phone(
        pi.payer_phone,
        "payment_failed",
        "Pagamento nao concluido",
        result.detail_message or "Tente novamente.",
        data={"payment_reference": pi.reference},
    )
    return {"status": pi.status, "provider": pi.provider, "reference": pi.reference, "detail": result.detail_message, "error": result.error}
