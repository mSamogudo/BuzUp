from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.guest_checkouts.ticket_codes import ticket_reference, ticket_short_code
from apps.sms.services.sender import send_sms


def validity_window(trip) -> tuple:
    """Janela de validade do passe, a partir da partida a que ele pertence.

    Sem partida marcada (compra a bordo, carreira urbana), vale 24h: o bilhete
    e para o autocarro que esta ali.

    Com partida marcada — o interprovincial comprado dias antes — vale desde
    3h antes da partida ate 12h depois. As 3h cobrem quem chega cedo ao
    terminal; as 12h cobrem um atraso na estrada, para o bilhete nao expirar
    com o passageiro ainda a viajar.

    **Vive aqui, e nao em cada caminho de compra.** Estava duplicada, e a
    compra pela carteira usava "agora + 24h" a seco: um bilhete comprado na app
    para daqui a seis dias nascia com validade de um, e o passageiro era
    recusado no embarque com o bilhete pago.
    """
    now = timezone.now()
    departure = getattr(trip, "planned_departure_at", None) if trip else None
    if not departure:
        return now, now + timedelta(hours=24)
    return min(now, departure - timedelta(hours=3)), departure + timedelta(hours=12)


def _validity_window(gc: GuestCheckout) -> tuple:
    return validity_window(gc.trip if gc.trip_id else None)


def issue_guest_pass(guest_checkout: GuestCheckout) -> list[DigitalTravelPass]:
    passes = []
    with transaction.atomic():
        gc = GuestCheckout.objects.select_for_update().get(pk=guest_checkout.pk)
        if gc.status == GuestCheckout.Status.ISSUED:
            return list(gc.travel_passes.all())

        gc.status = GuestCheckout.Status.ISSUED
        gc.save(update_fields=["status", "updated_at"])

        valid_from, valid_until = _validity_window(gc)
        departure = getattr(gc.trip, "planned_departure_at", None) if gc.trip_id else None
        # Compra feita por um passageiro autenticado (app): o bilhete e nominal
        # e entra directamente na conta dele.
        linked = gc.linked_passenger
        # Moeda de exibicao escolhida na compra, congelada a taxa da altura.
        unit_display = None
        if gc.display_currency != "MZN" and gc.exchange_rate:
            unit_display = (gc.unit_amount / gc.exchange_rate).quantize(Decimal("0.01"))
        # Um passe por passageiro quando ha dados nominais; senao, por unidade.
        people = list(gc.passengers or [])
        for i in range(gc.quantity):
            person = people[i] if i < len(people) else {}
            raw_token, token_hash = DigitalTravelPass.generate_token()
            travel_pass = DigitalTravelPass.objects.create(
                guest_checkout=gc,
                passenger_account=linked,
                payer_phone=gc.payer_phone,
                route_code=gc.route_code,
                route_name=gc.route_name,
                origin_stop=gc.origin_stop,
                destination_stop=gc.destination_stop,
                origin_stop_ref=gc.origin_stop_ref,
                destination_stop_ref=gc.destination_stop_ref,
                trip=gc.trip,
                passenger_name=(person.get("name") or (linked.full_name if linked else "") or gc.buyer_name or "")[:255],
                document_type=person.get("document_type") or (linked.document_type if linked else "") or "",
                document_number=(person.get("document_number") or (linked.document_number if linked else "") or "")[:64],
                seat_number=(person.get("seat") or "")[:8],
                # Contacto de emergencia: por passageiro quando vem, senao o
                # da compra — numa familia que viaja junta, e o mesmo.
                emergency_contact_name=(
                    person.get("emergency_contact_name")
                    or gc.emergency_contact_name or ""
                )[:120],
                emergency_contact_phone=(
                    person.get("emergency_contact_phone")
                    or gc.emergency_contact_phone or ""
                )[:20],
                departure_at=departure,
                fare_amount=gc.unit_amount,
                display_currency=gc.display_currency or "MZN",
                display_fare_amount=unit_display,
                exchange_rate=gc.exchange_rate,
                token=raw_token,
                token_hash=token_hash,
                delivery_channel=(
                    DigitalTravelPass.DeliveryChannel.APP if linked
                    else DigitalTravelPass.DeliveryChannel.SMS
                ),
                valid_from=valid_from,
                valid_until=valid_until,
            )
            # Codigo curto do proprio bilhete (inclui a sequencia -01, -02...)
            travel_pass.short_code = ticket_short_code(
                ticket_reference(travel_pass, sequence=i + 1, total=gc.quantity))
            travel_pass.save(update_fields=["short_code", "updated_at"])
            travel_pass._raw_token = raw_token
            passes.append(travel_pass)

    # SMS só depois do commit. Esta função é chamada de dentro de transacções
    # que detêm locks de dinheiro (venda POS por cartão bloqueia a carteira);
    # com o gateway de SMS a 20s por mensagem, uma venda de 10 bilhetes retinha
    # o lock ~200s e punha validações e recargas do mesmo passageiro em fila.
    # on_commit também garante que ninguém recebe SMS de um bilhete cujo
    # rollback o fez desaparecer.
    for p in passes:
        transaction.on_commit(lambda pass_=p: _deliver_pass_sms(gc, pass_))

    return passes


def _deliver_pass_sms(gc: GuestCheckout, travel_pass: DigitalTravelPass):
    raw_token = getattr(travel_pass, "_raw_token", None)
    if not raw_token:
        return
    base = str(getattr(settings, "PUBLIC_BASE_URL", "") or "").rstrip("/")
    ticket_url = f"{base}/api/public/ticket/{raw_token}/" if base else f"/api/public/ticket/{raw_token}/"
    message = (
        f"BuzUp: Bilhete {gc.route_name or gc.route_code} "
        f"{gc.origin_stop} -> {gc.destination_stop}. "
        f"Ref: {gc.reference}. "
        f"Link: {ticket_url}"
    )
    # O numero de emergencia saiu do bilhete e passou para aqui: no bilhete
    # ocupava espaco a competir com os dados da viagem, e quem precisa dele
    # esta a meio da estrada com o telemovel na mao — nao a olhar para o PDF.
    # O SMS fica na caixa de mensagens e liga-se com um toque.
    emergencia = _linha_de_emergencia()
    if emergencia:
        message = f"{message} {emergencia}"
    send_sms(gc.payer_phone, message, purpose="GUEST_PASS_DELIVERY")


def _linha_de_emergencia() -> str:
    """Linha de emergencia da operadora para juntar ao SMS do bilhete."""
    try:
        from apps.branding.models import BrandingSettings

        linha = BrandingSettings.load()
        numero = (linha.emergency_phone or linha.support_phone or "").strip()
    except Exception:
        return ""
    return f"Emergencia: {numero}." if numero else ""
