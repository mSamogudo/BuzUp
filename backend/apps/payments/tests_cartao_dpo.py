"""Pagamento por cartao (DPO Pay) — do XML ao bilhete, sem rede.

O que se fixa aqui e o que o cartao tem de diferente: nunca ha sucesso
sincrono (e um redirect), e nenhuma das tres portas de regresso — a pagina, a
notificacao do DPO, o cron — confirma sem o `verifyToken` dizer que sim.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from apps.fares.models import FareProduct, FareRule
from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.payments.models import PaymentIntent
from apps.payments.services.card_gateway import (
    DpoCardGateway,
    DpoConfig,
    interpretar_verify,
    parse_dpo_xml,
)
from apps.payments.services.gateway import PaymentGatewayResult, get_payment_gateway
from apps.payments.services.reconciliation import referencia_para_consulta
from apps.routes.models import Route, RouteStop, Stop
from apps.trips.models import Trip, Vehicle

# Respostas com a forma documentada da API v6 do DPO.
XML_TOKEN_OK = """<?xml version="1.0" encoding="utf-8"?>
<API3G><Result>000</Result><ResultExplanation>Transaction created</ResultExplanation>
<TransToken>72983CAC-5DB1-4C7F-BD88-352066B71592</TransToken><TransRef>PAY-GC-ABC</TransRef></API3G>"""
XML_TOKEN_ERRO = """<API3G><Result>904</Result><ResultExplanation>Currency not supported</ResultExplanation></API3G>"""
XML_PAGO = """<API3G><Result>000</Result><ResultExplanation>Transaction Paid</ResultExplanation>
<TransactionApproval>123456</TransactionApproval><TransactionCurrency>MZN</TransactionCurrency>
<TransactionAmount>6600.00</TransactionAmount><TransactionRef>DPO-9911</TransactionRef>
<CustomerName>Jessica Cossa</CustomerName></API3G>"""
XML_NAO_PAGO = """<API3G><Result>900</Result><ResultExplanation>Transaction not paid yet</ResultExplanation></API3G>"""
XML_CANCELADO = """<API3G><Result>904</Result><ResultExplanation>Cancelled by customer</ResultExplanation></API3G>"""
XML_DESCONHECIDO = """<API3G><Result>777</Result><ResultExplanation>?</ResultExplanation></API3G>"""


def _cfg(**extra) -> DpoConfig:
    base = dict(company_token="TOKEN", service_type="3854",
                api_url="https://secure.3gdirectpay.com/API/v6/",
                payment_url="https://secure.3gdirectpay.com/payv2.php?ID=",
                currency="MZN", ptl_minutes=25, timeout=5)
    base.update(extra)
    return DpoConfig(**base)


class LeituraDoXmlTests(SimpleTestCase):
    def test_xml_plano_vira_dicionario(self):
        d = parse_dpo_xml(XML_TOKEN_OK)
        self.assertEqual(d["Result"], "000")
        self.assertEqual(d["TransToken"], "72983CAC-5DB1-4C7F-BD88-352066B71592")

    def test_lixo_nao_rebenta_nem_confirma(self):
        d = parse_dpo_xml("<html>502 Bad Gateway</html")
        self.assertIn("raw_response", d)
        self.assertNotIn("Result", d)
        self.assertEqual(parse_dpo_xml(""), {})


class InterpretacaoDoVerifyTests(SimpleTestCase):
    """Em dinheiro, na duvida, nao se confirma nem se cancela."""

    def test_000_e_pago_com_a_referencia_do_dpo(self):
        r = interpretar_verify(parse_dpo_xml(XML_PAGO), 200, "TOKEN-1")
        self.assertTrue(r.success)
        self.assertEqual(r.provider_reference, "DPO-9911")

    def test_900_ainda_nao_pagou(self):
        r = interpretar_verify(parse_dpo_xml(XML_NAO_PAGO), 200, "TOKEN-1")
        self.assertFalse(r.success)
        self.assertTrue(r.pending)

    def test_904_e_falha_e_liberta_o_lugar(self):
        r = interpretar_verify(parse_dpo_xml(XML_CANCELADO), 200, "TOKEN-1")
        self.assertFalse(r.success)
        self.assertFalse(r.pending)
        self.assertIn("cancelado", r.error.lower())

    def test_codigo_desconhecido_fica_pendente(self):
        r = interpretar_verify(parse_dpo_xml(XML_DESCONHECIDO), 200, "TOKEN-1")
        self.assertTrue(r.pending)

    def test_sem_resposta_fica_pendente(self):
        # Timeout nosso, 5xx, corpo sem XML: a mesma licao de 2026-09-03.
        for status, corpo in ((408, {"detail": "Request timed out.", "_timeout_local": True}),
                              (502, {"detail": "down"}),
                              (200, {"raw_response": "<html>"})):
            r = interpretar_verify(corpo, status, "TOKEN-1")
            self.assertTrue(r.pending, (status, corpo))
            self.assertFalse(r.success)


@override_settings(PAYMENTS_ALLOW_SANDBOX=False)
class IniciarPagamentoTests(SimpleTestCase):
    def test_token_criado_e_pendente_com_redirect(self):
        gw = DpoCardGateway(_cfg())
        with patch("apps.payments.services.card_gateway._post_xml",
                   return_value=(200, parse_dpo_xml(XML_TOKEN_OK))) as post:
            r = gw.initiate_payment("PAY-GC-ABC", Decimal("6600.00"), "843923574",
                                    redirect_url="https://buzup.test/comprar?ref=GC-ABC",
                                    buyer_name="Jessica Paulo Cossa")
        self.assertTrue(r.pending)
        self.assertFalse(r.success, "cartao nunca confirma na criacao do token")
        self.assertEqual(r.provider_reference, "72983CAC-5DB1-4C7F-BD88-352066B71592")
        self.assertTrue(r.redirect_url.endswith("payv2.php?ID=72983CAC-5DB1-4C7F-BD88-352066B71592"))
        xml_enviado = post.call_args.args[1]
        for pedaco in ("<Request>createToken</Request>", "<PaymentAmount>6600.00</PaymentAmount>",
                       "<PaymentCurrency>MZN</PaymentCurrency>", "<CompanyRef>PAY-GC-ABC</CompanyRef>",
                       "<CompanyRefUnique>1</CompanyRefUnique>", "<PTL>25</PTL>", "<PTLtype>minutes</PTLtype>",
                       "<customerFirstName>Jessica</customerFirstName>", "<ServiceType>3854</ServiceType>"):
            self.assertIn(pedaco, xml_enviado)

    def test_erro_do_dpo_e_falha_com_motivo(self):
        gw = DpoCardGateway(_cfg())
        with patch("apps.payments.services.card_gateway._post_xml",
                   return_value=(200, parse_dpo_xml(XML_TOKEN_ERRO))):
            r = gw.initiate_payment("PAY-GC-ABC", Decimal("10.00"), "843923574")
        self.assertFalse(r.pending)
        self.assertFalse(r.success)
        self.assertIn("Currency", r.error)

    def test_sem_configuracao_o_metodo_esta_desligado(self):
        gw = DpoCardGateway(_cfg(company_token=""))
        with patch("apps.payments.services.card_gateway._post_xml") as post:
            r = gw.initiate_payment("PAY-GC-ABC", Decimal("10.00"), "843923574")
        post.assert_not_called()
        self.assertFalse(r.pending)
        self.assertIn("M-Pesa", r.detail_message)

    def test_sandbox_em_producao_e_recusado_sem_contactar(self):
        gw = DpoCardGateway(_cfg(api_url="https://secure1.sandbox.directpay.online/API/v6/"))
        with patch("apps.payments.services.card_gateway._post_xml") as post:
            r = gw.initiate_payment("PAY-GC-ABC", Decimal("10.00"), "843923574")
        post.assert_not_called()
        self.assertIn("simulador", r.error)

    @override_settings(PAYMENTS_ALLOW_SANDBOX=True)
    def test_no_staging_o_sandbox_funciona(self):
        gw = DpoCardGateway(_cfg(api_url="https://secure1.sandbox.directpay.online/API/v6/",
                                 payment_url="https://secure1.sandbox.directpay.online/payv2.php?ID="))
        with patch("apps.payments.services.card_gateway._post_xml",
                   return_value=(200, parse_dpo_xml(XML_TOKEN_OK))):
            r = gw.initiate_payment("PAY-GC-ABC", Decimal("10.00"), "843923574")
        self.assertTrue(r.pending)
        self.assertIn("sandbox", r.redirect_url)


@override_settings(PAYMENT_GATEWAY_PROVIDER="AUTO")
class SelectorDoGatewayTests(SimpleTestCase):
    def test_dpo_e_card_dao_o_gateway_de_cartao(self):
        self.assertIsInstance(get_payment_gateway(provider="DPO"), DpoCardGateway)
        self.assertIsInstance(get_payment_gateway(provider="card"), DpoCardGateway)

    def test_o_telefone_continua_a_dar_a_carteira(self):
        gw = get_payment_gateway(payer_phone="841234567")
        self.assertNotIsInstance(gw, DpoCardGateway)
        self.assertEqual(gw.provider, "MPESA")


class _Cenario(TestCase):
    """Uma carreira urbana (sem lugares nem identidade) para a compra ser curta."""

    def setUp(self):
        self.rota = Route.objects.create(code="RT-CARD", name="Cartao", status=Route.Status.ACTIVE,
                                         service_type=Route.ServiceType.URBAN)
        self.a = Stop.objects.create(code="C-A", name="A", status="active")
        self.b = Stop.objects.create(code="C-B", name="B", status="active")
        for i, p in enumerate((self.a, self.b)):
            RouteStop.objects.create(route=self.rota, stop=p, sequence=i, direction=RouteStop.Direction.OUTBOUND)
        prod = FareProduct.objects.create(name="Avulso", product_type=FareProduct.ProductType.SINGLE_TRIP)
        FareRule.objects.create(fare_product=prod, route=self.rota,
                                calculation_method=FareRule.CalculationMethod.FIXED,
                                fixed_amount=Decimal("150.00"))
        v = Vehicle.objects.create(registration="CD-01-AA", seated_capacity=30)
        self.trip = Trip.objects.create(route=self.rota, vehicle=v, status=Trip.Status.SCHEDULED,
                                        direction=Trip.Direction.OUTBOUND,
                                        planned_departure_at=timezone.now() + timedelta(hours=3))

    def _comprar(self, **extra):
        corpo = {
            "trip_id": self.trip.id, "origin_stop": "A", "destination_stop": "B",
            "origin_stop_id": self.a.id, "destination_stop_id": self.b.id,
            "payer_phone": "843923574", "quantity": 2, "accept_terms": True,
            "buyer_name": "Jessica Cossa", **extra,
        }
        return self.client.post("/api/guest-checkouts/", corpo, content_type="application/json")


class _GatewayDeCartaoFalso:
    """Devolve o que se lhe mandar; regista o que lhe pediram."""

    provider = "DPO"

    def __init__(self, iniciar=None, verificar=None):
        self._iniciar, self._verificar = iniciar, verificar
        self.pedidos = []

    def initiate_payment(self, reference, amount, payer_phone, description="", **kw):
        self.pedidos.append({"reference": reference, "amount": amount, **kw})
        return self._iniciar

    def query_payment(self, token):
        self.pedidos.append({"query": token})
        return self._verificar


PENDENTE_COM_REDIRECT = PaymentGatewayResult(
    success=False, pending=True, provider="DPO",
    provider_reference="TOK-1", redirect_url="https://secure.3gdirectpay.com/payv2.php?ID=TOK-1",
    request_payload={"CompanyRef": "x"}, response_payload={"Result": "000"},
)
PAGO = PaymentGatewayResult(success=True, provider="DPO", provider_reference="DPO-9911")
NAO_PAGO = PaymentGatewayResult(success=False, pending=True, provider="DPO", provider_reference="TOK-1")
CANCELADO = PaymentGatewayResult(success=False, pending=False, provider="DPO", error="Cancelado")


class CompraPorCartaoTests(_Cenario):
    def test_a_compra_devolve_o_redirect_e_fica_pendente(self):
        falso = _GatewayDeCartaoFalso(iniciar=PENDENTE_COM_REDIRECT)
        with patch("apps.guest_checkouts.api.views.get_payment_gateway", return_value=falso):
            r = self._comprar(payment_method="card")
        self.assertEqual(r.status_code, 201, r.content)
        corpo = r.json()
        self.assertEqual(corpo["payment_status"], "pending")
        self.assertEqual(corpo["redirect_url"], "https://secure.3gdirectpay.com/payv2.php?ID=TOK-1")
        self.assertEqual(corpo["ticket_url"], "")
        gc = GuestCheckout.objects.get(reference=corpo["checkout_reference"])
        self.assertEqual(gc.status, GuestCheckout.Status.PAYMENT_PENDING)
        pi = PaymentIntent.objects.get(guest_checkout=gc)
        self.assertEqual((pi.status, pi.provider, pi.provider_reference),
                         (PaymentIntent.Status.PENDING, "DPO", "TOK-1"))
        # O DPO recebe para onde devolver o passageiro: a pagina da compra, com a referencia.
        pedido = falso.pedidos[0]
        self.assertIn(f"/comprar?ref={gc.reference}", pedido["redirect_url"])
        self.assertEqual(pedido["buyer_name"], "Jessica Cossa")

    def test_sem_payment_method_continua_a_ser_carteira(self):
        with patch("apps.guest_checkouts.api.views.get_payment_gateway") as gpg:
            gpg.return_value = _GatewayDeCartaoFalso(iniciar=PaymentGatewayResult(
                success=False, pending=True, provider="MPESA", provider_reference="X"))
            r = self._comprar()
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["redirect_url"], "")
        gpg.assert_called_once_with(payer_phone="843923574")

    def test_dpo_recusa_o_token_e_o_lugar_e_libertado(self):
        falso = _GatewayDeCartaoFalso(iniciar=PaymentGatewayResult(
            success=False, pending=False, provider="DPO", error="Currency not supported",
            detail_message="Currency not supported"))
        with patch("apps.guest_checkouts.api.views.get_payment_gateway", return_value=falso):
            r = self._comprar(payment_method="card")
        self.assertEqual(r.status_code, 502)
        self.assertEqual(GuestCheckout.objects.get().status, GuestCheckout.Status.CANCELLED)


class RegressoDaPaginaTests(_Cenario):
    """`POST /guest-checkouts/<ref>/verify/` — a pagina pergunta, o DPO responde."""

    def _pendente(self):
        with patch("apps.guest_checkouts.api.views.get_payment_gateway",
                   return_value=_GatewayDeCartaoFalso(iniciar=PENDENTE_COM_REDIRECT)):
            r = self._comprar(payment_method="card")
        return r.json()["checkout_reference"]

    def _verify(self, ref, resposta):
        falso = _GatewayDeCartaoFalso(verificar=resposta)
        with patch("apps.payments.services.reconciliation.get_payment_gateway", return_value=falso):
            r = self.client.post(f"/api/guest-checkouts/{ref}/verify/")
        return r, falso

    def test_pago_emite_os_bilhetes_e_da_o_link(self):
        ref = self._pendente()
        r, falso = self._verify(ref, PAGO)
        self.assertEqual(r.status_code, 200, r.content)
        corpo = r.json()
        self.assertEqual((corpo["status"], corpo["payment_status"]), ("issued", "confirmed"))
        self.assertTrue(corpo["ticket_url"])
        self.assertEqual(DigitalTravelPass.objects.filter(guest_checkout__reference=ref).count(), 2)
        # Perguntou pelo TOKEN, que e o que o DPO conhece.
        self.assertEqual(falso.pedidos, [{"query": "TOK-1"}])
        pi = PaymentIntent.objects.get(guest_checkout__reference=ref)
        self.assertEqual(pi.provider_reference, "DPO-9911")

    def test_ainda_nao_pago_fica_como_esta(self):
        ref = self._pendente()
        r, _ = self._verify(ref, NAO_PAGO)
        corpo = r.json()
        self.assertEqual((corpo["status"], corpo["payment_status"]), ("payment_pending", "pending"))
        self.assertEqual(corpo["ticket_url"], "")

    def test_cancelado_liberta_o_lugar(self):
        ref = self._pendente()
        r, _ = self._verify(ref, CANCELADO)
        self.assertEqual(r.json()["status"], "cancelled")

    def test_o_url_de_regresso_nao_prova_nada(self):
        """`?TransID=..&CCDapproval=..` no URL e so texto: sem o DPO dizer 000, nao ha bilhete."""
        ref = self._pendente()
        r, _ = self._verify(ref, NAO_PAGO)
        self.assertEqual(DigitalTravelPass.objects.filter(guest_checkout__reference=ref).count(), 0)

    def test_confirmado_duas_vezes_nao_emite_duas_vezes(self):
        ref = self._pendente()
        self._verify(ref, PAGO)
        r, falso = self._verify(ref, PAGO)
        self.assertEqual(r.json()["payment_status"], "confirmed")
        self.assertEqual(falso.pedidos, [], "ja confirmado: nem se pergunta")
        self.assertEqual(DigitalTravelPass.objects.filter(guest_checkout__reference=ref).count(), 2)

    def test_referencia_desconhecida_e_404(self):
        self.assertEqual(self.client.post("/api/guest-checkouts/GC-NAO/verify/").status_code, 404)


class NotificacaoDoDpoTests(_Cenario):
    """`POST /payments/webhooks/dpo/` — um gatilho, nunca uma prova."""

    def _pendente(self):
        with patch("apps.guest_checkouts.api.views.get_payment_gateway",
                   return_value=_GatewayDeCartaoFalso(iniciar=PENDENTE_COM_REDIRECT)):
            return self._comprar(payment_method="card").json()

    def test_xml_com_o_token_confirma_pelo_verify(self):
        compra = self._pendente()
        xml = f"<API3G><TransactionToken>TOK-1</TransactionToken><CompanyRef>{compra['payment_reference']}</CompanyRef><Result>000</Result></API3G>"
        falso = _GatewayDeCartaoFalso(verificar=PAGO)
        with patch("apps.payments.services.reconciliation.get_payment_gateway", return_value=falso):
            r = self.client.post("/api/payments/webhooks/dpo/", xml, content_type="application/xml")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["payment_status"], "confirmed")
        self.assertEqual(falso.pedidos, [{"query": "TOK-1"}], "confirmou-se pelo verify, nao pelo corpo")

    def test_um_corpo_a_dizer_pago_nao_chega(self):
        """A notificacao diz 000; o DPO, perguntado, diz 900. Manda o DPO."""
        self._pendente()
        xml = "<API3G><TransactionToken>TOK-1</TransactionToken><Result>000</Result></API3G>"
        with patch("apps.payments.services.reconciliation.get_payment_gateway",
                   return_value=_GatewayDeCartaoFalso(verificar=NAO_PAGO)):
            r = self.client.post("/api/payments/webhooks/dpo/", xml, content_type="application/xml")
        self.assertEqual(r.json()["payment_status"], "pending")
        self.assertEqual(DigitalTravelPass.objects.count(), 0)

    def test_token_desconhecido_e_404(self):
        r = self.client.post("/api/payments/webhooks/dpo/",
                             "<API3G><TransactionToken>NOPE</TransactionToken></API3G>",
                             content_type="application/xml")
        self.assertEqual(r.status_code, 404)


class ReconciliacaoDoCartaoTests(TestCase):
    def test_pergunta_pelo_token(self):
        pi = PaymentIntent.objects.create(
            reference="PAY-GC-CARD1", idempotency_key="card-1",
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS, amount=Decimal("300.00"),
            payer_phone="843923574", status=PaymentIntent.Status.PENDING,
            provider="DPO", provider_reference="TOK-9",
            metadata={"gateway_request": {"CompanyRef": "PAY-GC-CARD1"}},
        )
        self.assertEqual(referencia_para_consulta(pi), "TOK-9")


class InterruptorNaMarcaTests(TestCase):
    """A compra publica so mostra "Cartao" quando o DPO esta configurado."""

    @override_settings(DPO_COMPANY_TOKEN="", DPO_SERVICE_TYPE="")
    def test_sem_configuracao_o_botao_nao_aparece(self):
        r = self.client.get("/api/branding/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIs(r.json()["card_payments_enabled"], False)

    @override_settings(DPO_COMPANY_TOKEN="TOKEN", DPO_SERVICE_TYPE="3854")
    def test_configurado_o_botao_aparece(self):
        r = self.client.get("/api/branding/")
        self.assertIs(r.json()["card_payments_enabled"], True)
