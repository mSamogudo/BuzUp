"""Dados de demonstração para todas as tabelas do sistema.

Enche as tabelas que nascem vazias — rotas, frota, viagens, carteiras, cartões,
pagamentos, validações, terminais, APKs, avisos e pedidos — com uma operação
coerente de Maputo, para o portal ter o que mostrar em desenvolvimento.

Regras que a operação respeita, para os números baterem certo entre ecrãs:

* Cada bilhete de convidado tem a sua intenção de pagamento e o seu passe.
* Cada validação desconta de uma carteira ou consome um passe, e o extracto da
  carteira fecha com o saldo em cache.
* Os fechos de viagem somam exactamente a receita das vendas dessa viagem.
* Os registos ficam espalhados pelas últimas três semanas: sem isso os
  gráficos do painel sairiam todos com uma barra só.

É idempotente por tabela: uma tabela que já tenha linhas fica como está, a não
ser que se passe `--force`, que apaga primeiro o que este comando semeia.

    python manage.py seed_demo
    python manage.py seed_demo --force
"""

from __future__ import annotations

import hashlib
import random
import secrets
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

SEMENTE = 20260828
DIAS = 21


def dec(valor) -> Decimal:
    return Decimal(str(valor)).quantize(Decimal("0.01"))


def sha(texto: str) -> str:
    return hashlib.sha256(texto.encode()).hexdigest()


class Command(BaseCommand):
    help = "Enche todas as tabelas vazias com dados de demonstração coerentes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Apaga o que este comando semeia e volta a semear.",
        )
        parser.add_argument(
            "--only",
            default="",
            help="Lista de rótulos separados por vírgula (ex.: routes.Route,trips.Trip).",
        )

    # -- utilitários ------------------------------------------------------

    def m(self, rotulo):
        return apps.get_model(rotulo)

    def salta(self, rotulo) -> bool:
        """Uma tabela já com linhas fica como está (a não ser com --force)."""
        if self.only and rotulo not in self.only:
            return True
        modelo = self.m(rotulo)
        if self.force:
            return False
        if modelo.objects.exists():
            self.feito[rotulo] = "já tinha"
            return True
        return False

    def conta(self, rotulo):
        self.feito[rotulo] = self.m(rotulo).objects.count()

    def quando(self, dias_atras: float, hora: int = 9, minuto: int = 0):
        """Instante dentro da janela de três semanas, sem cair no futuro."""
        base = self.agora - timedelta(days=dias_atras)
        return base.replace(hour=hora, minute=minuto, second=0, microsecond=0)

    def recuar(self, modelo, pks, instante):
        """`created_at` é `auto_now_add`: só se corrige depois de gravar."""
        modelo.objects.filter(pk__in=pks).update(created_at=instante, updated_at=instante)

    # -- entrada ----------------------------------------------------------

    def handle(self, *args, **opcoes):
        self.force = opcoes["force"]
        self.only = {s.strip() for s in opcoes["only"].split(",") if s.strip()}
        self.rng = random.Random(SEMENTE)
        self.agora = timezone.now()
        self.feito: dict[str, object] = {}

        with transaction.atomic():
            if self.force:
                self._limpar()
            self._utilizadores()
            self._paragens_e_rotas()
            self._frota()
            self._horarios_e_viagens()
            self._tarifas()
            self._passageiros_e_carteiras()
            self._cartoes()
            self._pacotes()
            self._terminais()
            self._sessoes_pos()
            self._compras_e_pagamentos()
            self._validacoes()
            self._fechos()
            self._apks()
            self._avisos_e_pedidos()
            self._tokens_revogados()
            self._agenda_cms()

        self.stdout.write("")
        for rotulo in sorted(self.feito):
            self.stdout.write(f"  {rotulo:44} {self.feito[rotulo]}")
        self.stdout.write(self.style.SUCCESS("\nDados de demonstração carregados."))

    def _limpar(self):
        """Apaga o que este comando semeia, do fim da cadeia para o princípio."""
        ordem = [
            "app_releases.DeviceAppUpdate", "app_releases.AppRelease",
            "agent_api.RecoverySession", "agent_api.AgentDayClose",
            "validations.ValidationEvent",
            "guest_checkouts.DigitalTravelPass", "guest_checkouts.GuestCheckout",
            "payments.PaymentCallback", "payments.PaymentIntent",
            "pos.PosSession",
            "packages.PassengerPackage", "packages.PackageRoute", "packages.Package",
            "cards.Card",
            "wallets.WalletTransaction", "wallets.Wallet", "passengers.PassengerAccount",
            "fares.FareRule", "fares.FareProduct", "fares.ExchangeRate",
            "trips.TripRevenueClosure", "trips.TripActivityEvent", "trips.Trip",
            "trips.RouteSchedule", "trips.Agent", "trips.Driver", "trips.Vehicle",
            "devices.DeviceActivationRequest", "devices.Device",
            "routes.RouteStop", "routes.Route", "routes.Stop",
            "notifications.Notification", "leads.ServiceRequest",
            "sms.SmsBroadcast", "cms.ScheduledPublication", "users.OtpChallenge",
            "token_blacklist.BlacklistedToken",
        ]
        for rotulo in ordem:
            if self.only and rotulo not in self.only:
                continue
            modelo = self.m(rotulo)
            gestor = getattr(modelo, "all_objects", modelo.objects)
            gestor.all().delete()

    # -- utilizadores de apoio -------------------------------------------

    def _utilizadores(self):
        """Contas para os motoristas e agentes ficarem ligados a um `User`."""
        User = self.m("users.User")
        Role = self.m("users.Role")
        UserRole = self.m("users.UserRole")

        self.users = {u.username: u for u in User.objects.all()}
        novos = [
            ("motorista1", "Alberto Mucavele", "driver", "+258841000101"),
            ("motorista2", "Salomão Chirindza", "driver", "+258841000102"),
            ("agente1", "Célia Nhantumbo", "agent", "+258841000201"),
            ("agente2", "Rui Macuácua", "agent", "+258841000202"),
        ]
        for username, nome, papel, telefone in novos:
            u = self.users.get(username)
            if not u:
                nomes = nome.split(" ", 1)
                u = User(
                    username=username, first_name=nomes[0], last_name=nomes[1],
                    email=f"{username}@updigital.co.mz", phone=telefone, is_active=True,
                )
                u.set_unusable_password()
                u.save()
                self.users[username] = u
            role = Role.objects.filter(code=papel).first()
            if role:
                UserRole.objects.get_or_create(user=u, role=role)

        self.admin = User.objects.filter(is_superuser=True).first() or next(iter(self.users.values()))
        self.feito["users.User (apoio)"] = len(novos)

    # -- rede -------------------------------------------------------------

    PARAGENS = [
        ("BAI", "Baixa", -25.9692, 32.5732),
        ("MUS", "Museu", -25.9741, 32.5931),
        ("CSO", "Costa do Sol", -25.9210, 32.6180),
        ("AER", "Aeroporto de Maputo", -25.9208, 32.5726),
        ("JUN", "Junta", -25.9182, 32.5405),
        ("MRC", "Marracuene", -25.7392, 32.6716),
        ("ZIM", "Zimpeto", -25.8600, 32.5420),
        ("XIP", "Xipamanine", -25.9530, 32.5560),
        ("COM", "Praça dos Combatentes", -25.9385, 32.5628),
        ("MTR", "Matola-Rio", -25.9010, 32.4130),
        ("BEI", "Terminal da Beira", -19.8436, 34.8389),
        ("INH", "Terminal de Inhambane", -23.8650, 35.3833),
    ]

    ROTAS = [
        ("L5", "Baixa — Aeroporto", "urban", ["BAI", "COM", "XIP", "AER"]),
        ("L2", "Museu — Costa do Sol", "urban", ["MUS", "BAI", "CSO"]),
        ("L6", "Junta — Marracuene", "urban", ["JUN", "ZIM", "MRC"]),
        ("IC1", "Maputo — Beira", "interprovincial", ["BAI", "MTR", "INH", "BEI"]),
    ]

    def _paragens_e_rotas(self):
        Stop = self.m("routes.Stop")
        Route = self.m("routes.Route")
        RouteStop = self.m("routes.RouteStop")

        if not self.salta("routes.Stop"):
            for codigo, nome, lat, lon in self.PARAGENS:
                Stop.objects.get_or_create(
                    code=codigo,
                    defaults={"name": nome, "latitude": dec(lat), "longitude": dec(lon)},
                )
            self.conta("routes.Stop")
        self.stops = {s.code: s for s in Stop.objects.all()}

        if not self.salta("routes.Route"):
            for codigo, nome, tipo, _ in self.ROTAS:
                Route.objects.get_or_create(
                    code=codigo,
                    defaults={
                        "name": nome,
                        "service_type": tipo,
                        "description": f"Percurso {nome}, operação de demonstração.",
                    },
                )
            self.conta("routes.Route")
        self.routes = {r.code: r for r in Route.objects.all()}

        if not self.salta("routes.RouteStop"):
            for codigo, _, _, paragens in self.ROTAS:
                rota = self.routes.get(codigo)
                if not rota:
                    continue
                # Ida e volta: a volta é a mesma lista ao contrário, com a
                # distância recontada a partir do novo ponto de partida.
                for sentido, lista in (("outbound", paragens), ("inbound", list(reversed(paragens)))):
                    km = Decimal("0.00")
                    for i, cod_paragem in enumerate(lista):
                        paragem = self.stops.get(cod_paragem)
                        if not paragem:
                            continue
                        RouteStop.objects.get_or_create(
                            route=rota, stop=paragem, sequence=i + 1, direction=sentido,
                            defaults={"distance_from_start_km": km},
                        )
                        km += dec(6.5 if rota.service_type == "urban" else 180)
            self.conta("routes.RouteStop")

    # -- frota ------------------------------------------------------------

    def _frota(self):
        Vehicle = self.m("trips.Vehicle")
        Driver = self.m("trips.Driver")
        Agent = self.m("trips.Agent")

        if not self.salta("trips.Vehicle"):
            frota = [
                ("ABC-123-MP", "Toyota", "Coaster", 32, 12, "2+2", 5, "active"),
                ("DEF-456-MP", "Toyota", "Hiace", 18, 6, "1+2", 4, "active"),
                ("GHI-789-MP", "Mercedes", "Sprinter", 22, 8, "2+2", 4, "active"),
                ("JKL-012-MP", "Higer", "KLQ6119", 51, 0, "2+2", 5, "active"),
                ("MNO-345-MP", "Toyota", "Coaster", 32, 12, "2+2", 5, "maintenance"),
            ]
            for matricula, marca, modelo, sentados, em_pe, layout, ultima, estado in frota:
                Vehicle.objects.get_or_create(
                    registration=matricula,
                    defaults={
                        "make": marca, "model_name": modelo,
                        "seated_capacity": sentados, "standing_capacity": em_pe,
                        "seat_layout": layout, "last_row_seats": ultima, "status": estado,
                    },
                )
            self.conta("trips.Vehicle")
        self.vehicles = list(Vehicle.objects.order_by("pk"))

        if not self.salta("trips.Driver"):
            motoristas = [
                ("Alberto Mucavele", "+258841000101", "MZ-2019-44120", "motorista1"),
                ("Salomão Chirindza", "+258841000102", "MZ-2020-51873", "motorista2"),
                ("Ivone Sitoe", "+258841000103", "MZ-2018-33091", None),
                ("Domingos Cossa", "+258841000104", "MZ-2021-60214", None),
            ]
            for nome, telefone, carta, username in motoristas:
                Driver.objects.get_or_create(
                    full_name=nome,
                    defaults={
                        "phone": telefone, "license_number": carta,
                        "user": self.users.get(username),
                    },
                )
            self.conta("trips.Driver")
        self.drivers = list(Driver.objects.order_by("pk"))

        if not self.salta("trips.Agent"):
            agentes = [
                ("Célia Nhantumbo", "+258841000201", "agente1"),
                ("Rui Macuácua", "+258841000202", "agente2"),
                ("Fátima Bila", "+258841000203", None),
            ]
            for nome, telefone, username in agentes:
                Agent.objects.get_or_create(
                    full_name=nome,
                    defaults={"phone": telefone, "user": self.users.get(username)},
                )
            self.conta("trips.Agent")
        self.agents = list(Agent.objects.order_by("pk"))

    # -- horários e viagens ------------------------------------------------

    def _horarios_e_viagens(self):
        RouteSchedule = self.m("trips.RouteSchedule")
        Trip = self.m("trips.Trip")
        TripActivityEvent = self.m("trips.TripActivityEvent")

        if not self.salta("trips.RouteSchedule"):
            grelha = [
                ("L5", time(5, 30), time(21, 0), 20, [0, 1, 2, 3, 4, 5]),
                ("L2", time(6, 0), time(20, 30), 30, [0, 1, 2, 3, 4, 5, 6]),
                ("L6", time(5, 0), time(20, 0), 25, [0, 1, 2, 3, 4]),
                ("IC1", time(6, 30), time(18, 0), 720, [0, 2, 4, 6]),
            ]
            for i, (codigo, inicio, fim, frequencia, dias) in enumerate(grelha):
                rota = self.routes.get(codigo)
                if not rota:
                    continue
                RouteSchedule.objects.get_or_create(
                    route=rota, start_time=inicio,
                    defaults={
                        "end_time": fim, "frequency_minutes": frequencia,
                        "days_of_week": dias,
                        "vehicle": self.vehicles[i % len(self.vehicles)],
                        "driver": self.drivers[i % len(self.drivers)],
                        "agent": self.agents[i % len(self.agents)],
                    },
                )
            self.conta("trips.RouteSchedule")
        self.schedules = {s.route.code: s for s in RouteSchedule.objects.select_related("route")}

        self.trips = []
        if not self.salta("trips.Trip"):
            criadas = []
            for dia in range(DIAS, -1, -1):
                for j, (codigo, _, _, _) in enumerate(self.ROTAS):
                    rota = self.routes.get(codigo)
                    if not rota:
                        continue
                    # Uma partida por rota e por dia; hoje ficam a decorrer.
                    hora = 6 + (j * 3)
                    partida = self.quando(dia, hora, 30)
                    if dia == 0:
                        estado = "departed" if hora <= self.agora.hour else "scheduled"
                    else:
                        estado = "cancelled" if (dia + j) % 17 == 0 else "completed"
                    duracao = timedelta(hours=1 if rota.service_type == "urban" else 9)
                    viagem = Trip(
                        route=rota,
                        vehicle=self.vehicles[j % len(self.vehicles)],
                        driver=self.drivers[j % len(self.drivers)],
                        agent=self.agents[j % len(self.agents)],
                        schedule=self.schedules.get(codigo),
                        planned_departure_at=partida,
                        planned_arrival_at=partida + duracao,
                        status=estado,
                    )
                    if estado in ("departed", "completed"):
                        viagem.actual_departure_at = partida + timedelta(minutes=self.rng.randint(0, 9))
                        viagem.activity_started_at = partida - timedelta(minutes=15)
                    if estado == "completed":
                        viagem.actual_arrival_at = partida + duracao + timedelta(minutes=self.rng.randint(0, 20))
                        viagem.activity_closed_at = viagem.actual_arrival_at
                        viagem.pause_seconds = self.rng.choice([0, 0, 180, 420])
                    criadas.append((viagem, partida))
            Trip.objects.bulk_create([v for v, _ in criadas])
            for viagem, partida in criadas:
                self.recuar(Trip, [Trip.objects.filter(planned_departure_at=partida, route=viagem.route)
                                   .values_list("pk", flat=True).first()], partida - timedelta(hours=12))
            self.conta("trips.Trip")
        self.trips = list(Trip.objects.select_related("route", "vehicle", "driver", "agent").order_by("pk"))
        self.trips_feitas = [t for t in self.trips if t.status == "completed"]

        if not self.salta("trips.TripActivityEvent"):
            eventos = []
            for viagem in self.trips:
                if viagem.status not in ("departed", "completed"):
                    continue
                marcos = [("start", viagem.activity_started_at), ("depart", viagem.actual_departure_at)]
                if viagem.pause_seconds:
                    pausa = viagem.actual_departure_at + timedelta(minutes=25)
                    marcos += [("pause", pausa), ("resume", pausa + timedelta(seconds=viagem.pause_seconds))]
                if viagem.activity_closed_at:
                    marcos.append(("close", viagem.activity_closed_at))
                for tipo, instante in marcos:
                    if not instante:
                        continue
                    eventos.append(TripActivityEvent(
                        trip=viagem, driver=viagem.driver, user=self.admin,
                        event_type=tipo, occurred_at=instante,
                        metadata={"origem": "seed_demo"},
                    ))
            TripActivityEvent.objects.bulk_create(eventos)
            self.conta("trips.TripActivityEvent")

    # -- tarifas -----------------------------------------------------------

    def _tarifas(self):
        FareProduct = self.m("fares.FareProduct")
        FareRule = self.m("fares.FareRule")
        ExchangeRate = self.m("fares.ExchangeRate")

        if not self.salta("fares.FareProduct"):
            for nome, tipo in [
                ("Bilhete simples", "single_trip"),
                ("Passe diário", "daily_pass"),
                ("Passe semanal", "weekly_pass"),
                ("Passe mensal", "monthly_pass"),
            ]:
                FareProduct.objects.get_or_create(name=nome, defaults={"product_type": tipo})
            self.conta("fares.FareProduct")
        self.products = {p.product_type: p for p in FareProduct.objects.all()}

        if not self.salta("fares.FareRule"):
            simples = self.products.get("single_trip")
            precos = {"L5": 25, "L2": 20, "L6": 30, "IC1": 1500}
            for codigo, valor in precos.items():
                rota = self.routes.get(codigo)
                if not rota or not simples:
                    continue
                for classe, factor in (("standard", 1), ("student", Decimal("0.5")), ("senior", Decimal("0.6")), ("child", Decimal("0.5"))):
                    FareRule.objects.get_or_create(
                        fare_product=simples, route=rota, passenger_class=classe,
                        calculation_method="fixed",
                        defaults={
                            "fixed_amount": dec(Decimal(valor) * Decimal(factor)),
                            "min_amount": dec(Decimal(valor) * Decimal(factor)),
                            "max_amount": dec(Decimal(valor) * Decimal(factor)),
                            "priority": 10 if classe == "standard" else 20,
                        },
                    )
            # Interprovincial: preço por par origem-destino, que é como se vende.
            ic1 = self.routes.get("IC1")
            if ic1 and simples:
                pares = [("BAI", "INH", 850), ("BAI", "BEI", 1500), ("INH", "BEI", 900)]
                for origem, destino, valor in pares:
                    o, d = self.stops.get(origem), self.stops.get(destino)
                    if not o or not d:
                        continue
                    FareRule.objects.get_or_create(
                        fare_product=simples, route=ic1, origin_stop=o, destination_stop=d,
                        passenger_class="standard", calculation_method="origin_destination",
                        defaults={"fixed_amount": dec(valor), "min_amount": dec(valor),
                                  "max_amount": dec(valor), "priority": 5},
                    )
            self.conta("fares.FareRule")

        if not self.salta("fares.ExchangeRate"):
            for moeda, taxa, passo, nota in [
                ("ZAR", "3.55", "1.00", "Rand sul-africano, venda em fronteira."),
                ("USD", "63.90", "5.00", "Dólar, venda a estrangeiros."),
                ("EUR", "69.40", "5.00", "Euro, venda a estrangeiros."),
            ]:
                ExchangeRate.objects.get_or_create(
                    currency=moeda,
                    defaults={"rate_to_mzn": Decimal(taxa), "rounding_step": Decimal(passo), "notes": nota},
                )
            self.conta("fares.ExchangeRate")

    # -- passageiros e carteiras -------------------------------------------

    NOMES = [
        "Maria Joaquim", "Ana Cumbe", "Paulo Matsinhe", "Jorge Tembe", "Rosa Mabjaia",
        "Hélder Nhaca", "Sandra Muianga", "Inácio Zandamela", "Teresa Chissano", "Nelson Guambe",
    ]

    def _passageiros_e_carteiras(self):
        PassengerAccount = self.m("passengers.PassengerAccount")
        Wallet = self.m("wallets.Wallet")
        WalletTransaction = self.m("wallets.WalletTransaction")

        if not self.salta("passengers.PassengerAccount"):
            for i, nome in enumerate(self.NOMES):
                PassengerAccount.objects.get_or_create(
                    phone_number=f"+2588412001{i:02d}",
                    defaults={
                        "full_name": nome,
                        "email": f"{nome.split()[0].lower()}@exemplo.co.mz",
                        "document_type": "bi",
                        "document_number": f"1101{i:07d}A",
                        "status": "blocked" if i == 9 else "active",
                    },
                )
            self.conta("passengers.PassengerAccount")
        self.passengers = list(PassengerAccount.objects.order_by("pk"))

        if not self.salta("wallets.Wallet"):
            for p in self.passengers:
                Wallet.objects.get_or_create(
                    passenger_account=p,
                    defaults={"status": "blocked" if p.status == "blocked" else "active"},
                )
            self.conta("wallets.Wallet")
        self.wallets = list(Wallet.objects.select_related("passenger_account").order_by("pk"))

        if not self.salta("wallets.WalletTransaction"):
            n = 0
            for carteira in self.wallets:
                saldo = Decimal("0.00")
                # Uma recarga por semana e alguns descontos pelo meio: o extracto
                # tem de fechar com o saldo em cache, senão o portal mente.
                for semana in range(3):
                    dia = DIAS - semana * 7 - 1
                    valor = dec(self.rng.choice([100, 200, 250, 500]))
                    antes, saldo = saldo, saldo + valor
                    ref = f"TOPUP-{carteira.pk:03d}-{semana}"
                    t = WalletTransaction.objects.create(
                        wallet=carteira, type="topup", direction="credit",
                        amount=valor, signed_amount=valor,
                        balance_before=antes, balance_after=saldo,
                        reference=ref, source=self.rng.choice(["mpesa", "emola", "pos"]),
                        metadata={"origem": "seed_demo"},
                    )
                    self.recuar(WalletTransaction, [t.pk], self.quando(dia, 8, 15))
                    n += 1
                    for k in range(self.rng.randint(1, 3)):
                        gasto = dec(self.rng.choice([20, 25, 30]))
                        if saldo < gasto:
                            continue
                        antes, saldo = saldo, saldo - gasto
                        t = WalletTransaction.objects.create(
                            wallet=carteira, type="fare_debit", direction="debit",
                            amount=gasto, signed_amount=-gasto,
                            balance_before=antes, balance_after=saldo,
                            reference=f"FARE-{carteira.pk:03d}-{semana}-{k}",
                            source="validation", metadata={"origem": "seed_demo"},
                        )
                        self.recuar(WalletTransaction, [t.pk], self.quando(dia - k, 17, 40))
                        n += 1
                carteira.balance_cached = saldo
                carteira.save(update_fields=["balance_cached"])
            self.feito["wallets.WalletTransaction"] = n

    # -- cartões -----------------------------------------------------------

    def _cartoes(self):
        Card = self.m("cards.Card")
        if self.salta("cards.Card"):
            self.cards = list(Card.objects.all())
            return
        for i, p in enumerate(self.passengers):
            carteira = next((w for w in self.wallets if w.passenger_account_id == p.pk), None)
            estado = "active"
            if i == 7:
                estado = "lost"
            elif i == 9:
                estado = "blocked"
            emitido = self.quando(DIAS - 1, 10, 0)
            fisico = Card.objects.create(
                card_type="physical", card_technology="mifare_classic",
                card_uid=f"04{secrets.token_hex(6).upper()}",
                card_number=f"0042 {1180 + i}",
                wallet=carteira, passenger_account=p, status=estado,
                issued_batch="LOTE-2026-01", batch_serial=f"{i + 1:04d}",
                manufacturer="Identiv", issued_at=emitido,
                activated_at=emitido if estado != "blocked" else None,
                blocked_at=self.quando(3, 11, 0) if estado == "blocked" else None,
            )
            self.recuar(Card, [fisico.pk], emitido)
            if i < 6:
                token = secrets.token_urlsafe(24)
                # `card_uid` é único entre cartões vivos, mesmo vazio: o passe
                # digital leva um identificador próprio em vez de string vazia.
                digital = Card.objects.create(
                    card_type="digital", card_technology="qr_code",
                    card_uid=f"QR{secrets.token_hex(6).upper()}",
                    card_number=f"QR-{p.phone_number[-6:]}",
                    qr_token=token, qr_token_hash=sha(token),
                    wallet=carteira, passenger_account=p, status="active",
                    issued_at=emitido, activated_at=emitido,
                )
                self.recuar(Card, [digital.pk], emitido)
        # O cartão perdido foi substituído: a substituição aponta para o novo.
        perdido = Card.objects.filter(status="lost").first()
        if perdido:
            substituto = Card.objects.create(
                card_type="physical", card_technology="mifare_classic",
                card_uid=f"04{secrets.token_hex(6).upper()}",
                card_number="0042 1199", wallet=perdido.wallet,
                passenger_account=perdido.passenger_account, status="active",
                issued_batch="LOTE-2026-02", batch_serial="0001",
                manufacturer="Identiv", issued_at=self.quando(2, 9, 0),
                activated_at=self.quando(2, 9, 5),
            )
            perdido.replaced_by = substituto
            perdido.status = "replaced"
            perdido.save(update_fields=["replaced_by", "status"])
        self.conta("cards.Card")
        self.cards = list(Card.objects.all())

    # -- pacotes -----------------------------------------------------------

    def _pacotes(self):
        Package = self.m("packages.Package")
        PackageRoute = self.m("packages.PackageRoute")
        PassengerPackage = self.m("packages.PassengerPackage")

        if not self.salta("packages.Package"):
            for nome, tipo, valor, preco, dias, viagens, descricao in [
                ("Passe Urbano 30 dias", "free_trips", 60, 1200, 30, 60,
                 "Sessenta viagens nas rotas urbanas, válidas por trinta dias."),
                ("Estudante -50%", "percentage", 50, 0, 180, 0,
                 "Metade do preço em todas as rotas urbanas, mediante comprovativo."),
                ("Trabalhador 10 viagens", "fixed_amount", 5, 200, 30, 10,
                 "Dez viagens com cinco meticais de desconto em cada."),
            ]:
                Package.objects.get_or_create(
                    name=nome,
                    defaults={
                        "description": descricao, "discount_type": tipo,
                        "discount_value": dec(valor), "price": dec(preco),
                        "validity_days": dias, "max_trips": viagens,
                    },
                )
            self.conta("packages.Package")
        self.packages = list(Package.objects.order_by("pk"))

        if not self.salta("packages.PackageRoute"):
            urbanas = [r for r in self.routes.values() if r.service_type == "urban"]
            for pacote in self.packages:
                for rota in urbanas:
                    PackageRoute.objects.get_or_create(package=pacote, route=rota)
            self.conta("packages.PackageRoute")

        if not self.salta("packages.PassengerPackage"):
            for i, p in enumerate(self.passengers[:6]):
                pacote = self.packages[i % len(self.packages)]
                carteira = next((w for w in self.wallets if w.passenger_account_id == p.pk), None)
                usadas = self.rng.randint(0, min(12, pacote.max_trips or 12))
                restam = max(pacote.max_trips - usadas, 0) if pacote.max_trips else 0
                activado = self.quando(DIAS - 2, 9, 0)
                pp = PassengerPackage.objects.create(
                    passenger_account=p, package=pacote, wallet=carteira,
                    special_balance=dec(self.rng.choice([0, 50, 120])),
                    trips_used=usadas, trips_remaining=restam,
                    status="exhausted" if (pacote.max_trips and restam == 0) else "active",
                    activated_at=activado,
                    expires_at=activado + timedelta(days=pacote.validity_days),
                )
                self.recuar(PassengerPackage, [pp.pk], activado)
            self.conta("packages.PassengerPackage")

    # -- terminais ---------------------------------------------------------

    def _terminais(self):
        Device = self.m("devices.Device")
        DeviceActivationRequest = self.m("devices.DeviceActivationRequest")

        if not self.salta("devices.Device"):
            catalogo = [
                ("SN-UROVO-0001", "urovo_i9100_pos", "i9100", "Urovo", "active", "agente1"),
                ("SN-UROVO-0002", "urovo_i9100_pos", "i9100", "Urovo", "active", "agente2"),
                ("SN-SUNMI-0003", "sunmi_v2s_pos", "V2s", "Sunmi", "active", "pos_agent"),
                ("SN-SUNMI-0004", "sunmi_v2s_pos", "V2s", "Sunmi", "pending_activation", None),
                ("SN-MOBILE-0005", "mobile_app", "Redmi Note 12", "Xiaomi", "self_onboarded", None),
                ("SN-UROVO-0006", "urovo_i9100_pos", "i9100", "Urovo", "blocked", None),
            ]
            for i, (serie, tipo, modelo, marca, estado, username) in enumerate(catalogo):
                activo = estado == "active"
                paragem = self.PARAGENS[i % len(self.PARAGENS)]
                d = Device.objects.create(
                    serial_number=serie, device_type=tipo, model_name=modelo,
                    manufacturer=marca, imei=f"35{i:013d}", android_id=secrets.token_hex(8),
                    capabilities=["nfc", "qr", "print"] if "pos" in tipo else ["qr"],
                    status=estado, assigned_agent=self.users.get(username) if username else None,
                    activation_code=f"{100000 + i * 7:06d}",
                    activated_at=self.quando(DIAS - 1, 8, 0) if activo else None,
                    last_seen_at=self.agora - timedelta(minutes=self.rng.randint(1, 40)) if activo else None,
                    app_version="1.4.2" if activo else "1.3.0",
                    app_version_code=142 if activo else 130,
                    configuration={"impressao": True, "moeda": "MZN"},
                    last_latitude=dec(paragem[2]), last_longitude=dec(paragem[3]),
                    last_speed=dec(self.rng.randint(0, 60)), last_heading=dec(self.rng.randint(0, 359)),
                    last_location_at=self.agora - timedelta(minutes=self.rng.randint(1, 30)) if activo else None,
                )
                self.recuar(Device, [d.pk], self.quando(DIAS, 8, 0))
            self.conta("devices.Device")
        self.devices = list(Device.objects.order_by("pk"))

        if not self.salta("devices.DeviceActivationRequest"):
            for i, d in enumerate(self.devices[:3]):
                estado = ["approved", "pending", "rejected"][i]
                pedido = self.quando(DIAS - i, 7, 30)
                r = DeviceActivationRequest.objects.create(
                    device=d, activation_code=d.activation_code,
                    requested_serial_number=d.serial_number,
                    requested_model=d.model_name, requested_manufacturer=d.manufacturer,
                    requested_imei=d.imei, requested_android_id=d.android_id,
                    requested_capabilities=d.capabilities, app_version=d.app_version,
                    status=estado, requested_at=pedido,
                    reviewed_by=self.admin if estado != "pending" else None,
                    reviewed_at=pedido + timedelta(hours=2) if estado != "pending" else None,
                    rejection_reason="Número de série não consta do contrato." if estado == "rejected" else "",
                )
                self.recuar(DeviceActivationRequest, [r.pk], pedido)
            self.conta("devices.DeviceActivationRequest")

    def _sessoes_pos(self):
        PosSession = self.m("pos.PosSession")
        if self.salta("pos.PosSession"):
            self.sessions = list(PosSession.objects.all())
            return
        activos = [d for d in self.devices if d.status == "active"]
        rotas = list(self.routes.values())
        for i in range(6):
            dispositivo = activos[i % len(activos)]
            agente = dispositivo.assigned_agent or self.users.get("pos_agent") or self.admin
            aberta = self.quando(i, 5, 45)
            fechada = None if i == 0 else aberta + timedelta(hours=self.rng.randint(6, 11))
            s = PosSession.objects.create(
                agent=agente, device=dispositivo,
                allocated_route=rotas[i % len(rotas)],
                status="active" if fechada is None else "closed",
                opened_at=aberta, closed_at=fechada,
                metadata={"turno": "manha" if i % 2 == 0 else "tarde"},
            )
            self.recuar(PosSession, [s.pk], aberta)
        self.conta("pos.PosSession")
        self.sessions = list(PosSession.objects.all())

    # -- compras, pagamentos e passes --------------------------------------

    def _compras_e_pagamentos(self):
        GuestCheckout = self.m("guest_checkouts.GuestCheckout")
        DigitalTravelPass = self.m("guest_checkouts.DigitalTravelPass")
        PaymentIntent = self.m("payments.PaymentIntent")
        PaymentCallback = self.m("payments.PaymentCallback")

        semear_compras = not self.salta("guest_checkouts.GuestCheckout")
        semear_intents = not self.salta("payments.PaymentIntent")

        ic1 = self.routes.get("IC1")
        viagens_ic1 = [t for t in self.trips if t.route_id == (ic1.pk if ic1 else None)]
        self.compras = []

        if semear_compras and ic1:
            for i in range(14):
                dia = DIAS - i
                viagem = viagens_ic1[i % len(viagens_ic1)] if viagens_ic1 else None
                quantidade = self.rng.choice([1, 1, 2, 3])
                unitario = dec(1500)
                estado = "issued" if i % 7 else ("payment_pending" if i % 14 == 7 else "expired")
                criada = self.quando(dia, 7 + (i % 8), 20)
                c = GuestCheckout.objects.create(
                    reference=f"GC-2026-{1000 + i}",
                    payer_phone=f"+2588412003{i:02d}",
                    buyer_name=self.NOMES[i % len(self.NOMES)],
                    buyer_email=f"comprador{i}@exemplo.co.mz",
                    emergency_contact_name="Contacto de emergência",
                    emergency_contact_phone=f"+2588412009{i:02d}",
                    passengers=[
                        {"nome": self.NOMES[(i + k) % len(self.NOMES)],
                         "documento": f"1101{i}{k}0000A", "lugar": f"{10 + k}"}
                        for k in range(quantidade)
                    ],
                    route_code=ic1.code, route_name=ic1.name,
                    origin_stop="Baixa", destination_stop="Terminal da Beira",
                    origin_stop_ref=self.stops.get("BAI"), destination_stop_ref=self.stops.get("BEI"),
                    quantity=quantidade, unit_amount=unitario,
                    total_amount=dec(unitario * quantidade),
                    status=estado, trip=viagem,
                    expires_at=criada + timedelta(hours=2),
                    terms_accepted_at=criada if estado != "expired" else None,
                    terms_version="2026-01",
                )
                self.recuar(GuestCheckout, [c.pk], criada)
                self.compras.append((c, criada))
            self.conta("guest_checkouts.GuestCheckout")
        else:
            self.compras = [(c, c.created_at) for c in GuestCheckout.objects.all()]

        # Cada compra paga tem a sua intenção; as recargas de carteira têm as
        # suas. É daqui que sai a receita que o painel mostra.
        intents = []
        if semear_intents:
            for c, criada in self.compras:
                estado = {"issued": "confirmed", "payment_pending": "pending", "expired": "expired"}.get(c.status, "created")
                pi = PaymentIntent.objects.create(
                    reference=f"PI-{c.reference}",
                    idempotency_key=f"idem-{c.reference}",
                    purpose="guest_travel_pass_purchase",
                    amount=c.total_amount, payer_phone=c.payer_phone,
                    provider=self.rng.choice(["mpesa", "emola"]), channel="web",
                    status=estado, guest_checkout=c,
                    provider_reference=f"MP{secrets.token_hex(5).upper()}",
                    expires_at=criada + timedelta(hours=2),
                    confirmed_at=criada + timedelta(minutes=3) if estado == "confirmed" else None,
                    metadata={"origem": "seed_demo", "compra": c.reference},
                )
                self.recuar(PaymentIntent, [pi.pk], criada)
                intents.append((pi, criada))

            for i, carteira in enumerate(self.wallets):
                criada = self.quando(DIAS - i, 8, 10)
                pi = PaymentIntent.objects.create(
                    reference=f"PI-TOPUP-{carteira.pk:03d}",
                    idempotency_key=f"idem-topup-{carteira.pk}",
                    purpose="mobile_wallet_topup",
                    amount=dec(self.rng.choice([100, 200, 500])),
                    payer_phone=carteira.passenger_account.phone_number,
                    provider=self.rng.choice(["mpesa", "emola"]), channel="app",
                    status="confirmed" if i % 6 else "failed", wallet=carteira,
                    provider_reference=f"MP{secrets.token_hex(5).upper()}",
                    confirmed_at=criada + timedelta(minutes=1) if i % 6 else None,
                    metadata={"origem": "seed_demo"},
                )
                self.recuar(PaymentIntent, [pi.pk], criada)
                intents.append((pi, criada))
            self.conta("payments.PaymentIntent")
        else:
            intents = [(pi, pi.created_at) for pi in PaymentIntent.objects.all()]

        if not self.salta("payments.PaymentCallback"):
            for pi, criada in intents:
                if pi.status not in ("confirmed", "failed"):
                    continue
                recebido = criada + timedelta(minutes=2)
                cb = PaymentCallback.objects.create(
                    payment_intent=pi,
                    provider_reference=pi.provider_reference,
                    raw_payload={
                        "reference": pi.reference, "amount": str(pi.amount),
                        "status": "SUCCESS" if pi.status == "confirmed" else "FAILED",
                        "provider": pi.provider,
                    },
                    signature_valid=True,
                    processing_status="processed" if pi.status == "confirmed" else "rejected",
                    received_at=recebido,
                )
                self.recuar(PaymentCallback, [cb.pk], recebido)
            self.conta("payments.PaymentCallback")

        if not self.salta("guest_checkouts.DigitalTravelPass"):
            for c, criada in self.compras:
                if c.status != "issued":
                    continue
                for k, pax in enumerate(c.passengers or [{}]):
                    token = secrets.token_urlsafe(32)
                    usado = self.rng.random() < 0.6
                    p = DigitalTravelPass.objects.create(
                        guest_checkout=c, trip=c.trip,
                        payer_phone=c.payer_phone,
                        route_code=c.route_code, route_name=c.route_name,
                        origin_stop=c.origin_stop, destination_stop=c.destination_stop,
                        origin_stop_ref=c.origin_stop_ref, destination_stop_ref=c.destination_stop_ref,
                        passenger_name=pax.get("nome", c.buyer_name),
                        document_type="bi", document_number=pax.get("documento", ""),
                        seat_number=pax.get("lugar", ""),
                        emergency_contact_name=c.emergency_contact_name,
                        emergency_contact_phone=c.emergency_contact_phone,
                        departure_at=c.trip.planned_departure_at if c.trip else None,
                        fare_amount=c.unit_amount,
                        status="used" if usado else "active",
                        token=token, token_hash=sha(token),
                        short_code=secrets.token_hex(3).upper(),
                        delivery_channel="sms" if k == 0 else "link",
                        valid_from=criada,
                        valid_until=criada + timedelta(days=2),
                        used_at=criada + timedelta(hours=1) if usado else None,
                    )
                    self.recuar(DigitalTravelPass, [p.pk], criada)
            self.conta("guest_checkouts.DigitalTravelPass")
        self.passes = list(DigitalTravelPass.objects.select_related("trip").all())

    # -- validações ---------------------------------------------------------

    def _validacoes(self):
        ValidationEvent = self.m("validations.ValidationEvent")
        if self.salta("validations.ValidationEvent"):
            return
        Card = self.m("cards.Card")
        cartoes = [c for c in Card.objects.filter(status="active") if c.wallet_id]
        activos = [d for d in self.devices if d.status == "active"]
        urbanas = [t for t in self.trips if t.route.service_type == "urban" and t.status in ("completed", "departed")]
        n = 0

        for i, viagem in enumerate(urbanas):
            for k in range(self.rng.randint(2, 6)):
                cartao = cartoes[(i + k) % len(cartoes)] if cartoes else None
                if not cartao:
                    break
                falha = "" if self.rng.random() > 0.12 else self.rng.choice(
                    ["insufficient_balance", "card_blocked", "no_fare_found"])
                instante = (viagem.actual_departure_at or viagem.planned_departure_at) + timedelta(minutes=5 + k * 7)
                if instante > self.agora:
                    continue
                v = ValidationEvent.objects.create(
                    validation_type="card_pay_as_you_go",
                    passenger_account=cartao.passenger_account, wallet=cartao.wallet,
                    physical_card=cartao, route=viagem.route, trip=viagem,
                    origin_stop=self.stops.get(self.ROTAS[i % len(self.ROTAS)][3][0]),
                    device=activos[(i + k) % len(activos)] if activos else None,
                    validated_by=self.admin,
                    amount_debited=dec(0) if falha else dec(self.rng.choice([20, 25, 30])),
                    status="denied" if falha else "approved",
                    failure_reason=falha,
                    idempotency_key=f"val-{viagem.pk}-{k}-{uuid.uuid4().hex[:8]}",
                    wallet_transaction_ref="" if falha else f"FARE-{cartao.wallet_id:03d}",
                )
                self.recuar(ValidationEvent, [v.pk], instante)
                n += 1

        # Passes de convidado: valida-se o passe, não a carteira.
        for p in self.passes:
            if p.status != "used" or not p.trip:
                continue
            instante = p.used_at or self.agora
            if instante > self.agora:
                continue
            v = ValidationEvent.objects.create(
                validation_type="guest_digital_travel_pass",
                digital_travel_pass=p, route=p.trip.route, trip=p.trip,
                origin_stop=p.origin_stop_ref, destination_stop=p.destination_stop_ref,
                device=activos[0] if activos else None, validated_by=self.admin,
                amount_debited=dec(0), status="approved",
                idempotency_key=f"val-pass-{p.pk}-{uuid.uuid4().hex[:8]}",
            )
            self.recuar(ValidationEvent, [v.pk], instante)
            n += 1
        self.feito["validations.ValidationEvent"] = n

    # -- fechos -------------------------------------------------------------

    def _fechos(self):
        TripRevenueClosure = self.m("trips.TripRevenueClosure")
        AgentDayClose = self.m("agent_api.AgentDayClose")
        RecoverySession = self.m("agent_api.RecoverySession")
        ValidationEvent = self.m("validations.ValidationEvent")
        GuestCheckout = self.m("guest_checkouts.GuestCheckout")

        if not self.salta("trips.TripRevenueClosure"):
            for viagem in self.trips_feitas:
                validacoes = ValidationEvent.objects.filter(trip=viagem, status="approved")
                carteira_receita = sum((v.amount_debited for v in validacoes), Decimal("0.00"))
                convidados = GuestCheckout.objects.filter(trip=viagem, status="issued")
                convidado_receita = sum((c.total_amount for c in convidados), Decimal("0.00"))
                total = dec(carteira_receita + convidado_receita)
                f = TripRevenueClosure.objects.create(
                    trip=viagem, route=viagem.route, vehicle=viagem.vehicle,
                    driver=viagem.driver, closed_by=self.admin,
                    opened_at=viagem.activity_started_at,
                    closed_at=viagem.activity_closed_at or viagem.planned_arrival_at,
                    pause_seconds=viagem.pause_seconds,
                    guest_checkout_revenue=dec(convidado_receita),
                    wallet_validation_revenue=dec(carteira_receita),
                    total_revenue=total,
                    summary={"validacoes": validacoes.count(), "bilhetes": convidados.count()},
                    manifest={"lugares_vendidos": convidados.count()},
                    passengers_aboard=validacoes.count() + convidados.count(),
                    passengers_no_show=self.rng.randint(0, 2),
                )
                self.recuar(TripRevenueClosure, [f.pk], f.closed_at or self.agora)
            self.conta("trips.TripRevenueClosure")

        if not self.salta("agent_api.AgentDayClose"):
            agentes_com_conta = [a for a in self.agents if a.user_id]
            for i in range(8):
                agente = agentes_com_conta[i % len(agentes_com_conta)] if agentes_com_conta else None
                if not agente:
                    break
                dia = (self.agora - timedelta(days=i + 1)).date()
                vendas = dec(self.rng.randint(1500, 9000))
                recargas = dec(self.rng.randint(200, 2500))
                validacoes = dec(self.rng.randint(300, 1800))
                fechado = self.quando(i + 1, 19, 30)
                f = AgentDayClose.objects.create(
                    agent_user=agente.user, agent_profile=agente,
                    closed_at=fechado, date=dia,
                    total_revenue=dec(vendas + recargas + validacoes),
                    sales_total=vendas, topups_total=recargas,
                    validations_revenue=validacoes,
                    tickets_count=self.rng.randint(8, 40),
                    validations_count=self.rng.randint(20, 90),
                    confirmed_count=self.rng.randint(20, 60),
                    pending_count=self.rng.randint(0, 3),
                    failed_count=self.rng.randint(0, 2),
                    sessions_closed=1,
                    payload={"origem": "seed_demo"},
                )
                self.recuar(AgentDayClose, [f.pk], fechado)
            self.conta("agent_api.AgentDayClose")

        if not self.salta("agent_api.RecoverySession"):
            agentes_com_conta = [a for a in self.agents if a.user_id]
            for i, p in enumerate(self.passengers[:4]):
                agente = agentes_com_conta[i % len(agentes_com_conta)] if agentes_com_conta else None
                if not agente:
                    break
                estado = ["consumed", "verified", "pending", "expired"][i]
                pedido = self.quando(i + 1, 14, 0)
                codigo = f"{self.rng.randint(100000, 999999)}"
                s = RecoverySession.objects.create(
                    challenge_id=secrets.token_hex(16),
                    agent_user=agente.user, passenger=p, phone=p.phone_number,
                    reason="Cartão perdido — pedido de segunda via.",
                    code_hash=sha(codigo), status=estado,
                    attempts=0 if estado == "pending" else 1,
                    expires_at=pedido + timedelta(minutes=10),
                    verified_at=pedido + timedelta(minutes=2) if estado in ("verified", "consumed") else None,
                    recovery_token=secrets.token_urlsafe(24) if estado in ("verified", "consumed") else "",
                    consumed_at=pedido + timedelta(minutes=5) if estado == "consumed" else None,
                )
                self.recuar(RecoverySession, [s.pk], pedido)
            self.conta("agent_api.RecoverySession")

    # -- APKs ---------------------------------------------------------------

    def _apks(self):
        AppRelease = self.m("app_releases.AppRelease")
        DeviceAppUpdate = self.m("app_releases.DeviceAppUpdate")

        if not self.salta("app_releases.AppRelease"):
            versoes = [
                ("pos", "1.3.0", 130, "published", False, "Primeira versão estável do POS."),
                ("pos", "1.4.2", 142, "published", True, "Correcção da validação NFC offline."),
                ("passenger", "0.9.0", 90, "published", False, "Compra e carteira no telemóvel."),
                ("passenger", "1.0.0", 100, "draft", False, "Passes digitais e histórico."),
            ]
            for i, (tipo, nome, codigo, estado, obrigatoria, notas) in enumerate(versoes):
                publicada = self.quando(DIAS - i * 5, 12, 0) if estado == "published" else None
                r = AppRelease.objects.create(
                    app_type=tipo, version_name=nome, version_code=codigo,
                    apk_url=f"https://apps.updigital.co.mz/busup-{tipo}-{nome}.apk",
                    checksum=sha(f"{tipo}-{nome}")[:64],
                    release_notes=notas, is_mandatory=obrigatoria,
                    min_supported_version_code=codigo - 20,
                    status=estado, published_at=publicada, created_by=self.admin,
                )
                self.recuar(AppRelease, [r.pk], publicada or self.quando(1, 12, 0))
            self.conta("app_releases.AppRelease")
        self.releases = list(AppRelease.objects.filter(status="published").order_by("pk"))

        if not self.salta("app_releases.DeviceAppUpdate"):
            alvo = next((r for r in self.releases if r.app_type == "pos" and r.version_code == 142), None)
            if alvo:
                estados = ["installed", "installed", "downloading", "prompted", "deferred", "failed"]
                for i, d in enumerate(self.devices):
                    estado = estados[i % len(estados)]
                    quando = self.quando(i, 8, 30)
                    u = DeviceAppUpdate.objects.create(
                        device=d, app_release=alvo,
                        current_version_code=d.app_version_code,
                        target_version_code=alvo.version_code, status=estado,
                        prompted_at=quando,
                        deferred_until=quando + timedelta(days=1) if estado == "deferred" else None,
                        downloaded_at=quando + timedelta(minutes=4) if estado in ("installed", "downloading") else None,
                        installed_at=quando + timedelta(minutes=9) if estado == "installed" else None,
                        failed_reason="Espaço insuficiente no dispositivo." if estado == "failed" else "",
                    )
                    self.recuar(DeviceAppUpdate, [u.pk], quando)
            self.conta("app_releases.DeviceAppUpdate")

    # -- avisos, pedidos e OTP ---------------------------------------------

    def _avisos_e_pedidos(self):
        Notification = self.m("notifications.Notification")
        ServiceRequest = self.m("leads.ServiceRequest")
        SmsBroadcast = self.m("sms.SmsBroadcast")
        OtpChallenge = self.m("users.OtpChallenge")

        if not self.salta("notifications.Notification"):
            modelos = [
                ("payment_confirmed", "Pagamento confirmado", "A recarga de 250,00 MZN entrou na carteira."),
                ("ticket_issued", "Bilhete emitido", "O bilhete Maputo — Beira está disponível."),
                ("trip_update", "Partida atrasada", "A partida das 06:30 sai com 15 minutos de atraso."),
                ("card_update", "Cartão activado", "O cartão NFC 0042 1187 ficou activo."),
                ("payment_failed", "Pagamento falhado", "A recarga de 500,00 MZN não foi concluída."),
            ]
            destinatarios = [u for u in self.users.values()][:4] or [self.admin]
            for i in range(14):
                tipo, titulo, corpo = modelos[i % len(modelos)]
                quando = self.quando(i % DIAS, 10 + (i % 8), 0)
                n = Notification.objects.create(
                    user=destinatarios[i % len(destinatarios)],
                    kind=tipo, title=titulo, body=corpo,
                    data={"origem": "seed_demo", "indice": i},
                    read_at=quando + timedelta(hours=1) if i % 3 else None,
                )
                self.recuar(Notification, [n.pk], quando)
            self.conta("notifications.Notification")

        if not self.salta("leads.ServiceRequest"):
            pedidos = [
                ("Amâncio Zavala", "Transportes Zavala", "operator", "12", "new"),
                ("Direcção Escolar", "Escola Portuguesa", "school", "4", "contacted"),
                ("Lúcia Mahumane", "Grupo Chuabo", "company", "30", "qualified"),
                ("Nuno Bila", "TPM-TUR", "operator", "48", "closed"),
                ("Aida Manjate", "Colégio Kitabu", "school", "6", "new"),
                ("Óscar Timane", "", "other", "", "new"),
                ("Bernardo Sitoe", "Rodoviária do Sul", "operator", "20", "contacted"),
                ("Célia Guilundo", "Mozal", "company", "15", "qualified"),
            ]
            for i, (nome, empresa, interesse, frota, estado) in enumerate(pedidos):
                quando = self.quando(i * 2, 11, 20)
                r = ServiceRequest.objects.create(
                    name=nome, organization=empresa,
                    phone=f"+2588412004{i:02d}",
                    email=f"pedido{i}@exemplo.co.mz",
                    interest=interesse, fleet_size=frota,
                    message="Gostaríamos de ver a plataforma a operar com as nossas rotas.",
                    status=estado, source="landing" if i % 2 else "contactos",
                )
                self.recuar(ServiceRequest, [r.pk], quando)
            self.conta("leads.ServiceRequest")

        if not self.salta("sms.SmsBroadcast"):
            for i in range(3):
                viagem = self.trips_feitas[i] if i < len(self.trips_feitas) else None
                enviados = self.rng.randint(20, 90)
                quando = self.quando(i + 1, 6, 45)
                b = SmsBroadcast.objects.create(
                    scope="trip" if viagem else "route",
                    trip=viagem, route=None if viagem else list(self.routes.values())[i],
                    body="A partida de hoje sai com 15 minutos de atraso. Pedimos desculpa.",
                    recipients=enviados + 2, sent=enviados, failed=2,
                    sent_by=self.admin,
                )
                SmsBroadcast.objects.filter(pk=b.pk).update(created_at=quando)
            self.conta("sms.SmsBroadcast")

        if not self.salta("users.OtpChallenge"):
            for i, p in enumerate(self.passengers[:5]):
                estado = ["verified", "verified", "pending", "expired", "verified"][i]
                quando = self.quando(i, 15, 0)
                codigo = f"{self.rng.randint(100000, 999999)}"
                d = OtpChallenge.objects.create(
                    phone=p.phone_number, code_hash=sha(codigo), status=estado,
                    expires_at=quando + timedelta(minutes=5),
                    attempts=1 if estado == "verified" else 0,
                    verified_at=quando + timedelta(minutes=1) if estado == "verified" else None,
                )
                self.recuar(OtpChallenge, [d.pk], quando)
            self.conta("users.OtpChallenge")

    # -- sessões terminadas -------------------------------------------------

    def _tokens_revogados(self):
        """Uma sessão terminada, para a lista negra de tokens não ficar vazia.

        Revoga-se um token emitido AQUI, para um utilizador de apoio: revogar um
        dos tokens vivos punha fora quem estivesse com sessão aberta.
        """
        if self.salta("token_blacklist.BlacklistedToken"):
            return
        try:
            from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
            from rest_framework_simplejwt.tokens import RefreshToken
        except ImportError:
            self.feito["token_blacklist.BlacklistedToken"] = "simplejwt ausente"
            return
        utilizador = self.users.get("agente1") or self.admin
        refresh = RefreshToken.for_user(utilizador)
        emitido = OutstandingToken.objects.filter(jti=refresh["jti"]).first()
        if not emitido:
            emitido = OutstandingToken.objects.create(
                user=utilizador, jti=refresh["jti"], token=str(refresh),
                created_at=self.quando(1, 8, 0),
                expires_at=self.agora + timedelta(days=1),
            )
        BlacklistedToken.objects.get_or_create(token=emitido)
        self.conta("token_blacklist.BlacklistedToken")

    # -- agendamentos do CMS ------------------------------------------------

    def _agenda_cms(self):
        ScheduledPublication = self.m("cms.ScheduledPublication")
        if self.salta("cms.ScheduledPublication"):
            return
        Page = self.m("cms.Page")
        paginas = list(Page.objects.order_by("pk")[:2])
        for i, pagina in enumerate(paginas):
            s = ScheduledPublication.objects.create(
                target_type="page", target_id=pagina.pk,
                run_at=self.agora + timedelta(days=i + 1, hours=3),
                status="scheduled", created_by=self.admin,
            )
            self.recuar(ScheduledPublication, [s.pk], self.quando(1, 9, 0))
        if paginas:
            s = ScheduledPublication.objects.create(
                target_type="page", target_id=paginas[0].pk,
                run_at=self.quando(2, 9, 0), status="done",
                created_by=self.admin, result="Publicado pelo agendador.",
            )
            self.recuar(ScheduledPublication, [s.pk], self.quando(3, 9, 0))
        self.conta("cms.ScheduledPublication")
