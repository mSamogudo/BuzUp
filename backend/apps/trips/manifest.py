"""Manifesto de bordo: quem vai dentro do autocarro, e como lá entrou.

Um autocarro que parte tem de levar a lista de quem vai a bordo. Serve para
três coisas concretas, e é por isso que este ficheiro existe:

* **A bordo** — o motorista precisa de saber quantos são e quem falta, sem
  contar cabeças. Numa rota interprovincial com lugar marcado, precisa também
  de saber que lugar é de quem.
* **Na estrada** — numa fiscalização ou num acidente, a lista de quem estava
  dentro é o documento que interessa; não pode ser reconstruída à pressa.
* **No fim** — o que se cobrou tem de bater com quem viajou. O manifesto é o
  lado dos passageiros da mesma conta de que a receita é o lado do dinheiro.

**Como se enche.** Não há uma lista escrita à mão em lado nenhum: o manifesto
é lido do que já existe. Um bilhete vendido para esta partida entra como
*esperado*; quando é validado à entrada, passa a *a bordo*. Quem paga com
cartão numa paragem não tinha bilhete nenhum — nasce directamente *a bordo* no
momento da validação. É isto que faz a lista crescer ao longo do percurso, sem
o motorista ter de registar nada.

**Porque é fotografado no fecho.** Ao terminar a viagem, esta lista é gravada
tal como estava (ver `activity.close_trip_activity`). Se ficasse a ser
recalculada, um bilhete cancelado ou reembolsado três dias depois mudava a
lista de uma viagem que já aconteceu — e o documento deixava de servir para
aquilo para que existe.
"""

from __future__ import annotations

from decimal import Decimal

from apps.guest_checkouts.models import DigitalTravelPass
from apps.validations.models import ValidationEvent


class Boarding:
    """Estado de um passageiro no manifesto."""

    ABOARD = "aboard"        # validado: entrou
    EXPECTED = "expected"    # bilhete vendido, ainda não validado
    NO_SHOW = "no_show"      # a viagem fechou e nunca validou


# Canais, na linguagem de quem lê o manifesto — não a do código.
CHANNEL_LABELS = {
    "counter": "Balcao",
    "app": "App",
    "web": "Web",
    "card": "Cartao",
    "qr": "QR",
}

# COMO foi pago, que é coisa diferente de ONDE foi comprado. Um bilhete
# vendido ao balcão pode ter sido pago por M-Pesa, e-Mola ou debitando o
# cartão do passageiro — e no fim do dia é isso que decide o que o motorista
# tem em mão e o que já entrou por via electrónica.
PAY_MPESA = "mpesa"
PAY_EMOLA = "emola"
PAY_CARD = "card"
PAY_WALLET = "wallet"
PAY_UNKNOWN = "unknown"

PAYMENT_LABELS = {
    PAY_MPESA: "M-Pesa",
    PAY_EMOLA: "e-Mola",
    PAY_CARD: "Cartao",
    PAY_WALLET: "Saldo BuzUp",
    PAY_UNKNOWN: "-",
}


def _pass_channel(travel_pass) -> str:
    gc = travel_pass.guest_checkout
    if gc is None:
        return "app"
    reference = (gc.reference or "")
    if reference.startswith("AS-"):
        return "counter"
    return "app" if travel_pass.passenger_account_id else "web"


def _payment_method(travel_pass) -> str:
    """Forma de pagamento de um bilhete, lida da intencao de pagamento.

    Sem `guest_checkout` a compra foi feita na app contra o saldo. Com
    checkout, quem manda e o `provider` do pagamento confirmado.
    """
    gc = travel_pass.guest_checkout
    if gc is None:
        return PAY_WALLET

    intents = list(gc.payment_intents.all())
    if not intents:
        return PAY_UNKNOWN
    # O confirmado e o que conta; entre varios, o ultimo.
    confirmado = [p for p in intents if p.status == "confirmed"]
    intent = (confirmado or intents)[-1]

    provider = (intent.provider or "").upper()
    if provider == "MPESA":
        return PAY_MPESA
    if provider == "EMOLA":
        return PAY_EMOLA
    if provider == "WALLET":
        # A carteira debitada pode ser a do cartao fisico (venda no POS com
        # cartao) ou a da conta na app.
        return PAY_CARD if (intent.channel or "") == "POS_CARD" else PAY_WALLET
    return PAY_UNKNOWN


def _entry(
    *,
    key: str,
    name: str,
    seat: str,
    document: str,
    phone: str,
    origin: str,
    destination: str,
    fare,
    channel: str,
    payment: str,
    boarding: str,
    boarded_at=None,
    reference: str = "",
    emergency_name: str = "",
    emergency_phone: str = "",
) -> dict:
    return {
        "key": key,
        "passenger_name": name or "",
        "seat": seat or "",
        "document": document or "",
        "phone": phone or "",
        "origin": origin or "",
        "destination": destination or "",
        "fare_amount": str(fare or Decimal("0.00")),
        "channel": channel,
        "channel_label": CHANNEL_LABELS.get(channel, channel),
        "payment_method": payment,
        "payment_label": PAYMENT_LABELS.get(payment, payment),
        "boarding": boarding,
        "boarded_at": boarded_at.isoformat() if boarded_at else "",
        "reference": reference,
        "emergency_name": emergency_name or "",
        "emergency_phone": emergency_phone or "",
    }


def _seat_sort_key(entry: dict):
    """Ordena por lugar (1A, 2B, 10C...) e só depois por nome.

    Sem isto, "10A" vinha antes de "2A" na ordenação por texto e o motorista
    perdia tempo a procurar a linha na lista.
    """
    seat = entry.get("seat") or ""
    digits = "".join(ch for ch in seat if ch.isdigit())
    letters = "".join(ch for ch in seat if ch.isalpha())
    return (0 if seat else 1, int(digits) if digits else 0, letters,
            entry.get("passenger_name", ""))


def build_manifest(trip, *, final: bool = False) -> dict:
    """Manifesto da partida `trip`.

    `final=True` marca quem nunca validou como falta — só faz sentido quando a
    viagem acaba, porque a meio do percurso um passageiro por validar é
    simplesmente alguém que ainda não entrou.
    """
    entries: list[dict] = []

    # 1. Bilhetes emitidos para esta partida. O estado do próprio bilhete diz
    #    se a pessoa já entrou: USED significa validado à porta.
    passes = (
        DigitalTravelPass.objects
        .filter(trip=trip)
        .exclude(status__in=[DigitalTravelPass.Status.CANCELLED,
                             DigitalTravelPass.Status.REFUNDED])
        .select_related("guest_checkout", "passenger_account")
        .prefetch_related("guest_checkout__payment_intents")
        .order_by("created_at")
    )
    for tp in passes:
        aboard = tp.status == DigitalTravelPass.Status.USED
        entries.append(_entry(
            key=f"pass:{tp.pk}",
            name=tp.passenger_name or (tp.passenger_account.full_name if tp.passenger_account_id else ""),
            seat=tp.seat_number,
            document=tp.document_number,
            phone=tp.payer_phone,
            origin=tp.origin_stop,
            destination=tp.destination_stop,
            fare=tp.fare_amount,
            channel=_pass_channel(tp),
            payment=_payment_method(tp),
            boarding=(Boarding.ABOARD if aboard
                      else (Boarding.NO_SHOW if final else Boarding.EXPECTED)),
            boarded_at=tp.used_at if aboard else None,
            reference=tp.short_code or "",
            emergency_name=tp.emergency_contact_name,
            emergency_phone=tp.emergency_contact_phone,
        ))

    # 2. Quem entrou numa paragem e pagou na hora (cartão ou QR da conta).
    #    Não tinha bilhete: entra já a bordo. As validações de passes digitais
    #    ficam de fora porque essas já vieram no passo 1 — contá-las aqui
    #    duplicava o passageiro.
    validations = (
        ValidationEvent.objects
        .filter(trip=trip, status=ValidationEvent.Status.APPROVED)
        .exclude(validation_type=ValidationEvent.ValidationType.GUEST_DIGITAL_TRAVEL_PASS)
        .exclude(digital_travel_pass__isnull=False)
        .select_related("passenger_account", "origin_stop", "destination_stop", "physical_card")
        .order_by("created_at")
    )
    for ev in validations:
        pa = ev.passenger_account
        entries.append(_entry(
            key=f"val:{ev.pk}",
            name=pa.full_name if pa else "Passageiro avulso",
            seat="",
            document=pa.document_number if pa else "",
            phone=pa.phone_number if pa else "",
            origin=ev.origin_stop.name if ev.origin_stop_id else "",
            destination=ev.destination_stop.name if ev.destination_stop_id else "",
            fare=ev.amount_debited,
            # O canal vem do TIPO de validacao, nao da presenca do cartao: uma
            # leitura de cartao cujo registo do cartao tenha sido apagado
            # continua a ser uma entrada por cartao, e aparecia como QR.
            channel=("card"
                     if ev.validation_type == ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO
                     else "qr"),
            payment=(PAY_CARD
                     if ev.validation_type == ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO
                     else PAY_WALLET),
            boarding=Boarding.ABOARD,
            boarded_at=ev.created_at,
            reference=ev.physical_card.card_number if ev.physical_card_id else "",
        ))

    entries.sort(key=_seat_sort_key)

    aboard = sum(1 for e in entries if e["boarding"] == Boarding.ABOARD)
    expected = sum(1 for e in entries if e["boarding"] == Boarding.EXPECTED)
    no_show = sum(1 for e in entries if e["boarding"] == Boarding.NO_SHOW)
    capacity = trip.vehicle.seated_capacity if trip.vehicle_id and trip.vehicle else 0
    total_fare = sum((Decimal(e["fare_amount"]) for e in entries), Decimal("0.00"))

    # Reparticao por forma de pagamento: e isto que permite ao motorista
    # declarar no fim o que recebeu por carteira movel e conferir o que
    # entrou por cartao ou saldo, que nao lhe passou pelas maos.
    by_payment: dict[str, dict] = {}
    for e in entries:
        if e["boarding"] == Boarding.NO_SHOW:
            continue          # quem faltou nao viajou; nao entra na conta
        slot = by_payment.setdefault(e["payment_method"], {
            "method": e["payment_method"],
            "label": e["payment_label"],
            "count": 0,
            "amount": Decimal("0.00"),
        })
        slot["count"] += 1
        slot["amount"] += Decimal(e["fare_amount"])

    return {
        "trip_id": trip.pk,
        "route_code": trip.route.code if trip.route_id else "",
        "route_name": trip.route.name if trip.route_id else "",
        "vehicle": trip.vehicle.registration if trip.vehicle_id else "",
        "driver": trip.driver.full_name if trip.driver_id else "",
        "planned_departure_at": (trip.planned_departure_at.isoformat()
                                 if trip.planned_departure_at else ""),
        "departed_at": trip.actual_departure_at.isoformat() if trip.actual_departure_at else "",
        "status": trip.status,
        "final": final,
        # Numa carreira urbana isto e um registo de bordo, nao o documento
        # nominal que se entrega numa fiscalizacao — e nem sequer se pedem
        # dados de contacto ao passageiro.
        "formal": bool(getattr(trip.route, "requires_manifest", False)) if trip.route_id else False,
        "service_type": trip.route.service_type if trip.route_id else "",
        "totals": {
            "aboard": aboard,
            "expected": expected,
            "no_show": no_show,
            "total": len(entries),
            "capacity": capacity,
            "seats_free": max(capacity - aboard, 0) if capacity else None,
            "fare_total": str(total_fare),
            "by_payment": [
                {**v, "amount": str(v["amount"])}
                for v in sorted(by_payment.values(), key=lambda x: -x["amount"])
            ],
        },
        "entries": entries,
    }
