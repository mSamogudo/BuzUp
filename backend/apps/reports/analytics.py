"""Analítica do dashboard: uma chamada, muitas séries, todas filtráveis.

O dashboard antigo tinha quatro séries fixas e nenhum filtro. Aqui as mesmas
condições (intervalo de datas, rota, motorista, agente, método de pagamento)
aplicam-se a TODAS as séries, para que os números batam certo entre cartões e
gráficos — a causa habitual de desconfiança num painel.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, F, Q, Sum
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.packages.models import PassengerPackage
from apps.payments.models import PaymentIntent
from apps.trips.models import Trip
from apps.validations.models import ValidationEvent
from apps.wallets.models import WalletTransaction

MAX_RANGE_DAYS = 400


def _money(value) -> str:
    return str(value or Decimal("0.00"))


class AnalyticsFilters:
    """Filtros do pedido, já normalizados e com limites sãos."""

    def __init__(self, params):
        now = timezone.now()
        self.date_to = self._parse_date(params.get("date_to")) or now.date()
        default_from = self.date_to - timedelta(days=29)
        self.date_from = self._parse_date(params.get("date_from")) or default_from
        if self.date_from > self.date_to:
            self.date_from, self.date_to = self.date_to, self.date_from
        # Um intervalo enorme derruba o painel; corta-se em silêncio mas
        # devolve-se o intervalo efectivo para a UI mostrar.
        if (self.date_to - self.date_from).days > MAX_RANGE_DAYS:
            self.date_from = self.date_to - timedelta(days=MAX_RANGE_DAYS)

        self.route_id = self._parse_int(params.get("route_id"))
        self.driver_id = self._parse_int(params.get("driver_id"))
        self.agent_id = self._parse_int(params.get("agent_id"))
        self.provider = (params.get("provider") or "").strip().upper() or None

        tz = timezone.get_current_timezone()
        self.dt_from = timezone.make_aware(
            timezone.datetime.combine(self.date_from, timezone.datetime.min.time()), tz)
        self.dt_to = timezone.make_aware(
            timezone.datetime.combine(self.date_to + timedelta(days=1), timezone.datetime.min.time()), tz)

    @staticmethod
    def _parse_date(value):
        from django.utils.dateparse import parse_date
        return parse_date(value) if value else None

    @staticmethod
    def _parse_int(value):
        try:
            return int(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None

    def as_dict(self) -> dict:
        return {
            "date_from": self.date_from.isoformat(),
            "date_to": self.date_to.isoformat(),
            "route_id": self.route_id,
            "driver_id": self.driver_id,
            "agent_id": self.agent_id,
            "provider": self.provider,
        }

    # --- aplicação dos filtros a cada fonte ---

    def validations(self):
        qs = ValidationEvent.objects.filter(
            status=ValidationEvent.Status.APPROVED,
            created_at__gte=self.dt_from, created_at__lt=self.dt_to,
        )
        if self.route_id:
            qs = qs.filter(route_id=self.route_id)
        if self.driver_id:
            qs = qs.filter(trip__driver_id=self.driver_id)
        if self.agent_id:
            qs = qs.filter(trip__agent_id=self.agent_id)
        return qs

    def passes(self):
        qs = DigitalTravelPass.objects.filter(
            created_at__gte=self.dt_from, created_at__lt=self.dt_to,
        ).exclude(status=DigitalTravelPass.Status.CANCELLED)
        if self.route_id:
            qs = qs.filter(Q(trip__route_id=self.route_id) | Q(guest_checkout__trip__route_id=self.route_id))
        if self.driver_id:
            qs = qs.filter(trip__driver_id=self.driver_id)
        if self.agent_id:
            qs = qs.filter(Q(trip__agent_id=self.agent_id) | Q(guest_checkout__trip__agent_id=self.agent_id))
        return qs

    def topups(self):
        qs = WalletTransaction.objects.filter(
            type=WalletTransaction.Type.TOPUP,
            status=WalletTransaction.Status.CONFIRMED,
            created_at__gte=self.dt_from, created_at__lt=self.dt_to,
        )
        return qs

    def payments(self):
        qs = PaymentIntent.objects.filter(
            status=PaymentIntent.Status.CONFIRMED,
            confirmed_at__gte=self.dt_from, confirmed_at__lt=self.dt_to,
        )
        if self.provider:
            qs = qs.filter(provider=self.provider)
        return qs

    def trips(self):
        qs = Trip.objects.filter(
            planned_departure_at__gte=self.dt_from, planned_departure_at__lt=self.dt_to,
        )
        if self.route_id:
            qs = qs.filter(route_id=self.route_id)
        if self.driver_id:
            qs = qs.filter(driver_id=self.driver_id)
        if self.agent_id:
            qs = qs.filter(agent_id=self.agent_id)
        return qs


def build_analytics(params) -> dict:
    f = AnalyticsFilters(params)

    validations = f.validations()
    passes = f.passes()
    topups = f.topups()
    payments = f.payments()

    validation_revenue = validations.aggregate(v=Sum("amount_debited"))["v"] or Decimal("0.00")
    ticket_revenue = passes.aggregate(v=Sum("fare_amount"))["v"] or Decimal("0.00")
    topup_total = topups.aggregate(v=Sum("amount"))["v"] or Decimal("0.00")
    payment_total = payments.aggregate(v=Sum("amount"))["v"] or Decimal("0.00")

    tickets_count = passes.count()
    validations_count = validations.count()

    methods = _payment_methods(payments)
    # Dinheiro que entrou mesmo na conta da empresa: M-Pesa, e-Mola, numerario.
    # Exclui pagamentos feitos com saldo BusUp — esse dinheiro ja entrou antes,
    # na recarga; conta-lo aqui seria conta-lo duas vezes.
    cash_in = sum(
        (Decimal(m["total"]) for m in methods if m["kind"] in ("mobile_money", "cash")),
        Decimal("0.00"),
    )

    kpis = {
        # Receita de transporte = bilhetes vendidos + validações pagas por carteira.
        # As recargas NÃO entram: são dinheiro que ainda não virou viagem.
        "transport_revenue": _money(ticket_revenue + validation_revenue),
        "cash_in": _money(cash_in),
        "ticket_revenue": _money(ticket_revenue),
        "validation_revenue": _money(validation_revenue),
        "topups_total": _money(topup_total),
        "payments_total": _money(payment_total),
        "tickets_sold": tickets_count,
        "validations": validations_count,
        "avg_ticket": _money(
            (ticket_revenue / tickets_count).quantize(Decimal("0.01")) if tickets_count else Decimal("0.00")
        ),
        "trips_total": f.trips().count(),
        "trips_completed": f.trips().filter(status=Trip.Status.COMPLETED).count(),
    }

    return {
        "filters": f.as_dict(),
        "kpis": kpis,
        "revenue_series": _revenue_series(f),
        "hourly": _hourly(validations),
        "payment_methods": methods,
        "top_routes": _top_routes(validations, passes),
        "top_trips": _top_trips(f),
        "top_drivers": _top_drivers(f),
        "top_agents": _top_agents(f),
        "packages": _packages(f),
        "recent": _recent(f),
    }


def _revenue_series(f: AnalyticsFilters) -> list[dict]:
    """Série diária com as três parcelas, sem dias em falta."""
    def by_day(qs, field, alias):
        return {
            r["day"]: r[alias]
            for r in qs.annotate(day=TruncDate("created_at")).values("day")
                       .annotate(**{alias: Sum(field)}).order_by("day")
        }

    tickets = by_day(f.passes(), "fare_amount", "total")
    vals = by_day(f.validations(), "amount_debited", "total")
    tops = by_day(f.topups(), "amount", "total")

    out = []
    day = f.date_from
    while day <= f.date_to:
        out.append({
            "date": day.isoformat(),
            "tickets": _money(tickets.get(day)),
            "validations": _money(vals.get(day)),
            "topups": _money(tops.get(day)),
        })
        day += timedelta(days=1)
    return out


def _hourly(validations) -> list[dict]:
    rows = (validations.annotate(hour=TruncHour("created_at")).values("hour")
            .annotate(count=Count("id")).order_by("hour"))
    buckets = {h: 0 for h in range(24)}
    for r in rows:
        buckets[timezone.localtime(r["hour"]).hour] += r["count"]
    return [{"hour": f"{h:02d}h", "count": c} for h, c in buckets.items()]


# O campo `provider` foi gravado com caixas diferentes ao longo do tempo
# ("mpesa" e "MPESA" sao o mesmo) e mistura carteiras moveis com o saldo
# interno. Aqui normaliza-se e diz-se ao painel o que cada coisa e.
PROVIDER_LABELS = {
    "MPESA": ("M-Pesa", "mobile_money"),
    "EMOLA": ("e-Mola", "mobile_money"),
    "WALLET": ("Saldo BusUp", "wallet"),
    "MOCK": ("Simulado (teste)", "test"),
    "CASH": ("Dinheiro", "cash"),
}


def _payment_methods(payments) -> list[dict]:
    """Metodos de pagamento, agrupados sem duplicados de caixa.

    `kind` distingue dinheiro que ENTRA (carteiras moveis) de pagamento feito
    com saldo ja carregado (`wallet`) — este ultimo nao e receita nova, senao
    contava-se duas vezes: uma na recarga e outra na viagem.
    """
    from collections import defaultdict

    acc = defaultdict(lambda: {"count": 0, "total": Decimal("0.00")})
    for r in payments.values("provider").annotate(count=Count("id"), total=Sum("amount")):
        key = (r["provider"] or "OUTRO").strip().upper()
        acc[key]["count"] += r["count"]
        acc[key]["total"] += r["total"] or Decimal("0.00")

    rows = []
    for key, v in acc.items():
        label, kind = PROVIDER_LABELS.get(key, (key.title(), "other"))
        rows.append({
            "provider": key,
            "label": label,
            "kind": kind,
            "count": v["count"],
            "total": _money(v["total"]),
        })
    rows.sort(key=lambda x: Decimal(x["total"]), reverse=True)
    return rows


def _top_routes(validations, passes) -> list[dict]:
    from collections import defaultdict
    acc = defaultdict(lambda: {"count": 0, "revenue": Decimal("0.00")})

    for r in (validations.filter(route__isnull=False).values("route__code", "route__name")
              .annotate(count=Count("id"), revenue=Sum("amount_debited"))):
        key = (r["route__code"], r["route__name"])
        acc[key]["count"] += r["count"]
        acc[key]["revenue"] += r["revenue"] or Decimal("0.00")

    for r in (passes.exclude(route_code="").values("route_code", "route_name")
              .annotate(count=Count("id"), revenue=Sum("fare_amount"))):
        key = (r["route_code"], r["route_name"])
        acc[key]["count"] += r["count"]
        acc[key]["revenue"] += r["revenue"] or Decimal("0.00")

    rows = [{"route_code": k[0], "route_name": k[1], "count": v["count"], "revenue": _money(v["revenue"])}
            for k, v in acc.items()]
    rows.sort(key=lambda x: Decimal(x["revenue"]), reverse=True)
    return rows[:8]


def _top_trips(f: AnalyticsFilters) -> list[dict]:
    rows = (f.trips().select_related("route", "vehicle", "driver")
            .annotate(pax=Count("travel_passes"), receita=Sum("travel_passes__fare_amount"))
            .filter(pax__gt=0).order_by("-receita")[:8])
    return [{
        "trip_id": t.id,
        "route": f"{t.route.code} · {t.route.name}" if t.route_id else "",
        "departure": t.planned_departure_at.isoformat() if t.planned_departure_at else None,
        "vehicle": t.vehicle.registration if t.vehicle_id else "",
        "driver": t.driver.full_name if t.driver_id else "",
        "passengers": t.pax,
        "revenue": _money(t.receita),
    } for t in rows]


def _top_drivers(f: AnalyticsFilters) -> list[dict]:
    rows = (f.trips().filter(driver__isnull=False)
            .values("driver_id", "driver__full_name")
            .annotate(viagens=Count("id", distinct=True),
                      concluidas=Count("id", filter=Q(status=Trip.Status.COMPLETED), distinct=True),
                      pax=Count("travel_passes"),
                      receita=Sum("travel_passes__fare_amount"))
            # Sem receita associada (viagens sem bilhete ligado), a ordem cai
            # para passageiros e depois viagens — senao a lista fica aleatoria.
            .order_by(F("receita").desc(nulls_last=True), "-pax", "-viagens")[:8])
    return [{
        "driver_id": r["driver_id"],
        "name": r["driver__full_name"],
        "trips": r["viagens"],
        "completed": r["concluidas"],
        "passengers": r["pax"],
        "revenue": _money(r["receita"]),
    } for r in rows]


def _top_agents(f: AnalyticsFilters) -> list[dict]:
    qs = GuestCheckout.objects.filter(
        created_at__gte=f.dt_from, created_at__lt=f.dt_to,
        status=GuestCheckout.Status.ISSUED,
    )
    if f.route_id:
        qs = qs.filter(trip__route_id=f.route_id)
    if f.agent_id:
        qs = qs.filter(trip__agent_id=f.agent_id)
    rows = (qs.filter(trip__agent__isnull=False)
            .values("trip__agent_id", "trip__agent__full_name")
            .annotate(vendas=Count("id"), receita=Sum("total_amount"))
            .order_by("-receita")[:8])
    return [{
        "agent_id": r["trip__agent_id"],
        "name": r["trip__agent__full_name"],
        "sales": r["vendas"],
        "revenue": _money(r["receita"]),
    } for r in rows]


def _packages(f: AnalyticsFilters) -> dict:
    subs = PassengerPackage.objects.filter(
        created_at__gte=f.dt_from, created_at__lt=f.dt_to,
    )
    by_package = (subs.values("package__name")
                  .annotate(count=Count("id"), revenue=Sum("package__price"))
                  .order_by("-count")[:8])
    now = timezone.now()
    return {
        "subscriptions": subs.count(),
        "active_now": PassengerPackage.objects.filter(
            status=PassengerPackage.Status.ACTIVE, expires_at__gt=now).count(),
        "by_package": [
            {"name": r["package__name"], "count": r["count"], "revenue": _money(r["revenue"])}
            for r in by_package
        ],
    }


def _recent(f: AnalyticsFilters, limit: int = 12) -> list[dict]:
    """Últimos movimentos — o painel deixa de parecer estático."""
    out = []
    for v in (f.validations().select_related("route").order_by("-created_at")[:limit]):
        out.append({
            "kind": "validation",
            "at": v.created_at.isoformat(),
            "label": f"Validação {v.route.code if v.route_id else ''}".strip(),
            "amount": _money(v.amount_debited),
        })
    for p in (f.passes().order_by("-created_at")[:limit]):
        out.append({
            "kind": "ticket",
            "at": p.created_at.isoformat(),
            "label": f"Bilhete {p.route_code} {p.origin_stop}→{p.destination_stop}".strip(),
            "amount": _money(p.fare_amount),
        })
    out.sort(key=lambda x: x["at"], reverse=True)
    return out[:limit]
