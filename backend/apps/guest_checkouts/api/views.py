from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.viewsets import BaseModelViewSet
from apps.guest_checkouts.api.serializers import (
    GuestCheckoutCreateSerializer,
    GuestCheckoutPublicSerializer,
    GuestCheckoutSerializer,
)
from apps.guest_checkouts.capacity import sale_state, seats_available, seats_taken_bulk
from apps.guest_checkouts.models import GuestCheckout
from apps.guest_checkouts.seatmap import occupied_seats, seat_map
from apps.fares.services import NoFareFoundError, quote_fare
from apps.payments.models import PaymentIntent
from apps.payments.services.gateway import get_payment_gateway
from apps.payments.services.processing import confirm_payment_immediately
from apps.routes.models import Route, Stop
from apps.routes.services import RouteSegmentError, resolve_route_segment, route_segments_for_stop_pair
from apps.trips.models import Trip


class GuestCheckoutViewSet(BaseModelViewSet):
    queryset = GuestCheckout.all_objects.all()
    serializer_class = GuestCheckoutSerializer
    http_method_names = ["get", "head", "options"]
    required_capabilities_by_action = {
        "list": ("passengers.read",),
        "retrieve": ("passengers.read",),
    }


class GuestCheckoutCreateView(APIView):
    # AllowAny mas COM autenticacao JWT: o mesmo endpoint serve o comprador
    # anonimo da web e a app do passageiro. Quando vem um token valido, a
    # compra fica ligada a conta e o bilhete entra directamente na app.
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GuestCheckoutCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        linked_passenger = None
        if getattr(request.user, "is_authenticated", False) and getattr(request.user, "phone", ""):
            from apps.passengers.models import PassengerAccount

            linked_passenger = PassengerAccount.objects.filter(
                phone_number=request.user.phone,
                status=PassengerAccount.Status.ACTIVE,
            ).first()

        origin = Stop.objects.filter(pk=data.get("origin_stop_id")).first() if data.get("origin_stop_id") else None
        destination = Stop.objects.filter(pk=data.get("destination_stop_id")).first() if data.get("destination_stop_id") else None
        trip = None
        if data.get("trip_id"):
            # Inclui SCHEDULED: e assim que se compra hoje um lugar para uma
            # partida de daqui a dias (interurbano). A janela de venda e a
            # lotacao sao validadas mais abaixo, com o lugar bloqueado.
            trip = Trip.objects.select_related("route", "vehicle").filter(
                pk=data["trip_id"],
                status__in=[Trip.Status.SCHEDULED, Trip.Status.BOARDING, Trip.Status.DEPARTED],
            ).first()
            if trip is None:
                return Response({"detail": "Partida nao disponivel para compra."}, status=status.HTTP_404_NOT_FOUND)
            if data.get("route_code") and trip.route.code != data["route_code"]:
                return Response({"detail": "A viagem nao pertence a rota seleccionada."}, status=status.HTTP_400_BAD_REQUEST)

        # Ida e volta: a partida da volta e uma partida propria, na mesma rota
        # e no sentido contrario. Resolve-se aqui para a tarifa e a lotacao
        # serem validadas antes de se cobrar seja o que for.
        return_trip = None
        if data.get("return_trip_id"):
            return_trip = Trip.objects.select_related("route", "vehicle").filter(
                pk=data["return_trip_id"],
                status__in=[Trip.Status.SCHEDULED, Trip.Status.BOARDING, Trip.Status.DEPARTED],
            ).first()
            if return_trip is None:
                return Response({"detail": "Partida de volta nao disponivel para compra."},
                                status=status.HTTP_404_NOT_FOUND)

        route = trip.route if trip else None
        if route is None and data.get("route_code"):
            route = Route.objects.filter(code=data["route_code"], status=Route.Status.ACTIVE).first()
        if route is None and origin and destination:
            # Sem rota explicita (app do passageiro): inferir do par de paragens,
            # preferindo deterministicamente o corredor de menor id.
            try:
                segments = route_segments_for_stop_pair(origin.id, destination.id)
            except RouteSegmentError:
                segments = {}
            route_ids = sorted(segments.keys())
            if route_ids:
                route = Route.objects.filter(pk=route_ids[0]).first()
        if route is None:
            return Response(
                {"detail": "Nao existe rota entre a origem e o destino seleccionados."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if route and (origin or destination):
            try:
                resolve_route_segment(route, origin.id if origin else None, destination.id if destination else None)
            except RouteSegmentError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Termos e condicoes. A regra vive em `apps.branding.termos` porque ha
        # mais do que uma porta para comprar um bilhete — o site, a app por
        # carteira, a app por M-Pesa — e cada copia da regra e uma porta que um
        # dia deixa de a aplicar. A verificacao esta no servidor e nao so na
        # caixa do site: um pedido feito por fora do browser nao pode comprar
        # sem aceitar aquilo que o balcao faz toda a gente aceitar.
        from apps.branding.termos import TermosNaoAceites, registar_aceitacao

        try:
            aceitou_em, versao_aceite = registar_aceitacao(
                aceitou=data.get("accept_terms", False),
                versao_enviada=data.get("terms_version", ""),
            )
        except TermosNaoAceites as e:
            return Response({"detail": e.detail}, status=e.status_code)

        # Contacto de emergencia: obrigatorio onde ha manifesto de bordo.
        # Numa carreira urbana nem se guarda — sao dados de terceiros que nao
        # foram pedidos nem vao ser usados.
        emerg_name = (data.get("emergency_contact_name") or "").strip()[:120]
        emerg_phone = (data.get("emergency_contact_phone") or "").strip()[:20]
        if route and getattr(route, "requires_emergency_contact", False):
            if not emerg_phone:
                return Response(
                    {"detail": "Indique o contacto de emergencia para esta viagem."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            emerg_name, emerg_phone = "", ""

        unit_amount = data.get("unit_amount") or 0
        if route and origin and destination:
            try:
                unit_amount = quote_fare(route=route, origin_stop=origin, destination_stop=destination).amount
            except NoFareFoundError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        if not unit_amount or unit_amount <= 0:
            return Response(
                {"detail": "Nao foi possivel calcular o preco para esta viagem. Tente novamente ou contacte o agente."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # A volta e cotada para o percurso INVERTIDO: nada obriga uma rota a
        # custar o mesmo nos dois sentidos, e copiar o preco da ida seria
        # inventar um numero.
        return_unit_amount = None
        if return_trip is not None:
            if return_trip.route_id != route.id:
                return Response({"detail": "A volta tem de ser na mesma rota."},
                                status=status.HTTP_400_BAD_REQUEST)
            if not (origin and destination):
                return Response({"detail": "Indique origem e destino para comprar ida e volta."},
                                status=status.HTTP_400_BAD_REQUEST)
            try:
                return_unit_amount = quote_fare(
                    route=route, origin_stop=destination, destination_stop=origin).amount
            except NoFareFoundError as e:
                return Response({"detail": f"Volta: {e}"}, status=status.HTTP_400_BAD_REQUEST)
            if return_unit_amount <= 0:
                return Response({"detail": "O percurso de volta nao esta a venda."},
                                status=status.HTTP_400_BAD_REQUEST)
            if (trip is not None and return_trip.planned_departure_at
                    and trip.planned_departure_at
                    and return_trip.planned_departure_at <= trip.planned_departure_at):
                return Response(
                    {"detail": "A volta tem de partir depois da ida."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        passengers = data.get("passengers") or []
        quantity = data["quantity"]
        if passengers and len(passengers) != quantity:
            return Response(
                {"detail": "Indique os dados de cada passageiro."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Documento de identificacao: so nas viagens interprovinciais e
        # internacionais, onde o bilhete e nominal, entra no manifesto de bordo
        # e pode ser conferido na fronteira. Numa carreira urbana ninguem mostra
        # o BI para apanhar o autocarro do bairro — pedi-lo seria guardar dados
        # pessoais sem necessidade e travar uma compra que tem de ser rapida.
        #
        # A FORMA do numero ja foi validada no serializer; aqui decide-se se ele
        # e sequer preciso.
        if route.requires_seat_selection:
            from apps.guest_checkouts.documents import DocumentError, validate_document_for

            for i, p in enumerate(passengers, start=1):
                if not (p.get("document_number") or "").strip():
                    return Response(
                        {"detail": f"Indique o documento do passageiro {i}. "
                                   "E obrigatorio nesta viagem."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                # Numa rota internacional a fronteira so aceita passaporte.
                # Sem esta guarda, comprava-se com BI e descobria-se em Ressano
                # Garcia — com o autocarro a espera e sem reembolso.
                try:
                    p["document_number"] = validate_document_for(
                        route.service_type, p.get("document_type") or "", p["document_number"])
                except DocumentError as e:
                    return Response(
                        {"detail": f"Passageiro {i}: {e}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            # Numa carreira com lugar marcado, a volta tambem tem lugar. Sem
            # esta guarda, comprava-se ida e volta com lugar so na ida e o
            # passageiro descobria-o a porta do autocarro no regresso.
            if return_trip is not None:
                for i, p in enumerate(passengers, start=1):
                    if not (p.get("return_seat") or "").strip():
                        return Response(
                            {"detail": f"Escolha o lugar de volta do passageiro {i}."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
        else:
            # Nao guardar o que nao foi pedido: se o cliente enviar documento
            # numa carreira urbana, ele nao entra na base.
            for p in passengers:
                p["document_type"] = ""
                p["document_number"] = ""
                p["return_seat"] = ""

        # Um pagamento cobre os dois trocos: o passageiro compra a viagem, nao
        # dois bilhetes que tem de pagar em separado.
        total = (unit_amount + (return_unit_amount or 0)) * quantity
        ref = f"GC-{uuid4().hex[:18].upper()}"

        # A tentativa anterior do MESMO comprador nao lhe pode tapar o lugar.
        # A reserva vale contra terceiros; contra quem a fez, nao. Ver
        # `apps.guest_checkouts.retomar`.
        from apps.guest_checkouts.retomar import (
            libertar_tentativas_mortas,
            pagamento_a_decorrer,
        )

        if trip is not None:
            libertar_tentativas_mortas(trip, data["payer_phone"])
            if return_trip is not None:
                libertar_tentativas_mortas(return_trip, data["payer_phone"])

        # Reserva do lugar: bloqueia a linha da viagem para que dois
        # compradores simultaneos nao levem o mesmo ultimo lugar.
        with transaction.atomic():
            if trip is not None:
                # of=("self",): a viatura e nullable (LEFT JOIN) e o Postgres
                # recusa FOR UPDATE sobre o lado nullable de um outer join.
                trip = (Trip.objects.select_related("route", "vehicle")
                        .select_for_update(of=("self",)).get(pk=trip.pk))
                can_sell, reason = sale_state(trip)
                if not can_sell:
                    return Response({"detail": reason}, status=status.HTTP_409_CONFLICT)
                available = seats_available(trip)
                if available is not None and quantity > available:
                    return Response(
                        {"detail": f"Restam apenas {available} lugares nesta partida."},
                        status=status.HTTP_409_CONFLICT,
                    )
                chosen = [p.get("seat") for p in passengers if p.get("seat")]
                if chosen:
                    if len(set(chosen)) != len(chosen):
                        return Response({"detail": "Lugar repetido na mesma compra."},
                                        status=status.HTTP_400_BAD_REQUEST)
                    taken = occupied_seats(trip)
                    clash = sorted(set(chosen) & taken)
                    if clash:
                        # Se quem segura o lugar e o proprio comprador, dizer-lhe
                        # "escolha outro" e mandá-lo resolver um problema que nao
                        # tem: o que ele precisa e de confirmar o PIN que ja lhe
                        # foi pedido. Libertar tambem nao serve — arriscava uma
                        # segunda cobranca pelo mesmo lugar.
                        proprio = pagamento_a_decorrer(trip, data["payer_phone"], chosen)
                        if proprio is not None:
                            return Response({
                                "detail": "Já tem um pagamento a decorrer para este lugar. "
                                          "Confirme o PIN no telemóvel, ou aguarde alguns "
                                          "minutos antes de tentar de novo.",
                                "checkout_reference": proprio.reference,
                            }, status=status.HTTP_409_CONFLICT)
                        return Response(
                            {"detail": f"Lugar(es) ja ocupado(s): {', '.join(clash)}. Escolha outro."},
                            status=status.HTTP_409_CONFLICT,
                        )

            # A volta tem a sua propria lotacao e os seus proprios lugares. Sem
            # a bloquear aqui, dois compradores levavam o mesmo lugar de volta
            # enquanto disputavam lugares diferentes na ida.
            if return_trip is not None:
                return_trip = (Trip.objects.select_related("route", "vehicle")
                               .select_for_update(of=("self",)).get(pk=return_trip.pk))
                pode, motivo = sale_state(return_trip)
                if not pode:
                    return Response({"detail": f"Volta: {motivo}"}, status=status.HTTP_409_CONFLICT)
                livres = seats_available(return_trip)
                if livres is not None and quantity > livres:
                    return Response(
                        {"detail": f"Restam apenas {livres} lugares na partida de volta."},
                        status=status.HTTP_409_CONFLICT,
                    )
                escolhidos_volta = [p.get("return_seat") for p in passengers if p.get("return_seat")]
                if escolhidos_volta:
                    if len(set(escolhidos_volta)) != len(escolhidos_volta):
                        return Response({"detail": "Lugar de volta repetido na mesma compra."},
                                        status=status.HTTP_400_BAD_REQUEST)
                    ocupados = occupied_seats(return_trip)
                    choque = sorted(set(escolhidos_volta) & ocupados)
                    if choque:
                        return Response(
                            {"detail": f"Lugar(es) de volta ja ocupado(s): {', '.join(choque)}. Escolha outro."},
                            status=status.HTTP_409_CONFLICT,
                        )
            # Moeda de exibicao (ex.: ZAR nas rotas p/ Africa do Sul). A taxa e
            # congelada agora, para o valor mostrado no bilhete nunca mudar.
            from apps.fares.models import ExchangeRate

            display_currency = str(data.get("display_currency") or "MZN").upper()
            display_total = None
            frozen_rate = None
            if display_currency != "MZN":
                converted = ExchangeRate.convert_from_mzn(total, display_currency)
                if converted is None:
                    display_currency = "MZN"      # sem taxa configurada: cai para MZN
                else:
                    display_total, frozen_rate = converted

            gc = GuestCheckout.objects.create(
                reference=ref,
                payer_phone=data["payer_phone"],
                buyer_name=data.get("buyer_name", ""),
                buyer_email=data.get("buyer_email", ""),
                passengers=passengers,
                route_code=route.code,
                route_name=data.get("route_name") or route.name,
                origin_stop=origin.name if origin else data["origin_stop"],
                destination_stop=destination.name if destination else data["destination_stop"],
                origin_stop_ref=origin,
                destination_stop_ref=destination,
                quantity=quantity,
                unit_amount=unit_amount,
                total_amount=total,
                display_currency=display_currency,
                display_total_amount=display_total,
                exchange_rate=frozen_rate,
                status=GuestCheckout.Status.PAYMENT_PENDING,
                expires_at=timezone.now() + timedelta(minutes=30),
                trip=trip,
                return_trip=return_trip,
                return_unit_amount=return_unit_amount,
                terms_accepted_at=aceitou_em,
                terms_version=versao_aceite,
                linked_passenger=linked_passenger,
                emergency_contact_name=emerg_name,
                emergency_contact_phone=emerg_phone,
            )

            # Dentro do MESMO atomic que o checkout: se a intencao de pagamento
            # falhar, o checkout tambem desaparece. Estando fora, um erro aqui
            # deixava um PAYMENT_PENDING commitado a ocupar o lugar 30 minutos
            # sem nunca haver pagamento a decorrer.
            pi = PaymentIntent.objects.create(
                reference=f"PAY-{ref}",
                idempotency_key=f"gc-{ref}",
                purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
                amount=total,
                payer_phone=data["payer_phone"],
                guest_checkout=gc,
                status=PaymentIntent.Status.PENDING,
                expires_at=gc.expires_at,
            )

        gateway = get_payment_gateway(payer_phone=data["payer_phone"])
        result = gateway.initiate_payment(
            reference=pi.reference,
            amount=total,
            payer_phone=data["payer_phone"],
            description=f"BuzUp bilhete {route.code}",
        )

        pi.provider = result.provider
        pi.metadata = {
            "gateway_request": result.request_payload or {},
            "gateway_response": result.response_payload or {},
        }

        if result.success:
            pi.provider_reference = result.provider_reference
            pi.save(update_fields=["provider", "provider_reference", "metadata", "updated_at"])
            confirm_payment_immediately(pi, result.provider_reference)
            pi.refresh_from_db()
            gc.refresh_from_db()
        elif result.pending:
            pi.provider_reference = result.provider_reference
            pi.save(update_fields=["provider", "provider_reference", "metadata", "updated_at"])
        else:
            gc.status = GuestCheckout.Status.CANCELLED
            gc.save(update_fields=["status", "updated_at"])
            pi.status = PaymentIntent.Status.FAILED
            pi.save(update_fields=["status", "provider", "metadata", "updated_at"])
            return Response({
                "detail": result.detail_message or "Falha ao iniciar pagamento.",
            }, status=status.HTTP_502_BAD_GATEWAY)

        first_pass = gc.travel_passes.order_by("created_at").first() if gc.status == GuestCheckout.Status.ISSUED else None
        return Response({
            "checkout_reference": gc.reference,
            "payment_reference": pi.reference,
            "total_amount": str(total),
            "status": gc.status,
            "payment_status": pi.status,
            "detail_message": result.detail_message,
            "ticket_url": _public_ticket_url(first_pass.token) if first_pass else "",
        }, status=status.HTTP_201_CREATED)


class PublicTripSearchView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        from apps.routes.models import RouteStop
        from datetime import timedelta

        route_id = request.query_params.get("route")
        origin_id = request.query_params.get("origin")
        destination_id = request.query_params.get("destination")
        date_str = request.query_params.get("date")

        if origin_id and destination_id and origin_id == destination_id:
            return Response({"detail": "Destino deve ser diferente da origem."}, status=status.HTTP_400_BAD_REQUEST)

        segments_by_route: dict[int, object] = {}
        if origin_id and destination_id:
            try:
                segments_by_route = route_segments_for_stop_pair(origin_id, destination_id, route_id)
            except RouteSegmentError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            if route_id and not segments_by_route:
                return Response({"detail": "Nao existe direccao valida entre a origem e o destino nesta rota."}, status=status.HTTP_400_BAD_REQUEST)

        # Inclui SCHEDULED para a venda antecipada (interurbano). Sem data,
        # mantem-se o comportamento urbano: so o que ja esta a circular.
        wanted_statuses = [Trip.Status.BOARDING, Trip.Status.DEPARTED]
        if date_str:
            wanted_statuses.append(Trip.Status.SCHEDULED)
        qs = Trip.objects.select_related("route", "vehicle", "driver").filter(
            status__in=wanted_statuses,
            vehicle__isnull=False,
        )

        if route_id:
            qs = qs.filter(route_id=route_id)
        if origin_id and destination_id:
            qs = qs.filter(route_id__in=segments_by_route.keys())

        if date_str:
            from django.utils.dateparse import parse_date
            day = parse_date(date_str)
            if day:
                day_start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
                qs = qs.filter(planned_departure_at__gte=day_start, planned_departure_at__lt=day_start + timedelta(days=1))

        qs = qs.order_by("planned_departure_at", "route__code")[:40]

        # Origem e destino sao os MESMOS para todas as partidas do resultado:
        # buscá-los dentro do ciclo eram 2 queries por partida (80 no total)
        # para obter sempre a mesma linha. Idem a tarifa, que depende da rota e
        # nao da partida: com varias partidas da mesma rota, `quote_fare` (~8
        # queries) corria uma vez por partida em vez de uma por rota. Este
        # endpoint e o da pesquisa publica do site — o mais exposto de todos.
        origin = Stop.objects.filter(pk=origin_id).first() if origin_id else None
        dest = Stop.objects.filter(pk=destination_id).first() if destination_id else None
        fare_by_route: dict[int, str | None] = {}
        # Lotacao de todas as partidas num agregado, em vez de dois por partida
        # (`seats_available` + `sale_state`, que o chamava outra vez).
        trips = list(qs)
        taken_by_trip = seats_taken_bulk(trips)

        results = []
        for trip in trips:
            if trip.route_id in fare_by_route:
                fare_amount = fare_by_route[trip.route_id]
            else:
                fare_amount = None
                try:
                    q = quote_fare(route=trip.route, origin_stop=origin, destination_stop=dest)
                    fare_amount = str(q.amount)
                except NoFareFoundError:
                    pass
                fare_by_route[trip.route_id] = fare_amount

            # Sem preco nao ha nada para vender: ou a rota nao tem tarifa
            # configurada para este percurso, ou o percurso esta marcado a
            # custo zero — que e como o operador diz "este troco nao se vende".
            # Mostra-lo dava ao passageiro um resultado onde ele so podia
            # tropecar.
            if fare_amount is None:
                continue

            segment = segments_by_route.get(trip.route_id)
            taken = taken_by_trip.get(trip.id, 0)
            can_sell, reason = sale_state(trip, taken=taken)
            results.append({
                "trip_id": trip.id,
                "route_id": trip.route_id,
                "route_code": trip.route.code,
                "route_name": trip.route.name,
                # O percurso que o passageiro escolheu. O preco e DESTE percurso
                # e nao da rota inteira: mostra-lo ao lado do nome da rota
                # ("Maputo x Nelspruit · 1500 MZN") dizia ao passageiro que ia
                # pagar aquilo pela viagem toda, quando so pediu um troco dela.
                "origin_stop": origin.name if origin else "",
                "destination_stop": dest.name if dest else "",
                "vehicle": trip.vehicle.registration if trip.vehicle else None,
                "driver": trip.driver.full_name if trip.driver else None,
                "departure": trip.planned_departure_at.isoformat() if trip.planned_departure_at else None,
                "started_at": trip.activity_started_at.isoformat() if trip.activity_started_at else None,
                "direction": segment.direction if segment else "",
                "status": trip.status,
                "fare_amount": fare_amount,
                # O cliente nao pergunta ao passageiro que tipo de viagem e:
                # le daqui se ha lugar a marcar e salta a etapa quando nao ha.
                "service_type": trip.route.service_type,
                "seat_selection": trip.route.requires_seat_selection,
                # Disponibilidade legivel: o site mostra "3 lugares" ou o
                # motivo de indisponibilidade, nunca um botao morto.
                "seats_available": seats_available(trip, taken=taken),
                "on_sale": can_sell,
                "sale_unavailable_reason": reason,
            })

        routes_list = list(Route.objects.filter(status="active").values("id", "code", "name"))
        if route_id:
            stops_list = []
            seen_stop_ids = set()
            route_stops = RouteStop.objects.select_related("stop").filter(
                route_id=route_id,
                stop__status="active",
            ).order_by("direction", "sequence")
            for route_stop in route_stops:
                if route_stop.stop_id in seen_stop_ids:
                    continue
                seen_stop_ids.add(route_stop.stop_id)
                stops_list.append({
                    "id": route_stop.stop_id,
                    "code": route_stop.stop.code,
                    "name": route_stop.stop.name,
                })
        elif request.query_params.get("sellable"):
            # Portal publico: so paragens de rotas com partidas futuras — evita
            # oferecer origens/destinos onde nao ha nada para comprar.
            sellable_routes = Trip.objects.filter(
                status=Trip.Status.SCHEDULED,
                planned_departure_at__gte=timezone.now(),
                vehicle__isnull=False,
            ).values_list("route_id", flat=True).distinct()
            stops_list = list(
                Stop.objects.filter(
                    status="active", route_stops__route_id__in=list(sellable_routes),
                ).distinct().order_by("name").values("id", "code", "name")
            )
        else:
            stops_list = list(Stop.objects.filter(status="active").values("id", "code", "name"))

        return Response({
            "routes": routes_list,
            "stops": stops_list,
            "trips": results,
        })


class PublicTripSeatsView(APIView):
    """Planta de lugares de uma partida, para o passageiro escolher o lugar."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, trip_id: int):
        trip = Trip.objects.select_related("route", "vehicle").filter(
            pk=trip_id,
            status__in=[Trip.Status.SCHEDULED, Trip.Status.BOARDING, Trip.Status.DEPARTED],
        ).first()
        if trip is None:
            return Response({"detail": "Partida nao encontrada."}, status=status.HTTP_404_NOT_FOUND)
        can_sell, reason = sale_state(trip)
        data = seat_map(trip)
        data.update({
            "trip_id": trip.id,
            "route_code": trip.route.code,
            "route_name": trip.route.name,
            "vehicle": trip.vehicle.registration if trip.vehicle_id else "",
            "departure": trip.planned_departure_at.isoformat() if trip.planned_departure_at else None,
            "on_sale": can_sell,
            "sale_unavailable_reason": reason,
        })
        return Response(data)


class PublicDocumentTypesView(APIView):
    """Tipos de documento aceites e a forma de cada um.

    O portal le daqui o limite do campo, o exemplo e a regra por palavras, em
    vez de os ter escritos outra vez em TypeScript. Assim a validacao do
    formulario e a do servidor nao podem discordar — e quando um formato mudar,
    muda num sitio so.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        from apps.guest_checkouts.documents import public_rules

        # `?service_type=international` devolve so o passaporte: e o unico
        # documento com que se atravessa a fronteira.
        return Response({
            "document_types": public_rules(request.query_params.get("service_type")),
        })


class PublicBusInfoView(APIView):
    """Lookup info for a bus QR code scan: vehicle + active trips + stops + fares."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, vehicle_uuid):
        from apps.trips.models import Vehicle
        from apps.routes.models import RouteStop

        vehicle = Vehicle.objects.filter(uuid=vehicle_uuid).first()
        if not vehicle:
            return Response({"detail": "Autocarro nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        trips = Trip.objects.select_related("route", "driver").filter(
            vehicle=vehicle,
            status__in=[Trip.Status.BOARDING, Trip.Status.DEPARTED, Trip.Status.SCHEDULED],
        ).order_by("planned_departure_at")[:5]

        trips_payload = []
        for trip in trips:
            stops = list(
                RouteStop.objects.select_related("stop")
                .filter(route=trip.route, stop__status="active")
                .order_by("direction", "sequence")
            )
            stops_seen = {}
            for rs in stops:
                key = rs.stop_id
                if key not in stops_seen:
                    stops_seen[key] = {
                        "id": rs.stop_id,
                        "code": rs.stop.code,
                        "name": rs.stop.name,
                    }
            trips_payload.append({
                "trip_id": trip.id,
                "route_id": trip.route_id,
                "route_code": trip.route.code,
                "route_name": trip.route.name,
                "driver": trip.driver.full_name if trip.driver else "",
                "departure": trip.planned_departure_at.isoformat() if trip.planned_departure_at else None,
                "started_at": trip.activity_started_at.isoformat() if trip.activity_started_at else None,
                "status": trip.status,
                # O tipo de carreira decide o que a pagina do QR pode fazer.
                # Numa urbana basta origem, destino e telemovel. Numa carreira
                # com lugar marcado o bilhete e nominal, leva assento, documento
                # e contacto de emergencia — coisas que um formulario rapido nao
                # recolhe, e que o servidor exige. Sem isto a pagina do QR nao
                # tinha como saber que estava a montar uma compra impossivel.
                "service_type": trip.route.service_type,
                "seat_selection": trip.route.requires_seat_selection,
                "stops": list(stops_seen.values()),
            })

        return Response({
            "vehicle": {
                "uuid": str(vehicle.uuid),
                "registration": vehicle.registration,
                "make": vehicle.make,
                "model_name": vehicle.model_name,
                "status": vehicle.status,
            },
            "active_trips": trips_payload,
        })


class TicketPdfView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        from apps.guest_checkouts.models import DigitalTravelPass
        from apps.guest_checkouts.ticket_pdf import generate_tickets_pdf
        import hashlib

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            tp = DigitalTravelPass.objects.select_related("guest_checkout").get(token_hash=token_hash)
        except DigitalTravelPass.DoesNotExist:
            return Response({"detail": "Bilhete nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if tp.guest_checkout_id:
            travel_passes = list(
                DigitalTravelPass.objects.select_related("guest_checkout").filter(
                    guest_checkout_id=tp.guest_checkout_id,
                ).order_by("created_at", "id")
            )
        else:
            travel_passes = [tp]

        pdf_bytes = generate_tickets_pdf(travel_passes)
        from django.http import HttpResponse as DjangoHttpResponse
        response = DjangoHttpResponse(pdf_bytes, content_type="application/pdf")
        ref = tp.guest_checkout.reference if tp.guest_checkout else str(tp.uuid)[:8]
        filename_prefix = "bilhetes" if len(travel_passes) > 1 else "bilhete"
        response["Content-Disposition"] = f'inline; filename="{filename_prefix}-{ref}.pdf"'
        return response


class GuestCheckoutLookupView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, reference):
        try:
            gc = GuestCheckout.objects.prefetch_related("travel_passes").get(reference=reference)
        except GuestCheckout.DoesNotExist:
            return Response({"detail": "Checkout nao encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return Response(GuestCheckoutPublicSerializer(gc).data)


def _public_ticket_url(token: str) -> str:
    base = str(getattr(settings, "PUBLIC_BASE_URL", "") or "").rstrip("/")
    return f"{base}/api/public/ticket/{token}/" if base else f"/api/public/ticket/{token}/"
