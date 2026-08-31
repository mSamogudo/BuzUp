"""Criterios de pronto do CMS (03-cms-especificacao.md, seccao 6).

Cada teste corresponde a uma linha dessa lista.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.cms.models import (
    EcoSystem,
    Menu,
    MenuItem,
    Page,
    PageBlock,
    PageVersion,
    ScheduledPublication,
    SeoMeta,
)
from apps.cms.services import run_due_publications

User = get_user_model()


def i18n(pt, en=None):
    return {"pt": pt, "en": en if en is not None else pt}


class CmsBaseTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_superuser(
            username="admin-cms", password="segredo-forte-1", email="admin@updigital.co.mz",
        )
        self.client.force_authenticate(self.admin)

    def _page(self, slug="teste", status=Page.Status.DRAFT):
        page = Page.objects.create(
            slug=slug, title=i18n("Teste", "Test"),
            template=Page.Template.GENERIC, status=status, locales=["pt", "en"],
        )
        SeoMeta.objects.create(
            page=page, title=i18n("Titulo", "Title"), description=i18n("Descricao", "Description"),
        )
        PageBlock.objects.create(
            page=page, type="cta", position=0, enabled=True,
            content={"h2": i18n("Antes", "Before"), "lead": i18n("Texto", "Text"),
                     "cta1": i18n("Ir", "Go"), "cta2": i18n("", "")},
        )
        return page


class EdicaoEPublicacaoTest(CmsBaseTest):
    def test_gravar_bloco_cria_versao_e_publicar_muda_o_site(self):
        page = self._page()
        antes = PageVersion.objects.filter(page=page).count()

        resposta = self.client.put(
            f"/api/cms/pages/{page.pk}/blocks/",
            [{"type": "cta", "enabled": True,
              "content": {"h2": i18n("Depois", "After"), "lead": i18n("Texto", "Text"),
                          "cta1": i18n("Ir", "Go"), "cta2": i18n("", "")}}],
            format="json",
        )
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(PageVersion.objects.filter(page=page).count(), antes + 1)

        publicar = self.client.post(f"/api/cms/pages/{page.pk}/publish/", {}, format="json")
        self.assertEqual(publicar.status_code, 200, publicar.data)

        self.client.force_authenticate(None)
        publico = self.client.get(f"/api/public/pages/{page.slug}/pt/")
        self.assertEqual(publico.status_code, 200)
        self.assertEqual(publico.data["blocks"][0]["content"]["h2"], "Depois")

        ingles = self.client.get(f"/api/public/pages/{page.slug}/en/")
        self.assertEqual(ingles.data["blocks"][0]["content"]["h2"], "After")

    def test_publicar_recusa_pagina_incompleta(self):
        page = self._page(slug="incompleta")
        page.seo.description = {"pt": "", "en": ""}
        page.seo.save()
        resposta = self.client.post(f"/api/cms/pages/{page.pk}/publish/", {}, format="json")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("errors", resposta.data)

    def test_publicar_invalida_a_cache(self):
        page = self._page(slug="cacheada", status=Page.Status.PUBLISHED)
        self.client.force_authenticate(None)
        primeira = self.client.get(f"/api/public/pages/{page.slug}/pt/")
        self.assertEqual(primeira.data["blocks"][0]["content"]["h2"], "Antes")

        self.client.force_authenticate(self.admin)
        self.client.put(
            f"/api/cms/pages/{page.pk}/blocks/",
            [{"type": "cta", "enabled": True,
              "content": {"h2": i18n("Novo", "New"), "lead": i18n("Texto", "Text"),
                          "cta1": i18n("Ir", "Go"), "cta2": i18n("", "")}}],
            format="json",
        )
        self.client.post(f"/api/cms/pages/{page.pk}/publish/", {}, format="json")

        self.client.force_authenticate(None)
        segunda = self.client.get(f"/api/public/pages/{page.slug}/pt/")
        self.assertEqual(segunda.data["blocks"][0]["content"]["h2"], "Novo")


class AgendamentoTest(CmsBaseTest):
    def test_agendamento_vai_ao_ar_sozinho(self):
        page = self._page(slug="agendada")
        futuro = timezone.now() + timedelta(minutes=5)
        resposta = self.client.post(
            f"/api/cms/pages/{page.pk}/schedule/", {"run_at": futuro.isoformat()}, format="json",
        )
        self.assertEqual(resposta.status_code, 201, resposta.data)
        page.refresh_from_db()
        self.assertEqual(page.status, Page.Status.SCHEDULED)

        # O worker so age depois da hora marcada.
        self.assertEqual(run_due_publications(now=timezone.now()), [])
        run_due_publications(now=futuro + timedelta(seconds=1))

        page.refresh_from_db()
        self.assertEqual(page.status, Page.Status.PUBLISHED)
        job = ScheduledPublication.objects.get(target_id=page.pk)
        self.assertEqual(job.status, ScheduledPublication.Status.DONE)

    def test_agendamento_no_passado_e_recusado(self):
        page = self._page(slug="passado")
        passado = timezone.now() - timedelta(minutes=1)
        resposta = self.client.post(
            f"/api/cms/pages/{page.pk}/schedule/", {"run_at": passado.isoformat()}, format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_cancelar_agendamento_devolve_a_pagina_a_rascunho(self):
        page = self._page(slug="cancelavel")
        futuro = timezone.now() + timedelta(minutes=5)
        criada = self.client.post(
            f"/api/cms/pages/{page.pk}/schedule/", {"run_at": futuro.isoformat()}, format="json",
        )
        job_id = criada.data["id"]
        self.client.delete(f"/api/cms/schedules/{job_id}/")
        page.refresh_from_db()
        self.assertEqual(page.status, Page.Status.DRAFT)
        self.assertEqual(
            ScheduledPublication.objects.get(pk=job_id).status,
            ScheduledPublication.Status.CANCELLED,
        )


class VersoesTest(CmsBaseTest):
    def test_restaurar_nao_perde_historico(self):
        page = self._page(slug="versionada")
        primeira = PageVersion.objects.create(
            page=page, number=1, snapshot={
                "page": {"slug": page.slug, "title": page.title, "template": page.template,
                         "locales": page.locales},
                "blocks": [{"type": "cta", "position": 0, "enabled": True,
                            "content": {"h2": i18n("Original", "Original")}}],
                "seo": None,
            },
        )
        self.client.put(
            f"/api/cms/pages/{page.pk}/blocks/",
            [{"type": "cta", "enabled": True, "content": {"h2": i18n("Alterado", "Changed")}}],
            format="json",
        )
        total_antes = PageVersion.objects.filter(page=page).count()

        resposta = self.client.post(f"/api/cms/versions/{primeira.pk}/restore/", {}, format="json")
        self.assertEqual(resposta.status_code, 200, resposta.data)

        self.assertEqual(PageVersion.objects.filter(page=page).count(), total_antes + 1)
        self.assertTrue(PageVersion.objects.filter(pk=primeira.pk).exists())
        page.refresh_from_db()
        self.assertEqual(page.blocks.first().content["h2"]["pt"], "Original")
        self.assertEqual(page.status, Page.Status.DRAFT)

    def test_comparar_versoes_mostra_diferencas(self):
        page = self._page(slug="comparada")
        a = PageVersion.objects.create(page=page, number=1, snapshot={"blocks": [{"content": {"h2": "A"}}]})
        b = PageVersion.objects.create(page=page, number=2, snapshot={"blocks": [{"content": {"h2": "B"}}]})
        resposta = self.client.get(f"/api/cms/versions/compare/?a={a.pk}&b={b.pk}")
        self.assertEqual(resposta.status_code, 200)
        campos = [item["field"] for item in resposta.data["changes"]]
        self.assertIn("blocks[0].content.h2", campos)


class MenusTest(CmsBaseTest):
    def test_ordem_do_menu_muda_o_rodape_em_pt_e_en(self):
        menu = Menu.objects.create(key=Menu.Key.FOOTER_PRODUCT, label=i18n("Produto", "Product"))
        MenuItem.objects.create(menu=menu, label=i18n("Um", "One"), href="/um", position=0)
        MenuItem.objects.create(menu=menu, label=i18n("Dois", "Two"), href="/dois", position=1)

        resposta = self.client.put(
            f"/api/cms/menus/{menu.key}/items/",
            [
                {"label": i18n("Dois", "Two"), "href": "/dois", "visible": True},
                {"label": i18n("Um", "One"), "href": "/um", "visible": True},
            ],
            format="json",
        )
        self.assertEqual(resposta.status_code, 200, resposta.data)

        self.client.force_authenticate(None)
        pt = self.client.get("/api/public/site/pt/")
        en = self.client.get("/api/public/site/en/")
        self.assertEqual([i["label"] for i in pt.data["menus"]["footer_product"]["items"]], ["Dois", "Um"])
        self.assertEqual([i["label"] for i in en.data["menus"]["footer_product"]["items"]], ["Two", "One"])


class PermissoesTest(CmsBaseTest):
    def test_gestor_de_conteudo_nao_abre_modulos_de_operacao(self):
        from apps.users.models import Role, UserRole

        role, _ = Role.objects.get_or_create(
            code="content_manager",
            defaults={"name": "Gestor de Conteudo", "permissions": [
                "content.read", "content.write", "content.publish",
                "media.manage", "menus.manage", "seo.manage", "plans.manage", "requests.read",
            ]},
        )
        editor = User.objects.create_user(
            username="editora", password="segredo-forte-2", email="editor@updigital.co.mz",
        )
        UserRole.objects.create(user=editor, role=role)

        self.client.force_authenticate(editor)
        self.assertEqual(self.client.get("/api/cms/pages/").status_code, 200)
        # Operacao fechada: rotas e pagamentos devolvem 403.
        self.assertEqual(self.client.get("/api/routes/").status_code, 403)
        self.assertEqual(self.client.get("/api/payments/intents/").status_code, 403)


class MediaTest(CmsBaseTest):
    def test_media_em_uso_nao_pode_ser_eliminada(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.cms.models import MediaAsset

        asset = MediaAsset.objects.create(
            file=SimpleUploadedFile("logo.png", b"\x89PNG\r\n\x1a\n", content_type="image/png"),
            filename="logo.png", mime="image/png", bytes=8,
        )
        page = self._page(slug="com-media")
        PageBlock.objects.create(
            page=page, type="media", position=1, enabled=True,
            content={"media_id": asset.pk, "caption": i18n("Logo", "Logo")},
        )
        resposta = self.client.delete(f"/api/cms/media/{asset.pk}/")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("used_in", resposta.data)

    def test_ecossistema_publico_so_mostra_publicados(self):
        EcoSystem.objects.create(name="PayUp", url="https://payup.updigital.co.mz",
                                 status=EcoSystem.Status.PUBLISHED, position=0)
        EcoSystem.objects.create(name="Rascunho", url="", status=EcoSystem.Status.DRAFT, position=1)
        self.client.force_authenticate(None)
        resposta = self.client.get("/api/public/eco-systems/")
        nomes = [s["name"] for s in resposta.data["systems"]]
        self.assertEqual(nomes, ["PayUp"])


class PrevisualizacaoTest(CmsBaseTest):
    def test_token_de_previsualizacao_abre_o_rascunho(self):
        page = self._page(slug="rascunho-previsto")
        token = self.client.get(f"/api/cms/pages/{page.pk}/preview-token/").data["token"]

        self.client.force_authenticate(None)
        sem_token = self.client.get(f"/api/public/pages/{page.slug}/pt/")
        self.assertEqual(sem_token.status_code, 404)

        com_token = self.client.get(f"/api/public/pages/{page.slug}/pt/?preview_token={token}")
        self.assertEqual(com_token.status_code, 200)
        self.assertTrue(com_token.data["preview"])
