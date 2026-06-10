"""Testes da autenticacao de webhooks de pagamento (anti-forja de top-ups)."""
from __future__ import annotations

import hashlib
import hmac

from django.test import SimpleTestCase

from apps.payments.services.webhook_security import verify_webhook_signature


class _FakeRequest:
    def __init__(self, body=b"", meta=None, get=None):
        self.body = body
        self.META = meta or {}
        self.GET = get or {}


SECRET = "s3cr3t-token-xyz"
BODY = b'{"status":"confirmed","reference":"TOP-abc"}'


def _good_hmac() -> str:
    return hmac.new(SECRET.encode(), BODY, hashlib.sha256).hexdigest()


class WebhookSignatureTests(SimpleTestCase):
    def test_no_secret_returns_no_secret(self):
        ok, method = verify_webhook_signature(_FakeRequest(BODY), "")
        self.assertEqual((ok, method), (False, "no-secret"))

    def test_valid_hmac_header(self):
        req = _FakeRequest(BODY, {"HTTP_X_WEBHOOK_SIGNATURE": _good_hmac()})
        self.assertEqual(verify_webhook_signature(req, SECRET), (True, "hmac"))

    def test_hmac_with_algorithm_prefix(self):
        req = _FakeRequest(BODY, {"HTTP_X_SIGNATURE": "sha256=" + _good_hmac()})
        self.assertEqual(verify_webhook_signature(req, SECRET), (True, "hmac"))

    def test_invalid_hmac_rejected(self):
        req = _FakeRequest(BODY, {"HTTP_X_WEBHOOK_SIGNATURE": "deadbeef"})
        self.assertEqual(verify_webhook_signature(req, SECRET), (False, "invalid"))

    def test_valid_token_header(self):
        req = _FakeRequest(BODY, {"HTTP_X_WEBHOOK_TOKEN": SECRET})
        self.assertEqual(verify_webhook_signature(req, SECRET), (True, "token-header"))

    def test_valid_token_query(self):
        req = _FakeRequest(BODY, {}, {"token": SECRET})
        self.assertEqual(verify_webhook_signature(req, SECRET), (True, "token-query"))

    def test_wrong_token_rejected(self):
        self.assertEqual(
            verify_webhook_signature(_FakeRequest(BODY, {}, {"token": "nope"}), SECRET),
            (False, "invalid"),
        )

    def test_no_proof_rejected(self):
        self.assertEqual(verify_webhook_signature(_FakeRequest(BODY), SECRET), (False, "invalid"))
