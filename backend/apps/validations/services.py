from __future__ import annotations

import hashlib
from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.cards.models import Card
from apps.devices.models import Device
from apps.fares.services import NoFareFoundError, quote_fare
from apps.guest_checkouts.models import DigitalTravelPass
from apps.guest_checkouts.ticket_codes import ticket_reference, ticket_short_code
from apps.packages.services import consume_package_trip, find_active_package_for_route
from apps.routes.models import Route, Stop
from apps.routes.services import RouteSegmentError, resolve_route_segment
from apps.trips.models import Trip
from apps.validations.models import ValidationEvent
from apps.wallets.models import WalletTransaction
from apps.wallets.services import InsufficientBalanceError, WalletBlockedError, debit_wallet


def _resolve_device(serial: str) -> Device | None:
    if not serial:
        return None
    return Device.objects.filter(serial_number=serial).first()


def _charge_with_package_fallback(
    passenger_account,
    wallet,
    route: Route,
    base_fare: Decimal,
    idempotency_key: str,
    metadata: dict,
) -> tuple[Decimal, str, str | None]:
    if passenger_account:
        sub = find_active_package_for_route(passenger_account, route)
        if sub:
            actual_charge = consume_package_trip(sub, base_fare)
            if actual_charge <= Decimal("0.00"):
                return Decimal("0.00"), f"package:{sub.package.name}", None

            if wallet:
                tx = debit_wallet(
                    wallet=wallet,
                    amount=actual_charge,
                    tx_type=WalletTransaction.Type.FARE_DEBIT,
                    source=f"validation:{idempotency_key}",
                    reference=f"VAL-{idempotency_key[:16]}",
                    metadata=metadata,
                )
                return actual_charge, f"package_partial:{sub.package.name}", tx.reference

    if wallet:
        tx = debit_wallet(
            wallet=wallet,
            amount=base_fare,
            tx_type=WalletTransaction.Type.FARE_DEBIT,
            source=f"validation:{idempotency_key}",
            reference=f"VAL-{idempotency_key[:16]}",
            metadata=metadata,
        )
        return base_fare, "wallet", tx.reference

    raise InsufficientBalanceError("Sem saldo disponivel.")


def validate_card(
    card_uid: str,
    route_id: int,
    origin_stop_id: int | None = None,
    destination_stop_id: int | None = None,
    trip_id: int | None = None,
    device_serial: str = "",
    idempotency_key: str = "",
) -> ValidationEvent:
    existing = ValidationEvent.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing

    device = _resolve_device(device_serial)
    if device and device.status == Device.Status.BLOCKED:
        return _denied(ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO, ValidationEvent.FailureReason.DEVICE_BLOCKED, idempotency_key, device=device)

    try:
        card = Card.objects.select_related("wallet", "passenger_account").get(card_uid=card_uid)
    except Card.DoesNotExist:
        return _denied(ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO, ValidationEvent.FailureReason.INVALID_TOKEN, idempotency_key, device=device)

    if card.status != Card.Status.ACTIVE:
        return _denied(ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO, ValidationEvent.FailureReason.CARD_BLOCKED, idempotency_key, physical_card=card, device=device)

    if not card.wallet:
        return _denied(ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO, ValidationEvent.FailureReason.INSUFFICIENT_BALANCE, idempotency_key, physical_card=card, device=device)

    try:
        route = Route.objects.get(pk=route_id)
    except Route.DoesNotExist:
        return _denied(ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO, ValidationEvent.FailureReason.ROUTE_NOT_ALLOWED, idempotency_key, physical_card=card, device=device)

    origin = Stop.objects.filter(pk=origin_stop_id).first() if origin_stop_id else None
    destination = Stop.objects.filter(pk=destination_stop_id).first() if destination_stop_id else None
    trip = Trip.objects.filter(pk=trip_id, route=route).first() if trip_id else None
    if trip_id and (not trip or trip.status not in {Trip.Status.BOARDING, Trip.Status.DEPARTED}):
        return _denied(ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO, ValidationEvent.FailureReason.ROUTE_NOT_ALLOWED, idempotency_key, physical_card=card, wallet=card.wallet, route=route, origin_stop=origin, destination_stop=destination, device=device)

    try:
        resolve_route_segment(route, origin_stop_id, destination_stop_id)
    except RouteSegmentError:
        return _denied(ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO, ValidationEvent.FailureReason.ROUTE_NOT_ALLOWED, idempotency_key, physical_card=card, wallet=card.wallet, route=route, origin_stop=origin, destination_stop=destination, device=device)

    try:
        quote = quote_fare(route=route, origin_stop=origin, destination_stop=destination)
    except NoFareFoundError:
        return _denied(ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO, ValidationEvent.FailureReason.NO_FARE_FOUND, idempotency_key, physical_card=card, route=route, origin_stop=origin, destination_stop=destination, device=device)

    # Carga + criacao do evento no MESMO atomic: assim, se dois pedidos com a
    # mesma idempotency_key correrem em paralelo, o segundo colide na unique
    # constraint do ValidationEvent e o rollback desfaz o debito/consumo de
    # pacote dessa tentativa (evita duplo-debito e duplo-consumo de pacote).
    try:
        with transaction.atomic():
            amount_charged, charge_source, tx_ref = _charge_with_package_fallback(
                passenger_account=card.passenger_account,
                wallet=card.wallet,
                route=route,
                base_fare=quote.amount,
                idempotency_key=idempotency_key,
                metadata={"route": route.code, "card_uid": card_uid},
            )
            return ValidationEvent.objects.create(
                validation_type=ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO,
                passenger_account=card.passenger_account, wallet=card.wallet,
                physical_card=card, route=route, trip=trip,
                origin_stop=origin, destination_stop=destination, device=device,
                amount_debited=amount_charged, status=ValidationEvent.Status.APPROVED,
                idempotency_key=idempotency_key, wallet_transaction_ref=tx_ref or charge_source,
            )
    except InsufficientBalanceError:
        return _denied(ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO, ValidationEvent.FailureReason.INSUFFICIENT_BALANCE, idempotency_key, physical_card=card, wallet=card.wallet, route=route, origin_stop=origin, destination_stop=destination, device=device)
    except WalletBlockedError:
        return _denied(ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO, ValidationEvent.FailureReason.ACCOUNT_BLOCKED, idempotency_key, physical_card=card, wallet=card.wallet, route=route, device=device)
    except IntegrityError:
        # Corrida: outro pedido com a mesma idempotency_key ja confirmou.
        existing = ValidationEvent.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing
        raise


def validate_qr_pass(
    token: str,
    route_id: int | None = None,
    trip_id: int | None = None,
    device_serial: str = "",
    idempotency_key: str = "",
) -> ValidationEvent:
    existing = ValidationEvent.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing

    device = _resolve_device(device_serial)
    if device and device.status == Device.Status.BLOCKED:
        return _denied(ValidationEvent.ValidationType.DIGITAL_TRAVEL_PASS, ValidationEvent.FailureReason.DEVICE_BLOCKED, idempotency_key, device=device)

    try:
        travel_pass = _resolve_digital_travel_pass(token, route_id=route_id, trip_id=trip_id)
    except DigitalTravelPass.DoesNotExist:
        return _denied(ValidationEvent.ValidationType.DIGITAL_TRAVEL_PASS, ValidationEvent.FailureReason.INVALID_TOKEN, idempotency_key, device=device)

    if travel_pass.status == DigitalTravelPass.Status.USED:
        return _denied(ValidationEvent.ValidationType.DIGITAL_TRAVEL_PASS, ValidationEvent.FailureReason.PASS_ALREADY_USED, idempotency_key, digital_travel_pass=travel_pass, device=device)
    if travel_pass.status == DigitalTravelPass.Status.EXPIRED:
        return _denied(ValidationEvent.ValidationType.DIGITAL_TRAVEL_PASS, ValidationEvent.FailureReason.PASS_EXPIRED, idempotency_key, digital_travel_pass=travel_pass, device=device)
    if travel_pass.status != DigitalTravelPass.Status.ACTIVE:
        return _denied(ValidationEvent.ValidationType.DIGITAL_TRAVEL_PASS, ValidationEvent.FailureReason.INVALID_TOKEN, idempotency_key, digital_travel_pass=travel_pass, device=device)

    now = timezone.now()
    if travel_pass.valid_until and now > travel_pass.valid_until:
        travel_pass.status = DigitalTravelPass.Status.EXPIRED
        travel_pass.save(update_fields=["status", "updated_at"])
        return _denied(ValidationEvent.ValidationType.DIGITAL_TRAVEL_PASS, ValidationEvent.FailureReason.PASS_EXPIRED, idempotency_key, digital_travel_pass=travel_pass, device=device)

    vtype = ValidationEvent.ValidationType.GUEST_DIGITAL_TRAVEL_PASS if (travel_pass.guest_checkout and not travel_pass.passenger_account) else ValidationEvent.ValidationType.DIGITAL_TRAVEL_PASS
    route = Route.objects.filter(pk=route_id).first() if route_id else None
    trip = Trip.objects.filter(pk=trip_id).first() if trip_id else None
    if trip and trip.status not in {Trip.Status.BOARDING, Trip.Status.DEPARTED}:
        return _denied(vtype, ValidationEvent.FailureReason.ROUTE_NOT_ALLOWED, idempotency_key, digital_travel_pass=travel_pass, device=device)
    if trip and route and trip.route_id != route.id:
        return _denied(vtype, ValidationEvent.FailureReason.ROUTE_NOT_ALLOWED, idempotency_key, digital_travel_pass=travel_pass, route=route, device=device)

    with transaction.atomic():
        tp = DigitalTravelPass.objects.select_for_update().get(pk=travel_pass.pk)
        if tp.status != DigitalTravelPass.Status.ACTIVE:
            return _denied(vtype, ValidationEvent.FailureReason.PASS_ALREADY_USED, idempotency_key, digital_travel_pass=tp, device=device)
        tp.status = DigitalTravelPass.Status.USED
        tp.used_at = now
        tp.save(update_fields=["status", "used_at", "updated_at"])

    return ValidationEvent.objects.create(
        validation_type=vtype, passenger_account=travel_pass.passenger_account,
        wallet=travel_pass.wallet, digital_travel_pass=travel_pass,
        route=route, trip=trip, device=device,
        amount_debited=travel_pass.fare_amount, status=ValidationEvent.Status.APPROVED,
        idempotency_key=idempotency_key,
    )


def _resolve_digital_travel_pass(
    token_or_short_code: str,
    route_id: int | None = None,
    trip_id: int | None = None,
) -> DigitalTravelPass:
    lookup = str(token_or_short_code or "").strip()
    token_hash = hashlib.sha256(lookup.encode()).hexdigest()
    base_qs = DigitalTravelPass.objects.select_related("guest_checkout", "passenger_account", "wallet")

    try:
        return base_qs.get(token_hash=token_hash)
    except DigitalTravelPass.DoesNotExist:
        pass

    normalized = "".join(ch for ch in lookup.upper() if ch.isalnum())
    short_code = ticket_short_code(normalized)
    if len(short_code) != 4 or normalized != short_code:
        raise DigitalTravelPass.DoesNotExist

    now = timezone.now()
    qs = base_qs.filter(
        guest_checkout__isnull=False,
        created_at__gte=now - timedelta(days=7),
    )
    if trip_id:
        qs = qs.filter(Q(trip_id=trip_id) | Q(guest_checkout__trip_id=trip_id))
    if route_id:
        route = Route.objects.filter(pk=route_id).only("code").first()
        if route:
            qs = qs.filter(
                Q(trip__route_id=route_id)
                | Q(guest_checkout__trip__route_id=route_id)
                | Q(route_code=route.code)
                | Q(guest_checkout__route_code=route.code)
            )

    candidates = [
        candidate
        for candidate in qs.order_by("-created_at")[:1000]
        if ticket_short_code(ticket_reference(candidate)) == short_code
    ]
    if len(candidates) == 1:
        return candidates[0]

    active_candidates = [
        candidate
        for candidate in candidates
        if candidate.status == DigitalTravelPass.Status.ACTIVE
        and (not candidate.valid_until or candidate.valid_until >= now)
    ]
    if len(active_candidates) == 1:
        return active_candidates[0]

    raise DigitalTravelPass.DoesNotExist


def validate_qr_account(
    passenger_account_id: int,
    route_id: int,
    origin_stop_id: int | None = None,
    destination_stop_id: int | None = None,
    trip_id: int | None = None,
    device_serial: str = "",
    idempotency_key: str = "",
) -> ValidationEvent:
    existing = ValidationEvent.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing

    device = _resolve_device(device_serial)
    from apps.passengers.models import PassengerAccount
    try:
        passenger = PassengerAccount.objects.select_related("wallet").get(pk=passenger_account_id)
    except PassengerAccount.DoesNotExist:
        return _denied(ValidationEvent.ValidationType.QR_PAY_AS_YOU_GO, ValidationEvent.FailureReason.ACCOUNT_BLOCKED, idempotency_key, device=device)

    if passenger.status != PassengerAccount.Status.ACTIVE:
        return _denied(ValidationEvent.ValidationType.QR_PAY_AS_YOU_GO, ValidationEvent.FailureReason.ACCOUNT_BLOCKED, idempotency_key, passenger_account=passenger, device=device)

    wallet = getattr(passenger, "wallet", None)
    if not wallet:
        return _denied(ValidationEvent.ValidationType.QR_PAY_AS_YOU_GO, ValidationEvent.FailureReason.INSUFFICIENT_BALANCE, idempotency_key, passenger_account=passenger, device=device)

    try:
        route = Route.objects.get(pk=route_id)
    except Route.DoesNotExist:
        return _denied(ValidationEvent.ValidationType.QR_PAY_AS_YOU_GO, ValidationEvent.FailureReason.ROUTE_NOT_ALLOWED, idempotency_key, passenger_account=passenger, wallet=wallet, device=device)

    origin = Stop.objects.filter(pk=origin_stop_id).first() if origin_stop_id else None
    destination = Stop.objects.filter(pk=destination_stop_id).first() if destination_stop_id else None
    trip = Trip.objects.filter(pk=trip_id, route=route).first() if trip_id else None
    if trip_id and (not trip or trip.status not in {Trip.Status.BOARDING, Trip.Status.DEPARTED}):
        return _denied(ValidationEvent.ValidationType.QR_PAY_AS_YOU_GO, ValidationEvent.FailureReason.ROUTE_NOT_ALLOWED, idempotency_key, passenger_account=passenger, wallet=wallet, route=route, origin_stop=origin, destination_stop=destination, device=device)

    try:
        resolve_route_segment(route, origin_stop_id, destination_stop_id)
    except RouteSegmentError:
        return _denied(ValidationEvent.ValidationType.QR_PAY_AS_YOU_GO, ValidationEvent.FailureReason.ROUTE_NOT_ALLOWED, idempotency_key, passenger_account=passenger, wallet=wallet, route=route, origin_stop=origin, destination_stop=destination, device=device)

    try:
        quote = quote_fare(route=route, origin_stop=origin, destination_stop=destination)
    except NoFareFoundError:
        return _denied(ValidationEvent.ValidationType.QR_PAY_AS_YOU_GO, ValidationEvent.FailureReason.NO_FARE_FOUND, idempotency_key, passenger_account=passenger, wallet=wallet, route=route, device=device)

    # Carga + criacao do evento no MESMO atomic (ver validate_card): impede
    # duplo-debito/duplo-consumo de pacote em pedidos concorrentes.
    try:
        with transaction.atomic():
            amount_charged, charge_source, tx_ref = _charge_with_package_fallback(
                passenger_account=passenger, wallet=wallet, route=route,
                base_fare=quote.amount, idempotency_key=idempotency_key,
                metadata={"route": route.code},
            )
            return ValidationEvent.objects.create(
                validation_type=ValidationEvent.ValidationType.QR_PAY_AS_YOU_GO,
                passenger_account=passenger, wallet=wallet, route=route, trip=trip,
                origin_stop=origin, destination_stop=destination, device=device,
                amount_debited=amount_charged, status=ValidationEvent.Status.APPROVED,
                idempotency_key=idempotency_key, wallet_transaction_ref=tx_ref or charge_source,
            )
    except InsufficientBalanceError:
        return _denied(ValidationEvent.ValidationType.QR_PAY_AS_YOU_GO, ValidationEvent.FailureReason.INSUFFICIENT_BALANCE, idempotency_key, passenger_account=passenger, wallet=wallet, route=route, origin_stop=origin, destination_stop=destination, device=device)
    except WalletBlockedError:
        return _denied(ValidationEvent.ValidationType.QR_PAY_AS_YOU_GO, ValidationEvent.FailureReason.ACCOUNT_BLOCKED, idempotency_key, passenger_account=passenger, wallet=wallet, route=route, device=device)
    except IntegrityError:
        existing = ValidationEvent.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing
        raise


def _denied(validation_type: str, failure: str, idempotency_key: str, **kwargs) -> ValidationEvent:
    return ValidationEvent.objects.create(
        validation_type=validation_type, status=ValidationEvent.Status.DENIED,
        failure_reason=failure, idempotency_key=idempotency_key,
        **{k: v for k, v in kwargs.items() if v is not None},
    )
