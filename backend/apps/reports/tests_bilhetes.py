# -*- coding: utf-8 -*-
"""O relatorio de bilhetes por passageiro.

Nasceu de uma folha de Excel que a TPM-TUR mantinha a mao ao lado do sistema:
uma linha por pessoa que viaja, com o nome, o tipo de viagem, as duas datas e
o valor. O relatorio de Vendas que ja existia conta PAGAMENTOS — uma familia
de tres e uma linha so, e o nome de quem viaja nao aparece em lado nenhum.

O que estes testes protegem e a juncao: no sistema, uma ida-e-volta sao DOIS
bilhetes; na folha do operador e UMA linha com as duas datas e o valor das
duas. Se a juncao falhar, ele ve o dobro das linhas e metade dos valores, e
deixa de confiar no relatorio — que era o ponto de o fazer.
"""
from __future__ import annotations

import secrets
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.reports.builder import REGISTRY, aggregate_totals
from apps.routes.models import Route
from apps.trips.models import Trip


class Base(TestCase):
    """Os dados daqui sao inventados, e tem de continuar a se-lo.

    Este repositorio e publico. Nomes de passageiros e numeros de telefone
    vindos da base de producao — ou da folha que o operador manda por
    WhatsApp — nao entram em testes. O numero segue a convencao que o resto
    do repo ja usa (`841234567`).
    """

    def setUp(self):
        self.rota = Route.objects.create(code="RT-TESTE", name="Maputo x Nelspruit")
        agora = timezone.now()
        self.ida = Trip.objects.create(
            route=self.rota, planned_departure_at=agora + timedelta(days=3),
            direction="outbound",
        )
        self.volta = Trip.objects.create(
            route=self.rota, planned_departure_at=agora + timedelta(days=3, hours=10),
            direction="inbound",
        )
        self.spec = REGISTRY["tickets"]
        self.filtros = {
            "date_from": agora - timedelta(days=1),
            "date_to": agora + timedelta(days=1),
        }

    def venda(self, *, volta=False, quantidade=1):
        return GuestCheckout.objects.create(
            reference=f"GC-{GuestCheckout.objects.count():06d}",
            payer_phone="841234567", trip=self.ida,
            return_trip=self.volta if volta else None,
            quantity=quantidade,
            unit_amount=Decimal("1650.00"),
            return_unit_amount=Decimal("1650.00") if volta else None,
            total_amount=Decimal("3300.00") if volta else Decimal("1650.00"),
            status=GuestCheckout.Status.ISSUED,
        )

    def bilhete(self, gc, nome, *, leg="outbound", codigo="", documento="", estado="active"):
        # `token` e `token_hash` sao unicos: e o que valida o bilhete a porta
        # do autocarro, e dois bilhetes nao podem partilhar um.
        token = secrets.token_urlsafe(24)
        return DigitalTravelPass.objects.create(
            guest_checkout=gc,
            token=token, token_hash=secrets.token_hex(30),
            trip=self.volta if leg == "return" else self.ida,
            route_code=self.rota.code, route_name=self.rota.name,
            passenger_name=nome, document_number=documento,
            departure_at=(self.volta if leg == "return" else self.ida).planned_departure_at,
            fare_amount=Decimal("1650.00"), leg=leg, short_code=codigo, status=estado,
        )

    def linhas(self, **extra):
        return list(self.spec.build_rows({**self.filtros, **extra}))


class UmaLinhaPorPassageiro(Base):
    def test_uma_ida_simples_da_uma_linha(self):
        gc = self.venda()
        self.bilhete(gc, "Passageiro Um", codigo="AB1201")

        (linha,) = self.linhas()
        self.assertEqual(linha["passageiro"], "Passageiro Um")
        self.assertEqual(linha["tipo_de_viagem"], "So ida")
        self.assertEqual(linha["bilhete"], "AB1201")
        self.assertIsNotNone(linha["ida_at"])
        self.assertIsNone(linha["regresso_at"], "uma ida simples nao tem regresso")
        self.assertEqual(Decimal(linha["fare_amount"]), Decimal("1650.00"))

    def test_uma_ida_e_volta_da_UMA_linha_com_as_duas_datas(self):
        """O teste que justifica este relatorio existir.

        No sistema sao dois bilhetes. Na folha do operador e uma linha. Se
        saissem duas, ele via o dobro das viagens e metade do valor em cada.
        """
        gc = self.venda(volta=True)
        self.bilhete(gc, "Passageiro Um", leg="outbound", codigo="AB1201")
        self.bilhete(gc, "Passageiro Um", leg="return", codigo="AB1202")

        (linha,) = self.linhas()
        self.assertEqual(linha["tipo_de_viagem"], "Ida e volta")
        self.assertIsNotNone(linha["ida_at"])
        self.assertIsNotNone(linha["regresso_at"])
        self.assertLess(linha["ida_at"], linha["regresso_at"], "o regresso vem depois da ida")
        self.assertEqual(Decimal(linha["fare_amount"]), Decimal("3300.00"),
                         "o valor da linha e o que o passageiro pagou pelas duas pernas")
        self.assertEqual(linha["bilhete"], "AB1201 / AB1202", "os dois codigos, os dois validam")

    def test_dois_passageiros_na_mesma_compra_dao_duas_linhas(self):
        """O relatorio de Vendas poe uma familia de tres numa linha so. Aqui
        cada pessoa tem a sua, que e o que o operador precisa a porta do
        autocarro."""
        gc = self.venda(quantidade=2)
        self.bilhete(gc, "Passageiro Um", codigo="AB1201")
        self.bilhete(gc, "Passageira Dois", codigo="AB1202")

        # Conjunto e nao lista: o que se prova e que sao DUAS linhas, uma por
        # pessoa. A ordem em que saem nao faz parte da promessa — e prende-la
        # aqui significa que mudar um nome no teste o parte, que foi o que
        # aconteceu.
        nomes = {l["passageiro"] for l in self.linhas()}
        self.assertEqual(nomes, {"Passageiro Um", "Passageira Dois"})

    def test_dois_irmaos_com_o_mesmo_nome_nao_se_fundem(self):
        """As pernas emparelham-se pelo nome E pelo documento.

        So pelo nome, dois homonimos na mesma compra — que numa familia
        acontece — apareciam colados numa linha, com quatro codigos e o dobro
        do valor.
        """
        gc = self.venda(volta=True, quantidade=2)
        for doc, codigo in (("AB111", "C1"), ("AB222", "C3")):
            self.bilhete(gc, "Homonimo Teste", leg="outbound", documento=doc, codigo=codigo)
            self.bilhete(gc, "Homonimo Teste", leg="return", documento=doc, codigo=codigo + "b")

        linhas = self.linhas()
        self.assertEqual(len(linhas), 2)
        for l in linhas:
            self.assertEqual(Decimal(l["fare_amount"]), Decimal("3300.00"))

    def test_o_nome_emparelha_sem_olhar_a_maiusculas(self):
        gc = self.venda(volta=True)
        self.bilhete(gc, "Passageiro Um", leg="outbound", codigo="A1")
        self.bilhete(gc, "PASSAGEIRO UM", leg="return", codigo="A2")
        self.assertEqual(len(self.linhas()), 1)

    def test_a_mesma_pessoa_em_duas_compras_da_duas_linhas(self):
        """Sao duas viagens compradas, e contam como duas."""
        for _ in range(2):
            self.bilhete(self.venda(), "Passageiro Um", codigo="A1")
        self.assertEqual(len(self.linhas()), 2)


class OEstadoEOsTotais(Base):
    def test_uma_perna_cancelada_marca_a_linha(self):
        """Um bilhete cancelado numa das pernas nao pode passar por activo na
        linha inteira — quem le o relatorio decidiria que a viagem esta de pe."""
        gc = self.venda(volta=True)
        self.bilhete(gc, "Passageiro Um", leg="outbound", codigo="A1")
        self.bilhete(gc, "Passageiro Um", leg="return", codigo="A2", estado="cancelled")

        (linha,) = self.linhas()
        self.assertEqual(linha["status"], "cancelled")

    def test_os_cancelados_nao_entram_no_total(self):
        """Um bilhete devolvido nao e receita. Somar tudo da sempre mais do
        que a conta, e o erro so aparece na reconciliacao."""
        self.bilhete(self.venda(), "Quem viaja", codigo="A1")
        self.bilhete(self.venda(), "Quem desistiu", codigo="A2", estado="cancelled")

        linhas = self.linhas()
        totais = aggregate_totals(self.spec, linhas)
        self.assertEqual(totais["count"], 2, "as duas linhas aparecem")
        self.assertEqual(totais["confirmed_count"], 1)
        self.assertEqual(Decimal(totais["total_amount"]), Decimal("1650.00"))

    def test_o_filtro_de_estado(self):
        self.bilhete(self.venda(), "Activo", codigo="A1")
        self.bilhete(self.venda(), "Cancelado", codigo="A2", estado="cancelled")
        nomes = [l["passageiro"] for l in self.linhas(status="cancelled")]
        self.assertEqual(nomes, ["Cancelado"])


class AsColunas(Base):
    def test_a_folha_do_operador_esta_toda_la(self):
        """As colunas que ele pediu, pelos nomes por que as conhece."""
        rotulos = {label for _, label in self.spec.columns}
        for pedido in ("Data da compra", "Nome do passageiro", "Tipo de viagem",
                       "Ida", "Regresso", "Nr do bilhete", "Valor do bilhete"):
            self.assertIn(pedido, rotulos, f"falta a coluna «{pedido}»")

    def test_as_datas_vao_como_datas(self):
        """E nao como texto ja formatado: os exportadores e o ecra sabem
        apresenta-las, e uma data em texto deixa de se poder ordenar no Excel."""
        from datetime import datetime

        gc = self.venda(volta=True)
        self.bilhete(gc, "Passageiro Um", leg="outbound", codigo="A1")
        self.bilhete(gc, "Passageiro Um", leg="return", codigo="A2")

        (linha,) = self.linhas()
        for campo in ("created_at", "ida_at", "regresso_at"):
            self.assertIsInstance(linha[campo], datetime, campo)

    def test_toda_a_coluna_declarada_existe_na_linha(self):
        """Uma coluna sem chave na linha sai vazia no PDF, em silencio."""
        self.bilhete(self.venda(), "Passageiro Um", codigo="A1")
        (linha,) = self.linhas()
        for chave, _ in self.spec.columns:
            self.assertIn(chave, linha, f"a coluna «{chave}» nao existe na linha")
