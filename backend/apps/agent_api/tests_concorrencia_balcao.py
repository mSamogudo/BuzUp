"""Dois operadores, ou o mesmo operador duas vezes, ao balcão em simultâneo.

O incidente que motivou estes testes: um bilhete foi emitido, falhou, outro
operador tentou e conseguiu, e a partir daí o sistema recusava com "já existe".

A causa é sempre a mesma forma escrita à mão em várias views — ler pela chave
de idempotência e, se não existir, criar. Entre a leitura e a escrita há uma
janela. Com a rede que estes terminais apanham, o POS repete o pedido e as duas
tentativas atravessam a leitura ao mesmo tempo: uma cria, a outra bate na
unique constraint e sai 500. O agente lê "erro" numa venda que afinal foi
feita, e volta a cobrar ao passageiro.

Estes testes correm pedidos HTTP a sério, em paralelo, contra o Postgres —
`TransactionTestCase` porque o `TestCase` embrulha tudo numa transacção e
esconde exactamente aquilo que se quer observar.
"""

from __future__ import annotations

import threading
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cards.models import Card
from apps.fares.models import FareProduct, FareRule
from apps.guest_checkouts.models import GuestCheckout
from apps.passengers.models import PassengerAccount
from apps.payments.models import PaymentIntent
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Agent, Driver, Trip, Vehicle
from apps.wallets.models import Wallet, WalletTransaction

CHAVE = "pos-mesma-chave-para-as-duas-tentativas"


def em_simultaneo(fn, n=2):
    """Corre `fn(i)` em n threads soltas ao mesmo tempo e devolve os resultados.

    A barreira garante que ninguém arranca antes de todos estarem prontos: sem
    ela as threads serializam-se sozinhas e o teste passava por acidente.
    """
    resultados: list = [None] * n
    barreira = threading.Barrier(n)

    def trabalhador(i):
        try:
            barreira.wait(timeout=10)
            resultados[i] = fn(i)
        except Exception as exc:
            resultados[i] = exc
        finally:
            connections.close_all()

    fios = [threading.Thread(target=trabalhador, args=(i,)) for i in range(n)]
    for f in fios:
        f.start()
    for f in fios:
        f.join(timeout=40)
    return resultados


class BalcaoBase(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        User = get_user_model()
        self.rota = Route.objects.create(
            code="R-BAL", name="Balcao", service_type=Route.ServiceType.URBAN,
            status=Route.Status.ACTIVE,
        )
        self.origem = Stop.objects.create(code="BAL-A", name="Paragem A", status="active")
        self.destino = Stop.objects.create(code="BAL-B", name="Paragem B", status="active")
        RouteStop.objects.create(route=self.rota, stop=self.origem, sequence=1, direction="outbound")
        RouteStop.objects.create(route=self.rota, stop=self.destino, sequence=2, direction="outbound")

        produto = FareProduct.objects.create(
            name="Avulso Balcao", product_type="single_trip", status="active")
        FareRule.objects.create(
            fare_product=produto, route=self.rota,
            calculation_method=FareRule.CalculationMethod.FIXED,
            fixed_amount=Decimal("50.00"),
        )

        self.viatura = Vehicle.objects.create(registration="BAL-01-MP", seated_capacity=40)
        self.motorista = Driver.objects.create(full_name="Motorista Balcao")
        self.viagem = Trip.objects.create(
            route=self.rota, vehicle=self.viatura, driver=self.motorista,
            status=Trip.Status.BOARDING, planned_departure_at=timezone.now(),
        )

        self.operador = self.cria_operador("balcao1")

    def cria_operador(self, username):
        User = get_user_model()
        user = User.objects.create_user(
            username=username, password="x", email=f"{username}@x.mz",
            phone=f"84900{username[-1]}000",
        )
        Agent.objects.create(
            full_name=f"Agente {username}", user=user, status=Agent.Status.ACTIVE,
        )
        return user

    def cliente(self, user=None):
        c = APIClient()
        c.force_authenticate(user or self.operador)
        return c

    def carteira_com_cartao(self, saldo="1000.00", uid="CARD-BAL-1", telefone="849001111"):
        passageiro = PassengerAccount.objects.create(
            full_name="Passageiro Balcao", phone_number=telefone,
            status=PassengerAccount.Status.ACTIVE,
        )
        carteira = Wallet.objects.create(
            passenger_account=passageiro, balance_cached=Decimal(saldo), status="active",
        )
        cartao = Card.objects.create(
            card_uid=uid, passenger_account=passageiro, wallet=carteira,
            status=Card.Status.ACTIVE,
        )
        return passageiro, carteira, cartao


class VendaRepetidaTests(BalcaoBase):
    """A venda que o POS repete porque não soube se a primeira chegou."""

    def vende(self, chave, user=None):
        return self.cliente(user).post(
            "/api/agent/sales/",
            {
                "trip_id": self.viagem.id,
                "origin_stop_id": self.origem.id,
                "destination_stop_id": self.destino.id,
                "passenger_phone": "849002222",
                "quantity": 1,
                # Sem contactar o gateway: aqui mede-se a idempotencia, nao o
                # M-Pesa — e em staging o gateway e o de verdade.
                "auto_request_payment": False,
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY=chave,
        )

    def test_duas_tentativas_ao_mesmo_tempo_dao_uma_venda_so(self):
        respostas = em_simultaneo(lambda i: self.vende(CHAVE))

        for r in respostas:
            self.assertNotIsInstance(r, Exception, f"o pedido rebentou: {r}")
            self.assertLess(
                r.status_code, 500,
                f"o agente viu um erro de servidor numa venda repetida: {getattr(r, 'data', None)}",
            )

        self.assertEqual(
            GuestCheckout.objects.count(), 1,
            "a mesma chave de idempotencia nao pode abrir duas vendas",
        )
        self.assertEqual(PaymentIntent.objects.count(), 1)

        referencias = {r.data.get("sale_reference") for r in respostas}
        self.assertEqual(
            len(referencias), 1,
            "as duas tentativas tem de apontar para a MESMA venda — senao o "
            "agente entrega dois bilhetes de uma so cobranca",
        )
        self.assertTrue(
            any(r.data.get("duplicate") for r in respostas),
            "a repeticao tem de vir marcada, para o POS nao imprimir duas vezes",
        )

    def test_repetir_depois_devolve_a_mesma_venda(self):
        """O caso do incidente: tentar outra vez, mais tarde, com a mesma chave."""
        primeira = self.vende(CHAVE)
        self.assertEqual(primeira.status_code, 201)

        segunda = self.vende(CHAVE)
        self.assertEqual(
            segunda.status_code, 200,
            "repetir nao pode dar erro: a venda existe e e essa que se devolve",
        )
        self.assertTrue(segunda.data["duplicate"])
        self.assertEqual(segunda.data["sale_reference"], primeira.data["sale_reference"])
        self.assertEqual(GuestCheckout.objects.count(), 1)

    def test_chave_igual_de_operadores_diferentes_sao_vendas_diferentes(self):
        """Dois balcoes nao partilham o espaco de chaves.

        O POS gera a chave sozinho e nao sabe o que os outros geraram. Sem
        separar por operador, o segundo agente recebia a venda do primeiro —
        e ficava sem conseguir vender ao passageiro que tinha a frente.
        """
        outro = self.cria_operador("balcao2")

        self.assertEqual(self.vende(CHAVE).status_code, 201)
        segunda = self.vende(CHAVE, user=outro)

        self.assertEqual(segunda.status_code, 201)
        self.assertFalse(segunda.data.get("duplicate"))
        self.assertEqual(GuestCheckout.objects.count(), 2)


class RecargaRepetidaTests(BalcaoBase):
    """Recarregar a carteira duas vezes é dinheiro a mais na conta."""

    def recarrega(self, chave, uid, valor="200.00"):
        return self.cliente().post(
            "/api/agent/topups/wallet/",
            {"card_uid": uid, "amount": valor, "method": "cash"},
            format="json",
            HTTP_IDEMPOTENCY_KEY=chave,
        )

    def test_duas_recargas_simultaneas_creditam_uma_vez(self):
        _, carteira, cartao = self.carteira_com_cartao(saldo="100.00", uid="CARD-BAL-TOP")

        # Quatro tentativas e nao duas: com duas, a primeira muitas vezes fecha
        # antes de a segunda comecar e a corrida nem chega a acontecer.
        respostas = em_simultaneo(lambda i: self.recarrega(CHAVE, cartao.card_uid), n=4)
        for r in respostas:
            self.assertNotIsInstance(r, Exception, f"o pedido rebentou: {r}")
            self.assertLess(r.status_code, 500, getattr(r, "data", None))

        carteira.refresh_from_db()
        self.assertEqual(
            carteira.balance_cached, Decimal("300.00"),
            "a mesma recarga foi creditada duas vezes",
        )
        self.assertEqual(PaymentIntent.objects.count(), 1)


class DebitoRepetidoTests(BalcaoBase):
    """Cobrar duas vezes ao passageiro é o pior resultado possível."""

    def cobra(self, chave, uid, valor="50.00"):
        return self.cliente().post(
            "/api/agent/payments/wallet/",
            {"card_uid": uid, "amount": valor},
            format="json",
            HTTP_IDEMPOTENCY_KEY=chave,
        )

    def test_duas_cobrancas_simultaneas_debitam_uma_vez(self):
        _, carteira, cartao = self.carteira_com_cartao(saldo="500.00", uid="CARD-BAL-PAY")

        respostas = em_simultaneo(lambda i: self.cobra(CHAVE, cartao.card_uid), n=4)
        for r in respostas:
            self.assertNotIsInstance(r, Exception, f"o pedido rebentou: {r}")
            self.assertLess(
                r.status_code, 500,
                f"500 numa cobranca leva o agente a cobrar outra vez: {getattr(r, 'data', None)}",
            )

        carteira.refresh_from_db()
        self.assertEqual(
            carteira.balance_cached, Decimal("450.00"),
            "o passageiro foi cobrado duas vezes pela mesma viagem",
        )
        self.assertEqual(
            WalletTransaction.objects.filter(
                type=WalletTransaction.Type.FARE_DEBIT).count(), 1,
        )

    def test_duas_cobrancas_do_mesmo_agente_com_chaves_diferentes_passam_ambas(self):
        """A proteccao nao pode impedir o agente de vender ao cliente seguinte.

        A referencia sai de um resumo da chave inteira. Se saisse dos primeiros
        caracteres, o prefixo do operador tornava todas as suas cobrancas
        iguais — e a segunda venda do dia falhava.
        """
        _, carteira, cartao = self.carteira_com_cartao(saldo="500.00", uid="CARD-BAL-SEQ")

        self.assertEqual(self.cobra("pos-primeira", cartao.card_uid).status_code, 201)
        self.assertEqual(self.cobra("pos-segunda", cartao.card_uid).status_code, 201)

        carteira.refresh_from_db()
        self.assertEqual(carteira.balance_cached, Decimal("400.00"))
        self.assertEqual(
            WalletTransaction.objects.filter(
                type=WalletTransaction.Type.FARE_DEBIT).count(), 2,
        )
