from django.test import SimpleTestCase
from django.urls import resolve

from apps.app_releases.api.views import AppDownloadPageView, AppLatestDownloadView


class AppReleasePublicUrlTests(SimpleTestCase):
    def test_download_page_accepts_trailing_and_non_trailing_slash(self):
        for url in ("/api/baixar", "/api/baixar/"):
            match = resolve(url)

            self.assertEqual(match.func.view_class, AppDownloadPageView)

    def test_short_download_aliases_accept_trailing_and_non_trailing_slash(self):
        cases = {
            "/api/pos": "pos",
            "/api/pos/": "pos",
            "/api/passageiro": "passageiro",
            "/api/passageiro/": "passageiro",
        }

        for url, slug in cases.items():
            match = resolve(url)

            self.assertEqual(match.func.view_class, AppLatestDownloadView)
            self.assertEqual(match.kwargs["slug"], slug)
