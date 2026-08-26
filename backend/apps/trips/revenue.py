from __future__ import annotations

from decimal import Decimal

from django.db.models import Count, Q, Sum

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.payments.models import CASH_PROVIDER, PaymentIntent
from apps.trips.models import Trip
from apps.validations.models import ValidationEvent


PAY_AS_YOU_GO_VALIDATION_TYPES = (
    ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO,
    ValidationEvent.ValidationType.QR_PAY_AS_YOU_GO,
)


def calculate_trip_revenue(trip: Trip) -> dict:
    vendidos = GuestCheckout.objects.filter(
        trip=trip,
        status__in=[GuestCheckout.Status.PAID, GuestCheckout.Status.ISSUED],
    )
    guest = vendidos.aggregate(
        count=Count("id"), tickets=Sum("quantity"), total=Sum("total_amount"))

    # NUMERARIO, em separado. Uma venda a dinheiro tambem e um `GuestCheckout`
    # e ja esta contada na linha acima — mas contada nao chega. As outras
    # formas de pagamento entram directamente na conta da operadora; esta fica
    # em NOTAS na mao do agente, e alguem tem de as receber no fim do dia.
    # Somada as de M-Pesa era impossivel dizer quanto cobrar a quem.
    #
    # Nao entra no `total`: seria contar o mesmo dinheiro duas vezes. E um
    # recorte do que ja la esta, e o fecho de caixa le-o como tal.
    dinheiro = vendidos.filter(
        payment_intents__status=PaymentIntent.Status.CONFIRMED,
        payment_intents__provider=CASH_PROVIDER,
    ).distinct().aggregate(
        count=Count("id", distinct=True), tickets=Sum("quantity"), total=Sum("total_amount"))

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
        # Recorte do `guest_checkout` acima, nao uma parcela a somar.
        "cash": {
            "count": dinheiro["count"] or 0,
            "tickets": dinheiro["tickets"] or 0,
            "revenue": str(_decimal(dinheiro["total"])),
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


def calculate_trips_revenue_bulk(trips) -> dict[int, dict]:
    """A mesma coisa que `calculate_trip_revenue`, mas para muitas viagens.

    O relatorio operacional percorria ate 1000 viagens chamando
    `calculate_trip_revenue` por cada uma — 8 agregados cada, ~8000 queries num
    unico pedido, uma delas um seq scan a `PaymentIntent` por `metadata__trip_id`.
    Ocupava um worker durante minutos e saturava o Postgres antes de ser morto
    pelo timeout.

    Aqui sao 6 agregados no total, agrupados por viagem, qualquer que seja o
    numero de viagens. Devolve {trip_id: mesmo dicionario de sempre}.
    """
    trip_ids = [t.pk for t in trips]
    if not trip_ids:
        return {}

    def by_trip(rows, key="trip_id"):
        return {row[key]: row for row in rows}

    guest = by_trip(
        GuestCheckout.objects
        .filter(trip_id__in=trip_ids,
                status__in=[GuestCheckout.Status.PAID, GuestCheckout.Status.ISSUED])
        .values("trip_id")
        .annotate(count=Count("id"), tickets=Sum("quantity"), total=Sum("total_amount"))
    )
    # Recorte a dinheiro, pelo mesmo criterio da versao por viagem. Tem de
    # existir aqui tambem: ha um teste que exige que as duas contas deem o
    # mesmo, e sem isto o relatorio em lote escondia o numerario.
    dinheiro = by_trip(
        GuestCheckout.objects
        .filter(trip_id__in=trip_ids,
                status__in=[GuestCheckout.Status.PAID, GuestCheckout.Status.ISSUED],
                payment_intents__status=PaymentIntent.Status.CONFIRMED,
                payment_intents__provider=CASH_PROVIDER)
        .values("trip_id")
        .annotate(count=Count("id", distinct=True), tickets=Sum("quantity"),
                  total=Sum("total_amount"))
    )
    app_passes = by_trip(
        DigitalTravelPass.objects
        .filter(trip_id__in=trip_ids, guest_checkout__isnull=True, passenger_account__isnull=False)
        .values("trip_id")
        .annotate(count=Count("id"), total=Sum("fare_amount"))
    )
    wallet_val = by_trip(
        ValidationEvent.objects
        .filter(trip_id__in=trip_ids, status=ValidationEvent.Status.APPROVED,
                validation_type__in=PAY_AS_YOU_GO_VALIDATION_TYPES)
        .values("trip_id")
        .annotate(count=Count("id"), total=Sum("amount_debited"))
    )
    pass_val = by_trip(
        ValidationEvent.objects
        .filter(trip_id__in=trip_ids, status=ValidationEvent.Status.APPROVED)
        .exclude(validation_type__in=PAY_AS_YOU_GO_VALIDATION_TYPES)
        .values("trip_id")
        .annotate(count=Count("id"), total=Sum("amount_debited"))
    )
    val_counts = by_trip(
        ValidationEvent.objects
        .filter(trip_id__in=trip_ids)
        .values("trip_id")
        .annotate(
            approved=Count("id", filter=Q(status=ValidationEvent.Status.APPROVED)),
            denied=Count("id", filter=Q(status=ValidationEvent.Status.DENIED)),
        )
    )
    # `metadata__trip_id` guarda o id como valor JSON; agrupar em SQL exigiria
    # uma expressao sobre JSONB. Uma unica query traz as linhas do periodo e o
    # agrupamento faz-se em memoria — continua a ser 1 query em vez de N.
    direct_rows = (
        PaymentIntent.objects
        .filter(status=PaymentIntent.Status.CONFIRMED,
                purpose=PaymentIntent.Purpose.DIRECT_TRIP_PAYMENT,
                metadata__trip_id__in=trip_ids)
        .values("metadata", "amount")
    )
    direct: dict[int, dict] = {}
    for row in direct_rows:
        tid = (row["metadata"] or {}).get("trip_id")
        if tid is None:
            continue
        entry = direct.setdefault(tid, {"count": 0, "total": Decimal("0.00")})
        entry["count"] += 1
        entry["total"] += Decimal(row["amount"] or "0.00")

    empty = {"count": 0, "tickets": 0, "total": None}
    result: dict[int, dict] = {}
    for trip_id in trip_ids:
        g = guest.get(trip_id, empty)
        a = app_passes.get(trip_id, empty)
        w = wallet_val.get(trip_id, empty)
        p = pass_val.get(trip_id, empty)
        v = val_counts.get(trip_id, {"approved": 0, "denied": 0})
        d = direct.get(trip_id, {"count": 0, "total": Decimal("0.00")})

        guest_total = _decimal(g.get("total"))
        app_total = _decimal(a.get("total"))
        wallet_total = _decimal(w.get("total"))
        direct_total = _decimal(d["total"])

        c = dinheiro.get(trip_id, empty)
        result[trip_id] = {
            "cash": {
                "count": c.get("count") or 0,
                "tickets": c.get("tickets") or 0,
                "revenue": str(_decimal(c.get("total"))),
            },
            "guest_checkout": {
                "count": g.get("count") or 0,
                "tickets": g.get("tickets") or 0,
                "revenue": str(guest_total),
            },
            "app_passes": {
                "count": a.get("count") or 0,
                "revenue": str(app_total),
            },
            "wallet_validations": {
                "count": w.get("count") or 0,
                "revenue": str(wallet_total),
            },
            "digital_pass_validations": {
                "count": p.get("count") or 0,
                "nominal_value": str(_decimal(p.get("total"))),
            },
            "direct_payments": {
                "count": d["count"],
                "revenue": str(direct_total),
            },
            "validations": {
                "approved": v.get("approved", 0),
                "denied": v.get("denied", 0),
            },
            "total_revenue": str(guest_total + app_total + wallet_total + direct_total),
        }
    return result
