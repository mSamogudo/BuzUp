"""Testes dos furos de segurança encontrados na auditoria.

Cada teste corresponde a um ataque concreto que era possível. São escritos do
ponto de vista do atacante: se um destes voltar a passar, alguém consegue
outra vez ver ou gastar o que não é seu.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.passengers.models import PassengerAccount
from apps.trips.models import Agent
from apps.users.models import PortalLoginChallenge
from apps.users.otp import _hash_otp
from apps.users.tokens import MARCA, token_para
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


class SenhaMudaTokenMorreTests(TestCase):
    """Repor a senha de uma conta comprometida nao expulsava ninguem.

    Era o ataque: alguem entra numa conta de agente, o administrador da por
    isso e repoe a senha, o SMS com a senha temporaria sai. E o intruso
    continua a vender no POS durante meia hora, porque o token de acesso que
    ja tinha na mao nao consulta nada e vale ate expirar.

    A lista negra nao resolvia — nem sequer era usada nestas vias — porque
    so apanha o refresh, e nao e o refresh que abre portas.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="agente", email="agente@exemplo.co.mz",
            password="senha-antiga-forte", phone="258840000009",
            # Sem segundo factor para poder exercitar a porta directa do
            # login; o caminho com 2FA tem teste proprio mais abaixo.
            is_2fa_enabled=False,
        )

    def _bilhete_de_entrada(self) -> str:
        """O que um intruso teria: um token de acesso valido, tirado antes."""
        return str(token_para(self.user).access_token)

    def _ainda_abre(self, access) -> int:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        try:
            return self.client.get(reverse("auth_me")).status_code
        finally:
            self.client.credentials()

    def test_an_admin_reset_locks_the_intruder_out_immediately(self):
        roubado = self._bilhete_de_entrada()
        self.assertEqual(self._ainda_abre(roubado), 200, "o cenario exige que abrisse antes")

        # O que o `AdminUserPasswordResetView` faz.
        self.user.set_password("temporaria-nova-forte")
        self.user.save(update_fields=["password", "updated_at"])

        self.assertEqual(self._ainda_abre(roubado), 401)

    def test_changing_my_own_password_ends_the_session_i_distrust(self):
        outra_sessao = self._bilhete_de_entrada()
        self.user.set_password("escolhida-por-mim-forte")
        self.user.save(update_fields=["password", "updated_at"])
        self.assertEqual(self._ainda_abre(outra_sessao), 401)

    def test_a_refresh_from_before_cannot_mint_a_working_token(self):
        """Fechar o acesso e inutil se o refresh velho puder fabricar outro.

        Nao pode: o `TokenRefreshView` copia as claims do refresh, por isso o
        acesso que sai nasce com a marca velha.
        """
        antigo = token_para(self.user)
        self.user.set_password("outra-bem-diferente-forte")
        self.user.save(update_fields=["password", "updated_at"])

        resposta = self.client.post(reverse("token_refresh"), {"refresh": str(antigo)})
        if resposta.status_code == 200:
            self.assertEqual(
                self._ainda_abre(resposta.data["access"]), 401,
                "o token nascido de um refresh velho nao pode abrir nada",
            )

    def test_the_direct_login_hands_out_a_stamped_token(self):
        """Se o login nao carimbar, tudo isto fica sem efeito para quem entra
        pela porta normal — que e toda a gente."""
        resposta = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "agente", "password": "senha-antiga-forte"}, format="json",
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(MARCA, RefreshToken(resposta.data["refresh"]).payload)

    def test_the_two_factor_login_also_hands_out_a_stamped_token(self):
        """O portal entra por aqui, nao pela porta directa. Sao dois sitios
        diferentes a emitir tokens, e um por carimbar deixava o buraco aberto
        por inteiro para quem entra por essa porta."""
        cache.clear()
        gestor = User.objects.create_user(
            username="gestor-marca", email="gestor-marca@exemplo.co.mz",
            password="senha-antiga-forte", phone="841234567", is_2fa_enabled=True,
        )
        primeiro = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "gestor-marca", "password": "senha-antiga-forte"}, format="json",
        )
        self.assertEqual(primeiro.status_code, 202, "a senha sozinha nao pode abrir o portal")

        desafio = PortalLoginChallenge.objects.get(user=gestor)
        # O codigo em claro nunca e guardado; nos testes reproduz-se o hash.
        for tentativa in range(1000000):
            codigo = f"{tentativa:06d}"
            if _hash_otp(codigo) == desafio.code_hash:
                break
        else:
            self.fail("nao foi possivel reproduzir o codigo")

        segundo = self.client.post(
            reverse("portal_2fa_verify"),
            {"challenge_id": str(desafio.uuid), "code": codigo}, format="json",
        )
        self.assertEqual(segundo.status_code, 200)
        self.assertIn(MARCA, RefreshToken(segundo.data["refresh"]).payload)

    def test_a_token_from_before_this_existed_still_works(self):
        """Ha terminais POS em campo com sessao aberta. Recusar os tokens sem
        marca deitava-os fora a meio de vendas, no momento do deploy."""
        sem_marca = RefreshToken.for_user(self.user)
        self.assertNotIn(MARCA, sem_marca.payload)
        self.assertEqual(self._ainda_abre(str(sem_marca.access_token)), 200)

    def test_someone_elses_reset_does_not_touch_my_session(self):
        outro = User.objects.create_user(
            username="colega", email="colega@exemplo.co.mz",
            password="seja-o-que-for-forte", phone="258840000010",
        )
        meu = self._bilhete_de_entrada()
        outro.set_password("mudou-a-dele-forte")
        outro.save(update_fields=["password", "updated_at"])
        self.assertEqual(self._ainda_abre(meu), 200)
