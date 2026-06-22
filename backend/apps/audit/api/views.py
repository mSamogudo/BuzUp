from django.db import models

from apps.audit.api.serializers import AuditLogSerializer
from apps.audit.models import AuditLog
from apps.core.viewsets import BaseModelViewSet


class AuditLogViewSet(BaseModelViewSet):
    """Trilho de auditoria (somente leitura). Requer `audit.read`.

    Filtros: ?action=&entity_type=&actor=&date_from=&date_to=&search=
    """

    queryset = AuditLog.objects.select_related("actor").all().order_by("-created_at")
    serializer_class = AuditLogSerializer
    http_method_names = ["get", "head", "options"]
    required_capabilities_by_action = {
        "list": ("audit.read",),
        "retrieve": ("audit.read",),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("action"):
            qs = qs.filter(action=p["action"])
        if p.get("entity_type"):
            qs = qs.filter(entity_type__icontains=p["entity_type"])
        if p.get("actor"):
            qs = qs.filter(actor_id=p["actor"])
        if p.get("date_from"):
            qs = qs.filter(created_at__date__gte=p["date_from"])
        if p.get("date_to"):
            qs = qs.filter(created_at__date__lte=p["date_to"])
        if p.get("search"):
            s = p["search"]
            qs = qs.filter(
                models.Q(entity_type__icontains=s)
                | models.Q(entity_id__icontains=s)
                | models.Q(action__icontains=s)
            )
        return qs
