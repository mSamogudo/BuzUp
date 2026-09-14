"""Reconciliação de pagamentos pendentes com o gateway.

O problema que isto resolve: a confirmação de um pagamento chega por webhook.
Com a rede móvel a oscilar — e é a norma no terreno — uma parte dos webhooks
nunca chega. O passageiro pagou no M-Pesa, o dinheiro saiu da conta dele, e o
`PaymentIntent` fica `PENDING` para sempre: nunca recebe bilhete, e nada no
sistema deteta que isso aconteceu. A reclamação chega ao balcão dias depois,
sem forma de provar o que se passou.

`query_payment` já existia no gateway e nunca era chamado por ninguém. Este
módulo é o chamador que faltava: pergunta ao gateway o que aconteceu de facto a
cada pagamento pendente e alinha o nosso estado com a resposta.

Uma decisão importante está aqui: quando o gateway confirma um pagamento cujo
checkout **já expirou**, NÃO emitimos o bilhete automaticamente. O lugar pode
ter sido libertado e revendido a outra pessoa, e emitir criaria dois
passageiros com o mesmo lugar — um problema pior do que o original. Esses casos
são marcados para revisão humana (com o dinheiro reconhecido como recebido),
porque a decisão entre reemitir e reembolsar depende de haver ou não lugar.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from django.utils import timezone

from apps.audit.services import audit
from apps.payments.models import PaymentCallback, PaymentIntent
from apps.payments.services.gateway import get_payment_gateway
from apps.payments.services.processing import _confirm_payment, _fail_payment

logger = logging.getLogger(__name__)

# Margem antes de perguntar ao gateway: um pagamento acabado de iniciar está
# legitimamente pendente enquanto o passageiro digita o PIN.
#
# Era 5. Com o cron de 2 em 2 minutos, um pagamento que escapasse ao timeout
# da cobrança só era confirmado 5 a 7 minutos depois — o "atraso nos
# pagamentos" de 2026-09-08 (352 s numa venda ao balcão). A cobrança já espera
# 45 s pelo PIN; ao fim de 1 minuto não há nada que a consulta possa estragar.
DEFAULT_MIN_AGE_MINUTES = 1


@dataclass
class ReconcileReport:
    checked: int = 0
    confirmed: int = 0
    failed: int = 0
    still_pending: int = 0
    needs_review: int = 0
    unsupported: int = 0
    errors: list[str] = field(default_factory=list)

    def as_line(self) -> str:
        return (
            f"verificados={self.checked} confirmados={self.confirmed} "
            f"falhados={self.failed} pendentes={self.still_pending} "
            f"revisao_manual={self.needs_review} sem_consulta={self.unsupported} "
            f"erros={len(self.errors)}"
        )


def _checkout_still_usable(payment_intent: PaymentIntent) -> bool:
    """O bilhete deste pagamento ainda pode ser emitido em segurança?

    Se o checkout expirou, o lugar já foi devolvido à lotação (ver
    `guest_checkouts/capacity.py`) e pode estar vendido a outra pessoa.
    """
    from apps.guest_checkouts.models import GuestCheckout

    gc = payment_intent.guest_checkout
    if gc is None:
        # Recargas de carteira não têm lugar associado: creditar é sempre seguro.
        return True
    if gc.status in (GuestCheckout.Status.EXPIRED, GuestCheckout.Status.CANCELLED):
        return False
    if gc.expires_at and gc.expires_at < timezone.now():
        return False
    return True


def _mark_for_review(payment_intent: PaymentIntent, provider_reference: str, detail: str) -> None:
    """Dinheiro recebido que não pode ser transformado em bilhete sozinho."""
    metadata = dict(payment_intent.metadata or {})
    metadata["reconciliation"] = {
        "needs_manual_review": True,
        "reason": detail,
        "provider_reference": provider_reference,
        "detected_at": timezone.now().isoformat(),
    }
    payment_intent.metadata = metadata
    payment_intent.save(update_fields=["metadata", "updated_at"])
    audit(
        "PAYMENT_NEEDS_REVIEW",
        entity_type="payment_intent",
        entity_id=str(payment_intent.id),
        after={
            "reference": payment_intent.reference,
            "amount": str(payment_intent.amount),
            "payer_phone": payment_intent.payer_phone,
            "reason": detail,
        },
    )
    logger.warning(
        "reconciliacao: pagamento %s confirmado pelo gateway mas o checkout ja expirou (%s)",
        payment_intent.reference, detail,
    )


def referencia_para_consulta(payment_intent: PaymentIntent) -> str:
    """Por que referência se pergunta à operadora.

    Era `provider_reference or reference`. No caso que esta função existe para
    resolver — o pedido morreu no nosso timeout — a `provider_reference` está
    VAZIA, porque a resposta nunca chegou. Caía então na nossa `PAY-GC-...`,
    que a operadora nunca viu: o que lhe foi enviado foi a compactada
    (`MP...`, ver `_compact_reference`). A Payless respondia `data: []`, que se
    lia como pendente, e o pagamento ficava assim até expirar.

    A 2026-09-03 foram 6.600 MT nesse limbo: a Payless tinha `INS-0` e o
    `transactionID` à espera de quem perguntasse pela referência certa.

    Primeiro o que FOI enviado (está na metadata) — é a única referência que
    se SABE que a pesquisa da Payless reconhece. Depois a da operadora, se a
    houver. Só então se deriva a compactada outra vez — é determinística, é
    para isso que a compactação existe — e nunca a nossa, no M-Pesa.
    """
    from apps.payments.services.gateway import _compact_reference

    pedido = (payment_intent.metadata or {}).get("gateway_request") or {}
    enviada = str(pedido.get("transactionReference") or "").strip()
    if enviada:
        return enviada
    if payment_intent.provider_reference:
        return payment_intent.provider_reference
    if payment_intent.provider == "MPESA" and payment_intent.reference:
        return _compact_reference("MP", payment_intent.reference)
    return payment_intent.reference or ""


def reconcile_payment(payment_intent: PaymentIntent, report: ReconcileReport) -> None:
    """Alinha um pagamento com o que o gateway diz ter acontecido."""
    report.checked += 1
    gateway = get_payment_gateway(
        provider=payment_intent.provider or None,
        payer_phone=payment_intent.payer_phone,
    )

    lookup_ref = referencia_para_consulta(payment_intent)
    if not lookup_ref:
        report.unsupported += 1
        return

    try:
        result = gateway.query_payment(lookup_ref)
    except Exception as exc:  # rede, timeout, resposta ilegível
        report.errors.append(f"{payment_intent.reference}: {exc}")
        logger.warning("reconciliacao: consulta falhou para %s: %s", payment_intent.reference, exc)
        return

    if not result.success and not result.pending and result.error and "not supported" in result.error.lower():
        report.unsupported += 1
        return

    if result.pending:
        report.still_pending += 1
        return

    if result.success:
        if not _checkout_still_usable(payment_intent):
            report.needs_review += 1
            _mark_for_review(
                payment_intent,
                result.provider_reference or lookup_ref,
                "pagamento confirmado apos a expiracao do checkout — o lugar pode ter sido revendido",
            )
            return

        callback = PaymentCallback.objects.create(
            payment_intent=payment_intent,
            provider_reference=result.provider_reference or lookup_ref,
            raw_payload={
                "source": "reconciliation",
                "provider": payment_intent.provider,
                "gateway_response": result.response_payload or {},
            },
            signature_valid=True,
            processing_status="received",
        )
        _confirm_payment(payment_intent, callback, result.provider_reference or lookup_ref)
        report.confirmed += 1
        logger.info(
            "reconciliacao: pagamento %s confirmado a partir do gateway (webhook perdido)",
            payment_intent.reference,
        )
        return

    # O gateway diz que falhou: fechar o pagamento e libertar o lugar.
    callback = PaymentCallback.objects.create(
        payment_intent=payment_intent,
        provider_reference=result.provider_reference or lookup_ref,
        raw_payload={
            "source": "reconciliation",
            "provider": payment_intent.provider,
            "gateway_response": result.response_payload or {},
        },
        signature_valid=True,
        processing_status="received",
    )
    _fail_payment(payment_intent, callback)
    report.failed += 1


#: Quem esta a espera no ecra pode pedir uma consulta a operadora, mas nao
#: em cada toque: a primeira so passados `ESPERA_INICIAL_S` (o PIN tem de ter
#: chegado ao telemovel), e nunca duas a menos de `INTERVALO_MINIMO_S`.
ESPERA_INICIAL_S = 20
INTERVALO_MINIMO_S = 5


def perguntar_a_operadora_se_for_altura(payment_intent: PaymentIntent) -> bool:
    """Consulta a operadora a pedido de quem espera — POS ou pagina — com freio.

    Devolve True se perguntou (e o estado pode ter mudado). O carimbo da ultima
    consulta fica na metadata, para o freio valer entre pedidos e entre
    processos.
    """
    from django.utils import timezone as _tz

    agora = _tz.now()
    if (agora - payment_intent.created_at).total_seconds() < ESPERA_INICIAL_S:
        return False
    md = dict(payment_intent.metadata or {})
    ultima = md.get("last_query_at")
    if ultima:
        try:
            if (agora - _tz.datetime.fromisoformat(ultima)).total_seconds() < INTERVALO_MINIMO_S:
                return False
        except ValueError:
            pass
    md["last_query_at"] = agora.isoformat()
    PaymentIntent.objects.filter(pk=payment_intent.pk).update(metadata=md)
    payment_intent.metadata = md
    try:
        reconcile_payment(payment_intent, ReconcileReport())
    except Exception:
        logger.exception("consulta a pedido falhou para %s", payment_intent.reference)
        return False
    return True


def reconcile_pending_payments(
    *,
    min_age_minutes: int = DEFAULT_MIN_AGE_MINUTES,
    limit: int = 200,
) -> ReconcileReport:
    """Consulta o gateway sobre os pagamentos pendentes e alinha o estado.

    `limit` existe para uma execução não crescer sem controlo: cada consulta é
    uma chamada HTTP a terceiros, e é preferível processar 200 por passagem de
    cinco em cinco minutos do que prender um worker durante muito tempo.
    """
    report = ReconcileReport()
    cutoff = timezone.now() - timedelta(minutes=min_age_minutes)

    pending = (
        PaymentIntent.objects
        .select_related("guest_checkout", "wallet")
        .filter(status=PaymentIntent.Status.PENDING, created_at__lt=cutoff)
        .order_by("created_at")[:limit]
    )

    for payment_intent in pending:
        try:
            reconcile_payment(payment_intent, report)
        except Exception as exc:
            # Um pagamento problemático não pode parar a reconciliação dos
            # outros — é exactamente o caso em que mais precisamos dela.
            report.errors.append(f"{payment_intent.reference}: {exc}")
            logger.exception("reconciliacao: erro inesperado em %s", payment_intent.reference)

    return report


# ---------------------------------------------------------------------------
# Segunda volta: os que ja foram dados como falhados
# ---------------------------------------------------------------------------
#
# A reconciliacao acima so olha para PENDING. Assim que um pagamento e marcado
# FAILED, ninguem volta a olhar para ele — nunca mais.
#
# Isso seria inofensivo se "falhado" quisesse sempre dizer "nao pago". Nao
# quer. Ate 2026-09-10 o nosso proprio timeout marcava FAILED, e a operadora
# podia estar a debitar o passageiro nesse preciso momento. A 2026-09-14 uma
# auditoria a mao encontrou **dois** pagamentos assim: 1.650 MZN de 28/08 e
# 3.300 MZN de 31/08, ambos cobrados, nenhum com bilhete. Estiveram 17 e 14
# dias sem ninguem dar por nada, e so foram encontrados porque alguem se
# lembrou de perguntar.
#
# Esta funcao e essa pergunta, feita sozinha e todos os dias.
#
# **Nao confirma nada.** O checkout de um pagamento falhado ja foi cancelado e
# o lugar devolvido a lotacao; a viagem pode ter partido ha semanas. Emitir um
# bilhete por cima disso cria dois passageiros no mesmo lugar, ou um bilhete
# para um autocarro que ja foi. Marca para revisao e avisa — a escolha entre
# reemitir e devolver o dinheiro e de quem conhece o caso.

#: Ha quantos dias para tras se procura. Sete cobre com folga o intervalo
#: entre a venda e a reclamacao; mais do que isso e arqueologia e repete
#: consultas a operadora sem ganho.
DIAS_A_REVER = 7

#: Nao repetir a pergunta sobre o mesmo pagamento todos os dias para sempre.
#: Tres passagens chegam: se a operadora nao mudou de ideias em tres dias, nao
#: muda mais.
MAXIMO_DE_AUDITORIAS = 3


@dataclass
class AuditoriaReport:
    verificados: int = 0
    mesmo_falhados: int = 0
    pagos_sem_bilhete: int = 0
    sem_consulta: int = 0
    ja_auditados: int = 0
    erros: list[str] = field(default_factory=list)

    def as_line(self) -> str:
        return (
            f"verificados={self.verificados} confirmados_falhados={self.mesmo_falhados} "
            f"PAGOS_SEM_BILHETE={self.pagos_sem_bilhete} sem_consulta={self.sem_consulta} "
            f"ja_auditados={self.ja_auditados} erros={len(self.erros)}"
        )


def _ja_auditado_vezes(payment_intent: PaymentIntent) -> int:
    return int(((payment_intent.metadata or {}).get("auditoria") or {}).get("vezes", 0))


def _registar_auditoria(payment_intent: PaymentIntent, veredicto: str) -> None:
    metadata = dict(payment_intent.metadata or {})
    anterior = metadata.get("auditoria") or {}
    metadata["auditoria"] = {
        "vezes": int(anterior.get("vezes", 0)) + 1,
        "ultima": timezone.now().isoformat(),
        "veredicto": veredicto,
    }
    PaymentIntent.objects.filter(pk=payment_intent.pk).update(
        metadata=metadata, updated_at=timezone.now(),
    )


def _avisar_dinheiro_encontrado(payment_intent: PaymentIntent, provider_reference: str) -> None:
    """Um SMS, uma vez, por pagamento.

    Isto nao e um alerta de infraestrutura: dispara duas vezes em mes e meio, e
    quando dispara ha dinheiro de alguem parado. A contencao esta em so avisar
    quando a operadora confirma que cobrou, e em nunca repetir pelo mesmo
    pagamento.
    """
    from django.conf import settings

    numeros = [
        n.strip()
        for n in str(getattr(settings, "PAYMENT_REVIEW_ALERT_NUMBERS", "") or "").split(",")
        if n.strip()
    ]
    if not numeros:
        return

    corpo = (
        f"BuzUp: pagamento {payment_intent.amount} MZN de {payment_intent.payer_phone} "
        f"foi COBRADO mas ficou sem bilhete ({payment_intent.reference}). "
        "Precisa de decisao: reemitir ou devolver."
    )
    from apps.sms.services.sender import send_sms

    for numero in numeros:
        try:
            send_sms(numero, corpo, purpose="PAYMENT_REVIEW")
        except Exception:  # pragma: no cover - avisar nunca pode partir a auditoria
            logger.exception("nao consegui avisar %s sobre %s", numero, payment_intent.reference)


def auditar_pagamentos_falhados(
    *, dias: int = DIAS_A_REVER, limit: int = 100,
) -> AuditoriaReport:
    """Pergunta a operadora se algum "falhado" recente foi afinal cobrado."""
    report = AuditoriaReport()
    desde = timezone.now() - timedelta(days=dias)

    falhados = (
        PaymentIntent.objects
        .select_related("guest_checkout")
        .filter(status=PaymentIntent.Status.FAILED, created_at__gte=desde)
        .order_by("-created_at")[: limit * 3]
    )

    for pi in falhados:
        if report.verificados >= limit:
            break
        if _ja_auditado_vezes(pi) >= MAXIMO_DE_AUDITORIAS:
            report.ja_auditados += 1
            continue
        try:
            gateway = get_payment_gateway(payer_phone=pi.payer_phone)
            referencia = referencia_para_consulta(pi)
            resultado = gateway.query_payment(referencia)
        except Exception as exc:
            report.erros.append(f"{pi.reference}: {exc.__class__.__name__}: {exc}")
            continue

        report.verificados += 1

        # O e-Mola nao tem consulta. Nao e um erro nosso — e um facto do canal,
        # e a unica forma de o resolver e a operadora passar a oferecer uma.
        if not resultado.success and str(resultado.error or "").lower().startswith("query not supported"):
            report.sem_consulta += 1
            continue

        if resultado.success:
            report.pagos_sem_bilhete += 1
            _mark_for_review(
                pi,
                resultado.provider_reference or referencia,
                "a operadora diz que este pagamento foi COBRADO, mas foi dado como falhado "
                "e nao emitiu bilhete",
            )
            if _ja_auditado_vezes(pi) == 0:
                _avisar_dinheiro_encontrado(pi, resultado.provider_reference or referencia)
            _registar_auditoria(pi, "pago")
            logger.error(
                "[auditoria] PAGO SEM BILHETE ref=%s valor=%s telefone=%s operadora=%s",
                pi.reference, pi.amount, pi.payer_phone,
                resultado.provider_reference or referencia,
            )
            continue

        report.mesmo_falhados += 1
        _registar_auditoria(pi, "nao pago")

    return report
