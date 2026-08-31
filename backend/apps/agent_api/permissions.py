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


def driver_only_scope(user):
    """Devolve o Driver quando o utilizador conduz um autocarro.

    Um motorista vende apenas nas viagens que lhe estao alocadas: cada um tem o
    seu terminal e o seu autocarro, e uma venda feita na viagem de outro so se
    descobre com o passageiro ja a bordo do errado.

    **A pergunta e "conduz?", e nao "que permissoes tem?".** Antes bastava ter
    `pos.operate` para ficar isento do limite — e o papel "Motorista" em
    producao tinha essa permissao, posta a mao no portal (a migracao que o cria
    deixa-o SEM permissoes nenhumas). Provavelmente para dar acesso ao POS, sem
    se saber que ser motorista activo ja bastava: ver `provision_pos_agent`.

    O resultado e que TODOS os motoristas ficavam isentos, e este limite nunca
    se aplicava a ninguem. O codigo estava certo; morria por causa de uma
    permissao concedida noutro sitio.

    Passa a depender do facto operacional — ter um registo de Motorista — que
    nao se liga nem desliga por engano numa caixa de permissoes. Quem nao
    conduz (agente de balcao) continua a escolher qualquer viagem.

    **O superuser tambem conta, se conduzir.** Um superuser SEM registo de
    motorista continua a ver tudo, porque precisa disso para diagnosticar. Mas
    a partir do momento em que existe um registo de Motorista com o nome dele,
    ele conduz um autocarro — e quem conduz vende so nas suas viagens. A regra
    do operador e sobre o autocarro, nao sobre o cargo: um bilhete emitido na
    viagem errada continua a por o passageiro no autocarro errado, quem quer
    que o tenha vendido.

    Quem precisar da conta de diagnostico sem limite tira-lhe o registo de
    Motorista — que e uma decisao explicita, e nao um efeito lateral.
    """
    from apps.trips.models import Driver

    if not user or not getattr(user, "is_authenticated", False):
        return None
    conduz = Driver.objects.filter(user=user).order_by("-status", "id").first()
    if getattr(user, "is_superuser", False) and conduz is None:
        return None
    # QUALQUER registo de motorista, activo ou nao.
    #
    # Filtrar por `status=ACTIVE` fazia com que DESACTIVAR um motorista lhe
    # desse MAIS acesso: deixava de contar como motorista e passava a ver e a
    # vender em todas as viagens. Uma desactivacao nunca pode alargar
    # permissoes.
    #
    # Quem conduz vende so nas suas. Sem viagens alocadas, o filtro devolve
    # lista vazia e ele nao vende nada — que e a regra do operador.
    return conduz


class DeviceBlocked(Exception):
    """O terminal indicado esta bloqueado — a operacao nao pode prosseguir."""


def get_authorized_device(user, serial_number: str | None = None) -> Device | None:
    """Resolve o dispositivo da operacao.

    Politica: dispositivos LIVRES — qualquer agente/motorista opera qualquer
    terminal nao bloqueado. Com serial, resolve por serial; sem serial, cai na
    alocacao administrativa (opcional, so informativa).

    Um terminal BLOQUEADO levanta `DeviceBlocked` em vez de devolver None.
    Devolver None fazia com que a chamada seguisse "sem dispositivo" — e a
    venda passava, porque a verificacao a jusante era
    `if device and device.status == BLOCKED`. Ou seja: bloquear um terminal
    roubado no portal nao o impedia de continuar a vender.
    """
    if not user or not user.is_authenticated:
        return None
    if serial_number:
        device = Device.objects.filter(serial_number=serial_number).first()
        if device and device.status == Device.Status.BLOCKED:
            raise DeviceBlocked("Terminal bloqueado. Contacte o administrador.")
        return device
    device = Device.objects.filter(assigned_agent=user).first()
    if device and device.status == Device.Status.BLOCKED:
        raise DeviceBlocked("Terminal bloqueado. Contacte o administrador.")
    return device


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
