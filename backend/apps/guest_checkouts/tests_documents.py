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

    def test_dire_tem_12_digitos(self):
        self.assertEqual(validate_document("dire", "123456789012"), "123456789012")
        for mau in ["12345678901", "1234567890123", "12345678901A"]:
            with self.assertRaises(DocumentError, msg=mau):
                validate_document("dire", mau)

    def test_cedula_tem_9_digitos(self):
        self.assertEqual(validate_document("cedula", "123456789"), "123456789")
        for mau in ["12345678", "1234567890", "12345678A"]:
            with self.assertRaises(DocumentError, msg=mau):
                validate_document("cedula", mau)

    def test_documentos_de_numero_fixo_abrem_teclado_numerico(self):
        # Sem isto o passageiro apanha o teclado de letras para escrever so
        # digitos — e ao balcao, com fila atras, isso custa tempo.
        for chave in ("dire", "cedula"):
            self.assertTrue(DOCUMENT_RULES[chave]["digits_only"], msg=chave)
        # O BI acaba em letra e o passaporte tem letras: teclado normal.
        for chave in ("bi", "passport"):
            self.assertFalse(DOCUMENT_RULES[chave]["digits_only"], msg=chave)

    def test_comprimento_maximo_bate_certo_com_a_regra(self):
        # O `max_length` limita o campo no formulario. Se for menor do que o
        # que a regra aceita, o campo trava antes de o numero estar completo.
        exemplos = {
            "bi": "110100123456A",
            "passport": "AB1234567",
            "dire": "123456789012",
            "cedula": "123456789",
        }
        for chave, numero in exemplos.items():
            self.assertEqual(validate_document(chave, numero), numero)
            self.assertGreaterEqual(
                DOCUMENT_RULES[chave]["max_length"], len(numero), msg=chave)

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
        # secure=True: em staging/producao o Django redirecciona HTTP para
        # HTTPS (301) e o cliente de teste nunca chegava a vista.
        return self.client.post(
            reverse("guest-checkout-create"), payload, format="json", secure=True)


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


class CompraPelaCarteiraTests(TestCase):
    """A compra pela carteira e um caminho SEPARADO do checkout de convidado.

    Era por aqui que o bilhete saia incompleto: o documento so era lido da
    conta (que quase nunca o tem) e a hora da partida nunca era copiada. O
    bilhete no telemovel mostrava entao a data da COMPRA no lugar da data da
    viagem, e o campo do documento vazio numa rota internacional.
    """

    def setUp(self):
        from apps.passengers.models import PassengerAccount
        from apps.trips.models import Trip, Vehicle
        from apps.wallets.models import Wallet
        from django.utils import timezone
        from datetime import timedelta

        self.rota = Route.objects.create(
            code="R-CART", name="Maputo - Xai-Xai",
            service_type=Route.ServiceType.INTERPROVINCIAL, status=Route.Status.ACTIVE,
        )
        self.origem = Stop.objects.create(code="ST-CA", name="Paragem A", status="active")
        self.destino = Stop.objects.create(code="ST-CB", name="Paragem B", status="active")
        RouteStop.objects.create(route=self.rota, stop=self.origem, sequence=1, direction="outbound")
        RouteStop.objects.create(route=self.rota, stop=self.destino, sequence=2, direction="outbound")

        produto = FareProduct.objects.create(
            name="Avulso carteira",
            product_type=FareProduct.ProductType.SINGLE_TRIP,
            status=FareProduct.Status.ACTIVE,
        )
        FareRule.objects.create(
            fare_product=produto, route=self.rota,
            calculation_method=FareRule.CalculationMethod.FIXED,
            fixed_amount=Decimal("100.00"),
        )

        viatura = Vehicle.objects.create(
            registration="AAA-11-MC", seated_capacity=20, status="active")
        self.partida = timezone.now() + timedelta(days=3)
        self.trip = Trip.objects.create(
            route=self.rota, vehicle=viatura,
            planned_departure_at=self.partida,
            status=Trip.Status.SCHEDULED,
        )

        # Conta SEM documento guardado — o caso real que produzia bilhetes
        # interprovinciais com o campo do documento vazio.
        self.passageiro = PassengerAccount.objects.create(
            full_name="Ana Cossa", phone_number="849777111",
            status=PassengerAccount.Status.ACTIVE,
        )
        Wallet.objects.create(passenger_account=self.passageiro,
                              balance_cached=Decimal("5000.00"), status="active")

    def _comprar(self, **extra):
        from apps.guest_checkouts.purchase import purchase_travel_pass

        return purchase_travel_pass(
            passenger=self.passageiro, route_id=self.rota.id,
            origin_stop_id=self.origem.id, destination_stop_id=self.destino.id,
            trip_id=self.trip.id, seat="1A", use_package=False,
            emergency_contact_name="Maria", emergency_contact_phone="849999999",
            **extra,
        )

    def test_bilhete_guarda_a_hora_da_partida(self):
        tp = self._comprar(document_type="bi", document_number="110100123456A")
        self.assertEqual(tp.departure_at, self.partida)

    def test_documento_enviado_pela_app_fica_no_bilhete(self):
        tp = self._comprar(document_type="bi", document_number="1101 0012 3456 a")
        self.assertEqual(tp.document_number, "110100123456A")
        self.assertEqual(tp.document_type, "bi")
        self.assertEqual(tp.passenger_name, "Ana Cossa")

    def test_conta_sem_documento_e_sem_envio_e_recusada(self):
        from apps.guest_checkouts.purchase import PurchaseError

        with self.assertRaises(PurchaseError) as ctx:
            self._comprar()
        self.assertIn("documento", str(ctx.exception).lower())

    def test_documento_mal_formado_e_recusado(self):
        from apps.guest_checkouts.purchase import PurchaseError

        with self.assertRaises(PurchaseError):
            self._comprar(document_type="bi", document_number="123")


class PontoPublicoTests(TestCase):
    def test_portal_le_as_regras_sem_autenticacao(self):
        r = APIClient().get(reverse("public-document-types"), secure=True)
        self.assertEqual(r.status_code, 200)
        tipos = {t["value"]: t for t in r.data["document_types"]}
        self.assertEqual(set(tipos), set(DOCUMENT_RULES))
        self.assertEqual(tipos["bi"]["max_length"], 13)
        self.assertTrue(tipos["bi"]["help"])
