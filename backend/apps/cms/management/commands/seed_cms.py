"""Carrega o conteudo dos prototipos para o CMS, verbatim.

Fonte do conteudo: `apps/cms/seeds/site_copy.json`, extraido dos objectos
`PT`/`EN` de docs/design-handoff/design/*.dc.html. Regra do handoff: nenhum
texto novo inventado — o que esta no desenho e o que vai para a base de dados.

Idempotente: correr duas vezes deixa o mesmo resultado.
"""

import json
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.cms.models import (
    EcoSystem,
    MediaAsset,
    Menu,
    MenuItem,
    Page,
    PageBlock,
    Plan,
    PlanFeature,
    SeoMeta,
)
from apps.cms.services import create_version, invalidate_all_cache

SEED_FILE = Path(__file__).resolve().parents[3] / "cms" / "seeds" / "site_copy.json"
# Os assets do handoff vivem no repositorio, fora do backend.
ASSETS_DIR = Path(settings.BASE_DIR).resolve().parents[0] / "docs" / "design-handoff" / "design" / "assets"


def i18n(pt, en):
    return {"pt": pt, "en": en}


def pair(pt_dict, en_dict, key):
    return i18n(pt_dict.get(key, ""), en_dict.get(key, ""))


def pair_list(pt_list, en_list, key):
    return i18n([item.get(key, "") for item in pt_list], [item.get(key, "") for item in en_list])


class Command(BaseCommand):
    help = "Carrega paginas, blocos, menus, planos e ecossistema do CMS a partir dos prototipos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--publish", action="store_true",
            help="Publica as paginas depois de as carregar (por omissao ficam em rascunho).",
        )
        parser.add_argument(
            "--if-empty", action="store_true",
            help="Nao faz nada se ja houver paginas. E o modo do arranque automatico: "
                 "um deploy novo nasce com o site, mas nunca sobrepoe o que a equipa editou.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options.get("if_empty") and Page.objects.exists():
            self.stdout.write("CMS ja tem conteudo; nada a fazer.")
            return
        if not SEED_FILE.exists():
            self.stderr.write(f"Ficheiro de conteudo em falta: {SEED_FILE}")
            return
        copy = json.loads(SEED_FILE.read_text(encoding="utf-8"))

        media = self._seed_media()
        systems = self._seed_eco_systems(copy, media)
        plans = self._seed_plans(copy)
        self._seed_plan_features(copy)

        landing = self._seed_landing(copy, media, plans, systems)
        pricing = self._seed_pricing(copy, plans, systems)
        contact = self._seed_contact(copy, systems)
        apps_page = self._seed_apps_page()

        self._seed_menus(copy, [landing, pricing, contact, apps_page])

        if options["publish"]:
            for page in (landing, pricing, contact):
                page.status = Page.Status.PUBLISHED
                page.published_at = timezone.now()
                page.save(update_fields=["status", "published_at", "updated_at"])

        invalidate_all_cache()
        self.stdout.write(self.style.SUCCESS(
            f"CMS carregado: {Page.objects.count()} paginas, {PageBlock.objects.count()} blocos, "
            f"{Plan.objects.count()} planos, {PlanFeature.objects.count()} linhas de comparacao, "
            f"{EcoSystem.objects.count()} sistemas, {MediaAsset.objects.count()} ficheiros."
        ))

    # -- Media --------------------------------------------------------------

    def _seed_media(self):
        wanted = [
            "logo-payup.png", "logo-cashup.png", "logo-gateup.png",
            "logo-vura.png", "logo-ossoma.png",
            "busup-logo-light.png", "busup-logo-dark.png", "busup-mark.png",
            "logo-updigital-dark.png", "logo-updigital-white.png",
            "mpesa.png", "emola.png",
        ]
        out = {}
        for name in wanted:
            source = ASSETS_DIR / name
            existing = MediaAsset.objects.filter(filename=name).first()
            if existing:
                out[name] = existing
                continue
            if not source.exists():
                self.stderr.write(f"Asset em falta, ignorado: {source}")
                continue
            asset = MediaAsset(
                filename=name,
                mime="image/png",
                bytes=source.stat().st_size,
                folder="marca",
                alt=i18n(name.replace("logo-", "").replace(".png", "").title(),
                         name.replace("logo-", "").replace(".png", "").title()),
            )
            with source.open("rb") as fh:
                asset.file.save(name, File(fh), save=False)
            asset.save()
            out[name] = asset
        return out

    # -- Ecossistema e planos ----------------------------------------------

    def _seed_eco_systems(self, copy, media):
        items = copy["landing"]["PT"]["ecoItems"]
        out = {}
        for position, item in enumerate(items):
            logo_name = Path(item["logo"]).name
            system, _ = EcoSystem.objects.update_or_create(
                name=item["name"],
                defaults={
                    "url": item["url"],
                    "logo": media.get(logo_name),
                    "status": EcoSystem.Status.PUBLISHED,
                    "position": position,
                },
            )
            out[item["name"]] = system
        # O BusUp faz parte do ecossistema que o rodape mostra.
        busup, _ = EcoSystem.objects.update_or_create(
            name="BusUp",
            defaults={
                "url": "https://busup.updigital.co.mz",
                "logo": media.get("busup-logo-light.png"),
                "status": EcoSystem.Status.PUBLISHED,
                "position": len(items),
            },
        )
        out["BusUp"] = busup
        return out

    def _seed_plans(self, copy):
        pt = copy["precos"]["PT"]["plans"]
        en = copy["precos"]["EN"]["plans"]
        out = []
        for position, (p, e) in enumerate(zip(pt, en)):
            plan, _ = Plan.objects.update_or_create(
                position=position,
                defaults={
                    "name": i18n(p["name"], e["name"]),
                    "price_label": i18n(p["price"], e["price"]),
                    # `who` e a linha de quem serve; `unit` e a base de cobranca.
                    # O desenho mostra as duas, separadas por um ponto.
                    "unit": i18n(f"{p['who']} {p['unit']}", f"{e['who']} {e['unit']}"),
                    "cta_label": i18n(p["cta"], e["cta"]),
                    "items": i18n(p["items"], e["items"]),
                    "highlighted": bool(p.get("featured")),
                    "visible": True,
                },
            )
            out.append(plan)
        return out

    def _seed_plan_features(self, copy):
        pt = copy["precos"]["PT"]["rows"]
        en = copy["precos"]["EN"]["rows"]
        PlanFeature.objects.all().hard_delete()
        for position, (p, e) in enumerate(zip(pt, en)):
            PlanFeature.objects.create(
                label=i18n(p["label"], e["label"]),
                urban=i18n(p["a"], e["a"]),
                intercity=i18n(p["b"], e["b"]),
                institutional=i18n(p["c"], e["c"]),
                position=position,
            )

    # -- Paginas ------------------------------------------------------------

    def _page(self, slug, template, title_pt, title_en, seo_title, seo_desc):
        page, _ = Page.objects.update_or_create(
            slug=slug,
            defaults={
                "title": i18n(title_pt, title_en),
                "template": template,
                "locales": ["pt", "en"],
            },
        )
        seo, _ = SeoMeta.objects.get_or_create(page=page)
        seo.title = seo_title
        seo.description = seo_desc
        seo.slug = i18n(slug, slug)
        seo.save()
        return page

    def _blocks(self, page, blocks):
        page.blocks.all().hard_delete()
        for position, (block_type, content) in enumerate(blocks):
            PageBlock.objects.create(
                page=page, type=block_type, position=position, enabled=True, content=content,
            )
        create_version(page, note="Carregado dos protótipos")

    def _seed_landing(self, copy, media, plans, systems):
        pt, en = copy["landing"]["PT"], copy["landing"]["EN"]
        page = self._page(
            "", Page.Template.LANDING, "Landing", "Landing",
            i18n("BusUp — bilhética digital para o transporte de passageiros",
                 "BusUp — digital ticketing for passenger transport"),
            i18n(pt["heroLead"][:160], en["heroLead"][:160]),
        )
        self._blocks(page, [
            ("heroi", {
                "badge": pair(pt, en, "heroBadge"),
                "h1a": pair(pt, en, "heroH1a"),
                "h1b": pair(pt, en, "heroH1b"),
                "lead": pair(pt, en, "heroLead"),
                "cta1": pair(pt, en, "ctaPrimary"),
                # O segundo botao do heroi vai para a compra de bilhetes; o
                # rotulo tem de ser o dessa accao, nao o de "ver a plataforma".
                "cta2": pair(pt, en, "buyTicket"),
                # O terceiro botao do desenho leva a maqueta do portal.
                "cta3": pair(pt, en, "ctaSecondary"),
                "chips": i18n(pt["chips"], en["chips"]),
                "tags": i18n(
                    [pt[k] for k in ("tag1", "tag2", "tag3", "tag4")],
                    [en[k] for k in ("tag1", "tag2", "tag3", "tag4")],
                ),
            }),
            ("logos", {
                "h2": pair(pt, en, "ecoStripTitle"),
                "lead": pair(pt, en, "logosLead"),
                # A tira do desenho abre com a UpDigital, que tem uma variante
                # por tema (o logotipo escuro nao se ve sobre fundo navy).
                "items": [
                    {
                        "media_id": media["logo-updigital-dark.png"].pk if media.get("logo-updigital-dark.png") else None,
                        "media_id_dark": media["logo-updigital-white.png"].pk if media.get("logo-updigital-white.png") else None,
                        "alt": i18n("UpDigital", "UpDigital"),
                        "href": i18n("https://updigital.co.mz", "https://updigital.co.mz"),
                    },
                ] + [
                    {
                        "media_id": (media.get(Path(item["logo"]).name).pk
                                     if media.get(Path(item["logo"]).name) else None),
                        "alt": i18n(item["name"], item["name"]),
                        "href": i18n(item["url"], item["url"]),
                    }
                    for item in pt["ecoItems"]
                ],
            }),
            ("recursos", {
                "h2": pair(pt, en, "featH2"),
                "lead": pair(pt, en, "featLead"),
                "map_title": pair(pt, en, "mapPanel"),
                "map_note": pair(pt, en, "mapPlaceholder"),
                "items": [
                    {
                        "title": pair(pt, en, f"f{n}t"),
                        "text": pair(pt, en, f"f{n}p"),
                        "bullets": i18n(
                            [pt[k] for k in ("f5a", "f5b", "f5c")] if n == 5 else [],
                            [en[k] for k in ("f5a", "f5b", "f5c")] if n == 5 else [],
                        ),
                    }
                    for n in (1, 2, 3, 4, 5)
                ],
            }),
            ("porque", {
                "h2": pair(pt, en, "statsH2"),
                "lead": pair(pt, en, "statsLead"),
                "stats": [
                    {"value": i18n(p["v"], e["v"]), "label": i18n(p["l"], e["l"])}
                    for p, e in zip(pt["stats"], en["stats"])
                ],
            }),
            ("passos", {
                "h2": pair(pt, en, "stepsH2"),
                "lead": pair(pt, en, "stepsLead"),
                "panel_title": pair(pt, en, "stepsPanelTitle"),
                "panel_text": pair(pt, en, "stepsPanelText"),
                "steps": [
                    {
                        "n": i18n(p["n"], e["n"]),
                        "title": i18n(p["title"], e["title"]),
                        "text": i18n(p["text"], e["text"]),
                        "m1": i18n(p["m1"], e["m1"]),
                        "m1cta": i18n(p["m1cta"], e["m1cta"]),
                        "m2": i18n(p["m2"], e["m2"]),
                        "m2a": i18n(p["m2a"], e["m2a"]),
                        "m2b": i18n(p["m2b"], e["m2b"]),
                    }
                    for p, e in zip(pt["steps"], en["steps"])
                ],
            }),
            ("casos", {
                "h2": pair(pt, en, "casesH2"),
                "lead": pair(pt, en, "casesLead"),
                "items": [
                    {
                        "kind": i18n(p["kind"], e["kind"]),
                        "quote": i18n(p["quote"], e["quote"]),
                        "who": i18n(p["who"], e["who"]),
                    }
                    for p, e in zip(pt["cases"], en["cases"])
                ],
            }),
            ("precos", {
                "h2": pair(pt, en, "priceH2"),
                "lead": pair(pt, en, "priceLead"),
                "plan_ids": [plan.pk for plan in plans],
            }),
            ("faq", {
                "h2": pair(pt, en, "faqH2"),
                "lead": pair(pt, en, "faqLead"),
                "items": [
                    {"q": i18n(p["q"], e["q"]), "a": i18n(p["a"], e["a"])}
                    for p, e in zip(pt["faqs"], en["faqs"])
                ],
            }),
            ("cta", {
                "h2": pair(pt, en, "ctaH2"),
                "lead": pair(pt, en, "ctaLead"),
                "cta1": pair(pt, en, "ctaContact"),
                "cta2": pair(pt, en, "ctaPricing"),
                "facts": i18n(pt["formFacts"], en["formFacts"]),
            }),
            ("eco", {
                "label": pair(pt, en, "ecoLabel"),
                "h2": pair(pt, en, "ecoH2"),
                "lead": pair(pt, en, "ecoLead"),
                "note": pair(pt, en, "ecoNote"),
                "system_ids": [systems[item["name"]].pk for item in pt["ecoItems"]],
            }),
        ])
        return page

    def _seed_pricing(self, copy, plans, systems):
        pt, en = copy["precos"]["PT"], copy["precos"]["EN"]
        page = self._page(
            "precos", Page.Template.PRICING, "Preços", "Pricing",
            i18n("Preços do BusUp — por operação, não por tabela",
                 "BusUp pricing — per operation, not per price list"),
            i18n(pt["lead"][:160], en["lead"][:160]),
        )
        self._blocks(page, [
            ("heroi", {
                "badge": pair(pt, en, "badge"),
                "h1a": pair(pt, en, "h1a"),
                "h1b": pair(pt, en, "h1b"),
                "lead": pair(pt, en, "lead"),
                # O heroi da pagina de precos nao tem botoes no desenho: a
                # accao esta nos cartoes dos planos, logo a seguir.
                "cta1": i18n("", ""),
                "cta2": i18n("", ""),
                "chips": i18n([], []),
            }),
            ("precos", {
                "h2": pair(pt, en, "tableH2"),
                "lead": pair(pt, en, "tableLead"),
                "plan_ids": [plan.pk for plan in plans],
                "table_col": pair(pt, en, "tableCol"),
                "table_foot": pair(pt, en, "tableFoot"),
                "quote": pair(pt, en, "quote"),
                "notes": [
                    {"h": i18n(p["h"], e["h"]), "p": i18n(p["p"], e["p"])}
                    for p, e in zip(pt["notes"], en["notes"])
                ],
            }),
            ("faq", {
                "h2": pair(pt, en, "faqH2"),
                "lead": pair(pt, en, "faqLead"),
                "items": [
                    {"q": i18n(p["q"], e["q"]), "a": i18n(p["a"], e["a"])}
                    for p, e in zip(pt["faqs"], en["faqs"])
                ],
            }),
            ("cta", {
                "h2": pair(pt, en, "ctaH2"),
                "lead": pair(pt, en, "ctaLead"),
                "cta1": pair(pt, en, "ctaContact"),
                "cta2": pair(pt, en, "ctaProduct"),
            }),
            ("eco", {
                "label": pair(pt, en, "ecoLabel"),
                "h2": pair(pt, en, "ecoH2"),
                "lead": pair(pt, en, "ecoLead"),
                "note": pair(pt, en, "ecoNote"),
                "system_ids": [systems[item["name"]].pk for item in pt["ecoItems"]],
            }),
        ])
        return page

    def _seed_contact(self, copy, systems):
        pt, en = copy["contactos"]["PT"], copy["contactos"]["EN"]
        page = self._page(
            "contactos", Page.Template.CONTACT, "Contactos", "Contact",
            i18n("Contactos — BusUp", "Contact — BusUp"),
            i18n(pt["lead"][:160], en["lead"][:160]),
        )
        self._blocks(page, [
            ("heroi", {
                "badge": pair(pt, en, "badge"),
                "h1a": pair(pt, en, "h1"),
                "h1b": i18n("", ""),
                "lead": pair(pt, en, "lead"),
                "cta1": i18n("", ""),
                "cta2": i18n("", ""),
                "chips": i18n([], []),
            }),
            ("form", {
                "h2": pair(pt, en, "formTitle"),
                "lead": pair(pt, en, "formSub"),
                "facts": i18n(
                    [pt["g1"], pt["g2"], pt["g3"]],
                    [en["g1"], en["g2"], en["g3"]],
                ),
                "fields": [
                    {"key": "name", "label": pair(pt, en, "fName"), "required": True},
                    {"key": "role", "label": pair(pt, en, "fRole"), "required": False},
                    {"key": "organization", "label": pair(pt, en, "fCompany"), "required": False},
                    {"key": "phone", "label": pair(pt, en, "fPhone"), "required": True},
                    {"key": "email", "label": pair(pt, en, "fEmail"), "required": False},
                    # `values` anda a par de `options`: o que se mostra e
                    # traduzido, o que se grava e a chave da API. Sem isto o
                    # formulario mandava o rotulo e o campo escolhia o valor
                    # pela POSICAO na lista — "Venda online" entrava como
                    # `operator` e as duas ultimas opcoes caiam ambas em
                    # `other`. Ninguem via erro nenhum; a lista comercial e que
                    # dizia outra coisa do que a pessoa tinha pedido.
                    {"key": "fleet_size", "label": pair(pt, en, "fFleet"), "required": False,
                     "options": i18n(pt["fleets"], en["fleets"]),
                     "values": ["1-10", "11-50", "51-200", "200+"]},
                    {"key": "operation_type", "label": pair(pt, en, "fType"), "required": False,
                     "options": i18n(pt["types"], en["types"]),
                     "values": ["urban", "intercity", "international", "institutional"]},
                    {"key": "topics", "label": pair(pt, en, "fInterest"), "required": False,
                     "multi": True,
                     "options": i18n(pt["interests"], en["interests"]),
                     "values": ["online_sales", "onboard_validation", "nfc_cards",
                                "reports", "packages"]},
                    {"key": "message", "label": pair(pt, en, "fMsg"), "required": False},
                ],
                "submit": pair(pt, en, "formCta"),
                "note": pair(pt, en, "formNote"),
                "sent_title": pair(pt, en, "sentTitle"),
                "sent_text": pair(pt, en, "sentText"),
                "send_another": pair(pt, en, "sendAnother"),
            }),
            ("richtext", {
                "h2": pair(pt, en, "directTitle"),
                "lead": pair(pt, en, "emailNote"),
                "html": i18n(
                    f"<h3>{pt['hoursTitle']}</h3><p>{pt['hours']}</p>"
                    f"<h3>{pt['addressTitle']}</h3><p>{pt['mapNote']}</p>",
                    f"<h3>{en['hoursTitle']}</h3><p>{en['hours']}</p>"
                    f"<h3>{en['addressTitle']}</h3><p>{en['mapNote']}</p>",
                ),
            }),
            ("eco", {
                "label": pair(pt, en, "ecoLabel"),
                "h2": pair(pt, en, "ecoH2"),
                "lead": pair(pt, en, "ecoLead"),
                "note": pair(pt, en, "ecoNote"),
                "system_ids": [systems[item["name"]].pk for item in pt["ecoItems"]],
            }),
        ])
        return page

    def _seed_apps_page(self):
        """A pagina Apps mostra os fluxos das apps; o texto vive no ecra.

        Fica como pagina do CMS para o menu e o SEO poderem apontar-lhe, com um
        bloco de texto editavel por cima.
        """
        page = self._page(
            "apps", Page.Template.APPS, "Apps", "Apps",
            i18n("Apps BusUp — passageiro, motorista, agente e POS",
                 "BusUp apps — passenger, driver, agent and POS"),
            i18n("Os cinco produtos do BusUp, com o vocabulário do Portal.",
                 "The five BusUp products, sharing the Portal vocabulary."),
        )
        if not page.blocks.exists():
            self._blocks(page, [
                ("richtext", {
                    "h2": i18n("Apps BusUp", "BusUp apps"),
                    "lead": i18n("Os cinco produtos, com o vocabulário do Portal.",
                                 "The five products, sharing the Portal vocabulary."),
                    "html": i18n("", ""),
                }),
            ])
        return page

    # -- Menus --------------------------------------------------------------

    def _seed_menus(self, copy, pages):
        pt, en = copy["landing"]["PT"], copy["landing"]["EN"]
        by_slug = {page.slug: page for page in pages}

        header, _ = Menu.objects.update_or_create(
            key=Menu.Key.HEADER, defaults={"label": i18n("Cabeçalho", "Header")},
        )
        self._items(header, [
            (pair(pt, en, "navProduct"), None, "/#produto"),
            (pair(pt, en, "navFeatures"), None, "/#recursos"),
            (pair(pt, en, "navWhy"), None, "/#porque"),
            (pair(pt, en, "navCases"), None, "/#casos"),
            (pair(pt, en, "navPricing"), by_slug.get("precos"), ""),
            (pair(pt, en, "navContact"), by_slug.get("contactos"), ""),
        ])

        product, _ = Menu.objects.update_or_create(
            key=Menu.Key.FOOTER_PRODUCT, defaults={"label": pair(pt, en, "footerProduct")},
        )
        self._items(product, [
            (pair(pt, en, "navFeatures"), None, "/#recursos"),
            (pair(pt, en, "navPricing"), by_slug.get("precos"), ""),
            (pair(pt, en, "footerPortal"), None, "/login"),
            (pair(pt, en, "footerApps"), by_slug.get("apps"), ""),
        ])

        contact, _ = Menu.objects.update_or_create(
            key=Menu.Key.FOOTER_CONTACT, defaults={"label": pair(pt, en, "footerContact")},
        )
        self._items(contact, [
            (i18n("sales@updigital.co.mz", "sales@updigital.co.mz"), None, "mailto:sales@updigital.co.mz"),
            (i18n("www.updigital.co.mz", "www.updigital.co.mz"), None, "https://www.updigital.co.mz"),
            (pair(pt, en, "navContact"), by_slug.get("contactos"), ""),
        ])

        eco, _ = Menu.objects.update_or_create(
            key=Menu.Key.FOOTER_ECO, defaults={"label": pair(pt, en, "footerEco")},
        )
        self._items(eco, [
            (i18n(item["name"], item["name"]), None, item["url"])
            for item in pt["ecoItems"]
        ])

    def _items(self, menu, rows):
        menu.items.all().hard_delete()
        for position, (label, page, href) in enumerate(rows):
            MenuItem.objects.create(
                menu=menu, label=label, page=page, href=href,
                position=position, target="_blank" if href.startswith("http") else "",
                visible=True,
            )
