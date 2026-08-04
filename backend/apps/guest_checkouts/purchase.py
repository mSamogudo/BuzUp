from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from uuid import uuid4

from django.utils import timezone

from apps.fares.services import NoFareFoundError, quote_fare
from apps.guest_checkouts.capacity import SeatsUnavailable, lock_trip_for_sale
from apps.guest_checkouts.documents import DocumentError, validate_document
from apps.guest_checkouts.ticket_codes import ticket_reference, ticket_short_code
from apps.guest_checkouts.models import DigitalTravelPass
from apps.packages.models import PackageRoute, PassengerPackage
from apps.packages.services import (
    calculate_discounted_fare,
    consume_package_trip,
    find_active_package_for_route,
)
from apps.passengers.models import PassengerAccount
from apps.routes.models import Route, Stop
from apps.routes.services import RouteSegmentError, resolve_route_segment
from apps.trips.models import Trip
from apps.wallets.models import WalletTransaction
from apps.wallets.services import InsufficientBalanceError, WalletBlockedError, debit_wallet


class PurchaseError(Exception):
    pass


def _resolve_passenger_package(
    passenger: PassengerAccount,
    route: Route,
    passenger_package_id: int | None,
    use_package: bool,
) -> PassengerPackage | None:
    if not use_package and passenger_package_id is None:
        return None

    # Pacotes so valem em carreiras urbanas/interurbanas. A verificacao esta
    # tambem aqui, e nao so em find_active_package_for_route, porque indicar o
    # pacote pelo id passa ao lado dessa funcao — era por ai que um pacote
    # urbano podia pagar uma viagem interprovincial.
    if not route.allows_package_discounts:
        if passenger_package_id is not None:
            raise PurchaseError(
                "Os pacotes especiais so sao validos em viagens urbanas e interurbanas."
            )
        return None

    if passenger_package_id is not None:
        try:
            sub = PassengerPackage.objects.select_related("package").get(
                pk=passenger_package_id,
                passenger_account=passenger,
            )
        except PassengerPackage.DoesNotExist:
            raise PurchaseError("Pacote nao encontrado para este passageiro.")
        if sub.status != PassengerPackage.Status.ACTIVE:
            raise PurchaseError("Pacote nao esta activo.")
        if sub.expires_at and sub.expires_at <= timezone.now():
            raise PurchaseError("Pacote expirado.")

        pkg_routes = PackageRoute.objects.filter(package=sub.package)
        if pkg_routes.exists() and not pkg_routes.filter(route=route).exists():
            raise PurchaseError("Este pacote nao cobre a rota seleccionada.")

        return sub

    return find_active_package_for_route(passenger, route)


def purchase_travel_pass(
    passenger: PassengerAccount,
    route_id: int,
    origin_stop_id: int | None = None,
    destination_stop_id: int | None = None,
    trip_id: int | None = None,
    seat: str = "",
    passenger_package_id: int | None = None,
    use_package: bool = True,
    display_currency: str = "MZN",
    emergency_contact_name: str = "",
    emergency_contact_phone: str = "",
    document_type: str = "",
    document_number: str = "",
) -> DigitalTravelPass:
    if passenger.status != PassengerAccount.Status.ACTIVE:
        raise PurchaseError("Conta bloqueada ou inactiva.")

    wallet = getattr(passenger, "wallet", None)
    if not wallet:
        raise PurchaseError("Passageiro sem carteira.")

    try:
        route = Route.objects.get(pk=route_id)
    except Route.DoesNotExist:
        raise PurchaseError("Rota nao encontrada.")

    origin = Stop.objects.filter(pk=origin_stop_id).first() if origin_stop_id else None
    destination = Stop.objects.filter(pk=destination_stop_id).first() if destination_stop_id else None
    # Nas carreiras com lugar marcado o bilhete vende-se com antecedencia, por
    # isso uma partida ainda agendada tambem serve. Nas urbanas continua a ser
    # so o autocarro que esta ali a embarcar.
    sellable = [Trip.Status.BOARDING, Trip.Status.DEPARTED]
    if route.requires_seat_selection:
        sellable = [Trip.Status.SCHEDULED, *sellable]
    trip = Trip.objects.filter(
        pk=trip_id, route=route, status__in=sellable,
    ).first() if trip_id else None
    if trip_id and not trip:
        raise PurchaseError("Autocarro nao esta disponivel para compra.")

    # Sem esta guarda, a app vendia um bilhete interprovincial sem partida e
    # sem lugar: ninguem descontava a lotacao e o autocarro podia sair com mais
    # gente do que bancos. So se descobria a bordo.
    seat = (seat or "").strip().upper()
    if route.requires_seat_selection:
        if trip is None:
            raise PurchaseError("Escolha a partida para esta viagem.")
        if not seat:
            raise PurchaseError("Escolha o lugar para esta viagem.")
    elif seat:
        # Carreira urbana nao marca lugar; guardar um numero de banco daria ao
        # passageiro a ideia de que tem lugar reservado.
        seat = ""

    # Contacto de emergencia: obrigatorio onde ha manifesto de bordo. Numa
    # viagem de horas, longe de casa, e o unico modo de avisar a familia — e
    # nao serve de nada pedi-lo depois do acidente.
    emergency_contact_name = (emergency_contact_name or "").strip()
    emergency_contact_phone = (emergency_contact_phone or "").strip()
    # Documento de identificacao: obrigatorio nas mesmas rotas, porque o
    # bilhete e nominal e pode ser conferido na fronteira. O que a app enviar
    # manda; sem isso vale o que a conta tiver guardado. Ate aqui so se lia da
    # conta — e como quase nenhuma tem documento registado, os bilhetes
    # interprovinciais sairam todos com o campo vazio.
    doc_type = (document_type or getattr(passenger, "document_type", "") or "").strip()
    doc_number = (document_number or getattr(passenger, "document_number", "") or "").strip()
    if route.requires_seat_selection:
        try:
            doc_number = validate_document(doc_type or "other", doc_number)
        except DocumentError as e:
            raise PurchaseError(str(e))
    else:
        # Carreira urbana nao pede documento: nao guardar dados pessoais que
        # nao foram pedidos nem vao ser usados.
        doc_type, doc_number = "", ""

    if route.requires_emergency_contact:
        if not emergency_contact_phone:
            raise PurchaseError("Indique o contacto de emergencia para esta viagem.")
    else:
        # Carreira urbana nao pede: nao guardar dados de terceiros que nao
        # foram pedidos nem vao ser usados.
        emergency_contact_name = ""
        emergency_contact_phone = ""

    try:
        resolve_route_segment(route, origin_stop_id, destination_stop_id)
    except RouteSegmentError as e:
        raise PurchaseError(str(e))

    try:
        quote = quote_fare(route=route, origin_stop=origin, destination_stop=destination)
    except NoFareFoundError as e:
        raise PurchaseError(str(e))

    base_fare = quote.amount
    subscription = _resolve_passenger_package(passenger, route, passenger_package_id, use_package)

    raw_token, token_hash = DigitalTravelPass.generate_token()
    package_used = None
    package_meta: dict = {}

    with transaction.atomic():
        # Lotacao: a compra na app tambem ocupa lugar. Sem este lock, o mesmo
        # ultimo lugar podia ser vendido pela app, pelo site e pelo POS ao
        # mesmo tempo. Trip antes de Wallet, como nos restantes caminhos.
        if trip is not None:
            try:
                trip = lock_trip_for_sale(trip, 1)
            except SeatsUnavailable as e:
                raise PurchaseError(str(e)) from e

            # Sob o lock: entre ver a planta e pagar, o lugar pode ter sido
            # vendido no balcao ou no site. Verificar antes do lock deixava as
            # duas compras passar e duas pessoas com o mesmo banco.
            if seat:
                from apps.guest_checkouts.seatmap import occupied_seats

                if seat in occupied_seats(trip):
                    raise PurchaseError(f"O lugar {seat} ja foi ocupado. Escolha outro.")

        wallet_amount = base_fare
        if subscription:
            wallet_amount = consume_package_trip(subscription, base_fare)
            package_used = subscription
            package_meta = {
                "package_id": subscription.package_id,
                "package_name": subscription.package.name,
                "discount_type": subscription.package.discount_type,
                "base_fare": str(base_fare),
                "wallet_amount": str(wallet_amount),
            }

        # Create a CONFIRMED PaymentIntent so the operation shows up in the
        # admin payments page (filterable by source=MOBILE). For partial
        # coverage we record the wallet_amount; for full package coverage we
        # still record the base_fare as `amount` with metadata describing the
        # discount, so financial reports see the gross value.
        from apps.payments.models import PaymentIntent
        from uuid import uuid4 as _uuid4
        recorded_amount = wallet_amount if wallet_amount > Decimal("0.00") else base_fare
        idem = f"app-tp-{_uuid4().hex[:32]}"
        payment_intent = PaymentIntent.objects.create(
            reference=idem,
            idempotency_key=idem,
            purpose=PaymentIntent.Purpose.APP_TRAVEL_PASS,
            amount=recorded_amount,
            currency=wallet.currency or "MZN",
            payer_phone=passenger.phone_number,
            provider="wallet",
            channel="wallet",
            status=PaymentIntent.Status.CONFIRMED,
            wallet=wallet,
            confirmed_at=timezone.now(),
            metadata={
                "route": route.code,
                "base_fare": str(base_fare),
                "wallet_amount": str(wallet_amount),
                "fully_covered_by_package": wallet_amount <= Decimal("0.00") and subscription is not None,
                **package_meta,
            },
        )

        if wallet_amount > Decimal("0.00"):
            debit_wallet(
                wallet=wallet,
                amount=wallet_amount,
                tx_type=WalletTransaction.Type.FARE_DEBIT,
                source=f"payment:{payment_intent.reference}",
                metadata={"route": route.code, **package_meta},
            )
        elif subscription:
            # Package fully covered the fare. Still record a zero-amount
            # FARE_DEBIT so the trip is visible in transactions list with the
            # package metadata — otherwise package-covered trips would be
            # invisible to the passenger (and to admin auditing).
            now = timezone.now()
            WalletTransaction.objects.create(
                wallet=wallet,
                type=WalletTransaction.Type.FARE_DEBIT,
                direction=WalletTransaction.Direction.DEBIT,
                amount=Decimal("0.00"),
                signed_amount=Decimal("0.00"),
                balance_before=wallet.balance_cached,
                balance_after=wallet.balance_cached,
                reference=f"TXN-PKG-{uuid4().hex[:16].upper()}",
                source="app_travel_pass_purchase",
                status=WalletTransaction.Status.CONFIRMED,
                metadata={"route": route.code, "fully_covered_by_package": True, **package_meta},
                created_at=now,
            )

        # Moeda de exibicao escolhida na app (rand nas rotas p/ Africa do Sul):
        # so visualizacao — a carteira debita sempre MZN.
        from apps.fares.models import ExchangeRate

        display_ccy = str(display_currency or "MZN").upper()
        display_amount = None
        frozen_rate = None
        if display_ccy != "MZN":
            converted = ExchangeRate.convert_from_mzn(wallet_amount, display_ccy)
            if converted is None:
                display_ccy = "MZN"
            else:
                display_amount, frozen_rate = converted

        travel_pass = DigitalTravelPass.objects.create(
            passenger_account=passenger,
            wallet=wallet,
            payer_phone=passenger.phone_number,
            route_code=route.code,
            route_name=route.name,
            origin_stop=origin.name if origin else "",
            destination_stop=destination.name if destination else "",
            origin_stop_ref=origin,
            destination_stop_ref=destination,
            trip=trip,
            seat_number=seat,
            # O bilhete comprado na app e NOMINAL: leva os dados do titular
            # da conta, como pedido pelo cliente.
            passenger_name=(passenger.full_name or "")[:255],
            emergency_contact_name=(emergency_contact_name or "")[:120],
            emergency_contact_phone=(emergency_contact_phone or "")[:20],
            document_type=doc_type,
            document_number=doc_number[:64],
            # Copia da partida: e a data que o bilhete mostra no topo e a que
            # o passageiro procura. Sem isto o bilhete caia para a data da
            # COMPRA — num bilhete comprado com dias de antecedencia, a data
            # errada no sitio mais visivel.
            departure_at=getattr(trip, "planned_departure_at", None) if trip else None,
            # Show what the passenger actually paid (after any package
            # discount), not the gross fare — the ticket, tickets list,
            # history and PDF all read this field.
            fare_amount=wallet_amount,
            display_currency=display_ccy,
            display_fare_amount=display_amount,
            exchange_rate=frozen_rate,
            token=raw_token,
            token_hash=token_hash,
            delivery_channel=DigitalTravelPass.DeliveryChannel.APP,
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(hours=24),
        )
        # Codigo curto para leitura manual (mesma regra do PDF).
        travel_pass.short_code = ticket_short_code(ticket_reference(travel_pass))
        travel_pass.save(update_fields=["short_code", "updated_at"])

    travel_pass._raw_token = raw_token
    if package_used:
        travel_pass._package_used = package_used
        travel_pass._wallet_amount = wallet_amount
    return travel_pass


def quote_for_passenger(
    passenger: PassengerAccount,
    route: Route,
    origin: Stop | None,
    destination: Stop | None,
    passenger_package_id: int | None = None,
    use_package: bool = True,
) -> dict:
    """Return base fare, applicable package and resulting wallet amount.

    When `use_package=False`, the quote ignores any active package and returns
    `wallet_amount == base_fare`. This lets the mobile UI surface the real
    cost when the passenger toggles off the special-package switch.
    """
    quote = quote_fare(route=route, origin_stop=origin, destination_stop=destination)
    base = quote.amount

    sub = None
    if not use_package or not route.allows_package_discounts:
        # Numa interprovincial/internacional nao ha pacote a aplicar, mesmo que
        # o passageiro tenha um activo e o cliente o indique pelo id.
        sub = None
    elif passenger_package_id is not None:
        try:
            sub = PassengerPackage.objects.select_related("package").get(
                pk=passenger_package_id,
                passenger_account=passenger,
                status=PassengerPackage.Status.ACTIVE,
            )
            pkg_routes = PackageRoute.objects.filter(package=sub.package)
            if pkg_routes.exists() and not pkg_routes.filter(route=route).exists():
                sub = None
        except PassengerPackage.DoesNotExist:
            sub = None
    else:
        sub = find_active_package_for_route(passenger, route)

    if sub:
        wallet_amount = calculate_discounted_fare(base, sub)
        return {
            "base_fare": str(base),
            "wallet_amount": str(wallet_amount),
            "package_id": sub.id,
            "package_name": sub.package.name,
            "discount_type": sub.package.discount_type,
        }
    return {
        "base_fare": str(base),
        "wallet_amount": str(base),
        "package_id": None,
        "package_name": "",
        "discount_type": "",
    }
