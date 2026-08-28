"""Dois pedidos sobre o mesmo cartao, ao mesmo tempo.

A guarda de estado estava escrita ANTES do bloqueio:

    if card.status != INACTIVE:          # le sem travar
        raise CardError(...)
    with transaction.atomic():
        card = select_for_update()...    # so aqui e que trava

Entre a leitura e o bloqueio ha uma janela, e no cartao ela custa dinheiro:
duas atribuicoes do mesmo cartao a passageiros diferentes atravessavam a guarda
as duas. A primeira atribuia-o ao A e mandava-lhe SMS a dizer que o cartao era
dele; a segunda ficava com a ultima palavra e punha la a carteira do B. O A
tinha a confirmacao no telemovel e um cartao que descontava da conta de outra
pessoa.

Estes testes correm em fios a serio contra o Postgres — `TransactionTestCase`,
porque o `TestCase` embrulha tudo numa transaccao e esconde justamente aquilo
que se quer observar. Mesma forma dos testes do balcao, mesma razao.
"""

from __future__ import annotations

import threading
from decimal import Decimal

from django.db import connections
from django.test import TransactionTestCase

from apps.cards.models import Card
from apps.cards.services import CardError, assign_card_to_passenger, block_card, replace_card
from apps.passengers.models import PassengerAccount
from apps.wallets.models import Wallet


def em_simultaneo(fn, n=2):
    """Corre `fn(i)` em n fios ao mesmo tempo e devolve os resultados.

    A barreira garante que ninguem arranca antes de todos estarem prontos: sem
    ela os fios serializam-se sozinhos e o teste passa por acidente.
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


def _passageiro(nome, telefone):
    p = PassengerAccount.objects.create(
        full_name=nome, phone_number=telefone,
        status=PassengerAccount.Status.ACTIVE,
    )
    Wallet.objects.create(passenger_account=p)
    return p


class UmCartaoUmDonoTests(TransactionTestCase):
    def test_duas_atribuicoes_ao_mesmo_tempo_so_uma_vinga(self):
        """O cartao fica com UM dono, e o outro pedido recebe erro.

        Antes ficava com o dono do ultimo pedido a gravar, mas AMBOS eram
        dados como bem sucedidos — e ambos os passageiros recebiam SMS.
        """
        a = _passageiro("Ana", "849010001")
        b = _passageiro("Bento", "849010002")
        cartao = Card.objects.create(
            card_type=Card.CardType.PHYSICAL, card_uid="UID-DISPUTA",
            status=Card.Status.INACTIVE,
        )
        donos = [a, b]

        def atribuir(i):
            return assign_card_to_passenger(
                Card.objects.get(pk=cartao.pk), donos[i], notify_sms=False)

        r = em_simultaneo(atribuir)
        ganhou = [x for x in r if isinstance(x, Card)]
        recusou = [x for x in r if isinstance(x, CardError)]

        self.assertEqual(len(ganhou), 1, f"esperava uma atribuicao, obtive {r}")
        self.assertEqual(len(recusou), 1, f"esperava uma recusa, obtive {r}")

        cartao.refresh_from_db()
        self.assertEqual(cartao.passenger_account_id, ganhou[0].passenger_account_id)
        self.assertEqual(cartao.status, Card.Status.ACTIVE)

    def test_duas_substituicoes_ao_mesmo_tempo_nao_deixam_dois_cartoes_activos(self):
        """Duas substituicoes do mesmo cartao davam dois cartoes na mesma carteira.

        E os dois activos — o passageiro passava a ter duas chaves para o mesmo
        saldo, uma delas nas maos de quem foi ao balcao a seguir.
        """
        dono = _passageiro("Carla", "849010003")
        velho = assign_card_to_passenger(
            Card.objects.create(card_type=Card.CardType.PHYSICAL,
                                card_uid="UID-VELHO-C", status=Card.Status.INACTIVE),
            dono, notify_sms=False)
        carteira = dono.wallet
        carteira.balance_cached = Decimal("500.00")
        carteira.save(update_fields=["balance_cached"])

        novos = [
            Card.objects.create(card_type=Card.CardType.PHYSICAL,
                                card_uid=f"UID-SUB-{i}", status=Card.Status.INACTIVE)
            for i in range(2)
        ]

        def substituir(i):
            return replace_card(Card.objects.get(pk=velho.pk),
                                Card.objects.get(pk=novos[i].pk))

        r = em_simultaneo(substituir)
        ok = [x for x in r if isinstance(x, Card)]
        self.assertEqual(len(ok), 1, f"esperava uma substituicao, obtive {r}")

        activos = Card.objects.filter(wallet=carteira, status=Card.Status.ACTIVE)
        self.assertEqual(activos.count(), 1, "a carteira ficou com mais do que uma chave")
        self.assertEqual(activos.first().wallet.balance_cached, Decimal("500.00"))

    def test_dois_bloqueios_ao_mesmo_tempo_so_um_vinga(self):
        """Menos grave, mas a mesma janela: dois 200 para uma so accao."""
        dono = _passageiro("Dino", "849010004")
        cartao = assign_card_to_passenger(
            Card.objects.create(card_type=Card.CardType.PHYSICAL,
                                card_uid="UID-BLOQ", status=Card.Status.INACTIVE),
            dono, notify_sms=False)

        r = em_simultaneo(lambda i: block_card(Card.objects.get(pk=cartao.pk)))
        self.assertEqual(len([x for x in r if isinstance(x, Card)]), 1, r)
        self.assertEqual(len([x for x in r if isinstance(x, CardError)]), 1, r)

        cartao.refresh_from_db()
        self.assertEqual(cartao.status, Card.Status.BLOCKED)
