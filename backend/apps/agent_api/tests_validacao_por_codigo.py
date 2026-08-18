"""Validar o bilhete pelo codigo impresso, tal como o POS o faz.

O codigo curto passou de 4 para 6 caracteres para deixar de haver colisoes, e o
lado do servidor foi corrigido e testado. O POS ficou para tras: o campo
continuava com `maxLength: 4` e recusava qualquer coisa que nao tivesse
exactamente 4 caracteres. Como o bilhete imprime 6, o agente nao conseguia
sequer escrever o codigo que tinha a frente — e a metade testada do sistema
estava toda certa.

Estes testes seguram o contrato que a app consome, e nao apenas a funcao por
baixo dele.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout
from apps.guest_checkouts.ticket_codes import ticket_reference, ticket_short_code
from apps.trips.models import Agent


class ValidacaoPorCodigoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="fiscal", password="x", email="fiscal@x.mz", phone="849000009")
        Agent.objects.create(full_name="Fiscal", user=self.user, status=Agent.Status.ACTIVE)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _bilhete(self, referencia, *, comprimento=6, quantidade=1):
        gc = GuestCheckout.objects.create(
            reference=referencia, payer_phone="841000000",
            origin_stop="A", destination_stop="B", quantity=quantidade,
            unit_amount=Decimal("100.00"), total_amount=Decimal("100.00"),
            status=GuestCheckout.Status.ISSUED,
        )
        raw, token_hash = DigitalTravelPass.generate_token()
        tp = DigitalTravelPass.objects.create(
            guest_checkout=gc, payer_phone="841000000",
            origin_stop="A", destination_stop="B", fare_amount=Decimal("100.00"),
            token=raw, token_hash=token_hash,
            valid_from=timezone.now(), valid_until=timezone.now() + timedelta(days=1),
        )
        tp.short_code = ticket_short_code(ticket_reference(tp), comprimento)
        tp.save(update_fields=["short_code", "updated_at"])
        return tp

    def verificar(self, **corpo):
        return self.client.post("/api/agent/tickets/verify/", corpo, format="json")

    def test_codigo_de_seis_valida_o_bilhete(self):
        """O caso do balcao: o agente le os 6 caracteres impressos."""
        tp = self._bilhete("GC-11112222333344445")
        self.assertEqual(len(tp.short_code), 6)

        r = self.verificar(shortcode=tp.short_code)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()["valid"])
        self.assertTrue(r.json()["consumed"])

        tp.refresh_from_db()
        self.assertEqual(tp.status, DigitalTravelPass.Status.USED)

    def test_codigo_em_minusculas_e_aceite(self):
        tp = self._bilhete("GC-ABCDEF0123456789A")
        r = self.verificar(shortcode=tp.short_code.lower())
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()["valid"])

    def test_bilhete_antigo_de_quatro_continua_a_validar(self):
        tp = self._bilhete("GC-99998888777766665", comprimento=4)
        r = self.verificar(shortcode=tp.short_code)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()["valid"])

    def test_segunda_leitura_do_mesmo_codigo_e_recusada(self):
        tp = self._bilhete("GC-55556666777788889")
        self.assertTrue(self.verificar(shortcode=tp.short_code).json()["valid"])
        segunda = self.verificar(shortcode=tp.short_code)
        self.assertEqual(segunda.status_code, 404, segunda.content)

    def test_codigo_ambiguo_devolve_candidatos_escolhiveis(self):
        """A 409 tem de trazer com que escolher — antes so trazia a lista."""
        a = self._bilhete("GC-1111111111AA0718")
        b = self._bilhete("GC-2222222222BB0718")
        # Forca a colisao: e o cenario que os 6 caracteres tornam raro, nao
        # impossivel.
        b.short_code = a.short_code
        b.save(update_fields=["short_code", "updated_at"])

        r = self.verificar(shortcode=a.short_code)
        self.assertEqual(r.status_code, 409, r.content)
        candidatos = r.json()["candidates"]
        self.assertEqual(len(candidatos), 2)
        for c in candidatos:
            self.assertTrue(c["uuid"], "sem identificador o agente nao pode escolher nenhum")
            self.assertTrue(c["reference"])
            self.assertNotIn("token", c, "o token do QR nunca sai numa lista de candidatos")

        escolhido = self.verificar(pass_uuid=candidatos[0]["uuid"])
        self.assertEqual(escolhido.status_code, 200, escolhido.content)
        self.assertTrue(escolhido.json()["valid"])

    def test_pedido_sem_nada_e_recusado(self):
        r = self.verificar()
        self.assertEqual(r.status_code, 400)
