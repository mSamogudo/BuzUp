"""Testes dos furos de segurança encontrados na auditoria.

Cada teste corresponde a um ataque concreto que era possível. São escritos do
ponto de vista do atacante: se um destes voltar a passar, alguém consegue
outra vez ver ou gastar o que não é seu.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.passengers.models import PassengerAccount
from apps.trips.models import Agent
from apps.wallets.models import Wallet

User = get_user_model()


class PhoneTakeoverTests(TestCase):
    """Trocar o telefone no perfil dava acesso à conta de outra pessoa.

    A identidade de passageiro é resolvida por telefone em toda a plataforma
    (carteira, bilhetes, pagamentos) e `User.phone` não é único. Quem pudesse
    gravar o telefone da vítima passava a ler e a GASTAR a carteira dela.
    """

    def setUp(self):
        self.attacker = User.objects.create_user(
            username="atacante", password="x", phone="258840000001",
        )
        self.victim_phone = "258849999999"
        victim = PassengerAccount.objects.create(
            full_name="Vitima", phone_number=self.victim_phone,
            status=PassengerAccount.Status.ACTIVE,
        )
        Wallet.objects.create(
            passenger_account=victim, balance_cached=Decimal("5000.00"),
            status=Wallet.Status.ACTIVE,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.attacker)

    def test_cannot_change_own_phone_to_someone_elses(self):
        res = self.client.patch(
            "/api/auth/me/profile/", {"phone": self.victim_phone}, format="json",
        )
        self.assertEqual(res.status_code, 400, res.data)
        self.attacker.refresh_from_db()
        self.assertEqual(
            self.attacker.phone, "258840000001",
            "o telefone foi alterado — a conta da vitima fica acessivel",
        )

    def test_can_still_edit_name_and_email(self):
        """A correcção não pode ter fechado a edição legítima do perfil."""
        res = self.client.patch(
            "/api/auth/me/profile/",
            {"first_name": "Novo", "email": "novo@exemplo.mz"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.attacker.refresh_from_db()
        self.assertEqual(self.attacker.first_name, "Novo")

    def test_submitting_own_unchanged_phone_is_accepted(self):
        """A app envia o perfil inteiro; repetir o próprio número não é ataque."""
        res = self.client.patch(
            "/api/auth/me/profile/",
            {"phone": "258840000001", "first_name": "Igual"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)


class TicketIdorTests(TestCase):
    """Ler o bilhete de outra pessoa sabendo apenas a referência."""

    def setUp(self):
        owner = PassengerAccount.objects.create(
            full_name="Dono", phone_number="258841111111",
            status=PassengerAccount.Status.ACTIVE,
        )
        self.checkout = GuestCheckout.objects.create(
            reference="GC-SEGTEST0001", payer_phone="258841111111",
            route_code="R1", route_name="Rota 1",
            origin_stop="A", destination_stop="B",
            quantity=1, unit_amount=Decimal("100.00"), total_amount=Decimal("100.00"),
            status=GuestCheckout.Status.ISSUED,
        )
        raw, token_hash = DigitalTravelPass.generate_token()
        self.raw_token = raw
        self.tp = DigitalTravelPass.objects.create(
            guest_checkout=self.checkout, passenger_account=owner,
            payer_phone="258841111111",
            route_code="R1", origin_stop="A", destination_stop="B",
            fare_amount=Decimal("100.00"), token=raw, token_hash=token_hash,
            status=DigitalTravelPass.Status.ACTIVE,
            valid_until=timezone.now() + timezone.timedelta(hours=6),
            document_number="110100999999X",
        )

    def test_user_without_passenger_account_cannot_read_others_ticket(self):
        """O buraco: sem conta de passageiro, nenhuma das verificações se
        aplicava e o bilheteiro — com token do QR e PDF — era devolvido."""
        outsider = User.objects.create_user(
            username="agente_qualquer", password="x", phone="258842222222",
        )
        client = APIClient()
        client.force_authenticate(user=outsider)

        detail = client.get(f"/api/mobile/tickets/{self.checkout.reference}/")
        self.assertEqual(detail.status_code, 403, detail.data)

        pdf = client.get(f"/api/mobile/tickets/{self.checkout.reference}/pdf/")
        self.assertEqual(pdf.status_code, 403)

    def test_public_checkout_lookup_does_not_leak_document(self):
        """A referência circula por SMS e no bilhete impresso: não pode servir
        de porta para a identificação do passageiro."""
        res = APIClient().get(f"/api/guest-checkouts/{self.checkout.reference}/")
        self.assertEqual(res.status_code, 200)
        body = str(res.data)
        self.assertNotIn("110100999999X", body, "numero de documento exposto")


class AgentTicketPermissionTests(TestCase):
    """Um agente não pode queimar o bilhete de uma venda que não é sua."""

    def setUp(self):
        self.other_agent_user = User.objects.create_user(
            username="agente_a", password="x", phone="258843333333",
        )
        Agent.objects.create(
            user=self.other_agent_user, full_name="Agente A", status=Agent.Status.ACTIVE,
        )
        self.checkout = GuestCheckout.objects.create(
            reference="GC-SEGTEST0002", payer_phone="258844444444",
            route_code="R1", origin_stop="A", destination_stop="B",
            quantity=1, unit_amount=Decimal("100.00"), total_amount=Decimal("100.00"),
            status=GuestCheckout.Status.ISSUED,
        )
        raw, token_hash = DigitalTravelPass.generate_token()
        self.tp = DigitalTravelPass.objects.create(
            guest_checkout=self.checkout, payer_phone="258844444444",
            route_code="R1", origin_stop="A", destination_stop="B",
            fare_amount=Decimal("100.00"), token=raw, token_hash=token_hash,
            status=DigitalTravelPass.Status.ACTIVE,
            valid_until=timezone.now() + timezone.timedelta(hours=6),
        )

    def test_agent_cannot_mark_used_a_ticket_from_another_sale(self):
        client = APIClient()
        client.force_authenticate(user=self.other_agent_user)
        res = client.post(f"/api/agent/tickets/{self.checkout.reference}/mark-used/")
        self.assertEqual(res.status_code, 403, res.data)
        self.tp.refresh_from_db()
        self.assertEqual(
            self.tp.status, DigitalTravelPass.Status.ACTIVE,
            "o bilhete de outra venda foi queimado",
        )


class DeviceOnboardingTests(TestCase):
    """O código de activação não pode ser obtido por quem sabe o serial."""

    def test_self_onboard_does_not_return_code_for_existing_device(self):
        from apps.devices.models import Device

        Device.objects.create(
            serial_number="SEG-TEST-0001", device_type="sunmi_v2s_pos",
            activation_code=Device.generate_activation_code(),
            status=Device.Status.PENDING_ACTIVATION,
        )
        res = APIClient().post(
            "/api/devices/self-onboard/",
            {"serial_number": "SEG-TEST-0001", "device_type": "sunmi_v2s_pos"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertNotIn(
            "activation_code", res.data,
            "o codigo de activacao foi devolvido — qualquer pessoa activa o terminal",
        )
