"""Fecho de caixa: o que conta como receita e o que ja foi cobrado antes.

Desde que o cartao passou a poder embarcar com um bilhete ja comprado, uma
validacao aprovada e DUAS coisas diferentes:

* **pay-as-you-go** — a carteira foi debitada nesta validacao. E dinheiro de
  hoje.
* **embarque com bilhete** — o valor entrou na receita no dia da COMPRA. O
  evento guarda o valor do bilhete para se saber quanto valeu quem embarcou,
  mas somar isso a receita conta o mesmo dinheiro duas vezes.

Somar tudo numa linha so era o caminho directo para um fecho que nao bate
certo com a conta bancaria — e ninguem daria por isso ate ao fim do mes.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.cards.models import Card
from apps.guest_checkouts.models import DigitalTravelPass
from apps.passengers.models import PassengerAccount
from apps.routes.models import Route
from apps.validations.models import ValidationEvent
from apps.wallets.models import Wallet


class FechoBase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="agente_fecho", password="x",
            phone="849333111", email="agente_fecho@x.mz",
        )
        self.rota = Route.objects.create(
            code="R-FECHO", name="Circular",
            service_type=Route.ServiceType.URBAN, status=Route.Status.ACTIVE,
        )
        self.passageiro = PassengerAccount.objects.create(
            full_name="Ana Cossa", phone_number="849333222",
            status=PassengerAccount.Status.ACTIVE,
        )
        self.carteira = Wallet.objects.create(
            passenger_account=self.passageiro,
            balance_cached=Decimal("1000.00"), status="active",
        )
        self.cartao = Card.objects.create(
            card_uid="CARD-FECHO-1", passenger_account=self.passageiro,
            wallet=self.carteira, status=Card.Status.ACTIVE,
        )

    def _bilhete(self):
        agora = timezone.now()
        return DigitalTravelPass.objects.create(
            passenger_account=self.passageiro, wallet=self.carteira,
            route_code=self.rota.code, fare_amount=Decimal("50.00"),
            status=DigitalTravelPass.Status.USED,
            token=f"tok-{agora.timestamp()}", token_hash=f"h-{agora.timestamp()}",
            valid_from=agora, valid_until=agora + timedelta(hours=24),
        )

    def _evento(self, *, tipo, valor, bilhete=None):
        return ValidationEvent.objects.create(
            validation_type=tipo,
            passenger_account=self.passageiro, wallet=self.carteira,
            physical_card=self.cartao, route=self.rota,
            digital_travel_pass=bilhete,
            amount_debited=Decimal(valor),
            status=ValidationEvent.Status.APPROVED,
            validated_by=self.user,
            idempotency_key=f"k-{timezone.now().timestamp()}-{valor}",
        )

    def _payload(self):
        from apps.agent_api.views import AgentDayCloseView

        return AgentDayCloseView()._build_payload(self.user)


class ReceitaNaoContaDuasVezesTests(FechoBase):
    def test_pay_as_you_go_conta_como_movimento_de_hoje(self):
        self._evento(tipo=ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO, valor="50.00")
        t = self._payload()["totals"]
        self.assertEqual(Decimal(t["validations_revenue"]), Decimal("50.00"))
        self.assertEqual(Decimal(t["validations_prepaid"]), Decimal("0.00"))

    def test_embarque_com_bilhete_NAO_conta_como_receita(self):
        # O ponto todo desta suite: o bilhete foi pago no dia da compra.
        self._evento(
            tipo=ValidationEvent.ValidationType.DIGITAL_TRAVEL_PASS,
            valor="50.00", bilhete=self._bilhete(),
        )
        t = self._payload()["totals"]
        self.assertEqual(Decimal(t["validations_revenue"]), Decimal("0.00"),
                         "contou como receita de hoje um bilhete pago noutro dia")
        self.assertEqual(Decimal(t["validations_prepaid"]), Decimal("50.00"))

    def test_os_dois_juntos_ficam_separados(self):
        self._evento(tipo=ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO, valor="30.00")
        self._evento(
            tipo=ValidationEvent.ValidationType.DIGITAL_TRAVEL_PASS,
            valor="50.00", bilhete=self._bilhete(),
        )
        t = self._payload()["totals"]
        self.assertEqual(Decimal(t["validations_revenue"]), Decimal("30.00"))
        self.assertEqual(Decimal(t["validations_prepaid"]), Decimal("50.00"))
        self.assertEqual(t["validations"], 2, "os dois embarques contam na contagem")


class LinhaDoEmbarqueTests(FechoBase):
    def test_linha_leva_o_cartao_e_a_origem_do_dinheiro(self):
        self._evento(tipo=ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO, valor="50.00")
        linha = self._payload()["validations"][0]
        self.assertEqual(linha["card_uid"], "CARD-FECHO-1",
                         "sem o cartao a linha nao se liga a ninguem")
        self.assertTrue(linha["cobrou_agora"])

    def test_embarque_com_bilhete_marca_o_bilhete_e_nao_a_cobranca(self):
        tp = self._bilhete()
        self._evento(
            tipo=ValidationEvent.ValidationType.DIGITAL_TRAVEL_PASS,
            valor="50.00", bilhete=tp,
        )
        linha = self._payload()["validations"][0]
        self.assertFalse(linha["cobrou_agora"])
        self.assertEqual(linha["bilhete_id"], tp.id)

    def test_embarque_por_qr_da_conta_guarda_o_cartao(self):
        """O QR da conta e a mesma pessoa que o cartao.

        Sem isto, um embarque por QR aparecia no fecho sem cartao nenhum e a
        linha nao se ligava a ninguem.
        """
        from apps.validations.services import _card_of

        self.assertEqual(_card_of(self.passageiro), self.cartao)

    def test_linha_sem_cartao_mostra_quem_embarcou(self):
        from apps.agent_api.exporters import _quem_embarcou

        self.assertEqual(_quem_embarcou({"card_uid": "CARD-1"}), "CARD-1")
        self.assertEqual(
            _quem_embarcou({"card_uid": "", "passageiro": "Ana Cossa"}), "Ana Cossa")
        self.assertEqual(
            _quem_embarcou({"card_uid": "", "passageiro": "", "telefone": "***3256"}),
            "***3256")

    def test_a_coluna_do_pdf_diz_de_onde_veio_o_dinheiro(self):
        from apps.agent_api.exporters import _origem_do_dinheiro

        self.assertEqual(
            _origem_do_dinheiro({"status": "approved", "cobrou_agora": True}),
            "Debitado agora")
        self.assertEqual(
            _origem_do_dinheiro({"status": "approved", "bilhete_id": 7}),
            "Bilhete ja pago")
        self.assertEqual(
            _origem_do_dinheiro({"status": "denied", "cobrou_agora": True}), "-")
