from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

from apps.trips.models import RouteSchedule, Trip


def count_daily_trips(schedule: RouteSchedule, target_date=None) -> int:
    """Quantas viagens NOVAS este horario criaria neste dia, sem criar nada.

    Serve a pre-visualizacao: antes de programar duas semanas de viagens, o
    operador ve quantas vao nascer. Segue exactamente as mesmas regras de
    `generate_daily_trips` — se divergirem, o numero mostrado mente.
    """
    if schedule.status != RouteSchedule.Status.ACTIVE:
        return 0

    date = target_date or timezone.now().date()
    if schedule.days_of_week and date.weekday() not in schedule.days_of_week:
        return 0

    tz = timezone.get_current_timezone()
    current_time = datetime.combine(date, schedule.start_time)
    end_time = datetime.combine(date, schedule.end_time)

    existing = set(
        Trip.objects.filter(
            schedule=schedule,
            planned_departure_at__date=date,
        ).values_list("planned_departure_at", flat=True)
    )

    count = 0
    while current_time <= end_time:
        if timezone.make_aware(current_time, tz) not in existing:
            count += 1
        current_time += timedelta(minutes=schedule.frequency_minutes)
    return count


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
                # O horario descreve uma carreira num sentido; as partidas que
                # dele nascem vao para esse lado.
                direction=schedule.direction or "",
                planned_departure_at=departure,
                status=Trip.Status.SCHEDULED,
            )
            created.append(trip)

        current_time += timedelta(minutes=schedule.frequency_minutes)

    return created


def programar_partidas(
    *, route, dates, times, vehicle=None, driver=None, agent=None,
    duration_minutes: int | None = None, direction: str = "", preview: bool = False,
) -> dict:
    """Cria uma partida por cada (dia x hora) escolhidos no calendario.

    O horario recorrente (`RouteSchedule`) descreve uma carreira urbana: de 30
    em 30 minutos, das 06h as 20h, nestes dias da semana. Numa carreira
    interprovincial ou internacional isso nao se aplica — ha uma partida por
    dia, em dias que nao seguem regra nenhuma (feriados, epoca alta, o dia em
    que o autocarro esta na oficina). Exprimir isso como frequencia obrigava a
    inventar uma hora de fim e uma cadencia para uma unica saida, e ainda assim
    nao deixava saltar um dia a meio.

    Aqui o operador marca os dias no calendario e diz a hora. Repetir a mesma
    marcacao nao duplica nada: uma partida ja existente na mesma rota, a mesma
    hora, no mesmo sentido e com a mesma viatura e contada como ja programada.

    O `direction` diz para que lado vai a partida. A ida das 06h e a volta das
    06h sao duas partidas distintas da mesma rota — sem o sentido na chave, a
    segunda era descartada como repetida.
    """
    from apps.routes.services import sentido_obrigatorio

    # A rota diz se ha escolha a fazer. Numa rota com ida e volta isto recusa
    # a programacao sem sentido, em vez de a deixar nascer ambigua.
    direction = sentido_obrigatorio(route, direction)

    tz = timezone.get_current_timezone()
    por_dia: dict[str, dict] = {}
    criadas: list[Trip] = []

    for date in sorted(set(dates)):
        nascem = 0
        repetidas = 0
        for hora in sorted(set(times)):
            partida = timezone.make_aware(datetime.combine(date, hora), tz)
            ja_existe = Trip.objects.filter(
                route=route, planned_departure_at=partida, vehicle=vehicle,
                direction=direction or "",
            ).exists()
            if ja_existe:
                repetidas += 1
                continue
            nascem += 1
            if preview:
                continue
            criadas.append(Trip.objects.create(
                route=route, vehicle=vehicle, driver=driver, agent=agent,
                direction=direction or "",
                planned_departure_at=partida,
                planned_arrival_at=(
                    partida + timedelta(minutes=duration_minutes)
                    if duration_minutes else None
                ),
                status=Trip.Status.SCHEDULED,
            ))
        por_dia[date.isoformat()] = {"date": date.isoformat(), "count": nascem, "existing": repetidas}

    return {
        "created": 0 if preview else len(criadas),
        "would_generate": sum(d["count"] for d in por_dia.values()),
        "already_scheduled": sum(d["existing"] for d in por_dia.values()),
        "by_day": list(por_dia.values()),
        "trips": criadas,
    }


def generate_all_daily_trips(target_date=None) -> int:
    schedules = RouteSchedule.objects.filter(
        status=RouteSchedule.Status.ACTIVE,
    ).select_related("route", "vehicle", "driver")

    total = 0
    for schedule in schedules:
        trips = generate_daily_trips(schedule, target_date)
        total += len(trips)

    return total
