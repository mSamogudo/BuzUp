"""Abrir, fechar, conferir e reabrir um turno.

As regras vivem aqui e nao nas views porque sao as mesmas venha o pedido do
portal ou do POS, e porque o calculo do apurado nao pode ter duas versoes.
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from apps.payments.models import CASH_PROVIDER, PaymentIntent
from apps.shifts.models import Shift
from apps.validations.models import ValidationEvent


class ShiftError(Exception):
    """Regra de negocio do turno recusada. A view devolve-a como 400."""


def turno_aberto_de(user) -> Shift | None:
    """O turno aberto deste agente, se houver."""
    return Shift.objects.filter(agent_user=user, status=Shift.Status.OPEN).first()


@transaction.atomic
def abrir_turno(*, agent_user, vehicle=None, device=None, agent_profile=None,
                float_amount=Decimal("0.00"), opened_by=None) -> Shift:
    """Abre um turno para o agente.

    **Um turno aberto de cada vez por agente.** Dois turnos abertos ao mesmo
    tempo dividiam as vendas do agente entre as duas caixas sem criterio
    nenhum, e nenhuma das duas fechava certa. O bloqueio e por linha para que
    dois toques no mesmo botao nao abram dois.
    """
    existente = (
        Shift.objects.select_for_update()
        .filter(agent_user=agent_user, status=Shift.Status.OPEN)
        .first()
    )
    if existente:
        raise ShiftError(
            "Este agente ja tem um turno aberto. Feche o turno anterior antes de abrir outro."
        )
    if float_amount is None:
        float_amount = Decimal("0.00")
    if float_amount < 0:
        raise ShiftError("O fundo de maneio nao pode ser negativo.")

    return Shift.objects.create(
        agent_user=agent_user,
        agent_profile=agent_profile,
        vehicle=vehicle,
        device=device,
        float_amount=float_amount,
        opened_by=opened_by or agent_user,
        status=Shift.Status.OPEN,
    )


def apurado_esperado(shift: Shift) -> dict:
    """Quanto DINHEIRO FISICO devia estar na caixa deste turno.

    So conta numerario. As vendas por M-Pesa ou e-Mola entram directamente na
    conta da operadora e nunca passam pelas maos do agente; somar-lhes o valor
    fazia a caixa parecer sempre em falta pelo mesmo montante que o gateway ja
    tinha recebido. O mesmo para as validacoes, que descontam da carteira do
    passageiro: contam-se para o historico, mas nao entram no que ha para
    entregar.

    O fundo de maneio entra porque tambem tem de voltar: o agente devolve o
    troco com que comecou mais o que vendeu a dinheiro.
    """
    numerario = (
        PaymentIntent.objects
        .filter(
            guest_checkout__shift=shift,
            status=PaymentIntent.Status.CONFIRMED,
            provider=CASH_PROVIDER,
        )
        .aggregate(total=Sum("amount"), n=Count("id", distinct=True))
    )
    bilhetes = shift.checkouts.aggregate(n=Count("id"))
    validacoes = shift.validations.filter(
        status=ValidationEvent.Status.APPROVED,
    ).aggregate(n=Count("id"), total=Sum("amount_debited"))

    dinheiro = numerario["total"] or Decimal("0.00")
    return {
        "cash_sales": dinheiro,
        "expected": (shift.float_amount or Decimal("0.00")) + dinheiro,
        "tickets_count": bilhetes["n"] or 0,
        "validations_count": validacoes["n"] or 0,
        "validations_amount": validacoes["total"] or Decimal("0.00"),
    }


@transaction.atomic
def fechar_turno(shift: Shift, *, counted_amount, notes="") -> Shift:
    """Fecha o turno com o que o agente contou.

    O esperado e calculado AQUI, no servidor. Aceita-lo do cliente era deixar o
    agente declarar a sua propria diferenca — e ela dava sempre zero.
    """
    shift = Shift.objects.select_for_update().get(pk=shift.pk)
    if shift.status != Shift.Status.OPEN:
        raise ShiftError("So um turno aberto pode ser fechado.")
    if counted_amount is None:
        raise ShiftError("Indique quanto dinheiro foi contado.")
    if counted_amount < 0:
        raise ShiftError("O valor contado nao pode ser negativo.")

    contas = apurado_esperado(shift)
    shift.expected_amount = contas["expected"]
    shift.counted_amount = counted_amount
    shift.difference = counted_amount - contas["expected"]
    shift.tickets_count = contas["tickets_count"]
    shift.validations_count = contas["validations_count"]
    shift.closed_at = timezone.now()
    shift.status = Shift.Status.CLOSED
    if notes:
        shift.notes = notes
    shift.save(update_fields=[
        "expected_amount", "counted_amount", "difference",
        "tickets_count", "validations_count", "closed_at", "status", "notes",
        "updated_at",
    ])
    return shift


@transaction.atomic
def conferir_turno(shift: Shift, *, verified_by, notes="") -> Shift:
    """A tesouraria da a conta por boa.

    Conferir nao mexe nos numeros: um turno com diferenca conferido continua a
    ter a diferenca. Reescreve-la para dar zero era apagar a falta em vez de a
    resolver.
    """
    shift = Shift.objects.select_for_update().get(pk=shift.pk)
    if shift.status != Shift.Status.CLOSED:
        raise ShiftError("So um turno fechado pode ser conferido.")
    shift.status = Shift.Status.VERIFIED
    shift.verified_at = timezone.now()
    shift.verified_by = verified_by
    if notes:
        shift.notes = (f"{shift.notes}\n{notes}" if shift.notes else notes)
    shift.save(update_fields=[
        "status", "verified_at", "verified_by", "notes", "updated_at",
    ])
    return shift


@transaction.atomic
def reabrir_turno(shift: Shift, *, motivo: str, reopened_by=None) -> Shift:
    """Reabre um turno fechado ou conferido.

    **O motivo e obrigatorio.** Reabrir uma caixa ja fechada e desfazer uma
    conta que alguem deu por boa; sem o motivo escrito, o historico perdia a
    unica pista de que isso aconteceu.

    Os valores do fecho anterior ficam onde estao — quem fechar de novo
    recalcula-os. Limpa-los aqui deixava o turno num estado em que nao se
    percebia se ja tinha sido contado alguma vez.
    """
    motivo = (motivo or "").strip()
    if not motivo:
        raise ShiftError("Indique porque esta a reabrir o turno.")

    shift = Shift.objects.select_for_update().get(pk=shift.pk)
    if shift.status == Shift.Status.OPEN:
        raise ShiftError("Este turno ja esta aberto.")

    ja_aberto = (
        Shift.objects
        .filter(agent_user=shift.agent_user, status=Shift.Status.OPEN)
        .exclude(pk=shift.pk)
        .exists()
    )
    if ja_aberto:
        raise ShiftError(
            "Este agente tem outro turno aberto. Feche-o antes de reabrir este."
        )

    quem = getattr(reopened_by, "username", "") or "sistema"
    carimbo = timezone.now().strftime("%Y-%m-%d %H:%M")
    shift.notes = (
        f"{shift.notes}\n[reaberto {carimbo} por {quem}] {motivo}"
        if shift.notes else f"[reaberto {carimbo} por {quem}] {motivo}"
    )
    shift.status = Shift.Status.OPEN
    shift.closed_at = None
    shift.verified_at = None
    shift.verified_by = None
    shift.save(update_fields=[
        "status", "closed_at", "verified_at", "verified_by", "notes", "updated_at",
    ])
    return shift
