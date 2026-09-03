"""O que o balcao ve na lista de partidas.

O incidente: o cliente criou a viagem no portal, foi ao POS, e a lista estava
vazia. Nao havia erro nenhum — a viagem ficava `agendada` (e o unico estado com
que uma viagem nasce) e o POS so mostrava as que ja estavam em embarque. Ou
seja: a unica maneira de vender era o motorista abrir o embarque primeiro, o
que numa carreira internacional acontece horas depois de o bilhete ser vendido.

**A regra mudou em 2026-08-26, por decisao do operador.** O balcao passou a
mostrar SO o que esta a circular: a TPM-TUR nao vendia antecipado ao balcao, e
abrir o embarque e o acto que poe o autocarro a venda.

**E mudou outra vez em 2026-09-03, tambem por decisao do operador.** O agente
de recepcao nao viaja: quem atende ao balcao reserva para amanha e para a
semana, e o modelo "vende-se o autocarro que esta ali" nunca foi o dele.

O que NAO volta e a janela aberta de Agosto, que foi o que correu mal — o
balcao abria com 14 viagens das quais 3 estavam a acontecer, e as outras eram a
mesma rota repetida dia apos dia. A antecedencia volta com a data PEDIDA:

* sem `?date=`, a lista e a de hoje, identica a que estes testes ja fixavam;
* com `?date=AAAA-MM-DD`, sao as partidas desse dia e so desse, ate 30 dias.

A diferenca esta em quem escolhe. Em Agosto a viagem de amanha estava na lista
a espera de um toque a mais; agora e preciso pedir o dia.

`Trip.sellable_statuses_for` continua a permitir a venda a uma partida agendada
— o portal publico usa-a para a venda antecipada pelo site. O que mudou foi o
que o BALCAO ve.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Agent, Trip, Vehicle


class _CenarioDoBalcao:
    """Cenario partilhado pelas duas listas — a de hoje e a do dia pedido.

    Mixin, e nao heranca entre as classes de teste: as duas correm contra o
    mesmo mundo, mas herdar uma da outra punha os testes da primeira a correr
    duas vezes sem provar nada de novo.
    """

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="balcao", password="x", email="balcao@x.mz", phone="849000001")
        Agent.objects.create(full_name="Agente", user=self.user, status=Agent.Status.ACTIVE)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.viatura = Vehicle.objects.create(registration="AAA-01-MP", seated_capacity=40)

    def _rota(self, code, service_type):
        rota = Route.objects.create(
            code=code, name=code, service_type=service_type, status=Route.Status.ACTIVE)
        a = Stop.objects.create(code=f"{code}-A", name="A", status="active")
        b = Stop.objects.create(code=f"{code}-B", name="B", status="active")
        RouteStop.objects.create(route=rota, stop=a, sequence=1, direction="outbound")
        RouteStop.objects.create(route=rota, stop=b, sequence=2, direction="outbound")
        return rota

    def _viagem(self, rota, status, partida):
        return Trip.objects.create(
            route=rota, vehicle=self.viatura, status=status, planned_departure_at=partida)

    def ids_listados(self):
        r = self.client.get("/api/agent/trips/")
        self.assertEqual(r.status_code, 200, r.content)
        return {t["id"] for t in r.json()}

    def ids_do_dia(self, quando):
        """A lista com o dia pedido de proposito — a venda antecipada."""
        r = self.client.get("/api/agent/trips/", {"date": quando.strftime("%Y-%m-%d")})
        self.assertEqual(r.status_code, 200, r.content)
        return {t["id"] for t in r.json()}


class PartidasNoBalcaoTests(_CenarioDoBalcao, TestCase):
    def test_partida_agendada_de_hoje_aparece_no_balcao(self):
        """A viagem criada no portal nasce `agendada` e tem de aparecer.

        Era este o incidente original: o cliente criava a viagem no portal, ia
        ao POS, e a lista estava vazia. Chegou a estar escondida outra vez, e
        voltou quando a primeira venda passou a abrir o embarque — ver
        `tests_lista_de_venda`, que conta a historia toda.
        """
        rota = self._rota("R-INT", Route.ServiceType.INTERNATIONAL)
        viagem = self._viagem(rota, Trip.Status.SCHEDULED, timezone.now() + timedelta(minutes=90))
        self.assertIn(viagem.id, self.ids_listados())

    def test_abrir_o_embarque_poe_a_viagem_a_venda(self):
        """O outro lado da mesma regra — sem isto nao havia como vender nada."""
        rota = self._rota("R-INT-B", Route.ServiceType.INTERNATIONAL)
        viagem = self._viagem(rota, Trip.Status.BOARDING, timezone.now() + timedelta(minutes=90))
        self.assertIn(viagem.id, self.ids_listados())

    def test_partida_de_amanha_nao_aparece_na_lista_de_hoje(self):
        """A venda antecipada existe, mas nao se intromete na lista de hoje.

        E esta a licao de Agosto: a viagem de amanha na lista por omissao era a
        14a linha visualmente igual as outras, a espera de um toque distraido.
        Continua fora dela. Quem quer amanha, pede amanha — ver
        `test_partida_de_amanha_aparece_quando_se_pede_o_dia`.
        """
        rota = self._rota("R-INT-AM", Route.ServiceType.INTERNATIONAL)
        viagem = self._viagem(rota, Trip.Status.SCHEDULED, timezone.now() + timedelta(days=1))
        self.assertNotIn(viagem.id, self.ids_listados())

    def test_partida_agendada_de_rota_urbana_nao_aparece(self):
        """Na urbana vende-se o autocarro que esta ali, nao o de amanha.

        Vale para a lista de hoje e para a data pedida — ver
        `test_urbana_nao_entra_na_venda_antecipada`.
        """
        rota = self._rota("R-URB", Route.ServiceType.URBAN)
        viagem = self._viagem(rota, Trip.Status.SCHEDULED, timezone.now() + timedelta(days=1))
        self.assertNotIn(viagem.id, self.ids_listados())

    def test_urbana_em_embarque_aparece(self):
        rota = self._rota("R-URB2", Route.ServiceType.URBAN)
        viagem = self._viagem(rota, Trip.Status.BOARDING, timezone.now())
        self.assertIn(viagem.id, self.ids_listados())

    def test_partida_atrasada_ja_em_embarque_continua_a_venda(self):
        """O autocarro atrasa-se; enquanto o embarque estiver aberto, vende."""
        rota = self._rota("R-INT2", Route.ServiceType.INTERNATIONAL)
        viagem = self._viagem(rota, Trip.Status.BOARDING, timezone.now() - timedelta(hours=1))
        self.assertIn(viagem.id, self.ids_listados())

    def test_partida_de_daqui_a_um_mes_nao_enche_a_lista(self):
        rota = self._rota("R-INT3", Route.ServiceType.INTERNATIONAL)
        viagem = self._viagem(rota, Trip.Status.SCHEDULED, timezone.now() + timedelta(days=30))
        self.assertNotIn(viagem.id, self.ids_listados())

    def test_partida_encerrada_nao_aparece(self):
        rota = self._rota("R-INT4", Route.ServiceType.INTERNATIONAL)
        viagem = self._viagem(rota, Trip.Status.COMPLETED, timezone.now() + timedelta(hours=2))
        self.assertNotIn(viagem.id, self.ids_listados())

    def test_tarifa_de_partida_agendada_e_calculavel(self):
        """Sem isto o agente ve a partida na lista e leva com erro ao avancar."""
        from apps.fares.models import FareProduct, FareRule

        rota = self._rota("R-INT5", Route.ServiceType.INTERNATIONAL)
        produto = FareProduct.objects.create(
            name="Avulso", product_type="single_trip", status="active")
        FareRule.objects.create(
            fare_product=produto, route=rota,
            calculation_method=FareRule.CalculationMethod.FIXED,
            fixed_amount=Decimal("1500.00"),
        )
        viagem = self._viagem(rota, Trip.Status.SCHEDULED, timezone.now() + timedelta(days=1))
        paragens = list(RouteStop.objects.filter(route=rota).order_by("sequence"))
        r = self.client.post(
            f"/api/agent/trips/{viagem.id}/fare/",
            {"origin_stop_id": paragens[0].stop_id, "destination_stop_id": paragens[1].stop_id},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["fare_amount"], "1500.00")


class VendaAntecipadaTests(_CenarioDoBalcao, TestCase):
    """A antecedencia com a data pedida — reposta em 2026-09-03."""

    def test_partida_de_amanha_aparece_quando_se_pede_o_dia(self):
        """O caso que motivou tudo: o agente de recepcao vende para amanha."""
        rota = self._rota("R-ANT-1", Route.ServiceType.INTERNATIONAL)
        amanha = timezone.localtime() + timedelta(days=1)
        viagem = self._viagem(rota, Trip.Status.SCHEDULED, amanha)
        self.assertIn(viagem.id, self.ids_do_dia(amanha))

    def test_o_dia_pedido_traz_so_esse_dia(self):
        """Senao era a lista de Agosto outra vez, so que com um botao a frente."""
        rota = self._rota("R-ANT-2", Route.ServiceType.INTERPROVINCIAL)
        amanha = timezone.localtime() + timedelta(days=1)
        depois = timezone.localtime() + timedelta(days=2)
        de_amanha = self._viagem(rota, Trip.Status.SCHEDULED, amanha)
        de_depois = self._viagem(rota, Trip.Status.SCHEDULED, depois)
        listados = self.ids_do_dia(amanha)
        self.assertIn(de_amanha.id, listados)
        self.assertNotIn(de_depois.id, listados)

    def test_pedir_hoje_da_a_lista_de_hoje_com_o_que_circula(self):
        """Nao ha duas verdades para o mesmo dia.

        Uma viagem em embarque sem hora de partida so aparece pelo ramo do
        "esta a circular". Se `?date=hoje` fosse uma consulta a parte, ela
        desaparecia — e o agente que carregasse em "hoje" via menos do que
        antes de carregar.
        """
        rota = self._rota("R-ANT-3", Route.ServiceType.INTERNATIONAL)
        circulando = Trip.objects.create(
            route=rota, vehicle=self.viatura, status=Trip.Status.BOARDING)
        self.assertIn(circulando.id, self.ids_do_dia(timezone.localtime()))

    def test_urbana_nao_entra_na_venda_antecipada(self):
        """Nao se reserva o autocarro urbano de quinta — entra-se no que esta la."""
        rota = self._rota("R-ANT-URB", Route.ServiceType.URBAN)
        amanha = timezone.localtime() + timedelta(days=1)
        viagem = self._viagem(rota, Trip.Status.SCHEDULED, amanha)
        self.assertNotIn(viagem.id, self.ids_do_dia(amanha))

    def test_viagem_ja_encerrada_num_dia_futuro_nao_se_vende(self):
        """Uma partida futura que nao esta `agendada` e erro de dados."""
        rota = self._rota("R-ANT-4", Route.ServiceType.INTERNATIONAL)
        amanha = timezone.localtime() + timedelta(days=1)
        viagem = self._viagem(rota, Trip.Status.COMPLETED, amanha)
        self.assertNotIn(viagem.id, self.ids_do_dia(amanha))

    def test_dia_alem_do_limite_diz_porque(self):
        """Lista vazia nao explicava nada; o limite tem de se anunciar."""
        alem = (timezone.localtime() + timedelta(days=31)).strftime("%Y-%m-%d")
        r = self.client.get("/api/agent/trips/", {"date": alem})
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("30", r.json()["detail"])

    def test_dia_que_ja_passou_e_recusado(self):
        ontem = (timezone.localtime() - timedelta(days=1)).strftime("%Y-%m-%d")
        r = self.client.get("/api/agent/trips/", {"date": ontem})
        self.assertEqual(r.status_code, 400, r.content)

    def test_data_com_lixo_nao_rebenta(self):
        r = self.client.get("/api/agent/trips/", {"date": "amanha"})
        self.assertEqual(r.status_code, 400, r.content)

    def test_data_vazia_e_a_lista_de_hoje(self):
        """O POS manda `date=` vazio quando o agente limpa a escolha."""
        rota = self._rota("R-ANT-5", Route.ServiceType.INTERNATIONAL)
        viagem = self._viagem(rota, Trip.Status.SCHEDULED, timezone.now() + timedelta(hours=2))
        r = self.client.get("/api/agent/trips/", {"date": ""})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn(viagem.id, {t["id"] for t in r.json()})
