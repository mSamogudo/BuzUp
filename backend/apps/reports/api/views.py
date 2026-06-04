from __future__ import annotations

import csv
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate, TruncHour
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import HasCapabilities
from apps.devices.models import Device
from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.passengers.models import PassengerAccount
from apps.payments.models import PaymentIntent
from apps.reports.api.serializers import DateRangeSerializer
from apps.trips.models import Trip
from apps.trips.revenue import calculate_trip_revenue
from apps.validations.models import ValidationEvent
from apps.wallets.models import Wallet, WalletTransaction


def _parse_dates(request):
    s = DateRangeSerializer(data=request.query_params)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    date_from = d.get("date_from")
    date_to = d.get("date_to")

    if date_from:
        dt_from = timezone.make_aware(timezone.datetime.combine(date_from, timezone.datetime.min.time()))
    else:
        dt_from = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if date_to:
        dt_to = timezone.make_aware(timezone.datetime.combine(date_to, timezone.datetime.min.time())) + timedelta(days=1)
    else:
        dt_to = dt_from + timedelta(days=1)

    return dt_from, dt_to, d


def _money(value) -> str:
    return str(Decimal(str(value or 0)).quantize(Decimal("0.01")))


def _stringify_money(totals: dict) -> dict:
    money_keys = {
        "guest_checkout_revenue",
        "app_pass_revenue",
        "wallet_validation_revenue",
        "direct_payment_revenue",
        "total_revenue",
    }
    return {key: _money(value) if key in money_keys else value for key, value in totals.items()}


def _stringify_grouped_money(rows) -> list[dict]:
    result = []
    for row in rows:
        item = dict(row)
        if "total_revenue" in item:
            item["total_revenue"] = _money(item["total_revenue"])
        result.append(item)
    return result


class DashboardView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("reports.read",)

    def get(self, request):
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        passengers_total = PassengerAccount.objects.count()
        wallets_total_balance = Wallet.objects.filter(
            status=Wallet.Status.ACTIVE,
        ).aggregate(total=Sum("balance_cached"))["total"] or 0

        today_validations = ValidationEvent.objects.filter(
            created_at__gte=today_start, created_at__lt=today_end,
        ).aggregate(
            total=Count("id"),
            approved=Count("id", filter=Q(status=ValidationEvent.Status.APPROVED)),
            denied=Count("id", filter=Q(status=ValidationEvent.Status.DENIED)),
            revenue=Sum("amount_debited", filter=Q(status=ValidationEvent.Status.APPROVED)),
        )

        today_topups = WalletTransaction.objects.filter(
            type=WalletTransaction.Type.TOPUP,
            status=WalletTransaction.Status.CONFIRMED,
            created_at__gte=today_start, created_at__lt=today_end,
        ).aggregate(
            count=Count("id"),
            total=Sum("amount"),
        )

        today_guest = GuestCheckout.objects.filter(
            created_at__gte=today_start, created_at__lt=today_end,
        ).aggregate(
            total=Count("id"),
            issued=Count("id", filter=Q(status=GuestCheckout.Status.ISSUED)),
        )

        pending_payments = PaymentIntent.objects.filter(
            status=PaymentIntent.Status.PENDING,
        ).count()

        active_devices = Device.objects.filter(status=Device.Status.ACTIVE).count()
        pending_devices = Device.objects.filter(
            status__in=[Device.Status.SELF_ONBOARDED, Device.Status.PENDING_ACTIVATION],
        ).count()

        return Response({
            "passengers_total": passengers_total,
            "wallets_total_balance": str(wallets_total_balance),
            "today": {
                "validations_total": today_validations["total"] or 0,
                "validations_approved": today_validations["approved"] or 0,
                "validations_denied": today_validations["denied"] or 0,
                "validation_revenue": str(today_validations["revenue"] or 0),
                "topups_count": today_topups["count"] or 0,
                "topups_total": str(today_topups["total"] or 0),
                "guest_checkouts_total": today_guest["total"] or 0,
                "guest_checkouts_issued": today_guest["issued"] or 0,
            },
            "pending_payments": pending_payments,
            "devices_active": active_devices,
            "devices_pending": pending_devices,
        })


class DashboardChartsView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("reports.read",)

    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = today_start - timedelta(days=6)

        revenue_7d = self._revenue_7d(seven_days_ago, now)
        payment_methods = self._payment_methods(seven_days_ago, now)
        top_routes = self._top_routes(seven_days_ago, now)
        hourly_today = self._hourly_today(today_start, now)
        validation_trend = self._validation_trend(seven_days_ago, now)

        return Response({
            "revenue_7d": revenue_7d,
            "payment_methods": payment_methods,
            "top_routes": top_routes,
            "hourly_today": hourly_today,
            "validation_trend": validation_trend,
        })

    def _revenue_7d(self, dt_from, dt_to):
        validations = (
            ValidationEvent.objects.filter(
                status=ValidationEvent.Status.APPROVED,
                created_at__gte=dt_from, created_at__lt=dt_to,
            )
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(revenue=Sum("amount_debited"), count=Count("id"))
            .order_by("day")
        )
        topups = (
            WalletTransaction.objects.filter(
                type=WalletTransaction.Type.TOPUP,
                status=WalletTransaction.Status.CONFIRMED,
                created_at__gte=dt_from, created_at__lt=dt_to,
            )
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(topups=Sum("amount"), topups_count=Count("id"))
            .order_by("day")
        )
        topup_map = {r["day"]: r for r in topups}

        result = []
        for v in validations:
            day = v["day"]
            t = topup_map.get(day, {})
            result.append({
                "date": day.isoformat(),
                "revenue": str(v["revenue"] or 0),
                "validations": v["count"] or 0,
                "topups": str(t.get("topups") or 0),
                "topups_count": t.get("topups_count") or 0,
            })
        all_days = {r["date"] for r in result}
        for t_day, t_data in topup_map.items():
            if t_day.isoformat() not in all_days:
                result.append({
                    "date": t_day.isoformat(),
                    "revenue": "0",
                    "validations": 0,
                    "topups": str(t_data.get("topups") or 0),
                    "topups_count": t_data.get("topups_count") or 0,
                })
        result.sort(key=lambda x: x["date"])
        return result

    def _payment_methods(self, dt_from, dt_to):
        qs = (
            PaymentIntent.objects.filter(
                status=PaymentIntent.Status.CONFIRMED,
                confirmed_at__gte=dt_from, confirmed_at__lt=dt_to,
            )
            .values("provider")
            .annotate(count=Count("id"), total=Sum("amount"))
            .order_by("-total")
        )
        return [
            {"provider": r["provider"] or "Outro", "count": r["count"], "total": str(r["total"] or 0)}
            for r in qs
        ]

    def _top_routes(self, dt_from, dt_to):
        qs = (
            ValidationEvent.objects.filter(
                status=ValidationEvent.Status.APPROVED,
                created_at__gte=dt_from, created_at__lt=dt_to,
                route__isnull=False,
            )
            .values("route__code", "route__name")
            .annotate(count=Count("id"), revenue=Sum("amount_debited"))
            .order_by("-count")[:5]
        )
        return [
            {
                "route_code": r["route__code"],
                "route_name": r["route__name"],
                "count": r["count"],
                "revenue": str(r["revenue"] or 0),
            }
            for r in qs
        ]

    def _hourly_today(self, today_start, now):
        qs = (
            ValidationEvent.objects.filter(
                created_at__gte=today_start, created_at__lt=now,
            )
            .annotate(hour=TruncHour("created_at"))
            .values("hour")
            .annotate(
                total=Count("id"),
                approved=Count("id", filter=Q(status=ValidationEvent.Status.APPROVED)),
                denied=Count("id", filter=Q(status=ValidationEvent.Status.DENIED)),
            )
            .order_by("hour")
        )
        return [
            {
                "hour": r["hour"].strftime("%H:00"),
                "total": r["total"],
                "approved": r["approved"],
                "denied": r["denied"],
            }
            for r in qs
        ]

    def _validation_trend(self, dt_from, dt_to):
        qs = (
            ValidationEvent.objects.filter(
                created_at__gte=dt_from, created_at__lt=dt_to,
            )
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                approved=Count("id", filter=Q(status=ValidationEvent.Status.APPROVED)),
                denied=Count("id", filter=Q(status=ValidationEvent.Status.DENIED)),
            )
            .order_by("day")
        )
        return [
            {"date": r["day"].isoformat(), "approved": r["approved"], "denied": r["denied"]}
            for r in qs
        ]


class RevenueReportView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("reports.read",)

    def get(self, request):
        dt_from, dt_to, params = _parse_dates(request)

        qs = ValidationEvent.objects.filter(
            status=ValidationEvent.Status.APPROVED,
            created_at__gte=dt_from, created_at__lt=dt_to,
        )
        if params.get("route_id"):
            qs = qs.filter(route_id=params["route_id"])
        if params.get("device_id"):
            qs = qs.filter(device_id=params["device_id"])

        by_type = qs.values("validation_type").annotate(
            count=Count("id"), total=Sum("amount_debited"),
        ).order_by("validation_type")

        by_route = qs.values("route__code", "route__name").annotate(
            count=Count("id"), total=Sum("amount_debited"),
        ).order_by("-total")

        totals = qs.aggregate(count=Count("id"), total=Sum("amount_debited"))

        topups = WalletTransaction.objects.filter(
            type=WalletTransaction.Type.TOPUP,
            status=WalletTransaction.Status.CONFIRMED,
            created_at__gte=dt_from, created_at__lt=dt_to,
        ).aggregate(count=Count("id"), total=Sum("amount"))

        return Response({
            "period": {"from": dt_from.isoformat(), "to": dt_to.isoformat()},
            "validations": {
                "total_count": totals["count"] or 0,
                "total_revenue": str(totals["total"] or 0),
                "by_type": list(by_type),
                "by_route": list(by_route),
            },
            "topups": {
                "count": topups["count"] or 0,
                "total": str(topups["total"] or 0),
            },
        })


class OperationalRevenueReportView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("reports.read",)

    def get(self, request):
        dt_from, dt_to, params = _parse_dates(request)

        trips = Trip.objects.select_related("route", "vehicle", "driver").filter(
            Q(activity_started_at__gte=dt_from, activity_started_at__lt=dt_to)
            | Q(activity_closed_at__gte=dt_from, activity_closed_at__lt=dt_to)
            | Q(guest_checkouts__created_at__gte=dt_from, guest_checkouts__created_at__lt=dt_to)
            | Q(validation_events__created_at__gte=dt_from, validation_events__created_at__lt=dt_to)
        ).distinct()

        if params.get("route_id"):
            trips = trips.filter(route_id=params["route_id"])
        if params.get("vehicle_id"):
            trips = trips.filter(vehicle_id=params["vehicle_id"])
        if params.get("driver_id"):
            trips = trips.filter(driver_id=params["driver_id"])
        if params.get("trip_id"):
            trips = trips.filter(pk=params["trip_id"])
        if params.get("stop_id"):
            stop_id = params["stop_id"]
            trips = trips.filter(
                Q(guest_checkouts__origin_stop_ref_id=stop_id)
                | Q(guest_checkouts__destination_stop_ref_id=stop_id)
                | Q(validation_events__origin_stop_id=stop_id)
                | Q(validation_events__destination_stop_id=stop_id)
            ).distinct()

        trip_rows = []
        totals = {
            "guest_checkout_revenue": 0,
            "app_pass_revenue": 0,
            "wallet_validation_revenue": 0,
            "direct_payment_revenue": 0,
            "total_revenue": 0,
            "validations_approved": 0,
            "validations_denied": 0,
        }

        for trip in trips.order_by("route__code", "vehicle__registration", "activity_started_at", "planned_departure_at")[:1000]:
            summary = calculate_trip_revenue(trip)
            row = {
                "trip_id": trip.id,
                "route_id": trip.route_id,
                "route_code": trip.route.code,
                "route_name": trip.route.name,
                "vehicle_id": trip.vehicle_id,
                "vehicle_registration": trip.vehicle.registration if trip.vehicle else "",
                "driver_id": trip.driver_id,
                "driver_name": trip.driver.full_name if trip.driver else "",
                "status": trip.status,
                "opened_at": trip.activity_started_at,
                "closed_at": trip.activity_closed_at,
                "pause_seconds": trip.pause_seconds,
                "summary": summary,
            }
            totals["guest_checkout_revenue"] += float(summary["guest_checkout"]["revenue"])
            totals["app_pass_revenue"] += float(summary["app_passes"]["revenue"])
            totals["wallet_validation_revenue"] += float(summary["wallet_validations"]["revenue"])
            totals["direct_payment_revenue"] += float(summary["direct_payments"]["revenue"])
            totals["total_revenue"] += float(summary["total_revenue"])
            totals["validations_approved"] += summary["validations"]["approved"]
            totals["validations_denied"] += summary["validations"]["denied"]
            trip_rows.append(row)

        by_vehicle = {}
        for row in trip_rows:
            key = row["vehicle_id"] or 0
            current = by_vehicle.setdefault(key, {
                "vehicle_id": row["vehicle_id"],
                "vehicle_registration": row["vehicle_registration"] or "Sem autocarro",
                "trips": 0,
                "total_revenue": 0,
            })
            current["trips"] += 1
            current["total_revenue"] += float(row["summary"]["total_revenue"])

        by_route = {}
        for row in trip_rows:
            key = row["route_id"]
            current = by_route.setdefault(key, {
                "route_id": row["route_id"],
                "route_code": row["route_code"],
                "route_name": row["route_name"],
                "trips": 0,
                "total_revenue": 0,
            })
            current["trips"] += 1
            current["total_revenue"] += float(row["summary"]["total_revenue"])

        return Response({
            "period": {"from": dt_from.isoformat(), "to": dt_to.isoformat()},
            "filters": {
                "route_id": params.get("route_id"),
                "vehicle_id": params.get("vehicle_id"),
                "driver_id": params.get("driver_id"),
                "stop_id": params.get("stop_id"),
                "trip_id": params.get("trip_id"),
            },
            "totals": _stringify_money(totals),
            "by_vehicle": _stringify_grouped_money(by_vehicle.values()),
            "by_route": _stringify_grouped_money(by_route.values()),
            "trips": trip_rows,
        })


class ValidationReportView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("reports.read",)

    def get(self, request):
        dt_from, dt_to, params = _parse_dates(request)

        qs = ValidationEvent.objects.filter(
            created_at__gte=dt_from, created_at__lt=dt_to,
        )
        if params.get("route_id"):
            qs = qs.filter(route_id=params["route_id"])
        if params.get("device_id"):
            qs = qs.filter(device_id=params["device_id"])

        by_status = qs.values("status").annotate(count=Count("id")).order_by("status")
        by_type = qs.values("validation_type").annotate(count=Count("id")).order_by("validation_type")
        by_failure = qs.filter(status=ValidationEvent.Status.DENIED).values(
            "failure_reason",
        ).annotate(count=Count("id")).order_by("-count")

        by_device = qs.filter(device__isnull=False).values(
            "device__serial_number", "device__device_type",
        ).annotate(
            count=Count("id"),
            approved=Count("id", filter=Q(status=ValidationEvent.Status.APPROVED)),
            revenue=Sum("amount_debited", filter=Q(status=ValidationEvent.Status.APPROVED)),
        ).order_by("-count")[:20]

        return Response({
            "period": {"from": dt_from.isoformat(), "to": dt_to.isoformat()},
            "by_status": list(by_status),
            "by_type": list(by_type),
            "by_failure_reason": list(by_failure),
            "by_device": list(by_device),
        })


class ReconciliationView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("reconciliation.read",)

    def get(self, request):
        dt_from, dt_to, _ = _parse_dates(request)

        payments_confirmed = PaymentIntent.objects.filter(
            status=PaymentIntent.Status.CONFIRMED,
            confirmed_at__gte=dt_from, confirmed_at__lt=dt_to,
        ).aggregate(count=Count("id"), total=Sum("amount"))

        payments_pending = PaymentIntent.objects.filter(
            status=PaymentIntent.Status.PENDING,
            created_at__gte=dt_from, created_at__lt=dt_to,
        ).aggregate(count=Count("id"), total=Sum("amount"))

        payments_failed = PaymentIntent.objects.filter(
            status=PaymentIntent.Status.FAILED,
            created_at__gte=dt_from, created_at__lt=dt_to,
        ).aggregate(count=Count("id"), total=Sum("amount"))

        topup_txs = WalletTransaction.objects.filter(
            type=WalletTransaction.Type.TOPUP,
            status=WalletTransaction.Status.CONFIRMED,
            created_at__gte=dt_from, created_at__lt=dt_to,
        ).aggregate(count=Count("id"), total=Sum("amount"))

        fare_txs = WalletTransaction.objects.filter(
            type=WalletTransaction.Type.FARE_DEBIT,
            status=WalletTransaction.Status.CONFIRMED,
            created_at__gte=dt_from, created_at__lt=dt_to,
        ).aggregate(count=Count("id"), total=Sum("amount"))

        guest_paid = GuestCheckout.objects.filter(
            status__in=[GuestCheckout.Status.PAID, GuestCheckout.Status.ISSUED],
            created_at__gte=dt_from, created_at__lt=dt_to,
        ).aggregate(count=Count("id"), total=Sum("total_amount"))

        guest_passes_issued = DigitalTravelPass.objects.filter(
            guest_checkout__isnull=False,
            created_at__gte=dt_from, created_at__lt=dt_to,
        ).aggregate(
            total=Count("id"),
            used=Count("id", filter=Q(status=DigitalTravelPass.Status.USED)),
            expired=Count("id", filter=Q(status=DigitalTravelPass.Status.EXPIRED)),
            active=Count("id", filter=Q(status=DigitalTravelPass.Status.ACTIVE)),
        )

        total_balance = Wallet.objects.filter(
            status=Wallet.Status.ACTIVE,
        ).aggregate(total=Sum("balance_cached"))

        negative_wallets = Wallet.objects.filter(
            balance_cached__lt=0,
        ).count()

        return Response({
            "period": {"from": dt_from.isoformat(), "to": dt_to.isoformat()},
            "payments": {
                "confirmed": {"count": payments_confirmed["count"] or 0, "total": str(payments_confirmed["total"] or 0)},
                "pending": {"count": payments_pending["count"] or 0, "total": str(payments_pending["total"] or 0)},
                "failed": {"count": payments_failed["count"] or 0, "total": str(payments_failed["total"] or 0)},
            },
            "wallet_transactions": {
                "topups": {"count": topup_txs["count"] or 0, "total": str(topup_txs["total"] or 0)},
                "fare_debits": {"count": fare_txs["count"] or 0, "total": str(fare_txs["total"] or 0)},
            },
            "guest_checkouts": {
                "paid": {"count": guest_paid["count"] or 0, "total": str(guest_paid["total"] or 0)},
                "passes_issued": guest_passes_issued["total"] or 0,
                "passes_used": guest_passes_issued["used"] or 0,
                "passes_expired": guest_passes_issued["expired"] or 0,
                "passes_active": guest_passes_issued["active"] or 0,
            },
            "circulation": {
                "total_balance": str(total_balance["total"] or 0),
                "negative_wallets": negative_wallets,
            },
        })


class ExportValidationsView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("reports.read",)

    def get(self, request):
        dt_from, dt_to, params = _parse_dates(request)

        qs = ValidationEvent.objects.select_related(
            "route", "device", "passenger_account", "physical_card",
        ).filter(
            created_at__gte=dt_from, created_at__lt=dt_to,
        ).order_by("-created_at")

        if params.get("route_id"):
            qs = qs.filter(route_id=params["route_id"])

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Data", "Tipo", "Estado", "Valor", "Rota",
            "Paragem Origem", "Paragem Destino",
            "Passageiro", "Cartao", "Dispositivo", "Falha",
        ])

        for v in qs[:5000]:
            writer.writerow([
                v.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                v.validation_type,
                v.status,
                str(v.amount_debited),
                v.route.code if v.route else "",
                v.origin_stop.name if v.origin_stop else "",
                v.destination_stop.name if v.destination_stop else "",
                v.passenger_account.full_name if v.passenger_account else "",
                v.physical_card.card_uid if v.physical_card else "",
                v.device.serial_number if v.device else "",
                v.failure_reason,
            ])

        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=validations.csv"
        return response


from apps.reports.builder import REGISTRY, aggregate_totals
from apps.reports.exporters import render_pdf, render_xlsx
from rest_framework.authentication import BaseAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication


class _QueryTokenJWT(JWTAuthentication):
    """Allow ?token=... so an anchor link can stream PDFs/XLSX."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            return result
        token = request.query_params.get("token") if hasattr(request, "query_params") else request.GET.get("token")
        if not token:
            return None
        validated = self.get_validated_token(token)
        return (self.get_user(validated), validated)


def _parse_filters(request):
    """Builder-specific filter parser. Accepts everything the registry needs."""
    from django.utils.dateparse import parse_date
    from datetime import datetime as _dt

    qp = request.query_params
    df = parse_date(qp.get("date_from") or "")
    dtt = parse_date(qp.get("date_to") or "")
    out = {}
    if df:
        out["date_from"] = timezone.make_aware(_dt.combine(df, _dt.min.time()))
    if dtt:
        out["date_to"] = timezone.make_aware(_dt.combine(dtt, _dt.min.time())) + timedelta(days=1)
    for key in ("status", "agent_user_id", "route_id", "provider", "kind",
                "validation_type", "device_id"):
        if qp.get(key):
            out[key] = qp[key]
    return out


def _filters_summary(filters: dict) -> str:
    if not filters:
        return ""
    items = []
    for k, v in filters.items():
        if k in ("date_from", "date_to"):
            continue
        items.append(f"{k}={v}")
    return " · ".join(items)


def _resolve_spec(report_kind: str):
    spec = REGISTRY.get(report_kind)
    if not spec:
        raise ValueError(f"Relatorio desconhecido: {report_kind}")
    return spec


class ReportBuilderListView(APIView):
    """Returns metadata about every supported report (frontend uses this to
    build the kind picker + column headers).
    """
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("reports.read",)

    def get(self, request):
        return Response({
            "reports": [
                {
                    "key": s.key,
                    "title": s.title,
                    "columns": [{"key": k, "label": l} for k, l in s.columns],
                }
                for s in REGISTRY.values()
            ],
        })


class ReportBuilderRunView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    authentication_classes = [JWTAuthentication, _QueryTokenJWT]
    required_capabilities = ("reports.read",)

    def get(self, request, kind: str):
        try:
            spec = _resolve_spec(kind)
        except ValueError as e:
            return Response({"detail": str(e)}, status=404)

        filters = _parse_filters(request)
        rows = spec.build_rows(filters)
        totals = aggregate_totals(spec, rows)

        df = filters.get("date_from")
        dt_to = filters.get("date_to")
        period_from = df.date().isoformat() if df else ""
        period_to = (dt_to - timedelta(seconds=1)).date().isoformat() if dt_to else ""
        filters_summary = _filters_summary(filters)

        # NOTE: using `output` (not `format`) so DRF's content negotiator
        # doesn't intercept it and return 404 for unknown renderers.
        fmt = (request.query_params.get("output") or request.query_params.get("format") or "json").lower()

        if fmt == "pdf":
            pdf = render_pdf(
                title=spec.title, period_from=period_from, period_to=period_to,
                columns=spec.columns, rows=rows,
                totals=totals, filters_summary=filters_summary,
            )
            resp = HttpResponse(pdf, content_type="application/pdf")
            resp["Content-Disposition"] = f'inline; filename="relatorio-{kind}-{period_from}-{period_to}.pdf"'
            return resp

        if fmt == "xlsx":
            data = render_xlsx(
                title=spec.title, period_from=period_from, period_to=period_to,
                columns=spec.columns, rows=rows,
                totals=totals, filters_summary=filters_summary,
            )
            resp = HttpResponse(data, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            resp["Content-Disposition"] = f'attachment; filename="relatorio-{kind}-{period_from}-{period_to}.xlsx"'
            return resp

        return Response({
            "kind": spec.key,
            "title": spec.title,
            "period_from": period_from,
            "period_to": period_to,
            "filters": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in filters.items()},
            "totals": totals,
            "columns": [{"key": k, "label": l} for k, l in spec.columns],
            "rows": [
                {
                    k: (v.isoformat() if hasattr(v, "isoformat") else v)
                    for k, v in row.items()
                }
                for row in rows[:500]
            ],
            "row_count": len(rows),
            "truncated": len(rows) > 500,
        })


class ExportTransactionsView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("reports.read",)

    def get(self, request):
        dt_from, dt_to, _ = _parse_dates(request)

        qs = WalletTransaction.objects.select_related(
            "wallet__passenger_account",
        ).filter(
            created_at__gte=dt_from, created_at__lt=dt_to,
        ).order_by("-created_at")

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Data", "Referencia", "Tipo", "Direccao", "Valor",
            "Saldo Antes", "Saldo Depois", "Passageiro", "Fonte", "Estado",
        ])

        for t in qs[:5000]:
            passenger_name = ""
            if t.wallet and t.wallet.passenger_account:
                passenger_name = t.wallet.passenger_account.full_name
            writer.writerow([
                t.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                t.reference,
                t.type,
                t.direction,
                str(t.amount),
                str(t.balance_before),
                str(t.balance_after),
                passenger_name,
                t.source,
                t.status,
            ])

        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=transactions.csv"
        return response
