"""Admin endpoints for monitoring agent revenue and day-close submissions."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, Count
from django.http import HttpResponse as DjangoHttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.agent_api.exporters import session_pdf, session_xlsx, summary_pdf, summary_xlsx
from apps.agent_api.models import AgentDayClose
from apps.core.permissions import HasCapabilities


class QueryTokenJWTAuthentication(JWTAuthentication):
    """Accepts JWT in ?token=... too, so anchor tags can download files."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            return result
        token = request.query_params.get("token") if hasattr(request, "query_params") else request.GET.get("token")
        if not token:
            return None
        validated = self.get_validated_token(token)
        return (self.get_user(validated), validated)


class AdminAgentDayCloseListView(APIView):
    """Lists day-close records made by all agents, with filters."""
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("reports.read",)

    def get(self, request):
        qs = AgentDayClose.objects.select_related("agent_user", "agent_profile").all()

        agent_id = request.query_params.get("agent_id")
        if agent_id:
            qs = qs.filter(agent_profile_id=agent_id)

        agent_user_id = request.query_params.get("agent_user_id")
        if agent_user_id:
            qs = qs.filter(agent_user_id=agent_user_id)

        date_from = request.query_params.get("date_from")
        if date_from:
            d = parse_date(date_from)
            if d:
                qs = qs.filter(date__gte=d)

        date_to = request.query_params.get("date_to")
        if date_to:
            d = parse_date(date_to)
            if d:
                qs = qs.filter(date__lte=d)

        results = []
        for r in qs.order_by("-closed_at")[:500]:
            results.append({
                "id": r.id,
                "uuid": str(r.uuid),
                "agent_id": r.agent_profile_id,
                "agent_name": r.agent_profile.full_name if r.agent_profile else (r.agent_user.get_full_name() or r.agent_user.username),
                "agent_phone": r.agent_profile.phone if r.agent_profile else r.agent_user.phone,
                "date": r.date.isoformat(),
                "closed_at": r.closed_at.isoformat(),
                "total_revenue": str(r.total_revenue),
                "sales_total": str(r.sales_total),
                "topups_total": str(r.topups_total),
                "validations_revenue": str(r.validations_revenue),
                "tickets_count": r.tickets_count,
                "validations_count": r.validations_count,
                "confirmed_count": r.confirmed_count,
                "pending_count": r.pending_count,
                "failed_count": r.failed_count,
                "sessions_closed": r.sessions_closed,
            })
        return Response({"count": len(results), "results": results})


class AdminAgentDayCloseDetailView(APIView):
    """Full payload (sales/topups/validations arrays) for one day close."""
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("reports.read",)

    def get(self, request, pk):
        try:
            r = AgentDayClose.objects.select_related("agent_user", "agent_profile").get(pk=pk)
        except AgentDayClose.DoesNotExist:
            return Response({"detail": "Fecho nao encontrado."}, status=404)
        return Response({
            "id": r.id,
            "uuid": str(r.uuid),
            "agent_id": r.agent_profile_id,
            "agent_name": r.agent_profile.full_name if r.agent_profile else (r.agent_user.get_full_name() or r.agent_user.username),
            "agent_phone": r.agent_profile.phone if r.agent_profile else r.agent_user.phone,
            "date": r.date.isoformat(),
            "closed_at": r.closed_at.isoformat(),
            "total_revenue": str(r.total_revenue),
            "sales_total": str(r.sales_total),
            "topups_total": str(r.topups_total),
            "validations_revenue": str(r.validations_revenue),
            "tickets_count": r.tickets_count,
            "validations_count": r.validations_count,
            "confirmed_count": r.confirmed_count,
            "pending_count": r.pending_count,
            "failed_count": r.failed_count,
            "sessions_closed": r.sessions_closed,
            "payload": r.payload or {},
        })


class AdminAgentRevenueSummaryView(APIView):
    """Aggregated revenue per agent over a date range. Default last 30 days."""
    permission_classes = [IsAuthenticated, HasCapabilities]
    required_capabilities = ("reports.read",)

    def get(self, request):
        today = timezone.now().date()
        date_from = parse_date(request.query_params.get("date_from") or "") or (today - timedelta(days=30))
        date_to = parse_date(request.query_params.get("date_to") or "") or today

        qs = (
            AgentDayClose.objects.filter(date__gte=date_from, date__lte=date_to)
            .select_related("agent_profile", "agent_user")
            .values(
                "agent_profile_id", "agent_user_id",
                "agent_profile__full_name", "agent_profile__phone",
                "agent_user__first_name", "agent_user__last_name", "agent_user__username",
            )
            .annotate(
                total_revenue=Sum("total_revenue"),
                sales_total=Sum("sales_total"),
                topups_total=Sum("topups_total"),
                validations_revenue=Sum("validations_revenue"),
                tickets=Sum("tickets_count"),
                validations=Sum("validations_count"),
                closes=Count("id"),
            )
            .order_by("-total_revenue")
        )

        totals = {
            "total_revenue": Decimal("0.00"),
            "sales_total": Decimal("0.00"),
            "topups_total": Decimal("0.00"),
            "validations_revenue": Decimal("0.00"),
            "tickets": 0,
            "validations": 0,
            "closes": 0,
            "agents_count": 0,
        }
        results = []
        for r in qs:
            name = r["agent_profile__full_name"] or f"{r['agent_user__first_name'] or ''} {r['agent_user__last_name'] or ''}".strip() or r["agent_user__username"]
            results.append({
                "agent_id": r["agent_profile_id"],
                "agent_user_id": r["agent_user_id"],
                "agent_name": name,
                "agent_phone": r["agent_profile__phone"] or "",
                "total_revenue": str(r["total_revenue"] or 0),
                "sales_total": str(r["sales_total"] or 0),
                "topups_total": str(r["topups_total"] or 0),
                "validations_revenue": str(r["validations_revenue"] or 0),
                "tickets": int(r["tickets"] or 0),
                "validations": int(r["validations"] or 0),
                "closes": int(r["closes"] or 0),
            })
            totals["total_revenue"] += r["total_revenue"] or Decimal("0.00")
            totals["sales_total"] += r["sales_total"] or Decimal("0.00")
            totals["topups_total"] += r["topups_total"] or Decimal("0.00")
            totals["validations_revenue"] += r["validations_revenue"] or Decimal("0.00")
            totals["tickets"] += int(r["tickets"] or 0)
            totals["validations"] += int(r["validations"] or 0)
            totals["closes"] += int(r["closes"] or 0)
        totals["agents_count"] = len(results)
        totals["total_revenue"] = str(totals["total_revenue"])
        totals["sales_total"] = str(totals["sales_total"])
        totals["topups_total"] = str(totals["topups_total"])
        totals["validations_revenue"] = str(totals["validations_revenue"])

        return Response({
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "totals": totals,
            "agents": results,
        })


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

def _aggregate_summary(date_from, date_to) -> dict:
    qs = (
        AgentDayClose.objects.filter(date__gte=date_from, date__lte=date_to)
        .select_related("agent_profile", "agent_user")
        .values(
            "agent_profile_id", "agent_user_id",
            "agent_profile__full_name", "agent_profile__phone",
            "agent_user__first_name", "agent_user__last_name", "agent_user__username",
        )
        .annotate(
            total_revenue=Sum("total_revenue"),
            sales_total=Sum("sales_total"),
            topups_total=Sum("topups_total"),
            validations_revenue=Sum("validations_revenue"),
            tickets=Sum("tickets_count"),
            validations=Sum("validations_count"),
            closes=Count("id"),
        )
        .order_by("-total_revenue")
    )
    totals = {
        "total_revenue": Decimal("0.00"), "sales_total": Decimal("0.00"),
        "topups_total": Decimal("0.00"), "validations_revenue": Decimal("0.00"),
        "tickets": 0, "validations": 0, "closes": 0, "agents_count": 0,
    }
    agents = []
    for r in qs:
        name = r["agent_profile__full_name"] or f"{r['agent_user__first_name'] or ''} {r['agent_user__last_name'] or ''}".strip() or r["agent_user__username"]
        agents.append({
            "agent_id": r["agent_profile_id"],
            "agent_user_id": r["agent_user_id"],
            "agent_name": name,
            "agent_phone": r["agent_profile__phone"] or "",
            "total_revenue": r["total_revenue"] or Decimal("0.00"),
            "sales_total": r["sales_total"] or Decimal("0.00"),
            "topups_total": r["topups_total"] or Decimal("0.00"),
            "validations_revenue": r["validations_revenue"] or Decimal("0.00"),
            "tickets": int(r["tickets"] or 0),
            "validations": int(r["validations"] or 0),
            "closes": int(r["closes"] or 0),
        })
        totals["total_revenue"] += r["total_revenue"] or Decimal("0.00")
        totals["sales_total"] += r["sales_total"] or Decimal("0.00")
        totals["topups_total"] += r["topups_total"] or Decimal("0.00")
        totals["validations_revenue"] += r["validations_revenue"] or Decimal("0.00")
        totals["tickets"] += int(r["tickets"] or 0)
        totals["validations"] += int(r["validations"] or 0)
        totals["closes"] += int(r["closes"] or 0)
    totals["agents_count"] = len(agents)
    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "totals": totals,
        "agents": agents,
    }


class _BaseExportView(APIView):
    permission_classes = [IsAuthenticated, HasCapabilities]
    authentication_classes = [JWTAuthentication, QueryTokenJWTAuthentication]
    required_capabilities = ("reports.read",)


class AdminAgentDayCloseExportPdfView(_BaseExportView):
    def get(self, request, pk):
        try:
            record = AgentDayClose.objects.select_related("agent_user", "agent_profile").get(pk=pk)
        except AgentDayClose.DoesNotExist:
            return Response({"detail": "Nao encontrado."}, status=404)
        pdf = session_pdf(record)
        resp = DjangoHttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="fecho-{record.date}-{record.agent_user_id}.pdf"'
        return resp


class AdminAgentDayCloseExportXlsxView(_BaseExportView):
    def get(self, request, pk):
        try:
            record = AgentDayClose.objects.select_related("agent_user", "agent_profile").get(pk=pk)
        except AgentDayClose.DoesNotExist:
            return Response({"detail": "Nao encontrado."}, status=404)
        xlsx = session_xlsx(record)
        resp = DjangoHttpResponse(xlsx, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp["Content-Disposition"] = f'attachment; filename="fecho-{record.date}-{record.agent_user_id}.xlsx"'
        return resp


class AdminAgentRevenueExportPdfView(_BaseExportView):
    def get(self, request):
        today = timezone.now().date()
        date_from = parse_date(request.query_params.get("date_from") or "") or (today - timedelta(days=30))
        date_to = parse_date(request.query_params.get("date_to") or "") or today
        data = _aggregate_summary(date_from, date_to)
        pdf = summary_pdf(data)
        resp = DjangoHttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="resumo-receita-{date_from}-{date_to}.pdf"'
        return resp


class AdminAgentRevenueExportXlsxView(_BaseExportView):
    def get(self, request):
        today = timezone.now().date()
        date_from = parse_date(request.query_params.get("date_from") or "") or (today - timedelta(days=30))
        date_to = parse_date(request.query_params.get("date_to") or "") or today
        data = _aggregate_summary(date_from, date_to)
        xlsx = summary_xlsx(data)
        resp = DjangoHttpResponse(xlsx, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp["Content-Disposition"] = f'attachment; filename="resumo-receita-{date_from}-{date_to}.xlsx"'
        return resp
