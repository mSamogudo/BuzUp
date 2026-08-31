"""Regras do CMS: versoes, publicacao, validacao e cache.

Fonte: docs/design-handoff/03-cms-especificacao.md, seccoes 4 e 5.
"""

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.cms.models import (
    LOCALES,
    EcoSystem,
    Page,
    PageBlock,
    PageVersion,
    Plan,
    PlanFeature,
    SeoMeta,
    i18n_get,
)

CACHE_PREFIX = "cms:v1"
# Cinco minutos, como pede a especificacao. A publicacao invalida antes disso.
CACHE_TTL = 300

# Blocos cujo conteudo e obrigatorio para publicar uma pagina, por template.
REQUIRED_BLOCKS = {
    Page.Template.LANDING: ("heroi",),
    Page.Template.PRICING: ("heroi", "precos"),
    Page.Template.CONTACT: ("form",),
    Page.Template.APPS: (),
    Page.Template.GENERIC: (),
}

# Campos de texto obrigatorios por tipo de bloco, para a validacao de publicacao.
BLOCK_REQUIRED_FIELDS = {
    "heroi": ("h1a", "lead"),
    "recursos": ("h2",),
    "porque": ("h2",),
    "casos": ("h2",),
    "precos": ("h2",),
    "faq": ("h2",),
    "form": ("h2", "submit"),
    "eco": ("h2",),
    "cta": ("h2", "cta1"),
    "richtext": ("html",),
    "logos": (),
    "media": (),
}

# Limites de caracteres do editor (03-cms-especificacao.md, 1.3).
BLOCK_LIMITS = {
    "heroi": {"badge": 40, "h1a": 40, "h1b": 40, "lead": 180, "cta1": 24, "cta2": 24, "chips": 80},
}


# ---------------------------------------------------------------------------
# Versoes
# ---------------------------------------------------------------------------

def build_snapshot(page: Page) -> dict:
    """Fotografia da pagina: blocos ordenados + SEO. E o que se restaura."""
    seo = getattr(page, "seo", None)
    return {
        "page": {
            "slug": page.slug,
            "title": page.title,
            "template": page.template,
            "locales": page.locales,
        },
        "blocks": [
            {
                "type": b.type,
                "position": b.position,
                "enabled": b.enabled,
                "content": b.content,
            }
            for b in page.blocks.order_by("position", "id")
        ],
        "seo": None if seo is None else {
            "title": seo.title,
            "description": seo.description,
            "slug": seo.slug,
            "keywords": seo.keywords,
            "og_image_id": seo.og_image_id,
            "no_index": seo.no_index,
        },
    }


@transaction.atomic
def create_version(page: Page, author=None, note: str = "", restored_from: PageVersion | None = None) -> PageVersion:
    last = PageVersion.objects.filter(page=page).order_by("-number").first()
    version = PageVersion.objects.create(
        page=page,
        number=(last.number + 1) if last else 1,
        snapshot=build_snapshot(page),
        author=author if getattr(author, "is_authenticated", False) else None,
        note=note,
        restored_from=restored_from,
    )
    Page.objects.filter(pk=page.pk).update(current_version=version)
    page.current_version = version
    return version


@transaction.atomic
def restore_version(version: PageVersion, author=None) -> PageVersion:
    """Repoe o conteudo de uma versao e grava-o como versao nova.

    A pagina volta a rascunho: repor conteudo antigo nao e o mesmo que decidir
    publica-lo.
    """
    page = version.page
    snap = version.snapshot or {}
    page_data = snap.get("page") or {}
    page.title = page_data.get("title", page.title)
    page.template = page_data.get("template", page.template)
    page.locales = page_data.get("locales", page.locales)
    page.status = Page.Status.DRAFT
    page.updated_by = author if getattr(author, "is_authenticated", False) else None
    page.save(update_fields=["title", "template", "locales", "status", "updated_by", "updated_at"])

    page.blocks.all().hard_delete()
    for block in snap.get("blocks") or []:
        PageBlock.objects.create(
            page=page,
            type=block.get("type", "richtext"),
            position=block.get("position", 0),
            enabled=block.get("enabled", True),
            content=block.get("content") or {},
        )

    seo_data = snap.get("seo")
    if seo_data is not None:
        seo, _ = SeoMeta.objects.get_or_create(page=page)
        seo.title = seo_data.get("title") or {}
        seo.description = seo_data.get("description") or {}
        seo.slug = seo_data.get("slug") or {}
        seo.keywords = seo_data.get("keywords") or {}
        seo.og_image_id = seo_data.get("og_image_id")
        seo.no_index = bool(seo_data.get("no_index"))
        seo.save()

    new_version = create_version(page, author=author, note=f"Restauro da versao {version.number}", restored_from=version)
    invalidate_page_cache(page)
    return new_version


def compare_versions(a: PageVersion, b: PageVersion) -> list[dict]:
    """Diferencas campo a campo entre duas versoes."""
    return _diff("", a.snapshot or {}, b.snapshot or {})


def _diff(path, left, right):
    out = []
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) | set(right)):
            out.extend(_diff(f"{path}.{key}" if path else str(key), left.get(key), right.get(key)))
        return out
    if isinstance(left, list) and isinstance(right, list):
        for i in range(max(len(left), len(right))):
            l = left[i] if i < len(left) else None
            r = right[i] if i < len(right) else None
            out.extend(_diff(f"{path}[{i}]", l, r))
        return out
    if left != right:
        out.append({"field": path, "a": left, "b": right})
    return out


# ---------------------------------------------------------------------------
# Publicacao
# ---------------------------------------------------------------------------

def validate_publish(page: Page, locales=None) -> list[str]:
    """Erros que impedem a publicacao. Lista vazia significa que pode ir ao ar.

    Regra da especificacao: todos os blocos obrigatorios preenchidos nos
    idiomas marcados, SEO com titulo e descricao, sem media em falta.
    """
    wanted = [l for l in (locales or page.locales or list(LOCALES)) if l in LOCALES]
    errors: list[str] = []

    blocks = list(page.blocks.filter(enabled=True).order_by("position", "id"))
    present = {b.type for b in blocks}
    for required in REQUIRED_BLOCKS.get(page.template, ()):  # type: ignore[arg-type]
        if required not in present:
            errors.append(f"Falta o bloco obrigatorio '{required}'.")

    for block in blocks:
        for field in BLOCK_REQUIRED_FIELDS.get(block.type, ()):
            value = (block.content or {}).get(field)
            for locale in wanted:
                if not str(i18n_get(value, locale) or "").strip():
                    errors.append(f"Bloco '{block.type}': campo '{field}' vazio em {locale.upper()}.")

    seo = getattr(page, "seo", None)
    if seo is None:
        errors.append("SEO por preencher: falta titulo e descricao.")
    else:
        for field in ("title", "description"):
            for locale in wanted:
                if not str(i18n_get(getattr(seo, field), locale) or "").strip():
                    errors.append(f"SEO: '{field}' vazio em {locale.upper()}.")

    for block in blocks:
        for media_id in _media_ids(block.content):
            from apps.cms.models import MediaAsset
            if not MediaAsset.objects.filter(pk=media_id).exists():
                errors.append(f"Bloco '{block.type}': media #{media_id} nao existe.")

    return errors


def _media_ids(node, out=None):
    out = [] if out is None else out
    if isinstance(node, dict):
        if isinstance(node.get("media_id"), int):
            out.append(node["media_id"])
        # Variante do ficheiro para o tema escuro, quando o logotipo precisa
        # de uma (um logotipo escuro nao se ve sobre fundo navy).
        if isinstance(node.get("media_id_dark"), int):
            out.append(node["media_id_dark"])
        for value in node.values():
            _media_ids(value, out)
    elif isinstance(node, list):
        for value in node:
            _media_ids(value, out)
    return out


@transaction.atomic
def publish_page(page: Page, author=None, locales=None) -> Page:
    page.status = Page.Status.PUBLISHED
    page.published_at = timezone.now()
    page.scheduled_for = None
    if locales:
        page.locales = [l for l in locales if l in LOCALES] or page.locales
    page.updated_by = author if getattr(author, "is_authenticated", False) else None
    page.save(update_fields=["status", "published_at", "scheduled_for", "locales", "updated_by", "updated_at"])
    create_version(page, author=author, note="Publicacao")
    invalidate_page_cache(page)
    return page


@transaction.atomic
def unpublish_page(page: Page, author=None) -> Page:
    page.status = Page.Status.DRAFT
    page.published_at = None
    page.updated_by = author if getattr(author, "is_authenticated", False) else None
    page.save(update_fields=["status", "published_at", "updated_by", "updated_at"])
    invalidate_page_cache(page)
    return page


# ---------------------------------------------------------------------------
# Cache das rotas publicas
# ---------------------------------------------------------------------------

def page_cache_key(slug: str, locale: str) -> str:
    return f"{CACHE_PREFIX}:page:{slug or '_home'}:{locale}"


def site_cache_key(locale: str) -> str:
    return f"{CACHE_PREFIX}:site:{locale}"


def plans_cache_key(locale: str) -> str:
    return f"{CACHE_PREFIX}:plans:{locale}"


ECO_CACHE_KEY = f"{CACHE_PREFIX}:eco"


def invalidate_page_cache(page: Page | None = None):
    keys = [ECO_CACHE_KEY]
    for locale in LOCALES:
        keys.append(site_cache_key(locale))
        keys.append(plans_cache_key(locale))
        if page is not None:
            keys.append(page_cache_key(page.slug, locale))
    cache.delete_many(keys)


def invalidate_all_cache():
    keys = [ECO_CACHE_KEY]
    for locale in LOCALES:
        keys.append(site_cache_key(locale))
        keys.append(plans_cache_key(locale))
    for slug in Page.objects.values_list("slug", flat=True):
        for locale in LOCALES:
            keys.append(page_cache_key(slug, locale))
    cache.delete_many(keys)


# ---------------------------------------------------------------------------
# Entrega ao site publico
# ---------------------------------------------------------------------------

def serialize_public_page(page: Page, locale: str) -> dict:
    seo = getattr(page, "seo", None)
    return {
        "slug": page.slug,
        "path": page.path,
        "template": page.template,
        "title": i18n_get(page.title, locale),
        "locale": locale,
        "published_at": page.published_at.isoformat() if page.published_at else None,
        "seo": None if seo is None else {
            "title": i18n_get(seo.title, locale),
            "description": i18n_get(seo.description, locale),
            "slug": i18n_get(seo.slug, locale),
            "keywords": i18n_get(seo.keywords, locale),
            "og_image": seo.og_image.url if seo.og_image else "",
            "no_index": seo.no_index,
        },
        "blocks": [
            {
                "type": block.type,
                "position": block.position,
                "content": resolve_media(localize(block.content, locale)),
            }
            for block in page.blocks.filter(enabled=True).order_by("position", "id")
        ],
    }


def resolve_media(node):
    """Troca cada `media_id` pelo endereco do ficheiro.

    O site publico nao tem forma de resolver um identificador de media sozinho,
    e uma segunda chamada por logotipo seria absurda — o endereco vem no mesmo
    payload, ao lado do identificador.
    """
    from apps.cms.models import MediaAsset

    ids = set(_media_ids(node))
    if not ids:
        return node
    urls = {
        asset.pk: asset.url
        for asset in MediaAsset.objects.filter(pk__in=ids)
    }

    def walk(value):
        if isinstance(value, dict):
            out = {k: walk(v) for k, v in value.items()}
            media_id = value.get("media_id")
            if isinstance(media_id, int):
                out["url"] = urls.get(media_id, "")
            media_dark = value.get("media_id_dark")
            if isinstance(media_dark, int):
                out["url_dark"] = urls.get(media_dark, "")
            return out
        if isinstance(value, list):
            return [walk(v) for v in value]
        return value

    return walk(node)


def localize(node, locale):
    """Reduz uma arvore i18n ao idioma pedido.

    Um dicionario que so tenha chaves de idioma e um valor traduzido; qualquer
    outro dicionario e estrutura e desce-se nele.
    """
    if isinstance(node, dict):
        keys = set(node)
        if keys and keys <= set(LOCALES):
            return i18n_get(node, locale)
        return {k: localize(v, locale) for k, v in node.items()}
    if isinstance(node, list):
        return [localize(v, locale) for v in node]
    return node


def serialize_public_plan(plan: Plan, locale: str) -> dict:
    return {
        "id": plan.pk,
        "name": i18n_get(plan.name, locale),
        "price_label": i18n_get(plan.price_label, locale),
        "unit": i18n_get(plan.unit, locale),
        "cta_label": i18n_get(plan.cta_label, locale),
        "items": i18n_get(plan.items, locale) or [],
        "highlighted": plan.highlighted,
        "position": plan.position,
    }


def serialize_public_plan_feature(feature: PlanFeature, locale: str) -> dict:
    return {
        "label": i18n_get(feature.label, locale),
        "urban": i18n_get(feature.urban, locale),
        "intercity": i18n_get(feature.intercity, locale),
        "institutional": i18n_get(feature.institutional, locale),
        "position": feature.position,
    }


def serialize_public_eco(system: EcoSystem, locale: str) -> dict:
    return {
        "id": system.pk,
        "name": system.name,
        "logo": system.logo.url if system.logo else "",
        "url": system.url,
        "note": i18n_get(system.note, locale),
        "position": system.position,
    }


# ---------------------------------------------------------------------------
# Worker de publicacoes agendadas
# ---------------------------------------------------------------------------

DUE_LOCK_KEY = f"{CACHE_PREFIX}:due-lock"


def run_due_publications(now=None) -> list:
    """Publica tudo o que ja passou da hora marcada.

    Corre pelo comando de gestao `cms_publish_scheduled` (cron) e tambem, a
    titulo de rede de seguranca, na primeira leitura publica de cada minuto:
    sem isso, um agendamento so iria ao ar quando alguem se lembrasse de correr
    o comando, e o criterio de pronto do handoff e "ve-la ir ao ar sozinha".
    """
    from apps.cms.models import ScheduledPublication

    now = now or timezone.now()
    done = []
    due = ScheduledPublication.objects.filter(
        status=ScheduledPublication.Status.SCHEDULED, run_at__lte=now,
    )
    for job in due:
        try:
            if job.target_type == ScheduledPublication.Target.PAGE:
                page = Page.objects.filter(pk=job.target_id).first()
                if page is None:
                    raise ValueError("A pagina ja nao existe.")
                errors = validate_publish(page)
                if errors:
                    raise ValueError("; ".join(errors))
                publish_page(page, author=job.created_by)
                job.result = f"Pagina '{page.slug or '(inicial)'}' publicada."
            elif job.target_type == ScheduledPublication.Target.PLAN:
                updated = Plan.objects.filter(pk=job.target_id).update(visible=True)
                if not updated:
                    raise ValueError("O plano ja nao existe.")
                job.result = "Plano tornado visivel."
                invalidate_all_cache()
            else:
                updated = EcoSystem.objects.filter(pk=job.target_id).update(
                    status=EcoSystem.Status.PUBLISHED,
                )
                if not updated:
                    raise ValueError("O sistema ja nao existe.")
                job.result = "Sistema publicado."
                invalidate_all_cache()
            job.status = ScheduledPublication.Status.DONE
        except Exception as exc:  # a falha fica registada, nao rebenta o worker
            job.status = ScheduledPublication.Status.FAILED
            job.result = str(exc)[:2000]
        job.save(update_fields=["status", "result", "updated_at"])
        done.append(job)
    return done


def run_due_publications_throttled():
    """Chamada barata para o caminho de leitura publica: uma vez por minuto."""
    if cache.get(DUE_LOCK_KEY):
        return []
    cache.set(DUE_LOCK_KEY, 1, 60)
    return run_due_publications()
