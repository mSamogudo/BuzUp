"""Bilhetes de descarga — a credencial que substitui o JWT no URL.

O JWT de acesso ia no URL dos downloads porque um `<a href>` nao leva
cabecalhos. Ficava gravado no log do nginx e no historico do browser, e quem
lesse o log podia agir como aquele utilizador em TODO o sistema, nao so no
ficheiro que ele quis abrir. O bilhete vale minutos e vale so para um tipo de
ficheiro.
"""

from __future__ import annotations

import time

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.download_scopes import CARD_QR, REPORT_BUILDER
from apps.core.download_tokens import (
    InvalidDownloadTicket,
    make_download_ticket,
    resolve_download_ticket,
)


class DownloadTicketTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="operador", password="x", phone="841234567",
        )

    def test_ticket_round_trips_for_its_own_scope(self):
        ticket = make_download_ticket(self.user, REPORT_BUILDER)
        self.assertEqual(resolve_download_ticket(ticket, REPORT_BUILDER).pk, self.user.pk)

    def test_ticket_for_one_file_does_not_open_another(self):
        """O caso que motiva o ambito: um link de QR nao pode virar um
        relatorio financeiro."""
        ticket = make_download_ticket(self.user, CARD_QR)
        with self.assertRaises(InvalidDownloadTicket):
            resolve_download_ticket(ticket, REPORT_BUILDER)

    def test_expired_ticket_is_refused(self):
        """Encontrado num log de acessos, o bilhete ja nao serve."""
        ticket = make_download_ticket(self.user, CARD_QR)
        time.sleep(1)
        with self.assertRaises(InvalidDownloadTicket):
            resolve_download_ticket(ticket, CARD_QR, max_age=0)

    def test_tampered_ticket_is_refused(self):
        ticket = make_download_ticket(self.user, CARD_QR)
        with self.assertRaises(InvalidDownloadTicket):
            resolve_download_ticket(ticket[:-3] + "aaa", CARD_QR)

    def test_missing_ticket_is_refused(self):
        for bad in ["", None]:
            with self.assertRaises(InvalidDownloadTicket):
                resolve_download_ticket(bad, CARD_QR)

    def test_ticket_dies_with_the_account(self):
        """Um bilhete nao pode sobreviver ao despedimento de quem o pediu."""
        ticket = make_download_ticket(self.user, CARD_QR)
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        with self.assertRaises(InvalidDownloadTicket):
            resolve_download_ticket(ticket, CARD_QR)

    def test_the_ticket_is_not_the_users_jwt(self):
        """Se fosse derivado da sessao, expirar o bilhete nao adiantava nada."""
        ticket = make_download_ticket(self.user, CARD_QR)
        self.assertNotIn(str(self.user.pk), ticket.split(":")[0])
        self.assertEqual(ticket.count(":"), 2)  # payload:timestamp:assinatura


class DownloadTicketEndpointTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="operador2", password="x", phone="841234568",
        )

    def _auth(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(self.user).access_token}"}

    def test_endpoint_issues_a_usable_ticket(self):
        r = self.client.post(
            "/api/auth/download-ticket/",
            data={"scope": REPORT_BUILDER},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(r.status_code, 200, r.content)
        ticket = r.json()["ticket"]
        self.assertEqual(resolve_download_ticket(ticket, REPORT_BUILDER).pk, self.user.pk)

    def test_unknown_scope_is_refused(self):
        r = self.client.post(
            "/api/auth/download-ticket/",
            data={"scope": "qualquer_coisa"},
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(r.status_code, 400)

    def test_anonymous_cannot_mint_tickets(self):
        r = self.client.post(
            "/api/auth/download-ticket/",
            data={"scope": REPORT_BUILDER},
            content_type="application/json",
        )
        self.assertIn(r.status_code, (401, 403))


class LegacyJwtInUrlTests(TestCase):
    """A compatibilidade com o link antigo tem de ser desligavel.

    Enquanto `ALLOW_JWT_IN_QUERY_STRING` for True o JWT continua a ser aceite no
    URL — e continua a ficar gravado nos logs. O interruptor existe para se
    poder fechar assim que as apps novas estiverem distribuidas.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="operador3", password="x", phone="841234569",
        )
        from rest_framework_simplejwt.tokens import RefreshToken

        self.jwt = str(RefreshToken.for_user(self.user).access_token)

    def _extract(self, **params):
        return self.client.get("/api/auth/me/passenger-portal/extract/", params)

    def test_legacy_link_still_works_while_the_switch_is_on(self):
        with self.settings(ALLOW_JWT_IN_QUERY_STRING=True):
            r = self._extract(token=self.jwt)
        self.assertNotIn(r.status_code, (401, 403), "link antigo deixou de funcionar cedo demais")

    def test_legacy_link_is_refused_once_the_switch_is_off(self):
        with self.settings(ALLOW_JWT_IN_QUERY_STRING=False):
            r = self._extract(token=self.jwt)
        self.assertIn(r.status_code, (401, 403))

    def test_ticket_works_regardless_of_the_switch(self):
        from apps.core.download_scopes import PASSENGER_EXTRACT

        ticket = make_download_ticket(self.user, PASSENGER_EXTRACT)
        with self.settings(ALLOW_JWT_IN_QUERY_STRING=False):
            r = self._extract(t=ticket)
        self.assertNotIn(r.status_code, (401, 403))

    def test_ticket_from_another_file_type_is_refused(self):
        """Um bilhete de QR nao pode puxar o extracto financeiro."""
        from apps.core.download_scopes import CARD_QR

        ticket = make_download_ticket(self.user, CARD_QR)
        with self.settings(ALLOW_JWT_IN_QUERY_STRING=False):
            r = self._extract(t=ticket)
        self.assertIn(r.status_code, (401, 403))
