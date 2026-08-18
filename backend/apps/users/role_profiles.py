"""Papeis do portal que tambem sao um registo operacional.

Dar a alguem o papel de **Motorista** no portal e dizer que essa pessoa
conduz. Mas quem conduz vive na tabela `Driver`: e dela que sai a lista de
alocacao de uma viagem, e e por ela que o POS sabe que viagens mostrar ao
motorista autenticado. Enquanto as duas coisas viveram em sitios separados,
atribuir o papel nao criava o motorista — o cliente marcava duas pessoas como
motoristas, ia criar a viagem, e o selector aparecia vazio sem nada em lado
nenhum a dizer porque.

O mesmo se aplica ao papel de **Agente/Cobrador** e a tabela `Agent`.

Retirar o papel nao apaga o registo: passa-o a inactivo. Um motorista tem
viagens, manifestos e receita atras dele — apagar isso porque alguem mexeu
numa caixa de papeis seria destruir historico.
"""

from __future__ import annotations


def sincronizar_perfis_operacionais(user) -> None:
    """Faz a tabela `Driver`/`Agent` concordar com os papeis do utilizador."""
    from apps.trips.models import Agent, Driver

    codigos = {
        atribuicao.role.code
        for atribuicao in user.role_assignments.select_related("role").all()
    }
    _alinhar(Driver, user, "driver" in codigos)
    _alinhar(Agent, user, bool({"agent", "pos_agent"} & codigos))


def _alinhar(modelo, user, deve_existir: bool) -> None:
    perfil = modelo.all_objects.filter(user=user).first()

    if not deve_existir:
        if perfil is not None and perfil.deleted_at is None and perfil.status == modelo.Status.ACTIVE:
            perfil.status = modelo.Status.INACTIVE
            perfil.save(update_fields=["status", "updated_at"])
        return

    nome = user.get_full_name().strip() or user.username
    telefone = (getattr(user, "phone", "") or "").strip()

    if perfil is None:
        modelo.objects.create(
            user=user, full_name=nome, phone=telefone,
            status=modelo.Status.ACTIVE,
        )
        return

    campos = []
    if perfil.deleted_at is not None:
        perfil.deleted_at = None
        campos.append("deleted_at")
    if perfil.status != modelo.Status.ACTIVE:
        perfil.status = modelo.Status.ACTIVE
        campos.append("status")
    # O nome do registo operacional segue o do utilizador enquanto ninguem lhe
    # tiver mexido a mao; um registo criado aqui nunca fica com o nome antigo.
    if not perfil.full_name.strip():
        perfil.full_name = nome
        campos.append("full_name")
    if telefone and not perfil.phone.strip():
        perfil.phone = telefone
        campos.append("phone")
    if campos:
        perfil.save(update_fields=[*campos, "updated_at"])
