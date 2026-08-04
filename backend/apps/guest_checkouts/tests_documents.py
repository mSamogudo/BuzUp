"""Documento de identificacao: quando e pedido e que forma tem de ter.

Duas regras distintas, que se estragam de maneiras diferentes:

* **Quando** — so em viagens interprovinciais e internacionais. Pedir o BI para
  apanhar o autocarro do bairro trava uma compra que tem de ser rapida e guarda
  dados pessoais sem necessidade.
* **Que forma** — cada tipo de documento tem a sua. Um campo que aceita o que o
  servidor recusa manda o comprador ate ao pagamento para falhar la, ja depois
  de ter escolhido o lugar.
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.fares.models import FareProduct, FareRule
from apps.guest_checkouts.documents import (
    DOCUMENT_RULES,
    DocumentError,
    normalize_document,
    validate_document,
)
from apps.routes.models import Route, RouteStop, Stop


class NormalizacaoTests(TestCase):
    def test_tira_espacos_tracos_e_poe_em_maiusculas(self):
        # As pessoas escrevem o BI de todas as maneiras. Guardar as duas formas
        # do mesmo documento fazia o mesmo passageiro parecer dois no manifesto.
        for escrito in ["1101 0012 3456 a", "110100123456a", "110-100-123456-A"]:
            self.assertEqual(normalize_document(escrito), "110100123456A")

    def test_valor_vazio_nao_rebenta(self):
        self.assertEqual(normalize_document(""), "")
        self.assertEqual(normalize_document(None), "")


class FormatoTests(TestCase):
    def test_bi_valido(self):
        self.assertEqual(validate_document("bi", "110100123456A"), "110100123456A")
        self.assertEqual(validate_document("bi", "1101 0012 3456 a"), "110100123456A")

    def test_bi_recusa_comprimento_errado(self):
        for mau in ["11010012345A", "1101001234567A", "110100123456"]:
            with self.assertRaises(DocumentError, msg=mau):
                validate_document("bi", mau)

    def test_bi_recusa_sem_letra_final(self):
        with self.assertRaises(DocumentError):
            validate_document("bi", "1101001234561")

    def test_passaporte_aceita_6_a_9(self):
        self.assertEqual(validate_document("passport", "ab1234567"), "AB1234567")
        self.assertEqual(validate_document("passport", "AB1234"), "AB1234")

    def test_passaporte_recusa_acima_do_limite_icao(self):
        with self.assertRaises(DocumentError):
            validate_document("passport", "AB12345678")

    def test_numero_vazio_e_recusado(self):
        with self.assertRaises(DocumentError):
            validate_document("bi", "   ")

    def test_tipo_desconhecido_cai_na_regra_de_outro(self):
        # Melhor aceitar um documento invulgar do que recusar a compra por
        # causa de uma lista desactualizada.
        self.assertEqual(validate_document("passe-do-futuro", "XPTO123"), "XPTO123")

    def test_todas_as_regras_tem_os_campos_que_o_portal_le(self):
        # O portal desenha o campo a partir disto. Uma chave em falta deixava
        # o formulario sem limite de caracteres ou sem explicacao do erro.
        for chave, regra in DOCUMENT_RULES.items():
            for campo in ("label", "pattern", "max_length", "placeholder", "help"):
                self.assertIn(campo, regra, msg=f"{chave} sem {campo}")


class CompraBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.urbana = Route.objects.create(
            code="R-URB-D", name="Circular",
            service_type=Route.ServiceType.URBAN, status=Route.Status.ACTIVE,
        )
        self.longa = Route.objects.create(
            code="R-INT-D", name="Maputo - Xai-Xai",
            service_type=Route.ServiceType.INTERPROVINCIAL, status=Route.Status.ACTIVE,
        )
        self.origem = Stop.objects.create(code="ST-DA", name="Paragem A", status="active")
        self.destino = Stop.objects.create(code="ST-DB", name="Paragem B", status="active")
        for rota in (self.urbana, self.longa):
            RouteStop.objects.create(route=rota, stop=self.origem, sequence=1, direction="outbound")
            RouteStop.objects.create(route=rota, stop=self.destino, sequence=2, direction="outbound")
            produto = FareProduct.objects.create(
                name=f"Avulso {rota.code}",
                product_type=FareProduct.ProductType.SINGLE_TRIP,
                status=FareProduct.Status.ACTIVE,
            )
            FareRule.objects.create(
                fare_product=produto, route=rota,
                calculation_method=FareRule.CalculationMethod.FIXED,
                fixed_amount=Decimal("100.00"),
            )

    def _comprar(self, rota, passageiros, **extra):
        payload = {
            "payer_phone": "841234567",
            "route_code": rota.code,
            "origin_stop": self.origem.name,
            "destination_stop": self.destino.name,
            "origin_stop_id": self.origem.id,
            "destination_stop_id": self.destino.id,
            "quantity": len(passageiros) or 1,
            "passengers": passageiros,
            **extra,
        }
        return self.client.post(
            reverse("guest-checkout-create"), payload, format="json")


class DocumentoExigidoTests(CompraBase):
    def test_urbana_compra_sem_documento(self):
        r = self._comprar(self.urbana, [{"name": "Ana Cossa"}])
        self.assertNotIn(r.status_code, (400, 422), msg=r.data)

    def test_urbana_nao_guarda_documento_enviado_por_engano(self):
        # Nao guardar o que nao foi pedido.
        r = self._comprar(self.urbana, [
            {"name": "Ana Cossa", "document_type": "bi", "document_number": "110100123456A"},
        ])
        self.assertNotIn(r.status_code, (400, 422), msg=r.data)

        from apps.guest_checkouts.models import GuestCheckout
        gc = GuestCheckout.objects.get(reference=r.data["checkout_reference"])
        self.assertEqual(gc.passengers[0]["document_number"], "")
        self.assertEqual(gc.passengers[0]["document_type"], "")

    def test_interprovincial_sem_documento_e_recusada(self):
        r = self._comprar(
            self.longa, [{"name": "Ana Cossa"}],
            emergency_contact_name="Maria", emergency_contact_phone="849999999",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("documento", str(r.data).lower())

    def test_interprovincial_com_bi_mal_formado_e_recusada(self):
        r = self._comprar(
            self.longa,
            [{"name": "Ana Cossa", "document_type": "bi", "document_number": "123"}],
            emergency_contact_name="Maria", emergency_contact_phone="849999999",
        )
        self.assertEqual(r.status_code, 400)

    def test_interprovincial_guarda_o_documento_normalizado(self):
        r = self._comprar(
            self.longa,
            [{"name": "Ana Cossa", "document_type": "bi",
              "document_number": "1101 0012 3456 a"}],
            emergency_contact_name="Maria", emergency_contact_phone="849999999",
        )
        self.assertNotIn(r.status_code, (400, 422), msg=r.data)

        from apps.guest_checkouts.models import GuestCheckout
        gc = GuestCheckout.objects.get(reference=r.data["checkout_reference"])
        self.assertEqual(gc.passengers[0]["document_number"], "110100123456A")


class PontoPublicoTests(TestCase):
    def test_portal_le_as_regras_sem_autenticacao(self):
        r = APIClient().get(reverse("public-document-types"))
        self.assertEqual(r.status_code, 200)
        tipos = {t["value"]: t for t in r.data["document_types"]}
        self.assertEqual(set(tipos), set(DOCUMENT_RULES))
        self.assertEqual(tipos["bi"]["max_length"], 13)
        self.assertTrue(tipos["bi"]["help"])
