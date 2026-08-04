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
    """Abre o EMBARQUE: o autocarro esta no terminal a receber passageiros.

    Antes, esta accao marcava tambem `actual_departure_at` — juntava o
    embarque com a partida e deixava a hora de saida errada por todo o tempo
    que o autocarro esteve parado a encher. A partida passou a ter accao
    propria (`depart_trip_activity`).
    """
    if trip.driver_id != driver.id:
        raise TripActivityError("Esta viagem nao esta alocada ao motorista autenticado.")
    if trip.status not in {Trip.Status.SCHEDULED, Trip.Status.BOARDING}:
        raise TripActivityError("A viagem nao pode iniciar embarque neste estado.")
    if not trip.vehicle_id:
        raise TripActivityError("A viagem precisa de um autocarro alocado.")

    now = timezone.now()
    with transaction.atomic():
        locked = Trip.objects.select_for_update().get(pk=trip.pk)
        if locked.status == Trip.Status.SCHEDULED:
            locked.status = Trip.Status.BOARDING
        locked.activity_started_at = locked.activity_started_at or now
        locked.activity_closed_at = None
        locked.save(update_fields=[
            "status", "activity_started_at", "activity_closed_at", "updated_at",
        ])
        _log(locked, driver, user, TripActivityEvent.EventType.START)
        return locked


def depart_trip_activity(trip: Trip, driver: Driver, user) -> Trip:
    """PARTIDA: o autocarro sai do terminal e passa a estar em movimento.

    E este o momento que conta como hora de saida — e o que fixa o manifesto
    de quem partiu do terminal. Quem entrar depois, entra numa paragem e
    aparece no manifesto ao ser validado.
    """
    if trip.driver_id != driver.id:
        raise TripActivityError("Esta viagem nao esta alocada ao motorista autenticado.")

    now = timezone.now()
    with transaction.atomic():
        locked = Trip.objects.select_for_update().get(pk=trip.pk)
        # O estado e verificado DEPOIS do lock, sobre a linha bloqueada: com a
        # verificacao feita sobre o objecto em memoria, dois toques seguidos no
        # botao (ou o terminal a repetir por timeout) passavam os dois pela
        # validacao e a segunda partida reescrevia a hora de saida.
        if locked.status == Trip.Status.DEPARTED:
            raise TripActivityError("A viagem ja partiu.")
        if locked.status != Trip.Status.BOARDING:
            raise TripActivityError("So se pode partir depois de abrir o embarque.")
        locked.status = Trip.Status.DEPARTED
        locked.activity_started_at = locked.activity_started_at or now
        locked.actual_departure_at = locked.actual_departure_at or now
        locked.save(update_fields=[
            "status", "activity_started_at", "actual_departure_at", "updated_at",
        ])
        from apps.trips.manifest import build_manifest
        manifesto = build_manifest(locked)
        _log(locked, driver, user, TripActivityEvent.EventType.DEPART, {
            "aboard_at_departure": manifesto["totals"]["aboard"],
            "expected": manifesto["totals"]["expected"],
        })
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
        # Retomar devolve ao estado em que estava: um autocarro que parou a
        # meio da estrada volta a EM VIAGEM, nao a embarque no terminal.
        # Antes voltava sempre a embarque e a viagem perdia o estado real.
        locked.status = (Trip.Status.DEPARTED if locked.actual_departure_at
                         else Trip.Status.BOARDING)
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

        # O manifesto e FOTOGRAFADO aqui, nao recalculado depois. Um bilhete
        # cancelado ou reembolsado dias mais tarde nao pode mudar a lista de
        # quem seguiu naquele autocarro naquele dia — e esse o documento que
        # vale numa fiscalizacao ou num sinistro.
        from apps.trips.manifest import build_manifest
        manifesto = build_manifest(locked, final=True)

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
                "manifest": manifesto,
                "passengers_aboard": manifesto["totals"]["aboard"],
                "passengers_no_show": manifesto["totals"]["no_show"],
            },
        )
        _log(locked, driver, user, TripActivityEvent.EventType.CLOSE, {
            "revenue": summary,
            "passengers_aboard": manifesto["totals"]["aboard"],
            "passengers_no_show": manifesto["totals"]["no_show"],
        })
        return locked


def _log(trip: Trip, driver: Driver, user, event_type: str, metadata: dict | None = None) -> None:
    TripActivityEvent.objects.create(
        trip=trip,
        driver=driver,
        user=user,
        event_type=event_type,
        metadata=metadata or {},
    )
