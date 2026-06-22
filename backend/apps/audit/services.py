from __future__ import annotations

from django.db import transaction

from apps.audit.models import AuditLog

# Chaves cujo valor nunca deve ser guardado no audit (snapshot redigido).
_REDACT = ("password", "token", "secret", "otp", "pin", "authorization", "api_key", "apikey", "checksum", "hash")


def _redact(name: str, value):
    if any(r in name.lower() for r in _REDACT):
        return "***"
    return value


def summarize_instance(instance) -> dict:
    """Snapshot JSON-safe e redigido dos campos concretos de uma instancia."""
    out: dict = {}
    try:
        for f in instance._meta.concrete_fields:
            name = f.name
            if name == "password":
                continue
            try:
                val = getattr(instance, f.attname, None)
            except Exception:
                continue
            if hasattr(val, "isoformat"):
                val = val.isoformat()
            elif not isinstance(val, (str, int, float, bool, type(None))):
                val = str(val)
            out[name] = _redact(name, val)
    except Exception:
        return {}
    return out


def record_model_audit(request, action: str, instance, before: dict | None = None):
    """Regista uma accao de CRUD do portal. Fail-open com savepoint: uma falha
    no insert do audit nunca envenena a transacao do chamador nem rebenta."""
    try:
        actor = getattr(request, "user", None) if request is not None else None
        with transaction.atomic():
            AuditLog.objects.create(
                actor=actor if (actor and getattr(actor, "is_authenticated", False)) else None,
                action=action,
                entity_type=getattr(instance._meta, "label", instance.__class__.__name__),
                entity_id=str(getattr(instance, "pk", "") or ""),
                before=before or {},
                after=summarize_instance(instance) if action != "delete" else {},
                ip_address=(client_ip(request) or None) if request is not None else None,
                device=(request.META.get("HTTP_USER_AGENT", "")[:255] if request is not None else ""),
            )
    except Exception:
        return None


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
