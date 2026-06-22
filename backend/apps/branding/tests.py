"""Testes da configuracao de marca (singleton + GET publico / PATCH protegido)."""
from __future__ import annotations

from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.branding.models import BrandingSettings

User = get_user_model()


def _png(name="logo.png"):
    from django.core.files.uploadedfile import SimpleUploadedFile

    # PNG minimo de 1x1 (cabecalho valido chega para um FileField).
    data = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
        b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return SimpleUploadedFile(name, data, content_type="image/png")


@override_settings(SECURE_SSL_REDIRECT=False)
class BrandingTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_singleton_load_returns_same_row(self):
        a = BrandingSettings.load()
        b = BrandingSettings.load()
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(BrandingSettings.objects.count(), 1)

    def test_get_is_public_and_returns_url_keys(self):
        resp = self.client.get("/api/branding/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("platform_name", resp.data)
        # slots expostos como <slot>_url (vazios por defeito)
        self.assertIn("primary_logo_url", resp.data)
        self.assertEqual(resp.data["primary_logo_url"], "")

    def test_patch_requires_auth(self):
        resp = self.client.patch("/api/branding/", {"platform_name": "X"})
        self.assertIn(resp.status_code, (401, 403))

    def test_patch_without_capability_is_forbidden(self):
        u = User.objects.create_user(username="nocaps", password="x")
        self.client.force_authenticate(u)
        resp = self.client.patch("/api/branding/", {"platform_name": "X"})
        self.assertEqual(resp.status_code, 403)

    def test_superuser_can_update_name_and_upload_logo(self):
        u = User.objects.create_superuser(username="boss", password="x")
        self.client.force_authenticate(u)
        resp = self.client.patch(
            "/api/branding/",
            {"platform_name": "BuzUp Teste", "primary_logo": _png()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["platform_name"], "BuzUp Teste")
        self.assertTrue(resp.data["primary_logo_url"])
        obj = BrandingSettings.load()
        self.assertTrue(obj.primary_logo)

    def test_invalid_logo_extension_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        u = User.objects.create_superuser(username="boss2", password="x")
        self.client.force_authenticate(u)
        bad = SimpleUploadedFile("evil.exe", b"MZ", content_type="application/octet-stream")
        resp = self.client.patch(
            "/api/branding/", {"primary_logo": bad}, format="multipart"
        )
        self.assertEqual(resp.status_code, 400)
