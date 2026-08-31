"""O turno de agente: abrir, fechar, conferir e reabrir.

O que estes testes protegem, por ordem de importancia para o dinheiro:

1. o apurado esperado e do SERVIDOR — se o cliente o pudesse mandar, a
   diferenca dava sempre zero e a conferencia nao conferia nada;
2. so o numerario conta para a caixa — o que foi por M-Pesa nunca passou pelas
   maos do agente;
3. um agente so tem um turno aberto de cada vez;
4. reabrir uma caixa dada por boa deixa rasto de quem o fez e porque.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.guest_checkouts.models import GuestCheckout
from apps.payments.models import CASH_PROVIDER, PaymentIntent
from apps.shifts.models import Shift
from apps.shifts.services import ShiftError, abrir_turno, fechar_turno, reabrir_turno
from apps.trips.models import Vehicle

User = get_user_model()


def _venda(shift, total, provider, status=PaymentIntent.Status.CONFIRMED):
    """Uma venda de balcao ligada ao turno, com o pagamento no estado pedido."""
    gc = GuestCheckout.objects.create(
        reference=f"GC-{provider}-{total}-{shift.pk}-{GuestCheckout.objects.count()}",
        payer_phone="258840000001",
        quantity=1,
        unit_amount=Decimal(total),
        total_amount=Decimal(total),
        status=GuestCheckout.Status.ISSUED,
        shift=shift,
    )
    PaymentIntent.objects.create(
        reference=f"PAY-{gc.reference}",
        idempotency_key=f"idem-{gc.reference}",
        purpose=PaymentIntent.Purpose.POS_CARD_TOPUP,
        amount=Decimal(total),
        payer_phone="258840000001",
        provider=provider,
        status=status,
        guest_checkout=gc,
    )
    return gc


class CaixaDoTurnoTests(TestCase):
    def setUp(self):
        self.agente = User.objects.create_user(
            username="agente", password="x", email="a@x.mz", phone="849000001")
        self.turno = abrir_turno(agent_user=self.agente, float_amount=Decimal("500.00"))

    def test_o_apurado_conta_so_o_numerario(self):
        """M-Pesa entra directamente na conta da operadora e nunca passa pela
        caixa. Soma-lo fazia o agente parecer sempre em falta pelo mesmo valor
        que o gateway ja tinha recebido."""
        _venda(self.turno, "300.00", CASH_PROVIDER)
        _venda(self.turno, "200.00", CASH_PROVIDER)
        _venda(self.turno, "999.00", "MPESA")

        fechado = fechar_turno(self.turno, counted_amount=Decimal("1000.00"))

        # 500 de fundo + 500 de numerario. Os 999 do M-Pesa ficam de fora.
        self.assertEqual(fechado.expected_amount, Decimal("1000.00"))
        self.assertEqual(fechado.difference, Decimal("0.00"))

    def test_pagamento_por_confirmar_nao_conta(self):
        """Uma venda pendente ainda nao e dinheiro na mao de ninguem."""
        _venda(self.turno, "400.00", CASH_PROVIDER, status=PaymentIntent.Status.PENDING)
        fechado = fechar_turno(self.turno, counted_amount=Decimal("500.00"))
        self.assertEqual(fechado.expected_amount, Decimal("500.00"))

    def test_a_diferenca_e_guardada_com_sinal(self):
        """Falta e sobra sao problemas diferentes e tem de se distinguir."""
        _venda(self.turno, "300.00", CASH_PROVIDER)
        fechado = fechar_turno(self.turno, counted_amount=Decimal("750.00"))
        self.assertEqual(fechado.expected_amount, Decimal("800.00"))
        self.assertEqual(fechado.difference, Decimal("-50.00"))

    def test_o_fundo_de_maneio_volta_na_conta(self):
        """Sem vendas nenhumas, a caixa tem de ter o troco com que comecou."""
        fechado = fechar_turno(self.turno, counted_amount=Decimal("500.00"))
        self.assertEqual(fechado.expected_amount, Decimal("500.00"))
        self.assertEqual(fechado.difference, Decimal("0.00"))


class UmTurnoDeCadaVezTests(TestCase):
    def setUp(self):
        self.agente = User.objects.create_user(
            username="agente2", password="x", email="a2@x.mz", phone="849000002")

    def test_nao_se_abrem_dois_turnos_ao_mesmo_agente(self):
        """Dois turnos abertos dividiam as vendas entre as duas caixas sem
        criterio, e nenhuma das duas fechava certa."""
        abrir_turno(agent_user=self.agente)
        with self.assertRaises(ShiftError):
            abrir_turno(agent_user=self.agente)

    def test_depois_de_fechar_ja_se_abre_outro(self):
        primeiro = abrir_turno(agent_user=self.agente)
        fechar_turno(primeiro, counted_amount=Decimal("0.00"))
        segundo = abrir_turno(agent_user=self.agente)
        self.assertEqual(segundo.status, Shift.Status.OPEN)

    def test_dois_agentes_tem_turnos_independentes(self):
        outro = User.objects.create_user(
            username="agente3", password="x", email="a3@x.mz", phone="849000003")
        abrir_turno(agent_user=self.agente)
        abrir_turno(agent_user=outro)
        self.assertEqual(Shift.objects.filter(status=Shift.Status.OPEN).count(), 2)


class ReabrirDeixaRastoTests(TestCase):
    def setUp(self):
        self.agente = User.objects.create_user(
            username="agente4", password="x", email="a4@x.mz", phone="849000004")
        self.chefe = User.objects.create_user(
            username="tesouraria", password="x", email="t@x.mz", phone="849000005")
        self.turno = abrir_turno(agent_user=self.agente, float_amount=Decimal("100.00"))
        fechar_turno(self.turno, counted_amount=Decimal("100.00"))
        self.turno.refresh_from_db()

    def test_reabrir_sem_motivo_e_recusado(self):
        """Sem motivo escrito, o historico perdia a unica pista de que a conta
        ja tinha sido dada por boa uma vez."""
        with self.assertRaises(ShiftError):
            reabrir_turno(self.turno, motivo="   ", reopened_by=self.chefe)

    def test_o_motivo_e_quem_reabriu_ficam_nas_notas(self):
        reaberto = reabrir_turno(
            self.turno, motivo="Faltava contar o saco das moedas", reopened_by=self.chefe)
        self.assertEqual(reaberto.status, Shift.Status.OPEN)
        self.assertIn("Faltava contar o saco das moedas", reaberto.notes)
        self.assertIn("tesouraria", reaberto.notes)
        self.assertIsNone(reaberto.closed_at)

    def test_nao_se_reabre_com_outro_turno_aberto(self):
        """Senao o agente ficava com dois, e voltavamos ao problema do inicio."""
        abrir_turno(agent_user=self.agente)
        with self.assertRaises(ShiftError):
            reabrir_turno(self.turno, motivo="engano", reopened_by=self.chefe)


class EndpointsDoTurnoTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="chefe-turnos", password="x", email="c@x.mz")
        self.agente = User.objects.create_user(
            username="agente5", password="x", email="a5@x.mz", phone="849000006")
        self.viatura = Vehicle.objects.create(registration="TUR-01-MP", seated_capacity=40)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_abrir_fechar_conferir_pelo_endpoint(self):
        r = self.client.post("/api/shifts/open/", {
            "agent_user": self.agente.id,
            "vehicle": self.viatura.id,
            "float_amount": "250.00",
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        shift_id = r.data["id"]
        self.assertEqual(r.data["status"], "open")

        _venda(Shift.objects.get(pk=shift_id), "150.00", CASH_PROVIDER)

        r = self.client.post(f"/api/shifts/{shift_id}/close/",
                             {"counted_amount": "400.00"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["status"], "closed")
        self.assertEqual(r.data["expected_amount"], "400.00")
        self.assertEqual(r.data["difference"], "0.00")

        r = self.client.post(f"/api/shifts/{shift_id}/verify/", {}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["status"], "verified")

    def test_o_apurado_enviado_pelo_cliente_e_ignorado(self):
        """A porta das traseiras que faria a conferencia nao conferir nada."""
        turno = abrir_turno(agent_user=self.agente, float_amount=Decimal("100.00"))
        _venda(turno, "900.00", CASH_PROVIDER)

        r = self.client.post(f"/api/shifts/{turno.pk}/close/", {
            "counted_amount": "1000.00",
            "expected_amount": "1000000.00",   # ignorado
            "difference": "0.00",              # ignorado
        }, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["expected_amount"], "1000.00")

    def test_fechar_duas_vezes_e_recusado(self):
        turno = abrir_turno(agent_user=self.agente)
        self.client.post(f"/api/shifts/{turno.pk}/close/",
                         {"counted_amount": "0.00"}, format="json")
        r = self.client.post(f"/api/shifts/{turno.pk}/close/",
                             {"counted_amount": "0.00"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_conferir_um_turno_ainda_aberto_e_recusado(self):
        turno = abrir_turno(agent_user=self.agente)
        r = self.client.post(f"/api/shifts/{turno.pk}/verify/", {}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_reabrir_pelo_endpoint_exige_motivo(self):
        turno = abrir_turno(agent_user=self.agente)
        fechar_turno(turno, counted_amount=Decimal("0.00"))
        r = self.client.post(f"/api/shifts/{turno.pk}/reopen/", {}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_a_lista_filtra_os_divergentes(self):
        """Por onde a tesouraria comeca o dia."""
        certo = abrir_turno(agent_user=self.agente)
        fechar_turno(certo, counted_amount=Decimal("0.00"))
        outro = User.objects.create_user(
            username="agente6", password="x", email="a6@x.mz", phone="849000007")
        torto = abrir_turno(agent_user=outro, float_amount=Decimal("100.00"))
        fechar_turno(torto, counted_amount=Decimal("40.00"))

        r = self.client.get("/api/shifts/?divergent=true")
        self.assertEqual(r.status_code, 200)
        ids = [linha["id"] for linha in r.data["results"]]
        self.assertIn(torto.pk, ids)
        self.assertNotIn(certo.pk, ids)

    def test_criar_turno_por_post_directo_nao_e_permitido(self):
        """Senao criava-se um turno ja fechado com o apurado que se quisesse."""
        r = self.client.post("/api/shifts/", {"agent_user": self.agente.id}, format="json")
        self.assertIn(r.status_code, (403, 405))


class QuemPodeOQueTests(TestCase):
    """Conferir e da tesouraria. Quem faz a caixa nao pode dar-lhe o visto."""

    def setUp(self):
        self.agente = User.objects.create_user(
            username="agente7", password="x", email="a7@x.mz", phone="849000008")
        self.turno = abrir_turno(agent_user=self.agente)
        fechar_turno(self.turno, counted_amount=Decimal("0.00"))
        self.client = APIClient()

    def test_sem_capacidade_nao_confere(self):
        self.client.force_authenticate(self.agente)
        r = self.client.post(f"/api/shifts/{self.turno.pk}/verify/", {}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_sem_capacidade_nao_le_a_lista(self):
        self.client.force_authenticate(self.agente)
        self.assertEqual(self.client.get("/api/shifts/").status_code, 403)
