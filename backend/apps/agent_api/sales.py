"""Agent POS sales service.

Reuses the guest_checkouts purchase pipeline to create a sale + payment intent
on behalf of the passenger. Tickets are issued only after the PaymentIntent
transitions to CONFIRMED (idempotent via process_payment_callback).
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from apps.audit.services import audit
from apps.devices.models import Device
from apps.fares.services import FareConflictError, NoFareFoundError, quote_fare
from apps.guest_checkouts.capacity import SeatsUnavailable, lock_trip_for_sale
from apps.guest_checkouts.models import GuestCheckout
from apps.notifications.services import notify_by_phone
from apps.packages.services import consume_package_trip, find_active_package_for_route
from apps.payments.models import CASH_PROVIDER, PaymentIntent
from apps.payments.services.gateway import get_payment_gateway
from apps.payments.services.processing import confirm_payment_immediately
from apps.routes.models import Route, Stop
from apps.routes.services import RouteSegmentError, resolve_route_segment
from apps.trips.models import Trip
from apps.users.otp import normalize_otp_phone


class SaleError(Exception):
    pass


def _seat_payload(seats: list[str] | None, quantity: int,
                  passengers: list[dict] | None = None) -> list[dict]:
    """Um registo por bilhete: lugar e identificacao de quem viaja.

    `issue_guest_pass` le daqui `seat`, `name`, `document_type` e
    `document_number`. Antes so se enchia o lugar, e por isso os bilhetes
    vendidos ao balcao saiam sem nome nem documento — inclusive nas rotas
    internacionais, onde e o documento que a fronteira confere.
    """
    chosen = [s for s in (seats or []) if s]
    gente = passengers or []
    if not chosen and not gente:
        return []
    saida = []
    for i in range(quantity):
        pessoa = gente[i] if i < len(gente) else {}
        saida.append({
            "seat": chosen[i] if i < len(chosen) else "",
            "name": (pessoa.get("name") or "").strip()[:255],
            "document_type": (pessoa.get("document_type") or "").strip(),
            "document_number": (pessoa.get("document_number") or "").strip()[:64],
        })
    return saida


# Primeira versao do POS que recolhe nome e documento do passageiro.
#
# A exigencia so vale para terminais que a conseguem cumprir. Os que ainda
# correm uma versao anterior nao tem os campos no ecra: exigi-lo deles nao
# tornava um bilhete nominal — parava a venda, com o passageiro a frente do
# agente e nada que ele pudesse fazer. Havia 7 terminais em servico quando
# isto foi escrito.
#
# Nao e um controlo de seguranca; e a pergunta "este cliente consegue
# responder?". Cada terminal passa a exigir a identificacao no dia em que
# actualiza, e quando o ultimo actualizar este ramo deixa de ser usado.
POS_MIN_VERSION_IDENTIDADE = (1, 8, 0)


def _versao(texto: str) -> tuple:
    """"1.8.0" -> (1, 8, 0). Lixo -> (0, 0, 0), que nunca exige nada."""
    partes = []
    for pedaco in str(texto or "").split(".")[:3]:
        digitos = "".join(c for c in pedaco if c.isdigit())
        partes.append(int(digitos) if digitos else 0)
    while len(partes) < 3:
        partes.append(0)
    return tuple(partes)


def _terminal_recolhe_identidade(device: Device | None) -> bool:
    """O terminal ja tem os campos de nome e documento no ecra?

    Sem terminal identificado (venda pelo portal do agente, testes) assume-se
    que sim: nao ha app velha do outro lado.
    """
    if device is None:
        return True
    return _versao(device.app_version) >= POS_MIN_VERSION_IDENTIDADE


def _identidades_para(route, passengers: list[dict] | None, quantity: int,
                      device: Device | None = None) -> list[dict]:
    """Valida o nome e o documento de cada passageiro contra a regra da rota.

    Nas rotas com manifesto de bordo o bilhete e nominal: sem nome nao ha
    manifesto, e numa internacional sem documento o passageiro nao passa a
    fronteira com o bilhete que acabou de comprar. O agente tem a pessoa a
    frente — e o unico momento em que da para perguntar.

    Numa carreira urbana nao se pede nada: guardar o documento de quem apanha
    o autocarro do bairro seria recolher dados pessoais sem necessidade.

    O que vier de um terminal antigo e gravado na mesma se vier — so nao e
    exigido. Ver `POS_MIN_VERSION_IDENTIDADE`.
    """
    from apps.guest_checkouts.documents import DocumentError, validate_document_for

    gente = list(passengers or [])
    if not getattr(route, "requires_manifest", False):
        return gente
    if not gente and not _terminal_recolhe_identidade(device):
        return gente

    servico = getattr(route, "service_type", "")
    limpos = []
    for i in range(quantity):
        pessoa = dict(gente[i]) if i < len(gente) else {}
        nome = (pessoa.get("name") or "").strip()
        if not nome:
            raise SaleError(
                f"Indique o nome do passageiro {i + 1}. Nesta rota o bilhete e "
                f"nominal e entra no manifesto de bordo."
            )
        tipo = (pessoa.get("document_type") or "").strip()
        numero = (pessoa.get("document_number") or "").strip()
        if not tipo or not numero:
            raise SaleError(
                f"Indique o documento do passageiro {i + 1} ({nome})."
            )
        try:
            numero = validate_document_for(servico, tipo, numero)
        except DocumentError as e:
            raise SaleError(f"Passageiro {i + 1} ({nome}): {e}") from e
        pessoa.update({"name": nome, "document_type": tipo, "document_number": numero})
        limpos.append(pessoa)
    return limpos


def abrir_embarque_se_preciso(trip, agent, user=None) -> None:
    """A primeira venda ABRE o embarque, se ainda estiver por abrir.

    O motorista tinha de carregar em "abrir embarque" antes de poder vender.
    Era um toque a mais para uma coisa que a propria venda ja prova: se ha
    passageiros a comprar, o autocarro esta a receber gente.

    E o registo fica MAIS fiel, nao menos. O `activity_started_at` passa a
    marcar o instante em que o embarque comecou de facto — a primeira venda —
    em vez de depender de alguem se lembrar de carregar num botao, o que numa
    fila cheia acontece tarde ou nao acontece.

    O que NAO muda: `actual_departure_at` continua a ser marcado so por
    "iniciar viagem". Juntar as duas coisas foi um defeito ja corrigido, e a
    hora de saida e o unico registo que diz se o autocarro se atrasou.

    Falhar aqui nao pode travar a venda: o dinheiro do passageiro nao depende
    de um estado de viagem. Se nao conseguir abrir, a venda segue e o embarque
    fica como estava.

    **So a partida de HOJE.** Desde que o balcao voltou a vender antecipado
    (`AgentTripListView`), a primeira venda para amanha punha a viagem de
    amanha em embarque hoje, e carimbava-lhe um `activity_started_at` de hoje.
    Duas coisas partiam-se de uma vez: perdia-se o registo de quando o embarque
    comecou de facto — que e a razao de ser desta funcao — e a viagem passava a
    contar como "a circular", ficando na lista do balcao ate ao dia seguinte.

    Uma partida sem data planeada continua a abrir: nao ha por onde julga-la, e
    e o caso da carreira urbana que se vende com o autocarro ali a frente.
    """
    if trip is None or trip.status != Trip.Status.SCHEDULED:
        return
    if trip.planned_departure_at is not None:
        from django.utils import timezone as _tz

        tz = _tz.get_current_timezone()
        if trip.planned_departure_at.astimezone(tz).date() > _tz.now().astimezone(tz).date():
            return
    try:
        from apps.trips.activity import start_trip_activity

        if trip.driver_id:
            start_trip_activity(trip, trip.driver, user or getattr(agent, "user", None))
        else:
            # Venda ao balcao numa partida sem motorista atribuido: nao ha
            # ciclo de motorista para abrir, mas a viagem tem de ficar
            # vendavel. Muda-se so o estado.
            from django.utils import timezone as _tz

            Trip.objects.filter(pk=trip.pk, status=Trip.Status.SCHEDULED).update(
                status=Trip.Status.BOARDING,
                activity_started_at=trip.activity_started_at or _tz.now(),
            )
        trip.refresh_from_db()
    except Exception:
        # Telemetria de estado nao pode custar uma venda.
        pass


def _assert_seats_free(trip, seats: list[str] | None) -> None:
    """Confirma que os lugares continuam livres. Chamar SOB o lock da viagem.

    Sem isto, dois agentes a vender ao mesmo tempo na mesma partida podiam
    atribuir o mesmo lugar a duas pessoas — e so se descobria a bordo.
    """
    chosen = {s for s in (seats or []) if s}
    if not chosen or trip is None:
        return
    from apps.guest_checkouts.seatmap import occupied_seats

    clash = sorted(chosen & occupied_seats(trip))
    if clash:
        raise SaleError(f"Lugar(es) ja ocupado(s): {', '.join(clash)}. Escolha outro.")


def _emergency_for(route, name: str, phone: str) -> tuple[str, str]:
    """Contacto de emergencia, validado contra a regra da rota.

    Obrigatorio onde ha manifesto de bordo (interprovincial/internacional):
    o agente ao balcao e quem tem o passageiro a frente, e e o unico momento
    em que da para perguntar. Numa carreira urbana nao se guarda.
    """
    name = (name or "").strip()
    phone = (phone or "").strip()
    if getattr(route, "requires_emergency_contact", False):
        if not phone:
            raise SaleError("Indique o contacto de emergencia do passageiro.")
        return name[:120], phone[:20]
    return "", ""


def create_pos_sale(
    *,
    agent,
    device: Device | None,
    trip_id: int | None,
    route_id: int | None,
    origin_stop_id: int,
    destination_stop_id: int,
    passenger_phone: str,
    quantity: int = 1,
    idempotency_key: str = "",
    display_currency: str = "MZN",
    seats: list[str] | None = None,
    emergency_contact_name: str = "",
    emergency_contact_phone: str = "",
    passengers: list[dict] | None = None,
    payment_method: str = "mobile_money",
) -> tuple[GuestCheckout, PaymentIntent]:
    """Create a sale + initiate payment for an agent's POS terminal.

    Backend computes the fare. Returns (GuestCheckout, PaymentIntent).

    `payment_method="cash"` e a mesma venda sem gateway: o passageiro paga em
    dinheiro ao agente e o pagamento nasce ja liquidado — nao ha carteira a
    debitar nem PIN a esperar. Tudo o resto (tarifa, lotacao, lugar,
    identificacao, bilhete por SMS) e igual, e por isso vive aqui em vez de
    numa segunda funcao que ia divergir desta a primeira alteracao.

    O telefone continua a ser pedido, mas ja nao e uma carteira: e para onde
    o bilhete vai por SMS.
    """
    if device and device.status == Device.Status.BLOCKED:
        raise SaleError("Dispositivo bloqueado. Contacte o administrador.")

    phone = normalize_otp_phone(passenger_phone)
    if not phone:
        raise SaleError("Telefone do passageiro invalido.")

    if quantity < 1 or quantity > 10:
        raise SaleError("Quantidade deve estar entre 1 e 10.")

    trip = None
    if trip_id:
        trip = Trip.objects.select_related("route").filter(pk=trip_id).first()
        if not trip or trip.status not in Trip.sellable_statuses_for(trip.route):
            raise SaleError("Viagem nao encontrada ou ja encerrada.")
        route = trip.route
    elif route_id:
        route = Route.objects.filter(pk=route_id, status=Route.Status.ACTIVE).first()
        if not route:
            raise SaleError("Rota nao encontrada.")
    else:
        raise SaleError("Forneca trip_id ou route_id.")

    origin = Stop.objects.filter(pk=origin_stop_id).first()
    destination = Stop.objects.filter(pk=destination_stop_id).first()
    if not origin or not destination:
        raise SaleError("Origem ou destino nao encontrados.")
    if origin.pk == destination.pk:
        raise SaleError("Origem e destino devem ser diferentes.")

    try:
        resolve_route_segment(route, origin.pk, destination.pk)
    except RouteSegmentError as e:
        raise SaleError(str(e))

    try:
        quote = quote_fare(route=route, origin_stop=origin, destination_stop=destination)
    except NoFareFoundError as e:
        audit(
            "FARE_RESOLUTION_FAILED",
            actor=getattr(agent, "user", None),
            entity_type="route", entity_id=str(route.id),
            after={"reason": str(e), "origin": origin.pk, "destination": destination.pk},
        )
        raise SaleError(str(e))
    except FareConflictError as e:
        audit(
            "FARE_RESOLUTION_FAILED",
            actor=getattr(agent, "user", None),
            entity_type="route", entity_id=str(route.id),
            after={"reason": "conflict", "detail": str(e)},
        )
        raise SaleError("Conflito de tarifas. Contacte o administrador.")

    total = quote.amount * quantity
    ref = f"AS-{uuid4().hex[:18].upper()}"

    from apps.fares.services import display_snapshot
    disp_ccy, disp_total, disp_rate = display_snapshot(total, display_currency)

    # Mesma regra da compra na app: se o telefone do passageiro tiver conta
    # activa, o bilhete entra-lhe na conta (alem do SMS que recebe sempre).
    # Ha contas gravadas com e sem o indicativo 258 — aceita as duas formas.
    from apps.passengers.models import PassengerAccount
    phone_forms = {phone}
    if phone.startswith("258") and len(phone) == 12:
        phone_forms.add(phone[3:])
    linked = PassengerAccount.objects.filter(
        phone_number__in=phone_forms, status=PassengerAccount.Status.ACTIVE,
    ).first()

    emerg_name, emerg_phone = _emergency_for(
        route, emergency_contact_name, emergency_contact_phone)
    # Validar ANTES do lock: recusar depois de reservar lugar deixava a
    # lotacao presa por uma venda que nunca ia acontecer.
    identidades = _identidades_para(route, passengers, quantity, device)

    # A primeira venda abre o embarque. Antes do lock, para o estado ja estar
    # certo quando a lotacao for contada.
    abrir_embarque_se_preciso(trip, agent)

    with transaction.atomic():
        # Lotacao: sem este lock, um agente e um comprador web vendiam o mesmo
        # ultimo lugar ao mesmo tempo (a compra web ja bloqueava, o POS nao).
        if trip is not None:
            try:
                trip = lock_trip_for_sale(trip, quantity)
            except SeatsUnavailable as e:
                raise SaleError(str(e)) from e
            _assert_seats_free(trip, seats)

        gc = GuestCheckout.objects.create(
            reference=ref,
            payer_phone=phone,
            buyer_name="",
            passengers=_seat_payload(seats, quantity, identidades),
            route_code=route.code,
            route_name=route.name,
            origin_stop=origin.name,
            destination_stop=destination.name,
            origin_stop_ref=origin,
            destination_stop_ref=destination,
            trip=trip,
            quantity=quantity,
            unit_amount=quote.amount,
            total_amount=total,
            display_currency=disp_ccy,
            display_total_amount=disp_total,
            exchange_rate=disp_rate,
            status=GuestCheckout.Status.PAYMENT_PENDING,
            expires_at=timezone.now() + timedelta(minutes=15),
            linked_passenger=linked,
            emergency_contact_name=emerg_name,
            emergency_contact_phone=emerg_phone,
        )

        a_dinheiro = payment_method == "cash"
        pi = PaymentIntent.objects.create(
            reference=f"PAY-{ref}",
            idempotency_key=idempotency_key or f"agent-sale-{ref}",
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
            amount=total,
            payer_phone=phone,
            guest_checkout=gc,
            status=PaymentIntent.Status.PENDING,
            # `provider` marca de onde veio o dinheiro, e no numerario isso
            # nao e um detalhe tecnico: e o unico sitio onde fica escrito que
            # ha notas na mao do agente para entregar no fecho de caixa. Sem
            # esta marca, a venda a dinheiro somava-se as de M-Pesa e ninguem
            # conseguia dizer quanto cobrar a quem.
            provider=CASH_PROVIDER if a_dinheiro else "",
            channel="POS_CASH" if a_dinheiro else "",
            expires_at=gc.expires_at,
            metadata={
                "agent_id": getattr(agent, "id", None),
                "agent_user_id": getattr(agent, "user_id", None),
                "device_id": device.id if device else None,
                "device_serial": device.serial_number if device else "",
                "payment_method": payment_method,
            },
            created_by=getattr(agent, "user", None),
        )

        if a_dinheiro:
            # Dentro da mesma transaccao que reservou o lugar: se a emissao
            # falhar, o lugar volta a ficar livre em vez de ficar preso por
            # uma venda que nunca chegou a existir.
            confirm_payment_immediately(pi, provider_reference=f"CASH-{ref}")

    if payment_method == "cash":
        # A liquidacao aconteceu dentro da transaccao acima e mudou a linha na
        # base de dados, nao este objecto. Sem isto quem chama recebia um
        # pagamento "pendente" que ja estava pago.
        pi.refresh_from_db()
        gc.refresh_from_db()

    audit(
        "SALE_CREATED",
        actor=getattr(agent, "user", None),
        entity_type="guest_checkout",
        entity_id=str(gc.id),
        after={
            "reference": gc.reference,
            "amount": str(total),
            "quantity": quantity,
            "trip_id": trip.id if trip else None,
            "device_serial": device.serial_number if device else "",
            "method": payment_method,
        },
    )

    return gc, pi


def create_card_sale(
    *,
    agent,
    device: Device | None,
    trip_id: int | None,
    route_id: int | None,
    origin_stop_id: int,
    destination_stop_id: int,
    card_uid: str = "",
    qr_token: str = "",
    quantity: int = 1,
    idempotency_key: str = "",
    display_currency: str = "MZN",
    seats: list[str] | None = None,
    emergency_contact_name: str = "",
    emergency_contact_phone: str = "",
    passengers: list[dict] | None = None,
) -> tuple[GuestCheckout, PaymentIntent, list]:
    """Card-based POS sale: lookup card -> debit wallet -> confirm + issue.

    Returns (GuestCheckout, PaymentIntent, list[DigitalTravelPass]).
    Raises SaleError on validation / insufficient balance / blocked card.
    """
    import hashlib
    from apps.cards.models import Card
    from apps.wallets.models import Wallet, WalletTransaction
    from apps.wallets.services import debit_wallet, InsufficientBalanceError, WalletBlockedError

    if device and device.status == Device.Status.BLOCKED:
        raise SaleError("Dispositivo bloqueado. Contacte o administrador.")
    if quantity < 1 or quantity > 10:
        raise SaleError("Quantidade deve estar entre 1 e 10.")

    # Resolve card by UID or QR token
    card = None
    if card_uid:
        card = (
            Card.objects.select_related("passenger_account")
            .filter(card_uid=card_uid.strip().upper())
            .first()
        )
    elif qr_token:
        token_hash = hashlib.sha256(qr_token.strip().encode()).hexdigest()
        card = (
            Card.objects.select_related("passenger_account")
            .filter(qr_token_hash=token_hash)
            .first()
        )
    if not card:
        raise SaleError("Cartao nao encontrado.")
    if card.status != Card.Status.ACTIVE:
        raise SaleError(f"Cartao {card.card_number} esta {card.status}.")
    if not card.passenger_account_id:
        raise SaleError("Cartao nao esta vinculado a um passageiro.")

    pa = card.passenger_account
    try:
        wallet = pa.wallet
    except Exception:
        wallet = None
    if wallet is None:
        raise SaleError("Passageiro sem carteira activa.")
    if wallet.status != Wallet.Status.ACTIVE:
        raise SaleError("Carteira bloqueada.")

    # Resolve trip / route + fare
    trip = None
    if trip_id:
        trip = Trip.objects.select_related("route").filter(pk=trip_id).first()
        if not trip or trip.status not in Trip.sellable_statuses_for(trip.route):
            raise SaleError("Viagem nao encontrada ou ja encerrada.")
        route = trip.route
    elif route_id:
        route = Route.objects.filter(pk=route_id, status=Route.Status.ACTIVE).first()
        if not route:
            raise SaleError("Rota nao encontrada.")
    else:
        raise SaleError("Forneca trip_id ou route_id.")

    origin = Stop.objects.filter(pk=origin_stop_id).first()
    destination = Stop.objects.filter(pk=destination_stop_id).first()
    if not origin or not destination:
        raise SaleError("Origem ou destino nao encontrados.")
    if origin.pk == destination.pk:
        raise SaleError("Origem e destino devem ser diferentes.")

    try:
        resolve_route_segment(route, origin.pk, destination.pk)
    except RouteSegmentError as e:
        raise SaleError(str(e))

    try:
        quote = quote_fare(route=route, origin_stop=origin, destination_stop=destination)
    except NoFareFoundError as e:
        raise SaleError(str(e))
    except FareConflictError:
        raise SaleError("Conflito de tarifas. Contacte o administrador.")

    base_unit = quote.amount
    gross_total = base_unit * quantity  # fare value (shown on the ticket)
    ref = f"AS-{uuid4().hex[:18].upper()}"
    phone = pa.phone_number or ""

    # Single atomic block:
    #   1. Re-read the wallet WITH a row lock (`select_for_update`) so two
    #      concurrent card sales for the same passenger can't both pass the
    #      balance check and overdraw.
    #   2. Create GuestCheckout + PaymentIntent.
    #   3. Debit the wallet (idempotent via the FARE-{ref} reference).
    #   4. Confirm the PaymentIntent (issues tickets via shared processor).
    # If ANY step raises, the whole transaction rolls back and the wallet
    # stays untouched, so no scenario leaves money debited without a ticket.
    from apps.wallets.models import Wallet  # local import to avoid cycle

    with transaction.atomic():
        # Ordem dos locks fixa em todo o sistema — Trip antes de Wallet — para
        # que dois caminhos concorrentes nunca se cruzem em deadlock.
        if trip is not None:
            try:
                trip = lock_trip_for_sale(trip, quantity)
            except SeatsUnavailable as e:
                raise SaleError(str(e)) from e
            _assert_seats_free(trip, seats)

        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        if wallet.status != Wallet.Status.ACTIVE:
            raise SaleError("Carteira bloqueada.")

        # Apply the passenger's active package (same rule as the mobile app):
        # consume one trip per unit and only charge the wallet the discounted
        # remainder. Without this the POS overcharged cardholders with a
        # package the full base fare. Consumption happens inside this atomic,
        # so an insufficient-balance abort below rolls it back.
        subscription = find_active_package_for_route(pa, route)
        package_meta: dict = {}
        if subscription:
            charged_total = Decimal("0.00")
            for _ in range(quantity):
                charged_total += consume_package_trip(subscription, base_unit)
            package_meta = {
                "package_id": subscription.package_id,
                "package_name": subscription.package.name,
                "discount_type": subscription.package.discount_type,
                "base_total": str(gross_total),
                "charged_total": str(charged_total),
            }
        else:
            charged_total = gross_total

        if wallet.balance_cached < charged_total:
            raise SaleError(
                f"Saldo insuficiente. Saldo: {wallet.balance_cached} MZN. Necessario: {charged_total} MZN."
            )

        # Issued passes read `unit_amount` as their fare — record the net paid
        # (after package discount) so the ticket shows what was charged, not
        # the gross fare.
        net_unit = (charged_total / quantity).quantize(Decimal("0.01")) if quantity else charged_total
        _card_emerg = _emergency_for(route, emergency_contact_name, emergency_contact_phone)
        identidades = _identidades_para(route, passengers, quantity, device)
        from apps.fares.services import display_snapshot
        disp_ccy, disp_total, disp_rate = display_snapshot(charged_total, display_currency)
        gc = GuestCheckout.objects.create(
            reference=ref,
            payer_phone=phone,
            buyer_name=pa.full_name or "",
            passengers=_seat_payload(seats, quantity, identidades),
            route_code=route.code,
            route_name=route.name,
            origin_stop=origin.name,
            destination_stop=destination.name,
            origin_stop_ref=origin,
            destination_stop_ref=destination,
            trip=trip,
            quantity=quantity,
            unit_amount=net_unit,
            total_amount=charged_total,
            display_currency=disp_ccy,
            display_total_amount=disp_total,
            exchange_rate=disp_rate,
            status=GuestCheckout.Status.PAYMENT_PENDING,
            expires_at=timezone.now() + timedelta(minutes=15),
            # O cartao pertence a uma conta conhecida: sem isto o bilhete
            # nascia orfao e nunca aparecia na app do titular.
            linked_passenger=pa,
            emergency_contact_name=_card_emerg[0],
            emergency_contact_phone=_card_emerg[1],
        )
        pi = PaymentIntent.objects.create(
            reference=f"PAY-{ref}",
            idempotency_key=idempotency_key or f"card-sale-{ref}",
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
            amount=charged_total,
            payer_phone=phone,
            guest_checkout=gc,
            wallet=wallet,
            status=PaymentIntent.Status.PENDING,
            provider="wallet",
            channel="POS_CARD",
            expires_at=gc.expires_at,
            metadata={
                "agent_id": getattr(agent, "id", None),
                "agent_user_id": getattr(agent, "user_id", None),
                "device_id": device.id if device else None,
                "device_serial": device.serial_number if device else "",
                "payment_method": "card",
                "card_uid": card.card_uid,
                "card_id": card.id,
                "passenger_account_id": pa.id,
                **package_meta,
            },
            created_by=getattr(agent, "user", None),
        )

        if charged_total > Decimal("0.00"):
            try:
                debit_wallet(
                    wallet=wallet,
                    amount=charged_total,
                    tx_type=WalletTransaction.Type.FARE_DEBIT,
                    source=f"agent:{getattr(agent, 'user_id', '')}",
                    reference=f"FARE-{ref}",
                    metadata={
                        "agent_user_id": getattr(agent, "user_id", None),
                        "card_uid": card.card_uid,
                        "card_id": card.id,
                        "guest_checkout": gc.reference,
                        "channel": "POS_CARD",
                        **package_meta,
                    },
                    notify=False,
                )
            except InsufficientBalanceError as e:
                raise SaleError(str(e))
            except WalletBlockedError as e:
                raise SaleError(str(e))

        # Confirm + issue tickets inside the same atomic. If issuance fails
        # the wallet debit is rolled back automatically by Django.
        confirm_payment_immediately(pi, provider_reference=f"WALLET-{ref}")

    audit(
        "SALE_CREATED",
        actor=getattr(agent, "user", None),
        entity_type="guest_checkout",
        entity_id=str(gc.id),
        after={
            "reference": gc.reference,
            "amount": str(charged_total),
            "base_amount": str(gross_total),
            "quantity": quantity,
            "trip_id": trip.id if trip else None,
            "device_serial": device.serial_number if device else "",
            "method": "card",
            "card_uid": card.card_uid,
        },
    )

    pi.refresh_from_db()
    gc.refresh_from_db()
    passes = list(gc.travel_passes.all())
    return gc, pi, passes


def request_payment(gc: GuestCheckout, pi: PaymentIntent) -> dict:
    """Trigger the configured payment gateway to ask passenger to confirm.

    Returns dict with payment status info. Idempotent: if PI already CONFIRMED,
    just returns the current status.
    """
    pi.refresh_from_db()
    if pi.status == PaymentIntent.Status.CONFIRMED:
        return {"status": pi.status, "provider": pi.provider, "reference": pi.reference, "detail": "Pagamento ja confirmado."}

    gateway = get_payment_gateway(payer_phone=pi.payer_phone)
    result = gateway.initiate_payment(
        reference=pi.reference,
        amount=pi.amount,
        payer_phone=pi.payer_phone,
        description=f"BuzUp bilhete {gc.route_code}",
    )

    pi.provider = result.provider
    pi.metadata = {
        **(pi.metadata or {}),
        "gateway_request": result.request_payload or {},
        "gateway_response": result.response_payload or {},
    }

    audit(
        "PAYMENT_REQUESTED",
        actor=pi.created_by,
        entity_type="payment_intent", entity_id=str(pi.id),
        after={"provider": result.provider, "amount": str(pi.amount), "success": result.success},
    )

    if result.success:
        pi.provider_reference = result.provider_reference
        pi.save(update_fields=["provider", "provider_reference", "metadata", "updated_at"])
        confirm_payment_immediately(pi, result.provider_reference)
        pi.refresh_from_db()
        notify_by_phone(
            pi.payer_phone,
            "payment_confirmed",
            "Pagamento confirmado",
            f"O seu pagamento de {pi.amount} MZN foi confirmado.",
            data={"payment_reference": pi.reference, "guest_checkout_reference": gc.reference},
        )
        return {"status": pi.status, "provider": pi.provider, "reference": pi.reference, "detail": result.detail_message}

    if result.pending:
        pi.provider_reference = result.provider_reference
        pi.status = PaymentIntent.Status.PENDING
        pi.save(update_fields=["status", "provider", "provider_reference", "metadata", "updated_at"])
        return {"status": pi.status, "provider": pi.provider, "reference": pi.reference, "detail": result.detail_message}

    gc.status = GuestCheckout.Status.CANCELLED
    gc.save(update_fields=["status", "updated_at"])
    pi.status = PaymentIntent.Status.FAILED
    pi.save(update_fields=["status", "provider", "metadata", "updated_at"])
    audit(
        "PAYMENT_FAILED",
        actor=pi.created_by,
        entity_type="payment_intent", entity_id=str(pi.id),
        after={"reason": result.error or result.detail_message},
    )
    notify_by_phone(
        pi.payer_phone,
        "payment_failed",
        "Pagamento nao concluido",
        result.detail_message or "Tente novamente.",
        data={"payment_reference": pi.reference},
    )
    return {"status": pi.status, "provider": pi.provider, "reference": pi.reference, "detail": result.detail_message, "error": result.error}
