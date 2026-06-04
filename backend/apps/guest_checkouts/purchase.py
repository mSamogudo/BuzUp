from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from uuid import uuid4

from django.utils import timezone

from apps.fares.services import NoFareFoundError, quote_fare
from apps.guest_checkouts.models import DigitalTravelPass
from apps.packages.models import PackageRoute, PassengerPackage
from apps.packages.services import (
    calculate_discounted_fare,
    consume_package_trip,
    find_active_package_for_route,
)
from apps.passengers.models import PassengerAccount
from apps.routes.models import Route, Stop
from apps.routes.services import RouteSegmentError, resolve_route_segment
from apps.trips.models import Trip
from apps.wallets.models import WalletTransaction
from apps.wallets.services import InsufficientBalanceError, WalletBlockedError, debit_wallet


class PurchaseError(Exception):
    pass


def _resolve_passenger_package(
    passenger: PassengerAccount,
    route: Route,
    passenger_package_id: int | None,
    use_package: bool,
) -> PassengerPackage | None:
    if not use_package and passenger_package_id is None:
        return None

    if passenger_package_id is not None:
        try:
            sub = PassengerPackage.objects.select_related("package").get(
                pk=passenger_package_id,
                passenger_account=passenger,
            )
        except PassengerPackage.DoesNotExist:
            raise PurchaseError("Pacote nao encontrado para este passageiro.")
        if sub.status != PassengerPackage.Status.ACTIVE:
            raise PurchaseError("Pacote nao esta activo.")
        if sub.expires_at and sub.expires_at <= timezone.now():
            raise PurchaseError("Pacote expirado.")

        pkg_routes = PackageRoute.objects.filter(package=sub.package)
        if pkg_routes.exists() and not pkg_routes.filter(route=route).exists():
            raise PurchaseError("Este pacote nao cobre a rota seleccionada.")

        return sub

    return find_active_package_for_route(passenger, route)


def purchase_travel_pass(
    passenger: PassengerAccount,
    route_id: int,
    origin_stop_id: int | None = None,
    destination_stop_id: int | None = None,
    trip_id: int | None = None,
    passenger_package_id: int | None = None,
    use_package: bool = True,
) -> DigitalTravelPass:
    if passenger.status != PassengerAccount.Status.ACTIVE:
        raise PurchaseError("Conta bloqueada ou inactiva.")

    wallet = getattr(passenger, "wallet", None)
    if not wallet:
        raise PurchaseError("Passageiro sem carteira.")

    try:
        route = Route.objects.get(pk=route_id)
    except Route.DoesNotExist:
        raise PurchaseError("Rota nao encontrada.")

    origin = Stop.objects.filter(pk=origin_stop_id).first() if origin_stop_id else None
    destination = Stop.objects.filter(pk=destination_stop_id).first() if destination_stop_id else None
    trip = Trip.objects.filter(
        pk=trip_id,
        route=route,
        status__in=[Trip.Status.BOARDING, Trip.Status.DEPARTED],
    ).first() if trip_id else None
    if trip_id and not trip:
        raise PurchaseError("Autocarro nao esta disponivel para compra.")

    try:
        resolve_route_segment(route, origin_stop_id, destination_stop_id)
    except RouteSegmentError as e:
        raise PurchaseError(str(e))

    try:
        quote = quote_fare(route=route, origin_stop=origin, destination_stop=destination)
    except NoFareFoundError as e:
        raise PurchaseError(str(e))

    base_fare = quote.amount
    subscription = _resolve_passenger_package(passenger, route, passenger_package_id, use_package)

    raw_token, token_hash = DigitalTravelPass.generate_token()
    package_used = None
    package_meta: dict = {}

    with transaction.atomic():
        wallet_amount = base_fare
        if subscription:
            wallet_amount = consume_package_trip(subscription, base_fare)
            package_used = subscription
            package_meta = {
                "package_id": subscription.package_id,
                "package_name": subscription.package.name,
                "discount_type": subscription.package.discount_type,
                "base_fare": str(base_fare),
                "wallet_amount": str(wallet_amount),
            }

        # Create a CONFIRMED PaymentIntent so the operation shows up in the
        # admin payments page (filterable by source=MOBILE). For partial
        # coverage we record the wallet_amount; for full package coverage we
        # still record the base_fare as `amount` with metadata describing the
        # discount, so financial reports see the gross value.
        from apps.payments.models import PaymentIntent
        from uuid import uuid4 as _uuid4
        recorded_amount = wallet_amount if wallet_amount > Decimal("0.00") else base_fare
        idem = f"app-tp-{_uuid4().hex[:32]}"
        payment_intent = PaymentIntent.objects.create(
            reference=idem,
            idempotency_key=idem,
            purpose=PaymentIntent.Purpose.APP_TRAVEL_PASS,
            amount=recorded_amount,
            currency=wallet.currency or "MZN",
            payer_phone=passenger.phone_number,
            provider="wallet",
            channel="wallet",
            status=PaymentIntent.Status.CONFIRMED,
            wallet=wallet,
            confirmed_at=timezone.now(),
            metadata={
                "route": route.code,
                "base_fare": str(base_fare),
                "wallet_amount": str(wallet_amount),
                "fully_covered_by_package": wallet_amount <= Decimal("0.00") and subscription is not None,
                **package_meta,
            },
        )

        if wallet_amount > Decimal("0.00"):
            debit_wallet(
                wallet=wallet,
                amount=wallet_amount,
                tx_type=WalletTransaction.Type.FARE_DEBIT,
                source=f"payment:{payment_intent.reference}",
                metadata={"route": route.code, **package_meta},
            )
        elif subscription:
            # Package fully covered the fare. Still record a zero-amount
            # FARE_DEBIT so the trip is visible in transactions list with the
            # package metadata — otherwise package-covered trips would be
            # invisible to the passenger (and to admin auditing).
            now = timezone.now()
            WalletTransaction.objects.create(
                wallet=wallet,
                type=WalletTransaction.Type.FARE_DEBIT,
                direction=WalletTransaction.Direction.DEBIT,
                amount=Decimal("0.00"),
                signed_amount=Decimal("0.00"),
                balance_before=wallet.balance_cached,
                balance_after=wallet.balance_cached,
                reference=f"TXN-PKG-{uuid4().hex[:16].upper()}",
                source="app_travel_pass_purchase",
                status=WalletTransaction.Status.CONFIRMED,
                metadata={"route": route.code, "fully_covered_by_package": True, **package_meta},
                created_at=now,
            )

        travel_pass = DigitalTravelPass.objects.create(
            passenger_account=passenger,
            wallet=wallet,
            payer_phone=passenger.phone_number,
            route_code=route.code,
            route_name=route.name,
            origin_stop=origin.name if origin else "",
            destination_stop=destination.name if destination else "",
            origin_stop_ref=origin,
            destination_stop_ref=destination,
            trip=trip,
            # Show what the passenger actually paid (after any package
            # discount), not the gross fare — the ticket, tickets list,
            # history and PDF all read this field.
            fare_amount=wallet_amount,
            token=raw_token,
            token_hash=token_hash,
            delivery_channel=DigitalTravelPass.DeliveryChannel.APP,
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(hours=24),
        )

    travel_pass._raw_token = raw_token
    if package_used:
        travel_pass._package_used = package_used
        travel_pass._wallet_amount = wallet_amount
    return travel_pass


def quote_for_passenger(
    passenger: PassengerAccount,
    route: Route,
    origin: Stop | None,
    destination: Stop | None,
    passenger_package_id: int | None = None,
    use_package: bool = True,
) -> dict:
    """Return base fare, applicable package and resulting wallet amount.

    When `use_package=False`, the quote ignores any active package and returns
    `wallet_amount == base_fare`. This lets the mobile UI surface the real
    cost when the passenger toggles off the special-package switch.
    """
    quote = quote_fare(route=route, origin_stop=origin, destination_stop=destination)
    base = quote.amount

    sub = None
    if not use_package:
        sub = None
    elif passenger_package_id is not None:
        try:
            sub = PassengerPackage.objects.select_related("package").get(
                pk=passenger_package_id,
                passenger_account=passenger,
                status=PassengerPackage.Status.ACTIVE,
            )
            pkg_routes = PackageRoute.objects.filter(package=sub.package)
            if pkg_routes.exists() and not pkg_routes.filter(route=route).exists():
                sub = None
        except PassengerPackage.DoesNotExist:
            sub = None
    else:
        sub = find_active_package_for_route(passenger, route)

    if sub:
        wallet_amount = calculate_discounted_fare(base, sub)
        return {
            "base_fare": str(base),
            "wallet_amount": str(wallet_amount),
            "package_id": sub.id,
            "package_name": sub.package.name,
            "discount_type": sub.package.discount_type,
        }
    return {
        "base_fare": str(base),
        "wallet_amount": str(base),
        "package_id": None,
        "package_name": "",
        "discount_type": "",
    }
