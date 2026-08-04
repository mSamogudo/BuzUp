"""Ciclo da viagem: embarque, partida, manifesto e fecho trancado.

O que estes testes protegem, por ordem de gravidade:

* A hora de partida tem de ser a hora a que o autocarro saiu, nao a hora a que
  abriu as portas no terminal.
* O manifesto tem de crescer com os embarques ao longo do percurso.
* Depois do fecho, o manifesto NAO pode mudar — e o documento que vale numa
  fiscalizacao ou num sinistro.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.activity import (
    close_trip_activity,
    depart_trip_activity,
    resume_trip_activity,
    pause_trip_activity,
    start_trip_activity,
    TripActivityError,
)
from apps.trips.manifest import build_manifest
from apps.trips.models import Driver, Trip, Vehicle


class TripCycleBase(TestCase):
    def setUp(self):
        self.route = Route.objects.create(code="R-MAN", name="Rota Manifesto",
                                          status=Route.Status.ACTIVE)
        self.origem = Stop.objects.create(code="ST-O", name="Terminal", status="active")
        self.destino = Stop.objects.create(code="ST-D", name="Destino", status="active")
        RouteStop.objects.create(route=self.route, stop=self.origem, sequence=1, direction="outbound")
        RouteStop.objects.create(route=self.route, stop=self.destino, sequence=2, direction="outbound")

        User = get_user_model()
        self.user = User.objects.create_user(username="mot_man", password="x", phone="849000001", email="mot_man@x.mz")
        self.driver = Driver.objects.create(full_name="Motorista Manifesto",
                                            user=self.user, status=Driver.Status.ACTIVE)
        self.vehicle = Vehicle.objects.create(registration="MAN-01-MP", seated_capacity=30)
        self.trip = Trip.objects.create(
            route=self.route, vehicle=self.vehicle, driver=self.driver,
            status=Trip.Status.SCHEDULED,
            planned_departure_at=timezone.now() + timedelta(hours=1),
        )

    def _emitir_bilhete(self, *, nome, lugar, usado=False):
        gc = GuestCheckout.objects.create(
            reference=f"AS-{nome[:6].upper()}{lugar}", payer_phone="841000000",
            route_code=self.route.code, route_name=self.route.name,
            origin_stop=self.origem.name, destination_stop=self.destino.name,
            quantity=1, unit_amount=Decimal("500.00"), total_amount=Decimal("500.00"),
            status=GuestCheckout.Status.ISSUED, trip=self.trip,
        )
        raw, token_hash = DigitalTravelPass.generate_token()
        return DigitalTravelPass.objects.create(
            guest_checkout=gc, payer_phone="841000000",
            route_code=self.route.code, route_name=self.route.name,
            origin_stop=self.origem.name, destination_stop=self.destino.name,
            trip=self.trip, passenger_name=nome, seat_number=lugar,
            fare_amount=Decimal("500.00"), token=raw, token_hash=token_hash,
            status=(DigitalTravelPass.Status.USED if usado
                    else DigitalTravelPass.Status.ACTIVE),
            used_at=timezone.now() if usado else None,
            valid_until=timezone.now() + timedelta(hours=12),
        )

    def _client(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.user).access_token}")
        return c


class EmbarqueEPartidaTests(TripCycleBase):
    def test_abrir_embarque_nao_marca_a_hora_de_partida(self):
        """O autocarro esta parado no terminal a encher — nao partiu."""
        trip = start_trip_activity(self.trip, self.driver, self.user)
        self.assertEqual(trip.status, Trip.Status.BOARDING)
        self.assertIsNotNone(trip.activity_started_at)
        self.assertIsNone(trip.actual_departure_at,
                          "abrir o embarque marcou uma partida que nao aconteceu")

    def test_partida_marca_a_hora_e_poe_em_viagem(self):
        start_trip_activity(self.trip, self.driver, self.user)
        trip = depart_trip_activity(Trip.objects.get(pk=self.trip.pk), self.driver, self.user)
        self.assertEqual(trip.status, Trip.Status.DEPARTED)
        self.assertIsNotNone(trip.actual_departure_at)

    def test_nao_se_pode_partir_sem_abrir_o_embarque(self):
        with self.assertRaises(TripActivityError):
            depart_trip_activity(self.trip, self.driver, self.user)

    def test_nao_se_parte_duas_vezes(self):
        start_trip_activity(self.trip, self.driver, self.user)
        depart_trip_activity(Trip.objects.get(pk=self.trip.pk), self.driver, self.user)
        with self.assertRaises(TripActivityError):
            depart_trip_activity(Trip.objects.get(pk=self.trip.pk), self.driver, self.user)

    def test_retomar_devolve_a_em_viagem_e_nao_a_embarque(self):
        """Uma paragem a meio da estrada nao volta ao terminal."""
        start_trip_activity(self.trip, self.driver, self.user)
        depart_trip_activity(Trip.objects.get(pk=self.trip.pk), self.driver, self.user)
        pause_trip_activity(Trip.objects.get(pk=self.trip.pk), self.driver, self.user)
        trip = resume_trip_activity(Trip.objects.get(pk=self.trip.pk), self.driver, self.user)
        self.assertEqual(trip.status, Trip.Status.DEPARTED)

    def test_retomar_antes_de_partir_volta_ao_embarque(self):
        start_trip_activity(self.trip, self.driver, self.user)
        pause_trip_activity(Trip.objects.get(pk=self.trip.pk), self.driver, self.user)
        trip = resume_trip_activity(Trip.objects.get(pk=self.trip.pk), self.driver, self.user)
        self.assertEqual(trip.status, Trip.Status.BOARDING)


class ManifestoTests(TripCycleBase):
    def test_bilhete_por_validar_conta_como_esperado(self):
        self._emitir_bilhete(nome="Ana Sitoe", lugar="1A")
        m = build_manifest(self.trip)
        self.assertEqual(m["totals"]["expected"], 1)
        self.assertEqual(m["totals"]["aboard"], 0)
        self.assertEqual(m["entries"][0]["passenger_name"], "Ana Sitoe")
        self.assertEqual(m["entries"][0]["seat"], "1A")

    def test_bilhete_validado_passa_a_bordo(self):
        self._emitir_bilhete(nome="Ana Sitoe", lugar="1A", usado=True)
        m = build_manifest(self.trip)
        self.assertEqual(m["totals"]["aboard"], 1)
        self.assertEqual(m["totals"]["expected"], 0)
        self.assertEqual(m["entries"][0]["boarding"], "aboard")

    def test_manifesto_cresce_quando_alguem_embarca_numa_paragem(self):
        """O caso que faz a lista crescer ao longo do percurso."""
        self._emitir_bilhete(nome="Ana Sitoe", lugar="1A", usado=True)
        start_trip_activity(self.trip, self.driver, self.user)
        depart_trip_activity(Trip.objects.get(pk=self.trip.pk), self.driver, self.user)
        antes = build_manifest(Trip.objects.get(pk=self.trip.pk))["totals"]["aboard"]

        from apps.validations.models import ValidationEvent
        ValidationEvent.objects.create(
            validation_type=ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO,
            status=ValidationEvent.Status.APPROVED, route=self.route,
            trip=Trip.objects.get(pk=self.trip.pk), origin_stop=self.origem,
            amount_debited=Decimal("50.00"), idempotency_key="paragem-1",
        )
        depois = build_manifest(Trip.objects.get(pk=self.trip.pk))
        self.assertEqual(depois["totals"]["aboard"], antes + 1,
                         "quem embarcou na paragem nao entrou no manifesto")
        canais = {e["channel"] for e in depois["entries"]}
        self.assertIn("card", canais)

    def test_bilhete_cancelado_fica_de_fora(self):
        tp = self._emitir_bilhete(nome="Ana Sitoe", lugar="1A")
        tp.status = DigitalTravelPass.Status.CANCELLED
        tp.save(update_fields=["status"])
        self.assertEqual(build_manifest(self.trip)["totals"]["total"], 0)

    def test_lugares_ordenam_por_numero_e_nao_por_texto(self):
        for lugar in ("10A", "2A", "1A"):
            self._emitir_bilhete(nome=f"P{lugar}", lugar=lugar)
        lugares = [e["seat"] for e in build_manifest(self.trip)["entries"]]
        self.assertEqual(lugares, ["1A", "2A", "10A"])

    def test_no_fecho_quem_nunca_validou_conta_como_falta(self):
        self._emitir_bilhete(nome="Faltou", lugar="1A")
        m = build_manifest(self.trip, final=True)
        self.assertEqual(m["totals"]["no_show"], 1)
        self.assertEqual(m["totals"]["aboard"], 0)


class FechoTrancadoTests(TripCycleBase):
    def test_fecho_guarda_o_manifesto_e_conta_passageiros(self):
        self._emitir_bilhete(nome="A bordo", lugar="1A", usado=True)
        self._emitir_bilhete(nome="Faltou", lugar="2A")
        start_trip_activity(self.trip, self.driver, self.user)
        depart_trip_activity(Trip.objects.get(pk=self.trip.pk), self.driver, self.user)
        trip = close_trip_activity(Trip.objects.get(pk=self.trip.pk), self.driver, self.user)

        closure = trip.revenue_closure
        self.assertEqual(closure.passengers_aboard, 1)
        self.assertEqual(closure.passengers_no_show, 1)
        self.assertTrue(closure.manifest, "o manifesto nao foi guardado no fecho")
        self.assertEqual(len(closure.manifest["entries"]), 2)
        self.assertTrue(closure.manifest["final"])

    def test_manifesto_guardado_nao_muda_se_um_bilhete_for_cancelado_depois(self):
        """O caso que justifica guardar em vez de recalcular."""
        tp = self._emitir_bilhete(nome="A bordo", lugar="1A", usado=True)
        start_trip_activity(self.trip, self.driver, self.user)
        depart_trip_activity(Trip.objects.get(pk=self.trip.pk), self.driver, self.user)
        trip = close_trip_activity(Trip.objects.get(pk=self.trip.pk), self.driver, self.user)
        antes = trip.revenue_closure.manifest["totals"]["aboard"]

        tp.status = DigitalTravelPass.Status.CANCELLED
        tp.save(update_fields=["status"])

        trip.revenue_closure.refresh_from_db()
        self.assertEqual(trip.revenue_closure.manifest["totals"]["aboard"], antes,
                         "cancelar um bilhete mudou a lista de quem ja viajou")

    def test_endpoint_devolve_a_fotografia_depois_do_fecho(self):
        tp = self._emitir_bilhete(nome="A bordo", lugar="1A", usado=True)
        start_trip_activity(self.trip, self.driver, self.user)
        depart_trip_activity(Trip.objects.get(pk=self.trip.pk), self.driver, self.user)
        close_trip_activity(Trip.objects.get(pk=self.trip.pk), self.driver, self.user)

        tp.status = DigitalTravelPass.Status.CANCELLED
        tp.save(update_fields=["status"])

        res = self._client().get(f"/api/driver/trips/{self.trip.pk}/manifest/")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["totals"]["aboard"], 1)


class ManifestoAcessoTests(TripCycleBase):
    def test_motorista_nao_ve_o_manifesto_de_viagem_alheia(self):
        """O manifesto tem nomes e documentos: nao pode vazar."""
        User = get_user_model()
        outro_user = User.objects.create_user(username="mot_outro", password="x", phone="849000002", email="mot_outro@x.mz")
        outro = Driver.objects.create(full_name="Outro", user=outro_user,
                                      status=Driver.Status.ACTIVE)
        alheia = Trip.objects.create(route=self.route, vehicle=self.vehicle, driver=outro,
                                     status=Trip.Status.BOARDING,
                                     planned_departure_at=timezone.now())
        res = self._client().get(f"/api/driver/trips/{alheia.pk}/manifest/")
        self.assertEqual(res.status_code, 404)

    def test_manifesto_exige_autenticacao(self):
        res = APIClient().get(f"/api/driver/trips/{self.trip.pk}/manifest/")
        self.assertIn(res.status_code, (401, 403))


class ManifestoPdfTests(TripCycleBase):
    def test_pdf_sai_com_os_passageiros(self):
        self._emitir_bilhete(nome="Ana Sitoe", lugar="1A", usado=True)
        from apps.trips.manifest_pdf import render_manifest_pdf

        pdf = render_manifest_pdf(build_manifest(self.trip))
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)

    def test_pdf_de_viagem_vazia_nao_rebenta(self):
        from apps.trips.manifest_pdf import render_manifest_pdf

        pdf = render_manifest_pdf(build_manifest(self.trip))
        self.assertTrue(pdf.startswith(b"%PDF"))


class FormaDePagamentoTests(TripCycleBase):
    """O manifesto tem de dizer COMO foi pago, nao so onde foi comprado.

    E isso que separa o que o motorista recebeu em mao (carteira movel) do
    que ja estava cobrado (cartao, saldo) quando faz a declaracao de receita.
    """

    def _com_pagamento(self, *, nome, lugar, provider, channel="", usado=True):
        tp = self._emitir_bilhete(nome=nome, lugar=lugar, usado=usado)
        from apps.payments.models import PaymentIntent
        PaymentIntent.objects.create(
            reference=f"PAY-{nome[:8]}{lugar}", idempotency_key=f"idem-{nome}{lugar}",
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
            amount=Decimal("500.00"), payer_phone="841000000",
            guest_checkout=tp.guest_checkout, provider=provider, channel=channel,
            status=PaymentIntent.Status.CONFIRMED,
        )
        return tp

    def test_mpesa_e_emola_aparecem_como_carteira_movel(self):
        self._com_pagamento(nome="Por MPesa", lugar="1A", provider="MPESA")
        self._com_pagamento(nome="Por eMola", lugar="1B", provider="EMOLA")
        metodos = {e["payment_method"] for e in build_manifest(self.trip)["entries"]}
        self.assertEqual(metodos, {"mpesa", "emola"})

    def test_venda_no_pos_com_cartao_aparece_como_cartao(self):
        self._com_pagamento(nome="Por Cartao", lugar="1A",
                            provider="wallet", channel="POS_CARD")
        e = build_manifest(self.trip)["entries"][0]
        self.assertEqual(e["payment_method"], "card")
        self.assertEqual(e["payment_label"], "Cartao")

    def test_compra_na_app_sem_checkout_conta_como_saldo(self):
        raw, token_hash = DigitalTravelPass.generate_token()
        DigitalTravelPass.objects.create(
            payer_phone="841000000", route_code=self.route.code,
            route_name=self.route.name, origin_stop=self.origem.name,
            destination_stop=self.destino.name, trip=self.trip,
            passenger_name="Na App", seat_number="2A",
            fare_amount=Decimal("500.00"), token=raw, token_hash=token_hash,
            status=DigitalTravelPass.Status.USED, used_at=timezone.now(),
            valid_until=timezone.now() + timedelta(hours=12),
        )
        e = build_manifest(self.trip)["entries"][0]
        self.assertEqual(e["payment_method"], "wallet")

    def test_totais_repartem_o_dinheiro_por_forma_de_pagamento(self):
        self._com_pagamento(nome="Por MPesa", lugar="1A", provider="MPESA")
        self._com_pagamento(nome="Outro MPesa", lugar="1B", provider="MPESA")
        self._com_pagamento(nome="Por Cartao", lugar="1C",
                            provider="wallet", channel="POS_CARD")
        reparticao = {r["method"]: r for r in build_manifest(self.trip)["totals"]["by_payment"]}
        self.assertEqual(reparticao["mpesa"]["count"], 2)
        self.assertEqual(reparticao["mpesa"]["amount"], "1000.00")
        self.assertEqual(reparticao["card"]["count"], 1)
        self.assertEqual(reparticao["card"]["amount"], "500.00")

    def test_quem_faltou_nao_entra_na_conta_do_dinheiro(self):
        """Um bilhete que ninguem usou nao e receita daquela viagem."""
        self._com_pagamento(nome="Faltou", lugar="1A", provider="MPESA", usado=False)
        totais = build_manifest(self.trip, final=True)["totals"]
        self.assertEqual(totais["no_show"], 1)
        self.assertEqual(totais["by_payment"], [])

    def test_validacao_por_cartao_numa_paragem_conta_como_cartao(self):
        from apps.validations.models import ValidationEvent
        ValidationEvent.objects.create(
            validation_type=ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO,
            status=ValidationEvent.Status.APPROVED, route=self.route,
            trip=self.trip, amount_debited=Decimal("50.00"),
            idempotency_key="paragem-cartao",
        )
        e = build_manifest(self.trip)["entries"][0]
        self.assertEqual(e["payment_method"], "card")


class ContactoDeEmergenciaTests(TripCycleBase):
    """So as rotas com manifesto pedem contacto de emergencia.

    Numa carreira urbana ninguem da o numero da mae para apanhar o autocarro
    do bairro — e guardar dados de terceiros que nao vao ser usados e recolha
    a mais.
    """

    _seq = 0

    def _rota(self, service_type):
        type(self)._seq += 1
        r = Route.objects.create(code=f"R-{service_type[:4].upper()}{self._seq}",
                                 name=f"Rota {service_type}",
                                 service_type=service_type, status=Route.Status.ACTIVE)
        RouteStop.objects.create(route=r, stop=self.origem, sequence=1, direction="outbound")
        RouteStop.objects.create(route=r, stop=self.destino, sequence=2, direction="outbound")
        return r

    def test_interprovincial_e_internacional_pedem_manifesto(self):
        self.assertTrue(self._rota("interprovincial").requires_manifest)
        self.assertTrue(self._rota("international").requires_manifest)

    def test_urbana_nao_pede_manifesto_formal(self):
        self.assertFalse(self._rota("urban").requires_manifest)
        self.assertFalse(self._rota("urban").requires_emergency_contact)

    def test_manifesto_diz_se_e_formal(self):
        self.route.service_type = "interprovincial"
        self.route.save(update_fields=["service_type"])
        self.assertTrue(build_manifest(Trip.objects.get(pk=self.trip.pk))["formal"])

        self.route.service_type = "urban"
        self.route.save(update_fields=["service_type"])
        self.assertFalse(build_manifest(Trip.objects.get(pk=self.trip.pk))["formal"])

    def test_contacto_de_emergencia_sai_no_manifesto(self):
        tp = self._emitir_bilhete(nome="Ana Sitoe", lugar="1A", usado=True)
        tp.emergency_contact_name = "Maria Sitoe"
        tp.emergency_contact_phone = "848000000"
        tp.save(update_fields=["emergency_contact_name", "emergency_contact_phone"])
        e = build_manifest(self.trip)["entries"][0]
        self.assertEqual(e["emergency_name"], "Maria Sitoe")
        self.assertEqual(e["emergency_phone"], "848000000")
        self.assertEqual(e["phone"], "841000000")

    def test_pdf_formal_leva_colunas_de_contacto(self):
        from apps.trips.manifest_pdf import COLUMNS_FORMAL, COLUMNS_SIMPLE

        chaves_formal = {c[0] for c in COLUMNS_FORMAL}
        self.assertIn("phone", chaves_formal)
        self.assertIn("emergency", chaves_formal)
        self.assertNotIn("emergency", {c[0] for c in COLUMNS_SIMPLE})

    def test_pdf_sai_nas_duas_variantes(self):
        from apps.trips.manifest_pdf import render_manifest_pdf

        self._emitir_bilhete(nome="Ana Sitoe", lugar="1A", usado=True)
        for tipo in ("interprovincial", "urban"):
            self.route.service_type = tipo
            self.route.save(update_fields=["service_type"])
            m = build_manifest(Trip.objects.get(pk=self.trip.pk))
            self.assertTrue(render_manifest_pdf(m).startswith(b"%PDF"), tipo)


class CompraExigeContactoTests(TripCycleBase):
    def _passageiro(self):
        from apps.passengers.models import PassengerAccount
        from apps.wallets.models import Wallet

        pa = PassengerAccount.objects.create(full_name="Compradora",
                                             phone_number="258849111222",
                                             status=PassengerAccount.Status.ACTIVE)
        Wallet.objects.create(passenger_account=pa, balance_cached=Decimal("5000.00"),
                              status=Wallet.Status.ACTIVE)
        return pa

    def _tarifa(self, route):
        from apps.fares.models import FareProduct, FareRule
        produto = FareProduct.objects.create(name=f"Avulso {route.code}",
                                             product_type="single_trip", status="active")
        FareRule.objects.create(fare_product=produto, route=route,
                                calculation_method=FareRule.CalculationMethod.FIXED,
                                fixed_amount=Decimal("500.00"))

    def test_interprovincial_recusa_compra_sem_contacto(self):
        from apps.guest_checkouts.purchase import PurchaseError, purchase_travel_pass

        self.route.service_type = "interprovincial"
        self.route.save(update_fields=["service_type"])
        self._tarifa(self.route)
        self.trip.status = Trip.Status.BOARDING
        self.trip.save(update_fields=["status"])

        with self.assertRaises(PurchaseError) as ctx:
            purchase_travel_pass(
                self._passageiro(), route_id=self.route.id,
                origin_stop_id=self.origem.id, destination_stop_id=self.destino.id,
                trip_id=self.trip.id, seat="1A",
            )
        self.assertIn("emergencia", str(ctx.exception).lower())

    def test_urbana_nao_guarda_contacto_mesmo_que_venha(self):
        from apps.guest_checkouts.purchase import purchase_travel_pass

        self._tarifa(self.route)      # a rota base e urbana
        tp = purchase_travel_pass(
            self._passageiro(), route_id=self.route.id,
            origin_stop_id=self.origem.id, destination_stop_id=self.destino.id,
            emergency_contact_name="Nao Pedido", emergency_contact_phone="840000000",
        )
        self.assertEqual(tp.emergency_contact_phone, "",
                         "guardou contacto de terceiro numa rota que nao o pede")
