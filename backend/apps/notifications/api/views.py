"""Notificacoes do utilizador autenticado.

Servem o sino do portal (A0.5 do inventario) e a app movel — sao as mesmas
notificacoes, filtradas pelo utilizador da sessao.
"""

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification


def serialize(notification):
    return {
        "id": notification.id,
        "uuid": str(notification.uuid),
        "kind": notification.kind,
        "title": notification.title,
        "body": notification.body,
        "data": notification.data,
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
        "created_at": notification.created_at.isoformat(),
    }


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(user=request.user).order_by("-created_at")[:100]
        unread = Notification.objects.filter(user=request.user, read_at__isnull=True).count()
        return Response({"unread_count": unread, "results": [serialize(n) for n in qs]})


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id: int):
        notification = Notification.objects.filter(pk=notification_id, user=request.user).first()
        if not notification:
            return Response({"detail": "Notificacao nao encontrada."}, status=404)
        if not notification.read_at:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at", "updated_at"])
        return Response({"detail": "ok", "read_at": notification.read_at.isoformat()})


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        marked = Notification.objects.filter(user=request.user, read_at__isnull=True).update(
            read_at=timezone.now(),
        )
        return Response({"detail": "ok", "marked": marked})
