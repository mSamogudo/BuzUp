from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.trips.models import Driver, Trip, TripActivityEvent, TripRevenueClosure
from apps.trips.revenue import calculate_trip_revenue


class TripActivityError(ValueError):
    pass


def resolve_driver_for_user(user) -> Driver | None:
    driver = Driver.objects.filter(user=user, status=Driver.Status.ACTIVE).first()
    if driver:
        return driver
    phone = str(getattr(user, "phone", "") or "").strip()
    if phone:
        return Driver.objects.filter(phone=phone, status=Driver.Status.ACTIVE).first()
    return None


def start_trip_activity(trip: Trip, driver: Driver, user) -> Trip:
    if trip.driver_id != driver.id:
        raise TripActivityError("Esta viagem nao esta alocada ao motorista autenticado.")
    if trip.status not in {Trip.Status.SCHEDULED, Trip.Status.BOARDING}:
        raise TripActivityError("A viagem nao pode ser iniciada neste estado.")
    if not trip.vehicle_id:
        raise TripActivityError("A viagem precisa de um autocarro alocado.")

    now = timezone.now()
    with transaction.atomic():
        locked = Trip.objects.select_for_update().get(pk=trip.pk)
        if locked.status == Trip.Status.SCHEDULED:
            locked.status = Trip.Status.BOARDING
        locked.activity_started_at = locked.activity_started_at or now
        locked.actual_departure_at = locked.actual_departure_at or now
        locked.activity_closed_at = None
        locked.save(update_fields=[
            "status", "activity_started_at", "actual_departure_at",
            "activity_closed_at", "updated_at",
        ])
        _log(locked, driver, user, TripActivityEvent.EventType.START)
        return locked


def pause_trip_activity(trip: Trip, driver: Driver, user) -> Trip:
    if trip.driver_id != driver.id:
        raise TripActivityError("Esta viagem nao esta alocada ao motorista autenticado.")
    if trip.status not in {Trip.Status.BOARDING, Trip.Status.DEPARTED}:
        raise TripActivityError("A viagem nao esta em circulacao.")

    now = timezone.now()
    with transaction.atomic():
        locked = Trip.objects.select_for_update().get(pk=trip.pk)
        locked.status = Trip.Status.PAUSED
        locked.activity_paused_at = now
        locked.save(update_fields=["status", "activity_paused_at", "updated_at"])
        _log(locked, driver, user, TripActivityEvent.EventType.PAUSE)
        return locked


def resume_trip_activity(trip: Trip, driver: Driver, user) -> Trip:
    if trip.driver_id != driver.id:
        raise TripActivityError("Esta viagem nao esta alocada ao motorista autenticado.")
    if trip.status != Trip.Status.PAUSED:
        raise TripActivityError("A viagem nao esta em repouso.")

    now = timezone.now()
    with transaction.atomic():
        locked = Trip.objects.select_for_update().get(pk=trip.pk)
        pause_seconds = locked.pause_seconds
        if locked.activity_paused_at:
            pause_seconds += max(0, int((now - locked.activity_paused_at).total_seconds()))
        locked.pause_seconds = pause_seconds
        locked.activity_paused_at = None
        locked.status = Trip.Status.BOARDING
        locked.save(update_fields=["pause_seconds", "activity_paused_at", "status", "updated_at"])
        _log(locked, driver, user, TripActivityEvent.EventType.RESUME, {"pause_seconds": pause_seconds})
        return locked


def close_trip_activity(trip: Trip, driver: Driver, user) -> Trip:
    if trip.driver_id != driver.id:
        raise TripActivityError("Esta viagem nao esta alocada ao motorista autenticado.")
    if trip.status in {Trip.Status.COMPLETED, Trip.Status.CANCELLED}:
        raise TripActivityError("A viagem ja esta encerrada.")

    now = timezone.now()
    with transaction.atomic():
        locked = Trip.objects.select_for_update().get(pk=trip.pk)
        pause_seconds = locked.pause_seconds
        if locked.status == Trip.Status.PAUSED and locked.activity_paused_at:
            pause_seconds += max(0, int((now - locked.activity_paused_at).total_seconds()))
        locked.pause_seconds = pause_seconds
        locked.status = Trip.Status.COMPLETED
        locked.activity_paused_at = None
        locked.activity_closed_at = now
        locked.actual_arrival_at = locked.actual_arrival_at or now
        summary = calculate_trip_revenue(locked)
        locked.closure_summary = summary
        locked.save(update_fields=[
            "pause_seconds", "status", "activity_paused_at", "activity_closed_at",
            "actual_arrival_at", "closure_summary", "updated_at",
        ])
        TripRevenueClosure.objects.update_or_create(
            trip=locked,
            defaults={
                "route": locked.route,
                "vehicle": locked.vehicle,
                "driver": locked.driver,
                "closed_by": user,
                "opened_at": locked.activity_started_at,
                "closed_at": now,
                "pause_seconds": pause_seconds,
                "guest_checkout_revenue": summary["guest_checkout"]["revenue"],
                "app_pass_revenue": summary["app_passes"]["revenue"],
                "wallet_validation_revenue": summary["wallet_validations"]["revenue"],
                "direct_payment_revenue": summary["direct_payments"]["revenue"],
                "total_revenue": summary["total_revenue"],
                "summary": summary,
            },
        )
        _log(locked, driver, user, TripActivityEvent.EventType.CLOSE, {"revenue": summary})
        return locked


def _log(trip: Trip, driver: Driver, user, event_type: str, metadata: dict | None = None) -> None:
    TripActivityEvent.objects.create(
        trip=trip,
        driver=driver,
        user=user,
        event_type=event_type,
        metadata=metadata or {},
    )
