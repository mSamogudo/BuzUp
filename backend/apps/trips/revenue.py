from __future__ import annotations

from decimal import Decimal

from django.db.models import Count, Sum

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.payments.models import PaymentIntent
from apps.trips.models import Trip
from apps.validations.models import ValidationEvent


PAY_AS_YOU_GO_VALIDATION_TYPES = (
    ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO,
    ValidationEvent.ValidationType.QR_PAY_AS_YOU_GO,
)


def calculate_trip_revenue(trip: Trip) -> dict:
    guest = GuestCheckout.objects.filter(
        trip=trip,
        status__in=[GuestCheckout.Status.PAID, GuestCheckout.Status.ISSUED],
    ).aggregate(count=Count("id"), tickets=Sum("quantity"), total=Sum("total_amount"))

    app_passes = DigitalTravelPass.objects.filter(
        trip=trip,
        guest_checkout__isnull=True,
        passenger_account__isnull=False,
    ).aggregate(count=Count("id"), total=Sum("fare_amount"))

    validations = ValidationEvent.objects.filter(trip=trip)
    approved_validations = validations.filter(status=ValidationEvent.Status.APPROVED)
    wallet_validations = approved_validations.filter(
        validation_type__in=PAY_AS_YOU_GO_VALIDATION_TYPES,
    ).aggregate(count=Count("id"), total=Sum("amount_debited"))
    digital_pass_validations = approved_validations.exclude(
        validation_type__in=PAY_AS_YOU_GO_VALIDATION_TYPES,
    ).aggregate(count=Count("id"), total=Sum("amount_debited"))

    direct_payments = PaymentIntent.objects.filter(
        status=PaymentIntent.Status.CONFIRMED,
        purpose=PaymentIntent.Purpose.DIRECT_TRIP_PAYMENT,
        metadata__trip_id=trip.id,
    ).aggregate(count=Count("id"), total=Sum("amount"))

    guest_total = _decimal(guest["total"])
    app_total = _decimal(app_passes["total"])
    wallet_total = _decimal(wallet_validations["total"])
    direct_total = _decimal(direct_payments["total"])
    total = guest_total + app_total + wallet_total + direct_total

    return {
        "guest_checkout": {
            "count": guest["count"] or 0,
            "tickets": guest["tickets"] or 0,
            "revenue": str(guest_total),
        },
        "app_passes": {
            "count": app_passes["count"] or 0,
            "revenue": str(app_total),
        },
        "wallet_validations": {
            "count": wallet_validations["count"] or 0,
            "revenue": str(wallet_total),
        },
        "digital_pass_validations": {
            "count": digital_pass_validations["count"] or 0,
            "nominal_value": str(_decimal(digital_pass_validations["total"])),
        },
        "direct_payments": {
            "count": direct_payments["count"] or 0,
            "revenue": str(direct_total),
        },
        "validations": {
            "approved": approved_validations.count(),
            "denied": validations.filter(status=ValidationEvent.Status.DENIED).count(),
        },
        "total_revenue": str(total),
    }


def _decimal(value) -> Decimal:
    return Decimal(value or "0.00").quantize(Decimal("0.01"))
