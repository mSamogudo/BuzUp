"""Avisar por SMS quem vai a bordo — e so quem vai a bordo.

O caso: o autocarro avaria na estrada e e preciso avisar os passageiros
daquela partida. O risco: escrever a toda a gente que alguma vez comprou um
bilhete naquela carreira. Sao mensagens pagas, uma a uma, e chegam a
telemoveis de pessoas reais.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.routes.models import Route
from apps.sms.models import SmsBroadcast, SmsMessage
from apps.trips.models import Trip, Vehicle
from apps.users.models import Role, UserRole


class BroadcastTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(username="chefe", password="x", email="c@x.mz")
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

        self.rota = Route.objects.create(
            code="RT-INT", name="Maputo x Nelspruit",
            service_type=Route.ServiceType.INTERNATIONAL, status=Route.Status.ACTIVE)
        self.viatura = Vehicle.objects.create(registration="AAA-01-MP", seated_capacity=52)
        self.viagem = Trip.objects.create(
            route=self.rota, vehicle=self.viatura, status=Trip.Status.DEPARTED,
            planned_departure_at=timezone.now() - timedelta(hours=1))
        self.viagem_antiga = Trip.objects.create(
            route=self.rota, vehicle=self.viatura, status=Trip.Status.COMPLETED,
            planned_departure_at=timezone.now() - timedelta(days=30))

    def _bilhete(self, telefone, viagem, estado=DigitalTravelPass.Status.ACTIVE, nome="Passageiro"):
        gc = GuestCheckout.objects.create(
            reference=f"GC-{telefone}-{viagem.id}-{estado}-{GuestCheckout.objects.count()}",
            payer_phone=telefone,
            origin_stop="A", destination_stop="B", quantity=1,
            unit_amount=Decimal("100.00"), total_amount=Decimal("100.00"),
            status=GuestCheckout.Status.ISSUED)
        raw, token_hash = DigitalTravelPass.generate_token()
        return DigitalTravelPass.objects.create(
            guest_checkout=gc, trip=viagem, payer_phone=telefone, passenger_name=nome,
            origin_stop="A", destination_stop="B", fare_amount=Decimal("100.00"),
            token=raw, token_hash=token_hash, status=estado,
            valid_from=timezone.now(), valid_until=timezone.now() + timedelta(days=1))

    def avisar(self, **corpo):
        return self.client.post("/api/admin/broadcasts/", corpo, format="json")

    # --- quem entra ----------------------------------------------------

    def test_bilhete_activo_recebe(self):
        """Comprou e ainda nao embarcou: e quem vai apanhar aquela partida."""
        self._bilhete("841000001", self.viagem)
        r = self.avisar(trip_id=self.viagem.id, preview=True)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["recipients"], 1)

    def test_bilhete_ja_validado_recebe(self):
        """Esta a bordo — e precisamente quem mais precisa de saber."""
        self._bilhete("841000002", self.viagem, DigitalTravelPass.Status.USED)
        self.assertEqual(self.avisar(trip_id=self.viagem.id, preview=True).json()["recipients"], 1)

    # --- quem fica de fora ---------------------------------------------

    def test_bilhete_cancelado_nao_recebe(self):
        self._bilhete("841000003", self.viagem, DigitalTravelPass.Status.CANCELLED)
        self.assertEqual(self.avisar(trip_id=self.viagem.id, preview=True).json()["recipients"], 0)

    def test_bilhete_reembolsado_nao_recebe(self):
        self._bilhete("841000004", self.viagem, DigitalTravelPass.Status.REFUNDED)
        self.assertEqual(self.avisar(trip_id=self.viagem.id, preview=True).json()["recipients"], 0)

    def test_viagem_ja_concluida_nao_recebe(self):
        """Quem viajou o mes passado ja esta em casa: avisa-lo e spam."""
        self._bilhete("841000005", self.viagem_antiga, DigitalTravelPass.Status.USED)
        self.assertEqual(self.avisar(route_id=self.rota.id, preview=True).json()["recipients"], 0)

    def test_avisar_a_rota_apanha_so_quem_esta_a_viajar(self):
        self._bilhete("841000006", self.viagem)
        self._bilhete("841000007", self.viagem_antiga, DigitalTravelPass.Status.USED)
        self.assertEqual(self.avisar(route_id=self.rota.id, preview=True).json()["recipients"], 1)

    # --- forma ----------------------------------------------------------

    def test_familia_com_um_telemovel_recebe_um_sms(self):
        """Tres bilhetes, um numero: tres mensagens seria cobrar tres vezes."""
        for i in range(3):
            self._bilhete("841000008", self.viagem, nome=f"Passageiro {i}")
        previa = self.avisar(trip_id=self.viagem.id, preview=True).json()
        self.assertEqual(previa["recipients"], 1)
        self.assertEqual(previa["sample"][0]["passes"], 3)

    def test_a_previa_nao_mostra_o_numero_completo(self):
        self._bilhete("841234567", self.viagem)
        previa = self.avisar(trip_id=self.viagem.id, preview=True).json()
        self.assertEqual(previa["sample"][0]["phone"], "***4567")

    def test_a_previa_conta_os_segmentos(self):
        self._bilhete("841000009", self.viagem)
        previa = self.avisar(trip_id=self.viagem.id, preview=True, body="a" * 200).json()
        self.assertEqual(previa["segments"], 2)
        self.assertEqual(previa["messages"], 2)

    def test_a_previa_nao_envia_nada(self):
        self._bilhete("841000010", self.viagem)
        self.avisar(trip_id=self.viagem.id, preview=True, body="teste")
        self.assertEqual(SmsMessage.objects.count(), 0)
        self.assertEqual(SmsBroadcast.objects.count(), 0)

    # --- envio ----------------------------------------------------------

    def test_envio_regista_quem_enviou_e_a_quem(self):
        self._bilhete("841000011", self.viagem)
        self._bilhete("841000012", self.viagem)
        r = self.avisar(trip_id=self.viagem.id, body="Avaria. Seguimos as 14h.")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["recipients"], 2)

        registo = SmsBroadcast.objects.get()
        self.assertEqual(registo.sent_by_id, self.admin.id)
        self.assertEqual(registo.recipients, 2)
        self.assertEqual(registo.body, "Avaria. Seguimos as 14h.")
        self.assertEqual(SmsMessage.objects.count(), 2)

    def test_mensagem_vazia_e_recusada(self):
        self._bilhete("841000013", self.viagem)
        self.assertEqual(self.avisar(trip_id=self.viagem.id, body="   ").status_code, 400)

    def test_mensagem_demasiado_longa_e_recusada(self):
        self._bilhete("841000014", self.viagem)
        r = self.avisar(trip_id=self.viagem.id, body="a" * 400)
        self.assertEqual(r.status_code, 400, r.content)

    def test_sem_ninguem_a_bordo_nao_envia(self):
        r = self.avisar(trip_id=self.viagem.id, body="ola")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(SmsMessage.objects.count(), 0)

    def test_partida_e_rota_ao_mesmo_tempo_e_recusado(self):
        r = self.avisar(trip_id=self.viagem.id, route_id=self.rota.id, preview=True)
        self.assertEqual(r.status_code, 400)

    def test_sem_alvo_nenhum_e_recusado(self):
        self.assertEqual(self.avisar(preview=True).status_code, 400)

    # --- permissao -------------------------------------------------------

    def test_quem_nao_tem_a_capacidade_nao_envia(self):
        User = get_user_model()
        ze = User.objects.create_user(username="ze", password="x", email="z@x.mz")
        self.client.force_authenticate(ze)
        self.assertEqual(self.avisar(trip_id=self.viagem.id, body="ola").status_code, 403)

    def test_gestor_operacional_pode_avisar(self):
        """Nao pode ser preciso ser Administrador para avisar um autocarro."""
        User = get_user_model()
        gestor = User.objects.create_user(username="gestor", password="x", email="g@x.mz")
        papel, _ = Role.objects.get_or_create(
            code="operations_manager",
            defaults={"name": "Gestor Operacional", "permissions": [], "is_system": True})
        papel.permissions = ["broadcasts.send"]
        papel.save(update_fields=["permissions"])
        UserRole.objects.create(user=gestor, role=papel)

        self._bilhete("841000015", self.viagem)
        self.client.force_authenticate(gestor)
        self.assertEqual(self.avisar(trip_id=self.viagem.id, body="ola").status_code, 201)
