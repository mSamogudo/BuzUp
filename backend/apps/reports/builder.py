"""Report builder: a small registry that exposes every supported report
under a single API. Each entry defines:

  - title (human-readable)
  - columns (list of (key, label) pairs used by the table preview + exports)
  - build_rows(filters) → list[dict]  (lazy execution; keep it under 5000)

The view layer (`views.py`) hands the right entry to the JSON/PDF/Excel
renderers so the frontend has ONE endpoint to call regardless of the report
type.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Callable

from django.db.models import Q
from django.utils import timezone

from apps.payments.models import PaymentIntent


def _mask(phone: str | None) -> str:
    p = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(p) < 4:
        return p
    return f"***{p[-4:]}"


def _date_range(filters: dict):
    df = filters.get("date_from")
    dt = filters.get("date_to")
    now = timezone.now()
    if not df:
        df = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if not dt:
        dt = (df + timedelta(days=1))
    return df, dt


# ---------------------------------------------------------------------------
# Report definitions
# ---------------------------------------------------------------------------

def _rows_sales(filters: dict) -> list[dict]:
    df, dt = _date_range(filters)
    qs = (
        PaymentIntent.objects
        .select_related("guest_checkout", "guest_checkout__trip", "guest_checkout__trip__route")
        .filter(
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
            created_at__gte=df, created_at__lt=dt,
        )
        .order_by("-created_at")
    )
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("agent_user_id"):
        qs = qs.filter(metadata__agent_user_id=int(filters["agent_user_id"]))
    if filters.get("route_id"):
        qs = qs.filter(guest_checkout__trip__route_id=int(filters["route_id"]))
    if filters.get("provider"):
        qs = qs.filter(provider__icontains=filters["provider"])

    out = []
    for pi in qs[:5000]:
        gc = pi.guest_checkout
        meta = pi.metadata or {}
        out.append({
            "created_at": pi.created_at,
            "reference": pi.reference,
            "sale_reference": gc.reference if gc else "",
            "route_code": gc.route_code if gc else "",
            "origin": gc.origin_stop if gc else "",
            "destination": gc.destination_stop if gc else "",
            "amount": str(pi.amount),
            "quantity": gc.quantity if gc else 0,
            "method": meta.get("payment_method", "mobile_money"),
            "agent_user_id": meta.get("agent_user_id"),
            "device_serial": meta.get("device_serial", ""),
            "payer": _mask(pi.payer_phone),
            "provider": pi.provider or "",
            "status": pi.status,
        })
    return out


SALES = ("sales", "Vendas (bilhetes guest)", [
    ("created_at", "Data"),
    ("reference", "Pagamento"),
    ("sale_reference", "Venda"),
    ("route_code", "Rota"),
    ("origin", "Origem"),
    ("destination", "Destino"),
    ("quantity", "Qtd"),
    ("amount", "Valor"),
    ("method", "Metodo"),
    ("agent_user_id", "Agente"),
    ("payer", "Pagador"),
    ("status", "Estado"),
])


def _rows_topups(filters: dict) -> list[dict]:
    df, dt = _date_range(filters)
    qs = (
        PaymentIntent.objects
        .filter(
            purpose=PaymentIntent.Purpose.POS_CARD_TOPUP,
            created_at__gte=df, created_at__lt=dt,
        )
        .order_by("-created_at")
    )
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("agent_user_id"):
        qs = qs.filter(metadata__agent_user_id=int(filters["agent_user_id"]))
    kind = filters.get("kind")  # wallet | package | card_issuance | card_recovery
    if kind:
        qs = qs.filter(metadata__kind=kind)

    out = []
    for pi in qs[:5000]:
        meta = pi.metadata or {}
        # Distinguish wallet topup vs package vs issuance vs recovery
        kind = meta.get("kind") or (
            "package" if "package_id" in meta else "wallet"
        )
        out.append({
            "created_at": pi.created_at,
            "reference": pi.reference,
            "kind": kind,
            "card_uid": meta.get("card_uid", ""),
            "amount": str(pi.amount),
            "agent_user_id": meta.get("agent_user_id"),
            "payer": _mask(pi.payer_phone),
            "provider": pi.provider or "",
            "status": pi.status,
        })
    return out


TOPUPS = ("topups", "Recargas / Pacotes / Emissoes", [
    ("created_at", "Data"),
    ("reference", "Referencia"),
    ("kind", "Tipo"),
    ("card_uid", "Cartao"),
    ("amount", "Valor"),
    ("agent_user_id", "Agente"),
    ("payer", "Pagador"),
    ("provider", "Provider"),
    ("status", "Estado"),
])


def _rows_validations(filters: dict) -> list[dict]:
    from apps.validations.models import ValidationEvent
    df, dt = _date_range(filters)
    qs = (
        ValidationEvent.objects
        .select_related("route", "device", "passenger_account")
        .filter(created_at__gte=df, created_at__lt=dt)
        .order_by("-created_at")
    )
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("route_id"):
        qs = qs.filter(route_id=int(filters["route_id"]))
    if filters.get("validation_type"):
        qs = qs.filter(validation_type=filters["validation_type"])
    if filters.get("device_id"):
        qs = qs.filter(device_id=int(filters["device_id"]))

    out = []
    for v in qs[:5000]:
        out.append({
            "created_at": v.created_at,
            "validation_type": v.validation_type,
            "route": v.route.code if v.route_id else "",
            "device": v.device.serial_number if v.device_id else "",
            "amount_debited": str(v.amount_debited),
            "status": v.status,
            "failure_reason": v.failure_reason or "",
            "passenger": v.passenger_account.full_name if v.passenger_account_id else "",
        })
    return out


VALIDATIONS = ("validations", "Validacoes", [
    ("created_at", "Data"),
    ("validation_type", "Tipo"),
    ("route", "Rota"),
    ("device", "Dispositivo"),
    ("amount_debited", "Debito"),
    ("status", "Estado"),
    ("failure_reason", "Motivo falha"),
    ("passenger", "Passageiro"),
])


def _rows_onboardings(filters: dict) -> list[dict]:
    """Card issuance flow audit. Reads PaymentIntents with kind=card_issuance.

    Useful to see how many new passengers each agent onboarded per period.
    """
    df, dt = _date_range(filters)
    qs = (
        PaymentIntent.objects
        .filter(
            purpose=PaymentIntent.Purpose.POS_CARD_TOPUP,
            metadata__kind="card_issuance",
            created_at__gte=df, created_at__lt=dt,
        )
        .order_by("-created_at")
    )
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("agent_user_id"):
        qs = qs.filter(metadata__agent_user_id=int(filters["agent_user_id"]))

    out = []
    for pi in qs[:5000]:
        meta = pi.metadata or {}
        out.append({
            "created_at": pi.created_at,
            "reference": pi.reference,
            "passenger_id": meta.get("passenger_id"),
            "card_uid": meta.get("card_uid", ""),
            "amount": str(pi.amount),
            "agent_user_id": meta.get("agent_user_id"),
            "device": meta.get("device_serial", ""),
            "payer": _mask(pi.payer_phone),
            "status": pi.status,
        })
    return out


ONBOARDING = ("onboarding", "Registo de passageiros (com cartao)", [
    ("created_at", "Data"),
    ("reference", "Pagamento"),
    ("passenger_id", "Passageiro"),
    ("card_uid", "UID cartao"),
    ("amount", "Taxa"),
    ("agent_user_id", "Agente"),
    ("device", "Dispositivo"),
    ("payer", "Pagador"),
    ("status", "Estado"),
])


def _rows_recoveries(filters: dict) -> list[dict]:
    df, dt = _date_range(filters)
    qs = (
        PaymentIntent.objects
        .filter(
            purpose=PaymentIntent.Purpose.POS_CARD_TOPUP,
            metadata__kind="card_recovery",
            created_at__gte=df, created_at__lt=dt,
        )
        .order_by("-created_at")
    )
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("agent_user_id"):
        qs = qs.filter(metadata__agent_user_id=int(filters["agent_user_id"]))

    out = []
    for pi in qs[:5000]:
        meta = pi.metadata or {}
        out.append({
            "created_at": pi.created_at,
            "reference": pi.reference,
            "passenger_id": meta.get("passenger_id"),
            "new_card_uid": meta.get("card_uid", ""),
            "blocked_cards": meta.get("blocked_cards", 0),
            "amount": str(pi.amount),
            "reason": meta.get("reason", ""),
            "agent_user_id": meta.get("agent_user_id"),
            "status": pi.status,
        })
    return out


RECOVERIES = ("recoveries", "Recuperacao de cartoes", [
    ("created_at", "Data"),
    ("reference", "Pagamento"),
    ("passenger_id", "Passageiro"),
    ("new_card_uid", "Novo UID"),
    ("blocked_cards", "Bloqueados"),
    ("amount", "Taxa"),
    ("reason", "Motivo"),
    ("agent_user_id", "Agente"),
    ("status", "Estado"),
])


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

@dataclass
class ReportSpec:
    key: str
    title: str
    columns: list[tuple[str, str]]
    build_rows: Callable[[dict], list[dict]]


REGISTRY: dict[str, ReportSpec] = {
    SALES[0]: ReportSpec(SALES[0], SALES[1], SALES[2], _rows_sales),
    TOPUPS[0]: ReportSpec(TOPUPS[0], TOPUPS[1], TOPUPS[2], _rows_topups),
    VALIDATIONS[0]: ReportSpec(VALIDATIONS[0], VALIDATIONS[1], VALIDATIONS[2], _rows_validations),
    ONBOARDING[0]: ReportSpec(ONBOARDING[0], ONBOARDING[1], ONBOARDING[2], _rows_onboardings),
    RECOVERIES[0]: ReportSpec(RECOVERIES[0], RECOVERIES[1], RECOVERIES[2], _rows_recoveries),
}


def aggregate_totals(spec: ReportSpec, rows: list[dict]) -> dict:
    """Compute headline totals for the report header. Specific per kind."""
    totals = {"count": len(rows)}
    if spec.key in {"sales", "topups", "onboarding", "recoveries"}:
        ok = [r for r in rows if r.get("status") == "confirmed"]
        totals["confirmed_count"] = len(ok)
        totals["total_amount"] = str(sum((Decimal(r["amount"]) for r in ok), Decimal("0.00")))
    elif spec.key == "validations":
        ok = [r for r in rows if r.get("status") == "approved"]
        totals["approved_count"] = len(ok)
        totals["total_debited"] = str(sum((Decimal(r["amount_debited"]) for r in ok), Decimal("0.00")))
    return totals
