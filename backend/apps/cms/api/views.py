"""Endpoints de gestao do CMS (`/api/cms/...`).

Fonte: docs/design-handoff/03-cms-especificacao.md, seccao 2.
"""

import mimetypes

from django.core import signing
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cms.api.serializers import (
    EcoSystemSerializer,
    MediaAssetSerializer,
    MenuItemSerializer,
    MenuSerializer,
    PageBlockSerializer,
    PageListSerializer,
    PageSerializer,
    PageVersionDetailSerializer,
    PageVersionSerializer,
    PlanFeatureSerializer,
    PlanSerializer,
    ScheduledPublicationSerializer,
    SeoMetaSerializer,
)
from apps.cms.models import (
    EcoSystem,
    MediaAsset,
    Menu,
    MenuItem,
    Page,
    PageBlock,
    PageVersion,
    Plan,
    PlanFeature,
    ScheduledPublication,
    SeoMeta,
)
from apps.cms.services import (
    compare_versions,
    create_version,
    invalidate_all_cache,
    invalidate_page_cache,
    publish_page,
    restore_version,
    unpublish_page,
    validate_publish,
)
from apps.core.permissions import HasCapabilities, has_capabilities
from apps.core.viewsets import BaseModelViewSet

PREVIEW_SALT = "cms.preview"
PREVIEW_MAX_AGE = 60 * 60 * 24  # 24 horas


def make_preview_token(page: Page) -> str:
    return signing.dumps({"page": page.pk}, salt=PREVIEW_SALT)


def read_preview_token(token: str):
    try:
        data = signing.loads(token, salt=PREVIEW_SALT, max_age=PREVIEW_MAX_AGE)
    except signing.BadSignature:
        return None
    return data.get("page")


def _actor(request):
    user = getattr(request, "user", None)
    return user if getattr(user, "is_authenticated", False) else None


class PageViewSet(BaseModelViewSet):
    queryset = Page.all_objects.select_related("current_version", "seo").prefetch_related("blocks")
    serializer_class = PageSerializer
    required_capabilities_by_action = {
        "list": ("content.read",),
        "retrieve": ("content.read",),
        "create": ("content.write",),
        "update": ("content.write",),
        "partial_update": ("content.write",),
        "destroy": ("content.write",),
        "blocks": ("content.read",),
        "duplicate": ("content.write",),
        "preview_token": ("content.read",),
        "versions": ("content.read",),
        "publish": ("content.publish",),
        "unpublish": ("content.publish",),
        "schedule": ("content.publish",),
        "submit_review": ("content.write",),
    }

    def get_serializer_class(self):
        if self.action == "list":
            return PageListSerializer
        return PageSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        page_status = params.get("status")
        if page_status:
            qs = qs.filter(status=page_status)
        locale = params.get("locale")
        if locale:
            qs = qs.filter(locales__contains=[locale])
        template = params.get("template")
        if template:
            qs = qs.filter(template=template)
        search = (params.get("q") or "").strip()
        if search:
            qs = qs.filter(slug__icontains=search) | qs.filter(title__icontains=search)
        return qs.distinct()

    def perform_create(self, serializer):
        actor = _actor(self.request)
        page = serializer.save(created_by=actor, updated_by=actor)
        SeoMeta.objects.get_or_create(page=page)
        create_version(page, author=actor, note="Criacao")
        self._audit("create", page)

    def perform_update(self, serializer):
        actor = _actor(self.request)
        page = serializer.save(updated_by=actor)
        # Gravar cria versao (03-cms-especificacao.md, 3.2).
        create_version(page, author=actor, note="Gravacao")
        invalidate_page_cache(page)
        self._audit("update", page)

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        invalidate_page_cache(instance)

    # -- Blocos -------------------------------------------------------------

    @action(detail=True, methods=["get", "put"], url_path="blocks")
    def blocks(self, request, pk=None):
        page = self.get_object()
        if request.method == "GET":
            data = PageBlockSerializer(page.blocks.order_by("position", "id"), many=True).data
            return Response(data)

        if not has_capabilities(request.user, ("content.write",)):
            raise PermissionDenied("Sem permissao para editar conteudo.")

        payload = request.data
        if not isinstance(payload, list):
            raise ValidationError({"detail": "Envie a lista completa de blocos."})

        with transaction.atomic():
            page.blocks.all().hard_delete()
            for position, raw in enumerate(payload):
                serializer = PageBlockSerializer(data={**raw, "position": position})
                serializer.is_valid(raise_exception=True)
                PageBlock.objects.create(page=page, **serializer.validated_data)
            actor = _actor(request)
            page.updated_by = actor
            page.save(update_fields=["updated_by", "updated_at"])
            create_version(page, author=actor, note="Gravacao de blocos")

        invalidate_page_cache(page)
        self._audit("update", page)
        return Response(PageBlockSerializer(page.blocks.order_by("position", "id"), many=True).data)

    # -- Publicacao ---------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        page = self.get_object()
        locales = request.data.get("locales") or page.locales
        errors = validate_publish(page, locales)
        if errors:
            raise ValidationError({"detail": "A pagina nao esta pronta para publicar.", "errors": errors})
        publish_page(page, author=_actor(request), locales=locales)
        self._audit("action", page)
        return Response(PageSerializer(page).data)

    @action(detail=True, methods=["post"], url_path="unpublish")
    def unpublish(self, request, pk=None):
        page = self.get_object()
        unpublish_page(page, author=_actor(request))
        self._audit("action", page)
        return Response(PageSerializer(page).data)

    @action(detail=True, methods=["post"], url_path="submit-review")
    def submit_review(self, request, pk=None):
        """Quem so tem `content.write` envia para revisao em vez de publicar."""
        page = self.get_object()
        page.status = Page.Status.REVIEW
        page.updated_by = _actor(request)
        page.save(update_fields=["status", "updated_by", "updated_at"])
        self._audit("action", page)
        return Response(PageSerializer(page).data)

    @action(detail=True, methods=["post"], url_path="schedule")
    def schedule(self, request, pk=None):
        page = self.get_object()
        run_at = request.data.get("run_at")
        if not run_at:
            raise ValidationError({"run_at": "Indique a data e hora da publicacao."})
        serializer = ScheduledPublicationSerializer(
            data={"target_type": ScheduledPublication.Target.PAGE, "target_id": page.pk, "run_at": run_at}
        )
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data["run_at"] <= timezone.now():
            raise ValidationError({"run_at": "A data tem de ser no futuro."})
        scheduled = serializer.save(created_by=_actor(request))
        page.status = Page.Status.SCHEDULED
        page.scheduled_for = scheduled.run_at
        page.save(update_fields=["status", "scheduled_for", "updated_at"])
        self._audit("action", page)
        return Response(ScheduledPublicationSerializer(scheduled).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="duplicate")
    def duplicate(self, request, pk=None):
        page = self.get_object()
        actor = _actor(request)
        base = page.slug or "inicial"
        slug = f"{base}-copia"
        n = 2
        while Page.objects.filter(slug=slug).exists():
            slug = f"{base}-copia-{n}"
            n += 1
        with transaction.atomic():
            copy = Page.objects.create(
                slug=slug,
                title={k: f"{v} (copia)" if v else v for k, v in (page.title or {}).items()},
                template=page.template,
                locales=page.locales,
                status=Page.Status.DRAFT,
                created_by=actor,
                updated_by=actor,
            )
            for block in page.blocks.order_by("position", "id"):
                PageBlock.objects.create(
                    page=copy, type=block.type, position=block.position,
                    enabled=block.enabled, content=block.content,
                )
            seo = getattr(page, "seo", None)
            new_seo, _ = SeoMeta.objects.get_or_create(page=copy)
            if seo:
                new_seo.title = seo.title
                new_seo.description = seo.description
                new_seo.slug = seo.slug
                new_seo.keywords = seo.keywords
                new_seo.og_image_id = seo.og_image_id
                new_seo.no_index = True  # a copia nao deve competir com o original
                new_seo.save()
            create_version(copy, author=actor, note=f"Duplicado de {page.slug or '(inicial)'}")
        self._audit("create", copy)
        return Response(PageSerializer(copy).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="preview-token")
    def preview_token(self, request, pk=None):
        page = self.get_object()
        return Response({"token": make_preview_token(page), "expires_in": PREVIEW_MAX_AGE})

    @action(detail=True, methods=["get"], url_path="versions")
    def versions(self, request, pk=None):
        page = self.get_object()
        data = PageVersionSerializer(page.versions.order_by("-number"), many=True).data
        return Response(data)


class PageBlockViewSet(BaseModelViewSet):
    """`PATCH /api/cms/blocks/{id}/` — editar um bloco isolado."""

    queryset = PageBlock.objects.select_related("page")
    serializer_class = PageBlockSerializer
    http_method_names = ["get", "patch", "head", "options"]
    required_capabilities_by_action = {
        "retrieve": ("content.read",),
        "partial_update": ("content.write",),
    }

    def perform_update(self, serializer):
        block = serializer.save()
        create_version(block.page, author=_actor(self.request), note="Gravacao de bloco")
        invalidate_page_cache(block.page)
        self._audit("update", block)


class VersionViewSet(BaseModelViewSet):
    queryset = PageVersion.objects.select_related("page", "author")
    serializer_class = PageVersionDetailSerializer
    http_method_names = ["get", "post", "head", "options"]
    required_capabilities_by_action = {
        "list": ("content.read",),
        "retrieve": ("content.read",),
        "compare": ("content.read",),
        "restore": ("content.write",),
    }

    def get_required_capabilities(self):
        # A classe base mapeia `restore` para as capacidades de `destroy`
        # (desarquivar um registo). Aqui `restore` e outra coisa: repor uma
        # versao de conteudo, que so exige poder escrever conteudo.
        if self.action == "restore":
            return ("content.write",)
        return super().get_required_capabilities()

    def get_queryset(self):
        qs = super().get_queryset()
        page_id = self.request.query_params.get("page")
        if page_id:
            qs = qs.filter(page_id=page_id)
        return qs

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, *args, **kwargs):
        """Repoe o conteudo desta versao. Substitui o `restore` da classe base:
        aqui nao ha nada de arquivado para desarquivar."""
        version = self.get_object()
        new_version = restore_version(version, author=_actor(request))
        self._audit("action", version)
        return Response(PageVersionSerializer(new_version).data)

    @action(detail=False, methods=["get"], url_path="compare")
    def compare(self, request):
        a_id, b_id = request.query_params.get("a"), request.query_params.get("b")
        if not a_id or not b_id:
            raise ValidationError({"detail": "Indique as duas versoes a comparar (a e b)."})
        versions = {str(v.pk): v for v in PageVersion.objects.filter(pk__in=[a_id, b_id])}
        if str(a_id) not in versions or str(b_id) not in versions:
            raise ValidationError({"detail": "Versao nao encontrada."})
        a, b = versions[str(a_id)], versions[str(b_id)]
        return Response({
            "a": PageVersionSerializer(a).data,
            "b": PageVersionSerializer(b).data,
            "changes": compare_versions(a, b),
        })


class MediaViewSet(BaseModelViewSet):
    queryset = MediaAsset.all_objects.all()
    serializer_class = MediaAssetSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    required_capabilities_by_action = {
        "list": ("content.read",),
        "retrieve": ("content.read",),
        "create": ("media.manage",),
        "update": ("media.manage",),
        "partial_update": ("media.manage",),
        "destroy": ("media.manage",),
    }

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["with_usage"] = self.action in ("retrieve", "create", "update", "partial_update")
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        folder = params.get("folder")
        if folder:
            qs = qs.filter(folder=folder)
        mime = params.get("mime")
        if mime:
            qs = qs.filter(mime__startswith=mime)
        search = (params.get("q") or "").strip()
        if search:
            qs = qs.filter(filename__icontains=search)
        return qs

    def perform_create(self, serializer):
        upload = serializer.validated_data.get("file")
        if upload is None:
            raise ValidationError({"file": "Escolha um ficheiro."})
        mime = getattr(upload, "content_type", "") or mimetypes.guess_type(upload.name)[0] or ""
        if mime and mime not in MediaAsset.ALLOWED_MIME:
            raise ValidationError({"file": "Formato nao aceite. Use PNG, JPG, WEBP, SVG ou PDF."})
        width, height = _image_size(upload)
        actor = _actor(self.request)
        asset = serializer.save(
            filename=serializer.validated_data.get("filename") or upload.name,
            mime=mime,
            bytes=upload.size,
            width=width,
            height=height,
            created_by=actor,
            updated_by=actor,
        )
        invalidate_all_cache()
        self._audit("create", asset)

    def perform_update(self, serializer):
        upload = serializer.validated_data.get("file")
        extra = {"updated_by": _actor(self.request)}
        if upload is not None:
            width, height = _image_size(upload)
            extra.update({
                "filename": upload.name,
                "mime": getattr(upload, "content_type", "") or "",
                "bytes": upload.size,
                "width": width,
                "height": height,
            })
        asset = serializer.save(**extra)
        # Substituir o ficheiro troca-o em todas as paginas que o usam.
        invalidate_all_cache()
        self._audit("update", asset)

    def perform_destroy(self, instance):
        if instance.in_use():
            raise ValidationError({
                "detail": "O ficheiro esta em uso e nao pode ser eliminado.",
                "used_in": instance.used_in(),
            })
        super().perform_destroy(instance)
        invalidate_all_cache()


def _image_size(upload):
    try:
        from PIL import Image  # noqa: PLC0415

        upload.seek(0)
        with Image.open(upload) as img:
            size = img.size
        upload.seek(0)
        return size
    except Exception:
        try:
            upload.seek(0)
        except Exception:
            pass
        return None, None


class MenuViewSet(BaseModelViewSet):
    queryset = Menu.objects.prefetch_related("items")
    serializer_class = MenuSerializer
    lookup_field = "key"
    http_method_names = ["get", "put", "head", "options"]
    allow_restore_action = False
    required_capabilities_by_action = {
        "list": ("content.read",),
        "retrieve": ("content.read",),
        "items": ("menus.manage",),
    }

    @action(detail=True, methods=["put"], url_path="items")
    def items(self, request, key=None):
        """Grava a ordem e os itens de um menu de uma vez (3.4)."""
        menu = self.get_object()
        payload = request.data
        if not isinstance(payload, list):
            raise ValidationError({"detail": "Envie a lista completa de itens."})
        with transaction.atomic():
            menu.items.all().hard_delete()
            for position, raw in enumerate(payload):
                serializer = MenuItemSerializer(data={**raw, "position": position})
                serializer.is_valid(raise_exception=True)
                MenuItem.objects.create(menu=menu, **serializer.validated_data)
        invalidate_all_cache()
        self._audit("update", menu)
        return Response(MenuSerializer(menu).data)


class SeoView(APIView):
    """`GET|PUT /api/cms/seo/{page_id}/`."""

    permission_classes = [IsAuthenticated, HasCapabilities]

    def get_required_capabilities(self):
        return ("content.read",) if self.request.method == "GET" else ("seo.manage",)

    def get(self, request, page_id):
        page = _page_or_404(page_id)
        seo, _ = SeoMeta.objects.get_or_create(page=page)
        return Response(SeoMetaSerializer(seo).data)

    def put(self, request, page_id):
        page = _page_or_404(page_id)
        seo, _ = SeoMeta.objects.get_or_create(page=page)
        serializer = SeoMetaSerializer(seo, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        create_version(page, author=_actor(request), note="Gravacao de SEO")
        invalidate_page_cache(page)
        return Response(serializer.data)


def _page_or_404(page_id):
    page = Page.objects.filter(pk=page_id).first()
    if page is None:
        from rest_framework.exceptions import NotFound

        raise NotFound("Pagina nao encontrada.")
    return page


class PlanViewSet(BaseModelViewSet):
    queryset = Plan.all_objects.all()
    serializer_class = PlanSerializer
    required_capabilities_by_action = {
        "list": ("content.read",),
        "retrieve": ("content.read",),
        "create": ("plans.manage",),
        "update": ("plans.manage",),
        "partial_update": ("plans.manage",),
        "destroy": ("plans.manage",),
        "order": ("plans.manage",),
    }

    def perform_create(self, serializer):
        actor = _actor(self.request)
        plan = serializer.save(created_by=actor, updated_by=actor)
        invalidate_all_cache()
        self._audit("create", plan)

    def perform_update(self, serializer):
        plan = serializer.save(updated_by=_actor(self.request))
        invalidate_all_cache()
        self._audit("update", plan)

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        invalidate_all_cache()

    @action(detail=False, methods=["put"], url_path="order")
    def order(self, request):
        ids = request.data.get("ids")
        if not isinstance(ids, list):
            raise ValidationError({"ids": "Envie a lista de identificadores pela ordem pretendida."})
        for position, plan_id in enumerate(ids):
            Plan.objects.filter(pk=plan_id).update(position=position)
        invalidate_all_cache()
        return Response(PlanSerializer(Plan.objects.order_by("position", "id"), many=True).data)


class PlanFeatureView(APIView):
    """Tabela comparativa: le e grava a lista inteira."""

    permission_classes = [IsAuthenticated, HasCapabilities]

    def get_required_capabilities(self):
        return ("content.read",) if self.request.method == "GET" else ("plans.manage",)

    def get(self, request):
        return Response(PlanFeatureSerializer(PlanFeature.objects.order_by("position", "id"), many=True).data)

    def put(self, request):
        payload = request.data
        if not isinstance(payload, list):
            raise ValidationError({"detail": "Envie a lista completa de linhas."})
        with transaction.atomic():
            PlanFeature.objects.all().hard_delete()
            for position, raw in enumerate(payload):
                serializer = PlanFeatureSerializer(data={**raw, "position": position})
                serializer.is_valid(raise_exception=True)
                PlanFeature.objects.create(**serializer.validated_data)
        invalidate_all_cache()
        return Response(PlanFeatureSerializer(PlanFeature.objects.order_by("position", "id"), many=True).data)


class EcoSystemViewSet(BaseModelViewSet):
    queryset = EcoSystem.all_objects.select_related("logo")
    serializer_class = EcoSystemSerializer
    required_capabilities_by_action = {
        "list": ("content.read",),
        "retrieve": ("content.read",),
        "create": ("content.write",),
        "update": ("content.write",),
        "partial_update": ("content.write",),
        "destroy": ("content.write",),
        "order": ("content.write",),
    }

    def perform_create(self, serializer):
        actor = _actor(self.request)
        system = serializer.save(created_by=actor, updated_by=actor)
        invalidate_all_cache()
        self._audit("create", system)

    def perform_update(self, serializer):
        system = serializer.save(updated_by=_actor(self.request))
        invalidate_all_cache()
        self._audit("update", system)

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        invalidate_all_cache()

    @action(detail=False, methods=["put"], url_path="order")
    def order(self, request):
        ids = request.data.get("ids")
        if not isinstance(ids, list):
            raise ValidationError({"ids": "Envie a lista de identificadores pela ordem pretendida."})
        for position, system_id in enumerate(ids):
            EcoSystem.objects.filter(pk=system_id).update(position=position)
        invalidate_all_cache()
        return Response(EcoSystemSerializer(EcoSystem.objects.order_by("position", "id"), many=True).data)


class ScheduleViewSet(BaseModelViewSet):
    queryset = ScheduledPublication.objects.all()
    serializer_class = ScheduledPublicationSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]
    allow_restore_action = False
    required_capabilities_by_action = {
        "list": ("content.read",),
        "retrieve": ("content.read",),
        "create": ("content.publish",),
        "destroy": ("content.publish",),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        state = self.request.query_params.get("status")
        if state:
            qs = qs.filter(status=state)
        return qs

    def perform_create(self, serializer):
        if serializer.validated_data["run_at"] <= timezone.now():
            raise ValidationError({"run_at": "A data tem de ser no futuro."})
        scheduled = serializer.save(created_by=_actor(self.request))
        if scheduled.target_type == ScheduledPublication.Target.PAGE:
            Page.objects.filter(pk=scheduled.target_id).update(
                status=Page.Status.SCHEDULED, scheduled_for=scheduled.run_at,
            )
        self._audit("create", scheduled)

    def perform_destroy(self, instance):
        """Cancelar nao apaga: o registo do que se cancelou tambem conta."""
        instance.status = ScheduledPublication.Status.CANCELLED
        instance.result = "Cancelada no portal."
        instance.save(update_fields=["status", "result", "updated_at"])
        if instance.target_type == ScheduledPublication.Target.PAGE:
            page = Page.objects.filter(pk=instance.target_id).first()
            if page and page.status == Page.Status.SCHEDULED:
                page.status = Page.Status.DRAFT
                page.scheduled_for = None
                page.save(update_fields=["status", "scheduled_for", "updated_at"])
        self._audit("action", instance)
