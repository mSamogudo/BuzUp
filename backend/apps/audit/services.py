from __future__ import annotations

from apps.audit.models import AuditLog


def audit(
    action: str,
    *,
    actor=None,
    entity_type: str = "",
    entity_id: str = "",
    before: dict | None = None,
    after: dict | None = None,
    ip: str = "",
    device: str = "",
) -> AuditLog | None:
    """Lightweight wrapper for AuditLog creation. Never raises."""
    try:
        return AuditLog.objects.create(
            actor=actor if (actor and getattr(actor, "is_authenticated", False)) else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else "",
            before=before or {},
            after=after or {},
            ip_address=ip or None,
            device=device or "",
        )
    except Exception:
        return None


def client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR", "")
