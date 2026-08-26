"""O bilhete do SMS tem de abrir depressa.

O link devolvia um PDF de 339 KB, dos quais 268 sao a imagem de fundo. Gerar
custava 100 ms — o servidor nunca foi o problema. Era o TAMANHO: medido daqui,
1,8 a 2,7 segundos so de transferencia; num telemovel com dados moveis, muito
mais. E o passageiro abre isto na paragem, com o autocarro a chegar.

A pagina que o substitui nao pede um unico ficheiro extra — nem CSS, nem tipos
de letra, nem imagens. O QR e SVG desenhado a partir da matriz.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.guest_checkouts.models import DigitalTravelPass, GuestCheckout


class PaginaDoBilheteTests(TestCase):
    def setUp(self):
        self.gc = GuestCheckout.objects.create(
            reference="GC-TESTE-1", payer_phone="258841234567",
            route_code="RT-X", route_name="Maputo x Nelspruit",
            origin_stop="Polana", destination_stop="Ilanga Mall",
            quantity=1, unit_amount=Decimal("1500.00"), total_amount=Decimal("1500.00"),
            status=GuestCheckout.Status.ISSUED,
            expires_at=timezone.now() + timedelta(days=1))
        raw, token_hash = DigitalTravelPass.generate_token()
        self.raw = raw
        self.tp = DigitalTravelPass.objects.create(
            guest_checkout=self.gc, payer_phone="258841234567",
            route_code="RT-X", route_name="Maputo x Nelspruit",
            origin_stop="Polana", destination_stop="Ilanga Mall",
            passenger_name="Ana Cossa", document_number="AB123456",
            seat_number="12A", fare_amount=Decimal("1500.00"),
            departure_at=timezone.now() + timedelta(days=1),
            token=raw, token_hash=token_hash, short_code="4EB781",
            status=DigitalTravelPass.Status.ACTIVE)

    def _abrir(self):
        return self.client.get(f"/api/public/ticket/{self.raw}/")

    # --- o que o passageiro recebe ---------------------------------------

    def test_o_link_do_sms_devolve_uma_pagina_e_nao_um_pdf(self):
        r = self._abrir()
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r["Content-Type"])

    def test_a_pagina_e_pequena(self):
        """O ponto todo. Um bilhete que demora a abrir nao serve de bilhete."""
        tamanho = len(self._abrir().content)
        self.assertLess(tamanho, 20_000,
                        f"a pagina cresceu para {tamanho/1024:.0f} KB — o PDF que "
                        f"substituiu tinha 339 KB e era esse o problema")

    def test_nao_vai_buscar_nada_ao_servidor(self):
        """Sem CSS, tipos de letra ou imagens externas: numa paragem com pouca
        rede, cada ficheiro extra e outra oportunidade de ficar em branco."""
        corpo = self._abrir().content.decode()
        for proibido in ("<link", "<script", "<img", "url(http", "@import"):
            self.assertNotIn(proibido, corpo, f"a pagina passou a depender de {proibido}")

    def test_mostra_o_que_o_revisor_confere(self):
        corpo = self._abrir().content.decode()
        for esperado in ("4EB781", "Ana Cossa", "12A", "Polana", "Ilanga Mall",
                         "Maputo x Nelspruit", "GC-TESTE-1"):
            self.assertIn(esperado, corpo, f"falta {esperado!r} no bilhete")

    def test_leva_o_qr_dentro_da_propria_pagina(self):
        corpo = self._abrir().content.decode()
        self.assertIn("<svg", corpo)
        self.assertIn("<path", corpo)

    def test_diz_se_o_bilhete_e_valido(self):
        self.assertIn("VALIDO", self._abrir().content.decode())
        self.tp.status = DigitalTravelPass.Status.USED
        self.tp.save(update_fields=["status"])
        self.assertIn("NAO VALIDO", self._abrir().content.decode())

    # --- o PDF nao desapareceu -------------------------------------------

    def test_o_pdf_continua_disponivel(self):
        r = self.client.get(f"/api/public/ticket/{self.raw}/pdf/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")

    def test_a_pagina_liga_para_o_pdf(self):
        self.assertIn("pdf/", self._abrir().content.decode())

    # --- o que nao existe ------------------------------------------------

    def test_um_token_inventado_nao_abre_bilhete_nenhum(self):
        r = self.client.get("/api/public/ticket/inventado123/")
        self.assertEqual(r.status_code, 404)
