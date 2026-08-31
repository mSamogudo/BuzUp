"""Endpoints criados para fechar lacunas de 04-lacunas-backend.md.

Um teste por lacuna: seguranca da conta (2FA), registo de webhooks e historico
de recuperacoes de cartao.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.payments.models import PaymentCallback, PaymentIntent

User = get_user_model()


class SegurancaDaContaTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="operadora", password="senha-antiga-1",
            email="operadora@updigital.co.mz", phone="258840000001",
        )
        self.client.force_authenticate(self.user)

    def test_senha_errada_nao_mexe_no_2fa(self):
        resposta = self.client.post(
            "/api/auth/me/2fa/", {"enabled": False, "current_password": "errada"}, format="json",
        )
        self.assertEqual(resposta.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_2fa_enabled)

    def test_utilizador_normal_nao_pode_desligar_o_2fa(self):
        """A conta nasce com 2FA ligado de proposito; so um superadministrador
        o desliga. Uma sessao roubada nao pode derrubar a segunda barreira."""
        resposta = self.client.post(
            "/api/auth/me/2fa/", {"enabled": False, "current_password": "senha-antiga-1"}, format="json",
        )
        self.assertEqual(resposta.status_code, 403)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_2fa_enabled)

    def test_superadministrador_desliga_e_volta_a_ligar(self):
        chefe = User.objects.create_superuser(
            username="chefe", password="senha-forte-1", email="chefe@updigital.co.mz",
        )
        chefe.phone = "258840000009"
        chefe.save(update_fields=["phone"])
        self.client.force_authenticate(chefe)

        desligar = self.client.post(
            "/api/auth/me/2fa/", {"enabled": False, "current_password": "senha-forte-1"}, format="json",
        )
        self.assertEqual(desligar.status_code, 200, desligar.data)
        chefe.refresh_from_db()
        self.assertFalse(chefe.is_2fa_enabled)

        ligar = self.client.post(
            "/api/auth/me/2fa/", {"enabled": True, "current_password": "senha-forte-1"}, format="json",
        )
        self.assertEqual(ligar.status_code, 200, ligar.data)
        chefe.refresh_from_db()
        self.assertTrue(chefe.is_2fa_enabled)

    def test_ligar_2fa_sem_telefone_e_recusado(self):
        sem_telefone = User.objects.create_user(
            username="sem-telefone", password="senha-antiga-2",
            email="sem-telefone@updigital.co.mz", phone="",
        )
        sem_telefone.is_2fa_enabled = False
        sem_telefone.save(update_fields=["is_2fa_enabled"])
        self.client.force_authenticate(sem_telefone)
        resposta = self.client.post(
            "/api/auth/me/2fa/", {"enabled": True, "current_password": "senha-antiga-2"}, format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_me_mostra_o_estado_do_2fa(self):
        resposta = self.client.get("/api/auth/me/")
        self.assertIn("is_2fa_enabled", resposta.data)
        self.assertIn("last_login", resposta.data)


class RegistoDeWebhooksTest(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin-webhooks", password="segredo-forte-1", email="a@updigital.co.mz",
        )
        self.client.force_authenticate(self.admin)
        self.intent = PaymentIntent.objects.create(
            reference="PAY-TESTE-1",
            idempotency_key="idem-teste-1",
            purpose=PaymentIntent.Purpose.POS_CARD_TOPUP,
            amount=Decimal("100.00"),
            payer_phone="258840000002",
            status=PaymentIntent.Status.PENDING,
        )
        PaymentCallback.objects.create(
            payment_intent=self.intent,
            provider_reference="MP-123",
            raw_payload={"status": "ok"},
            signature_valid=True,
            processing_status="processed",
        )

    def test_lista_mostra_o_que_o_gateway_enviou(self):
        resposta = self.client.get("/api/payments/callback-log/")
        self.assertEqual(resposta.status_code, 200)
        linhas = resposta.data.get("results", resposta.data)
        self.assertEqual(len(linhas), 1)
        self.assertEqual(linhas[0]["reference"], "PAY-TESTE-1")
        self.assertTrue(linhas[0]["signature_valid"])
        self.assertEqual(linhas[0]["raw_payload"], {"status": "ok"})

    def test_filtra_por_referencia(self):
        vazio = self.client.get("/api/payments/callback-log/?q=NAO-EXISTE")
        self.assertEqual(len(vazio.data.get("results", vazio.data)), 0)

    def test_sem_capacidade_nao_ve_o_registo(self):
        outro = User.objects.create_user(username="sem-permissao", password="segredo-forte-2", email="sem-permissao@updigital.co.mz")
        self.client.force_authenticate(outro)
        self.assertEqual(self.client.get("/api/payments/callback-log/").status_code, 403)


class HistoricoDeRecuperacoesTest(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin-recuperacoes", password="segredo-forte-3", email="b@updigital.co.mz",
        )
        self.client.force_authenticate(self.admin)

    def test_lista_as_intencoes_de_recuperacao_e_ignora_as_outras(self):
        PaymentIntent.objects.create(
            reference="PAY-REC-1",
            idempotency_key="idem-rec-1",
            purpose=PaymentIntent.Purpose.POS_CARD_TOPUP,
            amount=Decimal("150.00"),
            payer_phone="258840000003",
            status=PaymentIntent.Status.CONFIRMED,
            metadata={"kind": "card_recovery", "reason": "perdido", "old_card_ids": [1, 2], "blocked_cards": 2},
        )
        PaymentIntent.objects.create(
            reference="PAY-NORMAL-1",
            idempotency_key="idem-normal-1",
            purpose=PaymentIntent.Purpose.POS_CARD_TOPUP,
            amount=Decimal("50.00"),
            payer_phone="258840000004",
            status=PaymentIntent.Status.CONFIRMED,
            metadata={},
        )

        resposta = self.client.get("/api/card-recoveries/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["count"], 1)
        linha = resposta.data["results"][0]
        self.assertEqual(linha["reference"], "PAY-REC-1")
        self.assertEqual(linha["reason"], "perdido")
        self.assertEqual(linha["blocked_cards"], 2)
