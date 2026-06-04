from __future__ import annotations

from apps.notifications.models import Notification


def notify(user, kind: str, title: str, body: str = "", data: dict | None = None) -> Notification | None:
    """Create a notification for a user (silent no-op if user is None)."""
    if not user or not user.is_authenticated:
        return None
    return Notification.objects.create(
        user=user,
        kind=kind,
        title=title,
        body=body,
        data=data or {},
    )


def notify_by_phone(phone: str, kind: str, title: str, body: str = "", data: dict | None = None) -> list[Notification]:
    """Best-effort notify any User account with this phone."""
    from apps.users.models import User

    out: list[Notification] = []
    if not phone:
        return out
    users = User.objects.filter(phone=phone, is_active=True)
    for u in users:
        out.append(Notification.objects.create(
            user=u, kind=kind, title=title, body=body, data=data or {},
        ))
    return out
