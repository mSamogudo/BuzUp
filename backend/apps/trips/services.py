from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

from apps.trips.models import RouteSchedule, Trip


def generate_daily_trips(schedule: RouteSchedule, target_date: datetime | None = None) -> list[Trip]:
    if schedule.status != RouteSchedule.Status.ACTIVE:
        return []

    now = timezone.now()
    date = target_date or now.date()
    weekday = date.weekday()

    if schedule.days_of_week and weekday not in schedule.days_of_week:
        return []

    created = []
    current_time = datetime.combine(date, schedule.start_time)
    end_time = datetime.combine(date, schedule.end_time)
    tz = timezone.get_current_timezone()

    while current_time <= end_time:
        departure = timezone.make_aware(current_time, tz)

        exists = Trip.objects.filter(
            schedule=schedule,
            planned_departure_at=departure,
        ).exists()

        if not exists:
            trip = Trip.objects.create(
                route=schedule.route,
                vehicle=schedule.vehicle,
                driver=schedule.driver,
                schedule=schedule,
                planned_departure_at=departure,
                status=Trip.Status.SCHEDULED,
            )
            created.append(trip)

        current_time += timedelta(minutes=schedule.frequency_minutes)

    return created


def generate_all_daily_trips(target_date=None) -> int:
    schedules = RouteSchedule.objects.filter(
        status=RouteSchedule.Status.ACTIVE,
    ).select_related("route", "vehicle", "driver")

    total = 0
    for schedule in schedules:
        trips = generate_daily_trips(schedule, target_date)
        total += len(trips)

    return total
