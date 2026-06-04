from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.packages.models import Package, PackageRoute, PassengerPackage
from apps.passengers.models import PassengerAccount
from apps.routes.models import Route
from apps.wallets.models import WalletTransaction
from apps.wallets.services import credit_wallet, debit_wallet


class PackageError(Exception):
    pass


def subscribe_passenger(
    passenger: PassengerAccount,
    package: Package,
    pay_from_wallet: bool = True,
) -> PassengerPackage:
    """Subscribe (or re-charge) a passenger to a package.

    If the passenger already holds a subscription for this exact package that
    is still ACTIVE or EXHAUSTED but not yet expired, the existing row is
    topped up (special_balance / trips_remaining incremented, expiry extended)
    instead of creating a duplicate. This avoids the user accumulating multiple
    rows for the same product after several re-charges.
    """
    if package.status != Package.Status.ACTIVE:
        raise PackageError("Pacote inactivo.")
    if passenger.status != PassengerAccount.Status.ACTIVE:
        raise PackageError("Conta bloqueada.")

    wallet = getattr(passenger, "wallet", None)
    if not wallet:
        raise PackageError("Passageiro sem carteira.")

    with transaction.atomic():
        if pay_from_wallet and package.price > Decimal("0.00"):
            debit_wallet(
                wallet=wallet,
                amount=package.price,
                tx_type=WalletTransaction.Type.FEE,
                source=f"package:{package.id}",
                metadata={"package_name": package.name},
            )

        now = timezone.now()
        existing = (
            PassengerPackage.objects.select_for_update()
            .filter(
                passenger_account=passenger,
                package=package,
                status__in=[
                    PassengerPackage.Status.ACTIVE,
                    PassengerPackage.Status.EXHAUSTED,
                ],
                expires_at__gt=now,
            )
            .order_by("-activated_at")
            .first()
        )

        if existing is not None:
            new_expiry = max(existing.expires_at, now) + timedelta(days=package.validity_days)
            update_fields = ["expires_at", "status", "updated_at"]
            if package.discount_type == Package.DiscountType.FIXED_AMOUNT:
                existing.special_balance = (existing.special_balance or Decimal("0.00")) + package.price
                update_fields.append("special_balance")
            elif package.discount_type == Package.DiscountType.FREE_TRIPS:
                existing.trips_remaining = (existing.trips_remaining or 0) + package.max_trips
                update_fields.append("trips_remaining")
            existing.expires_at = new_expiry
            existing.status = PassengerPackage.Status.ACTIVE
            existing.save(update_fields=update_fields)
            return existing

        sub = PassengerPackage.objects.create(
            passenger_account=passenger,
            package=package,
            wallet=wallet,
            special_balance=package.price if package.discount_type == Package.DiscountType.FIXED_AMOUNT else Decimal("0.00"),
            trips_remaining=package.max_trips if package.discount_type == Package.DiscountType.FREE_TRIPS else 0,
            status=PassengerPackage.Status.ACTIVE,
            expires_at=now + timedelta(days=package.validity_days),
        )

    return sub


def topup_package(
    subscription: PassengerPackage,
    amount: Decimal,
) -> PassengerPackage:
    if subscription.status != PassengerPackage.Status.ACTIVE:
        raise PackageError("Subscricao inactiva.")

    subscription.special_balance += amount
    subscription.save(update_fields=["special_balance", "updated_at"])
    return subscription


def find_active_package_for_route(
    passenger: PassengerAccount,
    route: Route,
) -> PassengerPackage | None:
    now = timezone.now()
    subs = PassengerPackage.objects.filter(
        passenger_account=passenger,
        status=PassengerPackage.Status.ACTIVE,
        expires_at__gt=now,
    ).select_related("package").order_by("-activated_at")

    for sub in subs:
        pkg_routes = PackageRoute.objects.filter(package=sub.package)
        if pkg_routes.exists():
            if not pkg_routes.filter(route=route).exists():
                continue

        if sub.package.discount_type == Package.DiscountType.FREE_TRIPS:
            if sub.trips_remaining > 0:
                return sub
        elif sub.package.discount_type == Package.DiscountType.FIXED_AMOUNT:
            if sub.special_balance > Decimal("0.00"):
                return sub
        elif sub.package.discount_type == Package.DiscountType.PERCENTAGE:
            return sub

    return None


def calculate_discounted_fare(
    base_fare: Decimal,
    subscription: PassengerPackage,
) -> Decimal:
    pkg = subscription.package

    if pkg.discount_type == Package.DiscountType.FREE_TRIPS:
        if subscription.trips_remaining > 0:
            return Decimal("0.00")
        return base_fare

    if pkg.discount_type == Package.DiscountType.PERCENTAGE:
        discount = base_fare * pkg.discount_value / Decimal("100")
        return max(Decimal("0.00"), base_fare - discount).quantize(Decimal("0.01"))

    if pkg.discount_type == Package.DiscountType.FIXED_AMOUNT:
        if subscription.special_balance >= base_fare:
            return Decimal("0.00")
        remaining = base_fare - subscription.special_balance
        return max(Decimal("0.00"), remaining).quantize(Decimal("0.01"))

    return base_fare


def consume_package_trip(
    subscription: PassengerPackage,
    base_fare: Decimal,
) -> Decimal:
    pkg = subscription.package

    with transaction.atomic():
        sub = PassengerPackage.objects.select_for_update().get(pk=subscription.pk)

        if pkg.discount_type == Package.DiscountType.FREE_TRIPS:
            if sub.trips_remaining > 0:
                sub.trips_remaining -= 1
                sub.trips_used += 1
                if sub.trips_remaining == 0:
                    sub.status = PassengerPackage.Status.EXHAUSTED
                sub.save(update_fields=["trips_remaining", "trips_used", "status", "updated_at"])
                return Decimal("0.00")

        elif pkg.discount_type == Package.DiscountType.FIXED_AMOUNT:
            if sub.special_balance >= base_fare:
                sub.special_balance -= base_fare
                sub.trips_used += 1
                if sub.special_balance <= Decimal("0.00"):
                    sub.status = PassengerPackage.Status.EXHAUSTED
                sub.save(update_fields=["special_balance", "trips_used", "status", "updated_at"])
                return Decimal("0.00")
            elif sub.special_balance > Decimal("0.00"):
                remainder = base_fare - sub.special_balance
                sub.special_balance = Decimal("0.00")
                sub.trips_used += 1
                sub.status = PassengerPackage.Status.EXHAUSTED
                sub.save(update_fields=["special_balance", "trips_used", "status", "updated_at"])
                return remainder

        elif pkg.discount_type == Package.DiscountType.PERCENTAGE:
            discount = base_fare * pkg.discount_value / Decimal("100")
            discounted = max(Decimal("0.00"), base_fare - discount).quantize(Decimal("0.01"))
            sub.trips_used += 1
            sub.save(update_fields=["trips_used", "updated_at"])
            return discounted

    return base_fare


def expire_subscriptions():
    now = timezone.now()
    expired = PassengerPackage.objects.filter(
        status=PassengerPackage.Status.ACTIVE,
        expires_at__lte=now,
    )
    count = expired.update(status=PassengerPackage.Status.EXPIRED)
    return count
