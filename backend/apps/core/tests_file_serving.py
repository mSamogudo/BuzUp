"""Entrega de APKs: pelo nginx quando ha nginx, pelo Django quando nao ha.

O que estes testes protegem: um APK de 40 MB servido pelo gunicorn prende um
worker durante todo o download e e cortado ao fim de 120s. Com
X-Accel-Redirect o Django responde num instante e o nginx envia os bytes.
Se alguem voltar a por um FileResponse nestas vistas, isto acusa.
"""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.app_releases.models import AppRelease


class ApkServingTests(TestCase):
    def setUp(self):
        self.release = AppRelease.objects.create(
            app_type=AppRelease.AppType.POS,
            version_name="9.9.9",
            version_code=999,
            status=AppRelease.Status.PUBLISHED,
            apk_file=SimpleUploadedFile(
                "buzup-pos-teste.apk", b"conteudo-do-apk",
                content_type="application/vnd.android.package-archive",
            ),
        )

    def tearDown(self):
        self.release.apk_file.delete(save=False)

    @override_settings(USE_X_ACCEL_REDIRECT=True)
    def test_with_nginx_the_body_is_empty_and_nginx_gets_the_path(self):
        res = self.client.get(f"/api/app-releases/{self.release.pk}/download/")
        self.assertEqual(res.status_code, 200)
        redirect = res.headers.get("X-Accel-Redirect", "")
        self.assertTrue(redirect.startswith("/protected-media/"),
                        f"o nginx nao recebeu o caminho interno: {redirect!r}")
        self.assertIn("app-releases/", redirect)
        # O corpo tem de vir vazio: se o Django enviasse os bytes, o worker
        # ficava presos na mesma e o problema mantinha-se.
        self.assertEqual(res.content, b"")
        self.assertEqual(res.headers["Content-Type"],
                         "application/vnd.android.package-archive")
        self.assertIn("attachment", res.headers["Content-Disposition"])
        self.assertIn("buzup-pos-9.9.9.apk", res.headers["Content-Disposition"])

    @override_settings(USE_X_ACCEL_REDIRECT=False)
    def test_without_nginx_django_serves_the_bytes(self):
        res = self.client.get(f"/api/app-releases/{self.release.pk}/download/")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("X-Accel-Redirect", res.headers)
        self.assertEqual(b"".join(res.streaming_content), b"conteudo-do-apk")

    @override_settings(USE_X_ACCEL_REDIRECT=True)
    def test_friendly_link_uses_nginx_too(self):
        res = self.client.get("/api/apps/pos/download/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.headers.get("X-Accel-Redirect", "").startswith("/protected-media/"))
        self.assertEqual(res.content, b"")

    @override_settings(USE_X_ACCEL_REDIRECT=True)
    def test_unpublished_release_is_still_refused(self):
        """A delegacao ao nginx nao pode saltar a verificacao de estado."""
        self.release.status = AppRelease.Status.SUSPENDED
        self.release.save(update_fields=["status"])
        res = self.client.get(f"/api/app-releases/{self.release.pk}/download/")
        self.assertEqual(res.status_code, 404)
        self.assertNotIn("X-Accel-Redirect", res.headers)

    @override_settings(USE_X_ACCEL_REDIRECT=True)
    def test_path_is_escaped(self):
        """Nomes com espacos nao podem partir o cabecalho."""
        from apps.core.file_serving import serve_file_field

        class _Field:
            name = "app-releases/nome com espaco.apk"

        res = serve_file_field(_Field(), filename="x.apk", content_type="application/octet-stream")
        self.assertEqual(res["X-Accel-Redirect"],
                         "/protected-media/app-releases/nome%20com%20espaco.apk")
