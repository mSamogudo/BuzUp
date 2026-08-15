"""Segundo factor no portal.

Uma conta de gestão entra em tarifas, cartões e receita. Uma senha apanhada
por cima do ombro — ou reutilizada de outro sítio — não pode chegar para isso.
Daí o código por SMS entre a senha e os tokens.

Quem desliga esta protecção é apenas um superadministrador, e no painel de
administração: se qualquer conta com permissão de editar utilizadores a
pudesse desligar, a protecção valia o que valesse o elo mais fraco.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.users.admin import UserAdmin
from apps.users.models import PortalLoginChallenge
from apps.users.otp import OTP_MAX_ATTEMPTS, _hash_otp

User = get_user_model()
SENHA = "s3nh4-de-teste-comprida"


class DoisFactoresBase(APITestCase):
    def setUp(self):
        # O balde do limite de tentativas vive na cache e sobrevive entre
        # testes: sem limpar, o 12.º pedido da suite levava 429 e o teste
        # falhava por um motivo que nada tem a ver com o que estava a medir.
        cache.clear()
        self.gestor = User.objects.create_user(
            username="gestor", email="gestor@exemplo.co.mz", password=SENHA,
            phone="841234567", is_2fa_enabled=True,
        )

    def entrar(self, username="gestor", password=SENHA):
        return self.client.post("/api/auth/token/",
                                {"username": username, "password": password}, format="json")


class LoginTests(DoisFactoresBase):
    def test_senha_certa_nao_devolve_tokens_de_imediato(self):
        r = self.entrar()
        self.assertEqual(r.status_code, 202)
        self.assertTrue(r.data["two_factor"])
        self.assertNotIn("access", r.data, "a senha sozinha nao pode abrir o portal")
        self.assertIn("challenge_id", r.data)

    def test_o_numero_nao_e_publicado_por_inteiro(self):
        r = self.entrar()
        pista = r.data["phone_hint"]
        self.assertIn("***", pista)
        self.assertNotIn("1234567", pista, "quem so acertou na senha nao fica a saber o numero")

    def test_codigo_certo_devolve_os_tokens(self):
        self.entrar()
        d = PortalLoginChallenge.objects.get(user=self.gestor)
        # O código em claro nunca é guardado; nos testes reproduz-se o hash.
        for tentativa in range(1000000):
            codigo = f"{tentativa:06d}"
            if _hash_otp(codigo) == d.code_hash:
                break
        else:
            self.fail("nao foi possivel reproduzir o codigo")
        r = self.client.post("/api/auth/2fa/verify/",
                             {"challenge_id": str(d.uuid), "code": codigo}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
        d.refresh_from_db()
        self.assertEqual(d.status, PortalLoginChallenge.Status.CONSUMED)

    def test_codigo_errado_nao_abre_e_conta_a_tentativa(self):
        self.entrar()
        d = PortalLoginChallenge.objects.get(user=self.gestor)
        r = self.client.post("/api/auth/2fa/verify/",
                             {"challenge_id": str(d.uuid), "code": "000000"}, format="json")
        self.assertEqual(r.status_code, 400)
        d.refresh_from_db()
        self.assertGreaterEqual(d.failed_attempts, 1)

    def test_tentativas_esgotam_o_desafio(self):
        self.entrar()
        d = PortalLoginChallenge.objects.get(user=self.gestor)
        d.failed_attempts = OTP_MAX_ATTEMPTS
        d.save(update_fields=["failed_attempts"])
        r = self.client.post("/api/auth/2fa/verify/",
                             {"challenge_id": str(d.uuid), "code": "000000"}, format="json")
        self.assertEqual(r.status_code, 400)
        d.refresh_from_db()
        self.assertEqual(d.status, PortalLoginChallenge.Status.EXPIRED)

    def test_desafio_expirado_nao_serve(self):
        self.entrar()
        d = PortalLoginChallenge.objects.get(user=self.gestor)
        d.expires_at = timezone.now() - timedelta(minutes=1)
        d.save(update_fields=["expires_at"])
        r = self.client.post("/api/auth/2fa/verify/",
                             {"challenge_id": str(d.uuid), "code": "000000"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_pedir_novo_codigo_invalida_o_anterior(self):
        """Senao, pedir codigo novo era uma forma de somar tentativas."""
        self.entrar()
        antigo = PortalLoginChallenge.objects.get(user=self.gestor)
        self.entrar()
        antigo.refresh_from_db()
        self.assertEqual(antigo.status, PortalLoginChallenge.Status.EXPIRED)
        self.assertEqual(
            PortalLoginChallenge.objects.filter(
                user=self.gestor, status=PortalLoginChallenge.Status.PENDING).count(), 1)

    def test_sem_2fa_entra_como_sempre(self):
        self.gestor.is_2fa_enabled = False
        self.gestor.save(update_fields=["is_2fa_enabled"])
        r = self.entrar()
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)

    def test_apagar_o_telemovel_nao_contorna_o_segundo_factor(self):
        self.gestor.phone = ""
        self.gestor.save(update_fields=["phone"])
        r = self.entrar()
        self.assertEqual(r.status_code, 403, "sem numero, a conta fica travada — nao passa em claro")
        self.assertNotIn("access", r.data)

    def test_senha_errada_continua_a_falhar(self):
        r = self.entrar(password="errada")
        self.assertEqual(r.status_code, 401)
        self.assertFalse(PortalLoginChallenge.objects.exists(),
                         "nao se envia SMS a quem nem acertou na senha")


class QuemPodeDesligarTests(DoisFactoresBase):
    def campos_bloqueados(self, utilizador):
        pedido = RequestFactory().get("/admin/")
        pedido.user = utilizador
        admin = UserAdmin(User, None)
        return admin.get_readonly_fields(pedido, self.gestor)

    def test_superadministrador_pode_desligar(self):
        chefe = User.objects.create_superuser(
            username="chefe", email="chefe@exemplo.co.mz", password=SENHA)
        self.assertNotIn("is_2fa_enabled", self.campos_bloqueados(chefe))

    def test_staff_sem_ser_superadministrador_nao_pode(self):
        staff = User.objects.create_user(
            username="staff", email="staff@exemplo.co.mz", password=SENHA, is_staff=True)
        self.assertIn(
            "is_2fa_enabled", self.campos_bloqueados(staff),
            "so o superadministrador desliga — senao a proteccao vale o elo mais fraco",
        )
