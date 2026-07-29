"""Os endpoints do POS só podem ser usados por agentes activos.

Antes bastava um JWT de passageiro (obtido por OTP no próprio telemóvel)
para abrir sessão de POS, validar cartões alheios — debitando a carteira de
outra pessoa — e disparar pedidos M-Pesa para qualquer número.
"""

from django.test import TestCase
from rest_framework.test import APIClient

from apps.trips.models import Agent
from apps.users.models import User

POS_ENDPOINTS = [
    ("post", "/api/pos/sessions/open/", {"device_serial": "X", "route_id": 1}),
    ("post", "/api/pos/sessions/close/", {}),
    ("get", "/api/pos/sessions/active/", None),
    ("post", "/api/pos/validate/card/", {"card_uid": "AABBCCDD", "route_id": 1}),
    ("post", "/api/pos/validate/qr/", {"token": "x", "route_id": 1}),
    ("post", "/api/pos/card-topups/", {"card_uid": "AABBCCDD", "amount": "100.00", "payer_phone": "840000000"}),
    ("post", "/api/pos/package-subscribe/", {"card_uid": "AABBCCDD", "package_id": 1}),
]


class PosEndpointPermissionTests(TestCase):
    def setUp(self):
        self.passenger = User.objects.create_user(
            username="passageiro_teste", password="x", phone="+258840000001",
            email="passageiro.teste@exemplo.mz")
        self.agent_user = User.objects.create_user(
            username="agente_teste", password="x", phone="+258840000002",
            email="agente.teste@exemplo.mz")
        Agent.objects.create(full_name="Agente Teste", phone="+258840000002",
                             user=self.agent_user, status="active")

    def _client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        # staging/prod forcam HTTPS: sem isto o teste apanha 301 e nao chega
        # a exercitar a permissao.
        client.defaults["wsgi.url_scheme"] = "https"
        client.defaults["SERVER_PORT"] = "443"
        return client

    def test_passageiro_autenticado_nao_acede_a_nenhum_endpoint_pos(self):
        client = self._client_for(self.passenger)
        for method, url, payload in POS_ENDPOINTS:
            with self.subTest(url=url):
                response = (
                    getattr(client, method)(url, payload, format="json", secure=True)
                    if payload is not None
                    else getattr(client, method)(url, secure=True)
                )
                self.assertEqual(
                    response.status_code, 403,
                    f"{url} devolveu {response.status_code}: um passageiro nao pode operar o POS",
                )

    def test_anonimo_nao_acede(self):
        client = APIClient()
        client.defaults["wsgi.url_scheme"] = "https"
        client.defaults["SERVER_PORT"] = "443"
        for method, url, payload in POS_ENDPOINTS:
            with self.subTest(url=url):
                response = (
                    getattr(client, method)(url, payload, format="json", secure=True)
                    if payload is not None
                    else getattr(client, method)(url, secure=True)
                )
                self.assertIn(response.status_code, (401, 403))

    def test_agente_passa_a_barreira_de_permissao(self):
        """O agente não é bloqueado por permissão (o resto é validação de dados)."""
        client = self._client_for(self.agent_user)
        response = client.get("/api/pos/sessions/active/", secure=True)
        self.assertNotEqual(response.status_code, 403)
