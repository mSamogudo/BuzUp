"""O cartao e a carteira que anda com ele.

A app `cards` nao tinha um unico teste, e e das que mexem em dinheiro: um
cartao aponta para a carteira do passageiro, e o validador desconta dai. Se a
substituicao de um cartao perdido nao levasse a carteira consigo, o saldo do
passageiro ficaria preso num cartao que ja nao existe — e ninguem daria por
isso ate ele tentar viajar.

O que aqui se fixa sao invariantes, nao implementacao:

* a carteira segue o passageiro, nunca o plastico;
* um cartao substituido deixa de servir, no mesmo instante em que o novo passa
  a servir;
* os estados nao andam para tras;
* ler um cartao expoe dados do passageiro, por isso pede capacidade — nao basta
  ter sessao iniciada.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.cards.models import Card
from apps.cards.services import (
    CardError, activate_card, assign_card_to_passenger, block_card,
    create_digital_card, replace_card,
)
from apps.passengers.models import PassengerAccount
from apps.users.models import Role, UserRole
from apps.wallets.models import Wallet


def _passageiro(nome="Joana Mucavele", telefone="849000111"):
    p = PassengerAccount.objects.create(
        full_name=nome, phone_number=telefone,
        status=PassengerAccount.Status.ACTIVE,
    )
    Wallet.objects.create(passenger_account=p)
    return p


def _cartao(uid):
    return Card.objects.create(
        card_type=Card.CardType.PHYSICAL, card_uid=uid,
        status=Card.Status.INACTIVE,
    )


class CarteiraSegueOPassageiroTests(TestCase):
    """O dinheiro esta na carteira; o cartao e so a chave que lhe da acesso."""

    def setUp(self):
        self.passageiro = _passageiro()
        self.velho = _cartao("UID-VELHO")
        self.velho = assign_card_to_passenger(self.velho, self.passageiro, notify_sms=False)
        carteira = self.passageiro.wallet
        carteira.balance_cached = Decimal("750.00")
        carteira.save(update_fields=["balance_cached"])

    def test_substituir_leva_a_carteira_e_o_saldo(self):
        """O caso que motiva o teste: cartao perdido, saldo la dentro."""
        novo = _cartao("UID-NOVO")
        replace_card(self.velho, novo)

        novo.refresh_from_db()
        self.assertEqual(novo.wallet_id, self.passageiro.wallet.id)
        self.assertEqual(novo.passenger_account_id, self.passageiro.id)
        self.assertEqual(novo.wallet.balance_cached, Decimal("750.00"))

    def test_o_cartao_substituido_deixa_de_servir(self):
        """Metade da substituicao. Sem isto, um cartao perdido continua a pagar."""
        novo = _cartao("UID-NOVO-2")
        replace_card(self.velho, novo)

        self.velho.refresh_from_db()
        novo.refresh_from_db()
        self.assertEqual(self.velho.status, Card.Status.REPLACED)
        self.assertEqual(self.velho.replaced_by_id, novo.id)
        self.assertEqual(novo.status, Card.Status.ACTIVE)

    def test_nao_se_substitui_por_um_cartao_ja_em_uso(self):
        """O substituto tem de estar por estrear.

        Aceitar um cartao ja activo faria a sua carteira ser silenciosamente
        trocada pela do outro passageiro — e o saldo dele desaparecia.
        """
        outro = _passageiro("Amilcar Sitoe", "849000222")
        ocupado = _cartao("UID-OCUPADO")
        ocupado = assign_card_to_passenger(ocupado, outro, notify_sms=False)

        with self.assertRaises(CardError):
            replace_card(self.velho, ocupado)

        ocupado.refresh_from_db()
        self.assertEqual(ocupado.passenger_account_id, outro.id)

    def test_um_cartao_bloqueado_ainda_pode_ser_substituido(self):
        """Bloquear e o primeiro gesto de quem perde o cartao."""
        self.velho = block_card(self.velho)
        novo = _cartao("UID-NOVO-3")
        replace_card(self.velho, novo)
        novo.refresh_from_db()
        self.assertEqual(novo.status, Card.Status.ACTIVE)
        self.assertEqual(novo.wallet.balance_cached, Decimal("750.00"))


class EstadosDoCartaoTests(TestCase):
    """Os estados nao andam para tras."""

    def test_nao_se_bloqueia_o_que_nao_esta_activo(self):
        c = _cartao("UID-INACTIVO")
        with self.assertRaises(CardError):
            block_card(c)

    def test_nao_se_bloqueia_duas_vezes(self):
        p = _passageiro(telefone="849000333")
        c = _cartao("UID-DUPLO")
        c = assign_card_to_passenger(c, p, notify_sms=False)
        c = block_card(c)
        with self.assertRaises(CardError):
            block_card(c)

    def test_nao_se_activa_um_cartao_ja_activo(self):
        p = _passageiro(telefone="849000444")
        c = _cartao("UID-ACTIVO")
        c = assign_card_to_passenger(c, p, notify_sms=False)
        with self.assertRaises(CardError):
            activate_card(c)

    def test_nao_se_atribui_um_cartao_que_ja_tem_dono(self):
        a = _passageiro("A", "849000555")
        b = _passageiro("B", "849000666")
        c = _cartao("UID-DONO")
        c = assign_card_to_passenger(c, a, notify_sms=False)
        with self.assertRaises(CardError):
            c = assign_card_to_passenger(c, b, notify_sms=False)
        c.refresh_from_db()
        self.assertEqual(c.passenger_account_id, a.id)

    def test_activar_sem_dono_cria_carteira_propria(self):
        """Cartao ao portador: tem de ter onde guardar o saldo."""
        c = _cartao("UID-PORTADOR")
        activate_card(c)
        c.refresh_from_db()
        self.assertEqual(c.status, Card.Status.ACTIVE)
        self.assertIsNotNone(c.wallet_id)
        self.assertIsNotNone(c.passenger_account_id)


class CartaoDigitalTests(TestCase):
    def test_cada_cartao_digital_nasce_com_o_seu_proprio_segredo(self):
        """O QR e a credencial. Dois iguais seriam duas contas iguais."""
        a = create_digital_card(_passageiro("A", "849000777"))
        b = create_digital_card(_passageiro("B", "849000888"))
        self.assertTrue(a.qr_token)
        self.assertTrue(b.qr_token)
        self.assertNotEqual(a.qr_token, b.qr_token)
        self.assertNotEqual(a.qr_token_hash, b.qr_token_hash)
        self.assertNotEqual(a.card_uid, b.card_uid)

    def test_o_digital_reaproveita_a_carteira_que_o_passageiro_ja_tem(self):
        """Senao o saldo carregado ficava numa carteira e o QR noutra."""
        p = _passageiro("C", "849000999")
        p.wallet.balance_cached = Decimal("120.00")
        p.wallet.save(update_fields=["balance_cached"])
        c = create_digital_card(p)
        self.assertEqual(c.wallet_id, p.wallet.id)
        self.assertEqual(c.wallet.balance_cached, Decimal("120.00"))


class LerUmCartaoPedeCapacidadeTests(TestCase):
    """Consultar um cartao devolve o nome, o telefone e o saldo do dono.

    Ja foi `IsAuthenticated` apenas — qualquer sessao iniciada podia percorrer
    UIDs e recolher os dados dos passageiros. O teste existe para que a
    capacidade nao volte a cair sem se dar por isso.
    """

    def setUp(self):
        User = get_user_model()
        self.client = APIClient()
        self.passageiro = _passageiro("Rosa Mabjaia", "849001000")
        self.cartao = _cartao("UID-CONSULTA")
        assign_card_to_passenger(self.cartao, self.passageiro, notify_sms=False)

        self.qualquer = User.objects.create_user(
            username="qualquer", email="q@x.mz", password="x")
        self.autorizado = User.objects.create_user(
            username="balcao", email="b@x.mz", password="x")
        papel = Role.objects.create(
            name="Balcao", code="balcao", permissions=["cards.read"])
        UserRole.objects.create(user=self.autorizado, role=papel)

    def _consultar(self, utilizador):
        self.client.force_authenticate(utilizador)
        return self.client.post(
            "/api/card-actions/lookup/", {"card_uid": "UID-CONSULTA"}, format="json")

    def test_sessao_iniciada_nao_chega(self):
        self.assertEqual(self._consultar(self.qualquer).status_code, 403)

    def test_com_cards_read_consulta(self):
        r = self._consultar(self.autorizado)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["card_uid"], "UID-CONSULTA")

    def test_sem_sessao_nenhuma_nao_consulta(self):
        r = self.client.post(
            "/api/card-actions/lookup/", {"card_uid": "UID-CONSULTA"}, format="json")
        self.assertIn(r.status_code, (401, 403))

    def test_bloquear_pede_mais_do_que_ler(self):
        """`cards.read` deixa ver; mexer no cartao e outra coisa."""
        self.client.force_authenticate(self.autorizado)
        r = self.client.post(
            "/api/card-actions/block/", {"card_uid": "UID-CONSULTA"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.cartao.refresh_from_db()
        self.assertEqual(self.cartao.status, Card.Status.ACTIVE)
