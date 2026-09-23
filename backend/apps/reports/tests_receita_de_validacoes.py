# -*- coding: utf-8 -*-
"""Uma validacao de passe digital NAO e receita.

O `amount_debited` de um `ValidationEvent` quer dizer duas coisas conforme o
tipo. Num pay-as-you-go saiu saldo naquele momento: e receita. Num passe
digital o bilhete ja foi pago na compra, e o campo guarda apenas quanto esse
bilhete valia — para o manifesto saber o valor de quem embarcou.

O painel somava o campo todo. A TPM-TUR nao usa cartoes nem saldo: as sete
validacoes que tinha eram passes digitais, e a receita aparecia inflacionada
em 10 900,00 MZN sobre 55 450,00 — 20% a mais, sobre dinheiro que nunca
existiu. O cliente reparou antes de nos, e por duas vezes eu expliquei a
diferenca em vez de perguntar se ela devia existir.

O repositorio ja tinha a conta certa, em `apps.trips.revenue`, que exclui
estes eventos do total e lhes chama `nominal_value`. Eram duas implementacoes
da mesma coisa a discordar. Estes testes existem para que voltem a discordar
seja uma falha, e nao uma descoberta de um cliente seis meses depois.
"""
from __future__ import annotations

import secrets
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.reports.analytics import build_analytics
from apps.routes.models import Route
from apps.trips.models import Trip
from apps.validations.models import COBRA_NO_EMBARQUE, ValidationEvent


class Base(TestCase):
    """Dados inventados. Este repositorio e publico."""

    def setUp(self):
        self.rota = Route.objects.create(code="RT-VAL", name="Maputo x Nelspruit")
        agora = timezone.now()
        self.viagem = Trip.objects.create(
            route=self.rota, planned_departure_at=agora + timedelta(hours=6),
            direction="outbound",
        )
        self.params = {
            "date_from": (agora - timedelta(days=1)).date().isoformat(),
            "date_to": (agora + timedelta(days=1)).date().isoformat(),
        }

    def bilhete(self, valor="1650.00"):
        gc = GuestCheckout.objects.create(
            reference=f"GC-{GuestCheckout.objects.count():06d}",
            payer_phone="841234567", trip=self.viagem, quantity=1,
            unit_amount=Decimal(valor), total_amount=Decimal(valor),
            status=GuestCheckout.Status.ISSUED,
        )
        return DigitalTravelPass.objects.create(
            guest_checkout=gc, token=secrets.token_urlsafe(24),
            token_hash=secrets.token_hex(30), trip=self.viagem,
            route_code=self.rota.code, route_name=self.rota.name,
            passenger_name="Passageiro Um",
            departure_at=self.viagem.planned_departure_at,
            fare_amount=Decimal(valor), leg="outbound", status="active",
        )

    def validacao(self, tipo, valor="1650.00", passe=None):
        return ValidationEvent.objects.create(
            validation_type=tipo, route=self.rota, trip=self.viagem,
            digital_travel_pass=passe,
            amount_debited=Decimal(valor),
            status=ValidationEvent.Status.APPROVED,
            idempotency_key=secrets.token_hex(16),
        )

    def kpis(self):
        return build_analytics(self.params)["kpis"]


class ReceitaDeValidacoes(Base):
    def test_embarcar_um_bilhete_nao_acrescenta_receita(self):
        """O caso da TPM-TUR: bilhete comprado, depois validado a bordo."""
        passe = self.bilhete("1650.00")
        self.validacao(ValidationEvent.ValidationType.GUEST_DIGITAL_TRAVEL_PASS,
                       "1650.00", passe=passe)
        k = self.kpis()
        self.assertEqual(k["ticket_revenue"], "1650.00")
        self.assertEqual(k["validation_revenue"], "0.00")
        # 1650, e nao 3300: o bilhete conta uma vez, nao duas.
        self.assertEqual(k["transport_revenue"], "1650.00")

    def test_o_valor_embarcado_nao_se_perde(self):
        """Nao e receita, mas continua a ser informacao: quem embarcou valia isto."""
        passe = self.bilhete("1650.00")
        self.validacao(ValidationEvent.ValidationType.GUEST_DIGITAL_TRAVEL_PASS,
                       "1650.00", passe=passe)
        k = self.kpis()
        self.assertEqual(k["validations_nominal"], "1650.00")
        self.assertEqual(k["validations"], 1)

    def test_pagar_do_saldo_a_bordo_e_receita(self):
        """O outro lado: aqui o dinheiro move-se mesmo no embarque."""
        self.validacao(ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO, "100.00")
        k = self.kpis()
        self.assertEqual(k["validation_revenue"], "100.00")
        self.assertEqual(k["validations_nominal"], "0.00")
        self.assertEqual(k["transport_revenue"], "100.00")

    def test_os_dois_juntos_somam_uma_vez_cada(self):
        passe = self.bilhete("1650.00")
        self.validacao(ValidationEvent.ValidationType.GUEST_DIGITAL_TRAVEL_PASS,
                       "1650.00", passe=passe)
        self.validacao(ValidationEvent.ValidationType.QR_PAY_AS_YOU_GO, "100.00")
        k = self.kpis()
        self.assertEqual(k["transport_revenue"], "1750.00")

    def test_a_receita_por_rota_nao_conta_o_bilhete_duas_vezes(self):
        passe = self.bilhete("1650.00")
        self.validacao(ValidationEvent.ValidationType.GUEST_DIGITAL_TRAVEL_PASS,
                       "1650.00", passe=passe)
        rotas = build_analytics(self.params)["top_routes"]
        linha = next(r for r in rotas if r["route_code"] == self.rota.code)
        self.assertEqual(Decimal(linha["revenue"]), Decimal("1650.00"))

    def test_a_serie_diaria_nao_conta_o_bilhete_duas_vezes(self):
        passe = self.bilhete("1650.00")
        self.validacao(ValidationEvent.ValidationType.GUEST_DIGITAL_TRAVEL_PASS,
                       "1650.00", passe=passe)
        serie = build_analytics(self.params)["revenue_series"]
        self.assertEqual(
            sum(Decimal(d["validations"]) for d in serie), Decimal("0.00"))
        self.assertEqual(
            sum(Decimal(d["tickets"]) for d in serie), Decimal("1650.00"))


class UmaSoFonteDeVerdade(TestCase):
    """As duas implementacoes tem de concordar — foi a discordancia o erro."""

    def test_trips_revenue_usa_a_mesma_lista(self):
        from apps.trips.revenue import PAY_AS_YOU_GO_VALIDATION_TYPES
        self.assertEqual(tuple(PAY_AS_YOU_GO_VALIDATION_TYPES),
                         tuple(COBRA_NO_EMBARQUE))

    def test_todo_o_tipo_novo_tem_de_escolher_um_lado(self):
        """Se alguem acrescentar um ValidationType, este teste obriga-o a vir aqui.

        Deixar um tipo novo de fora por omissao e exactamente como o passe
        digital entrou na receita: ninguem decidiu, so aconteceu.
        """
        conhecidos = {
            ValidationEvent.ValidationType.CARD_PAY_AS_YOU_GO,
            ValidationEvent.ValidationType.QR_PAY_AS_YOU_GO,
            ValidationEvent.ValidationType.DIGITAL_TRAVEL_PASS,
            ValidationEvent.ValidationType.GUEST_DIGITAL_TRAVEL_PASS,
        }
        self.assertEqual(
            set(ValidationEvent.ValidationType), conhecidos,
            "Ha um tipo de validacao novo. Decida se COBRA_NO_EMBARQUE o inclui "
            "(o passageiro paga no momento) ou nao (o bilhete ja foi pago), e "
            "acrescente-o a este teste.",
        )
