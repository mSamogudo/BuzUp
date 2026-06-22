from __future__ import annotations

from rest_framework.permissions import BasePermission

from apps.devices.models import Device
from apps.trips.models import Agent


def get_agent_profile(user):
    """Return Agent profile linked to user, or None."""
    if not user or not getattr(user, "is_authenticated", False):
        return None
    return Agent.objects.filter(user=user, status=Agent.Status.ACTIVE).first()


def provision_pos_agent(user):
    """Garante um perfil de Agente ACTIVO para quem pode operar o POS.

    Permite que basta atribuir o papel "Agente POS" (capacidade pos.operate) —
    ou ser motorista activo / superuser — para aceder a app POS, sem ter de
    criar manualmente um registo de Agente. Devolve o Agent ou None se nao
    elegivel.
    """
    existing = get_agent_profile(user)
    if existing:
        return existing

    from apps.core.permissions.base import has_capabilities
    from apps.trips.models import Driver

    eligible = (
        getattr(user, "is_superuser", False)
        or has_capabilities(user, ("pos.operate",))
        or Driver.objects.filter(user=user, status=Driver.Status.ACTIVE).exists()
    )
    if not eligible:
        return None

    full_name = (user.get_full_name() or user.username or "").strip()
    agent, _ = Agent.objects.get_or_create(
        user=user,
        defaults={"full_name": full_name, "phone": getattr(user, "phone", "") or "", "status": Agent.Status.ACTIVE},
    )
    if agent.status != Agent.Status.ACTIVE:
        agent.status = Agent.Status.ACTIVE
        agent.save(update_fields=["status", "updated_at"])
    return agent


def get_authorized_device(user, serial_number: str | None = None) -> Device | None:
    """Return Device assigned to this user (and matching serial if provided)."""
    if not user or not user.is_authenticated:
        return None
    qs = Device.objects.filter(assigned_agent=user)
    if serial_number:
        qs = qs.filter(serial_number=serial_number)
    return qs.exclude(status=Device.Status.BLOCKED).first()


class IsActiveAgent(BasePermission):
    """Allow only authenticated users that have an active Agent profile."""

    message = "Acesso permitido apenas a agentes activos."

    def has_permission(self, request, view) -> bool:
        return bool(get_agent_profile(request.user))


class IsActivePassenger(BasePermission):
    """Allow only authenticated users that are linked to a PassengerAccount."""

    message = "Acesso permitido apenas a passageiros."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        from apps.passengers.models import PassengerAccount

        return PassengerAccount.objects.filter(
            phone_number=user.phone or "",
            status=PassengerAccount.Status.ACTIVE,
        ).exists()
