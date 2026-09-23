"""
Report builder: a small registry that exposes every supported report
under a single API. Each entry defines:

  - title (human-readable)
  - columns (list of (key, label) pairs used by the table preview + exports)
  - build_rows(filters) → RowSet (list[dict] com um sinal de truncagem)

The view layer (`views.py`) hands the right entry to the JSON/PDF/Excel
renderers so the frontend has ONE endpoint to call regardless of the report
type.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Callable

from django.db.models import Q
from django.utils import timezone

from apps.payments.models import PaymentIntent

# Tecto de linhas por relatorio. Existe porque o documento e construido inteiro
# em memoria antes de ser enviado, e um pedido sem tecto conseguia derrubar o
# worker.
MAX_ROWS = 5000


class RowSet(list):
    """Linhas de um relatorio, com a informacao de se ficaram a faltar.

    Antes o corte era mudo: um relatorio financeiro com 7000 movimentos saia com
    5000 e com ar de completo, e quem reconciliava so descobria a diferenca ao
    nao bater certo com a contabilidade. O sinal viaja com as linhas para o
    documento poder dize-lo em cima.
    """

    truncated = False


def _capped(rows: list) -> RowSet:
    """Corta no tecto e marca se sobrava mais.

    Os chamadores pedem `MAX_ROWS + 1` linhas a base de dados exactamente para
    esta funcao conseguir distinguir "sao mesmo 5000" de "sao mais de 5000".
    """
    out = RowSet(rows[:MAX_ROWS])
    out.truncated = len(rows) > MAX_ROWS
    return out


def _telefone(phone: str | None) -> str:
    """O numero inteiro, e sempre com a mesma cara.

    Saia mascarado («***6483»), o que nao serve para nada a quem recebe o
    relatorio: o operador precisa de ligar ao passageiro e de conciliar com o
    extracto do M-Pesa, onde o numero aparece por extenso. A mascara protegia
    o passageiro de quem ja tem acesso a todos os dados dele — ou seja, de
    ninguem.

    Normaliza-se porque a base guarda as duas formas: uns numeros com o 258 a
    frente, outros sem. Numa coluna so, a mesma pessoa aparecia de duas
    maneiras, e ordenar ou procurar deixava de funcionar.

    Fica como TEXTO com espacos, de proposito: um «258848818277» cru numa
    celula do Excel vira numero e perde a cara — e ninguem reconhece um
    telefone em notacao cientifica.
    """
    d = "".join(ch for ch in (phone or "") if ch.isdigit())
    if not d:
        return ""
    if len(d) == 12 and d.startswith("258"):
        d = d[3:]
    if len(d) == 9:
        return f"+258 {d[:2]} {d[2:5]} {d[5:]}"
    # Fora do formato conhecido, devolve-se o que ha. Inventar um formato para
    # um numero que nao o segue e pior do que o mostrar como esta.
    return phone or ""


def _date_range(filters: dict):
    df = filters.get("date_from")
    dt = filters.get("date_to")
    now = timezone.now()
    if not df:
        df = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if not dt:
        dt = (df + timedelta(days=1))
    return df, dt



def _metodo(provider: str, fallback: str = "") -> str:
    """O nome por que o financeiro conhece o metodo de pagamento.

    Antes saia `mobile_money` e `cash` — identificadores do codigo. Pior:
    `mobile_money` nem sequer diz QUAL carteira, e a carteira esta noutro
    campo que o relatorio nao mostrava. Quem concilia precisa de saber se
    entrou por M-Pesa ou por e-Mola, porque as contas sao diferentes.

    A tabela e a mesma que o painel ja usava (`analytics.PROVIDER_LABELS`) —
    de proposito: dois sitios a traduzir a mesma coisa acabam sempre a
    traduzi-la de maneira diferente.
    """
    from apps.reports.analytics import PROVIDER_LABELS

    chave = (provider or "").strip().upper()
    if chave in PROVIDER_LABELS:
        return PROVIDER_LABELS[chave][0]
    if chave:
        return chave.title()
    # Sem provedor: diz-se o que se sabe, e nunca o nome da variavel.
    return {"cash": "Dinheiro", "mobile_money": "Carteira movel"}.get(fallback, fallback or "—")



#: O que se comprou.
TIPOS = {
    "wallet": "Recarga de saldo",
    "package": "Pacote",
    "card_issuance": "Emissao de cartao",
    "card_recovery": "Recuperacao de cartao",
}


def _legivel(valor: str, tabela: dict) -> str:
    """Traduz, e quando nao souber traduzir devolve algo que ainda se le.

    Nunca devolve vazio: uma celula em branco num relatorio le-se como «nao
    houve», e aqui quer dizer «nao soubemos dizer».
    """
    v = (valor or "").strip()
    if not v:
        return "—"
    return tabela.get(v.lower(), v.replace("_", " ").capitalize())


_NOMES_DE_AGENTE: dict[int, str] = {}


def _agente(user_id) -> str:
    """O nome de quem vendeu, e nao o numero dele na base de dados.

    Um relatorio que diz «6» obriga quem o le a ir perguntar quem e o 6. Fica
    em cache por relatorio: sao meia duzia de agentes em milhares de linhas, e
    uma consulta por linha era uma consulta por linha.
    """
    if not user_id:
        return ""
    if user_id not in _NOMES_DE_AGENTE:
        from django.contrib.auth import get_user_model

        u = get_user_model().objects.filter(pk=user_id).first()
        nome = ""
        if u:
            nome = (u.get_full_name() or "").strip() or u.get_username()
        _NOMES_DE_AGENTE[user_id] = nome or f"#{user_id}"
    return _NOMES_DE_AGENTE[user_id]


# ---------------------------------------------------------------------------
# Report definitions
# ---------------------------------------------------------------------------

def _rows_sales(filters: dict) -> list[dict]:
    df, dt = _date_range(filters)
    qs = (
        PaymentIntent.objects
        .select_related("guest_checkout", "guest_checkout__trip", "guest_checkout__trip__route")
        .filter(
            purpose=PaymentIntent.Purpose.GUEST_TRAVEL_PASS,
            created_at__gte=df, created_at__lt=dt,
        )
        .order_by("-created_at")
    )
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("agent_user_id"):
        qs = qs.filter(metadata__agent_user_id=int(filters["agent_user_id"]))
    if filters.get("route_id"):
        qs = qs.filter(guest_checkout__trip__route_id=int(filters["route_id"]))
    if filters.get("provider"):
        qs = qs.filter(provider__icontains=filters["provider"])

    out = []
    for pi in qs[:MAX_ROWS + 1]:
        gc = pi.guest_checkout
        meta = pi.metadata or {}
        out.append({
            "created_at": pi.created_at,
            "reference": pi.reference,
            "sale_reference": gc.reference if gc else "",
            "route_code": gc.route_code if gc else "",
            "origin": gc.origin_stop if gc else "",
            "destination": gc.destination_stop if gc else "",
            "amount": str(pi.amount),
            "quantity": gc.quantity if gc else 0,
            "method": _metodo(pi.provider, meta.get("payment_method", "")),
            "agent_user_id": _agente(meta.get("agent_user_id")),
            "device_serial": meta.get("device_serial", ""),
            "payer": _telefone(pi.payer_phone),
            "provider": _metodo(pi.provider),
            "status": pi.status,
        })
    return _capped(out)


SALES = ("sales", "Vendas (bilhetes guest)", [
    ("created_at", "Data"),
    ("reference", "Pagamento"),
    ("sale_reference", "Venda"),
    ("route_code", "Rota"),
    ("origin", "Origem"),
    ("destination", "Destino"),
    ("quantity", "Qtd"),
    ("amount", "Valor"),
    ("method", "Metodo"),
    ("agent_user_id", "Agente"),
    ("payer", "Pagador"),
    ("status", "Estado"),
])


def _rows_topups(filters: dict) -> list[dict]:
    df, dt = _date_range(filters)
    qs = (
        PaymentIntent.objects
        .filter(
            purpose=PaymentIntent.Purpose.POS_CARD_TOPUP,
            created_at__gte=df, created_at__lt=dt,
        )
        .order_by("-created_at")
    )
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("agent_user_id"):
        qs = qs.filter(metadata__agent_user_id=int(filters["agent_user_id"]))
    kind = filters.get("kind")  # wallet | package | card_issuance | card_recovery
    if kind:
        qs = qs.filter(metadata__kind=kind)

    out = []
    for pi in qs[:MAX_ROWS + 1]:
        meta = pi.metadata or {}
        # Distinguish wallet topup vs package vs issuance vs recovery
        kind = meta.get("kind") or (
            "package" if "package_id" in meta else "wallet"
        )
        out.append({
            "created_at": pi.created_at,
            "reference": pi.reference,
            "kind": _legivel(kind, TIPOS),
            "card_uid": meta.get("card_uid", ""),
            "amount": str(pi.amount),
            "agent_user_id": _agente(meta.get("agent_user_id")),
            "payer": _telefone(pi.payer_phone),
            "provider": _metodo(pi.provider),
            "status": pi.status,
        })
    return _capped(out)


TOPUPS = ("topups", "Recargas / Pacotes / Emissoes", [
    ("created_at", "Data"),
    ("reference", "Referencia"),
    ("kind", "Tipo"),
    ("card_uid", "Cartao"),
    ("amount", "Valor"),
    ("agent_user_id", "Agente"),
    ("payer", "Pagador"),
    ("provider", "Provider"),
    ("status", "Estado"),
])


def _rows_validations(filters: dict) -> list[dict]:
    from apps.validations.models import ValidationEvent
    df, dt = _date_range(filters)
    qs = (
        ValidationEvent.objects
        .select_related("route", "device", "passenger_account")
        .filter(created_at__gte=df, created_at__lt=dt)
        .order_by("-created_at")
    )
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("route_id"):
        qs = qs.filter(route_id=int(filters["route_id"]))
    if filters.get("validation_type"):
        qs = qs.filter(validation_type=filters["validation_type"])
    if filters.get("device_id"):
        qs = qs.filter(device_id=int(filters["device_id"]))

    out = []
    for v in qs[:MAX_ROWS + 1]:
        out.append({
            "created_at": v.created_at,
            "validation_type": v.validation_type,
            "route": v.route.code if v.route_id else "",
            "device": v.device.serial_number if v.device_id else "",
            "amount_debited": str(v.amount_debited),
            "status": v.status,
            "failure_reason": v.failure_reason or "",
            "passenger": v.passenger_account.full_name if v.passenger_account_id else "",
        })
    return _capped(out)


VALIDATIONS = ("validations", "Validacoes", [
    ("created_at", "Data"),
    ("validation_type", "Tipo"),
    ("route", "Rota"),
    ("device", "Dispositivo"),
    # «Debito» mentia em metade das linhas: num passe digital nada foi
    # debitado, aquilo e quanto o bilhete valia. A coluna «Tipo» ao lado diz
    # qual e qual, com «(ja pago)» ou «(pago a bordo)».
    ("amount_debited", "Valor"),
    ("status", "Estado"),
    ("failure_reason", "Motivo falha"),
    ("passenger", "Passageiro"),
])


def _rows_onboardings(filters: dict) -> list[dict]:
    """Card issuance flow audit. Reads PaymentIntents with kind=card_issuance.

    Useful to see how many new passengers each agent onboarded per period.
    """
    df, dt = _date_range(filters)
    qs = (
        PaymentIntent.objects
        .filter(
            purpose=PaymentIntent.Purpose.POS_CARD_TOPUP,
            metadata__kind="card_issuance",
            created_at__gte=df, created_at__lt=dt,
        )
        .order_by("-created_at")
    )
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("agent_user_id"):
        qs = qs.filter(metadata__agent_user_id=int(filters["agent_user_id"]))

    out = []
    for pi in qs[:MAX_ROWS + 1]:
        meta = pi.metadata or {}
        out.append({
            "created_at": pi.created_at,
            "reference": pi.reference,
            "passenger_id": meta.get("passenger_id"),
            "card_uid": meta.get("card_uid", ""),
            "amount": str(pi.amount),
            "agent_user_id": _agente(meta.get("agent_user_id")),
            "device": meta.get("device_serial", ""),
            "payer": _telefone(pi.payer_phone),
            "status": pi.status,
        })
    return _capped(out)


ONBOARDING = ("onboarding", "Registo de passageiros (com cartao)", [
    ("created_at", "Data"),
    ("reference", "Pagamento"),
    ("passenger_id", "Passageiro"),
    ("card_uid", "UID cartao"),
    ("amount", "Taxa"),
    ("agent_user_id", "Agente"),
    ("device", "Dispositivo"),
    ("payer", "Pagador"),
    ("status", "Estado"),
])


def _rows_recoveries(filters: dict) -> list[dict]:
    df, dt = _date_range(filters)
    qs = (
        PaymentIntent.objects
        .filter(
            purpose=PaymentIntent.Purpose.POS_CARD_TOPUP,
            metadata__kind="card_recovery",
            created_at__gte=df, created_at__lt=dt,
        )
        .order_by("-created_at")
    )
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("agent_user_id"):
        qs = qs.filter(metadata__agent_user_id=int(filters["agent_user_id"]))

    out = []
    for pi in qs[:MAX_ROWS + 1]:
        meta = pi.metadata or {}
        out.append({
            "created_at": pi.created_at,
            "reference": pi.reference,
            "passenger_id": meta.get("passenger_id"),
            "new_card_uid": meta.get("card_uid", ""),
            "blocked_cards": meta.get("blocked_cards", 0),
            "amount": str(pi.amount),
            "reason": meta.get("reason", ""),
            "agent_user_id": _agente(meta.get("agent_user_id")),
            "status": pi.status,
        })
    return _capped(out)


RECOVERIES = ("recoveries", "Recuperacao de cartoes", [
    ("created_at", "Data"),
    ("reference", "Pagamento"),
    ("passenger_id", "Passageiro"),
    ("new_card_uid", "Novo UID"),
    ("blocked_cards", "Bloqueados"),
    ("amount", "Taxa"),
    ("reason", "Motivo"),
    ("agent_user_id", "Agente"),
    ("status", "Estado"),
])


def _rows_tickets(filters: dict) -> list[dict]:
    """Um bilhete por linha, do ponto de vista do PASSAGEIRO.

    O relatorio de Vendas conta PAGAMENTOS: uma familia de tres e uma linha so,
    e o nome de quem viaja nao aparece em lado nenhum. Quem opera a carreira
    nao trabalha assim — trabalha com a lista de quem vai no autocarro, que e
    exactamente a folha que a TPM-TUR mantinha a mao ao lado do sistema.

    **Uma linha por passageiro, e nao por perna.** No sistema, uma ida-e-volta
    sao dois bilhetes (05:00 e 15:30, com codigos proprios); na folha do
    operador e uma linha com as duas datas e o valor das duas. Junta-se aqui,
    porque e assim que ele confere — e o valor bate com o que o passageiro
    pagou, que e o numero que interessa quando alguem reclama.

    As duas pernas emparelham-se pelo nome E pelo documento. So pelo nome,
    dois irmaos com o mesmo nome proprio numa mesma compra apareciam fundidos
    numa linha.
    """
    from apps.guest_checkouts.models import DigitalTravelPass

    df, dt = _date_range(filters)
    qs = (
        DigitalTravelPass.objects
        .select_related("guest_checkout", "guest_checkout__return_trip", "trip", "trip__route")
        .filter(created_at__gte=df, created_at__lt=dt)
        .order_by("-created_at", "guest_checkout_id", "passenger_name", "leg")
    )
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("route_id"):
        qs = qs.filter(trip__route_id=int(filters["route_id"]))

    # O tecto conta LINHAS, e cada linha pode vir de duas pernas. Pede-se o
    # dobro para o `_capped` continuar a distinguir "sao mesmo 5000" de "sao
    # mais de 5000" depois de juntar.
    linhas: dict[tuple, dict] = {}
    for p in qs[: (MAX_ROWS + 1) * 2]:
        gc = p.guest_checkout
        chave = (p.guest_checkout_id, p.passenger_name.strip().lower(), p.document_number)

        linha = linhas.get(chave)
        if linha is None:
            linha = linhas[chave] = {
                "created_at": p.created_at,
                "bilhete": "",
                "passageiro": p.passenger_name or "",
                "documento": p.document_number or "",
                "tipo_de_viagem": "Ida e volta" if (gc and gc.return_trip_id) else "So ida",
                "ida_at": None,
                "regresso_at": None,
                "rota": p.route_name or p.route_code or "",
                "partida": p.origin_stop or "",
                "destino": p.destination_stop or "",
                "fare_amount": Decimal("0.00"),
                "status": p.status,
                # Guardados por perna e nao por ordem de chegada: as duas sao
                # criadas no mesmo instante, e a ordenacao por data punha o
                # codigo do regresso a frente do da ida. Quem le o bilhete le
                # a ida primeiro.
                "_codigos": {},
            }

        if p.leg == DigitalTravelPass.Leg.RETURN:
            linha["regresso_at"] = p.departure_at
        else:
            linha["ida_at"] = p.departure_at
            # A data da compra e a do bilhete de ida: e a da venda.
            linha["created_at"] = p.created_at

        linha["fare_amount"] += p.fare_amount or Decimal("0.00")
        if p.short_code:
            linha["_codigos"][p.leg] = p.short_code

        # Um bilhete cancelado numa das pernas nao pode passar por activo na
        # linha inteira: fica o estado mais grave dos dois.
        if p.status != DigitalTravelPass.Status.ACTIVE:
            linha["status"] = p.status

    out = []
    for linha in linhas.values():
        codigos = linha.pop("_codigos")
        linha["bilhete"] = " / ".join(
            codigos[perna] for perna in ("outbound", "return") if perna in codigos
        )
        linha["fare_amount"] = str(linha["fare_amount"])
        out.append(linha)
    return _capped(out)


TICKETS = ("tickets", "Bilhetes por passageiro", [
    ("created_at", "Data da compra"),
    ("bilhete", "Nr do bilhete"),
    ("passageiro", "Nome do passageiro"),
    ("documento", "Documento"),
    ("tipo_de_viagem", "Tipo de viagem"),
    ("ida_at", "Ida"),
    ("regresso_at", "Regresso"),
    ("rota", "Rota"),
    ("fare_amount", "Valor do bilhete"),
    ("status", "Estado"),
])

  # ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

@dataclass
class ReportSpec:
    key: str
    title: str
    columns: list[tuple[str, str]]
    build_rows: Callable[[dict], list[dict]]
    #: O que este relatorio conta, e o que NAO conta.
    #:
    #: Existe porque o cliente comparou o total de um relatorio com o cartao
    #: «Receita de transporte» do painel e encontrou 10 900,00 MZN de
    #: diferenca. Nao era erro: o painel soma bilhetes MAIS validacoes de
    #: cartao, e este relatorio so cobre um dos dois.
    #:
    #: Um numero que nao diz o que conta obriga quem o le a desconfiar de
    #: todos os outros. A frase vai dentro do documento, onde a pergunta
    #: aparece — e nao numa pagina de ajuda que ninguem abre.
    escopo: str = ""


REGISTRY: dict[str, ReportSpec] = {
    SALES[0]: ReportSpec(
        *SALES, _rows_sales,
        escopo="Conta os PAGAMENTOS de bilhetes comprados sem conta (guest). "
               "Nao inclui recargas de saldo. O relatorio de Validacoes NAO se "
               "soma a este: um bilhete validado a bordo e um destes bilhetes a "
               "embarcar, nao uma venda nova.",
    ),
    TOPUPS[0]: ReportSpec(
        *TOPUPS, _rows_topups,
        escopo="Conta recargas de saldo, pacotes e emissoes de cartao. "
               "Nao inclui bilhetes. Uma recarga e dinheiro recebido mas ainda "
               "em divida ao passageiro: so vira receita quando ele viaja.",
    ),
    VALIDATIONS[0]: ReportSpec(
        *VALIDATIONS, _rows_validations,
        escopo="Conta EMBARQUES: cada bilhete ou cartao lido a bordo. So «Cobrado "
               "a bordo» e receita — e o saldo que saiu no momento. «Bilhetes "
               "embarcados» e o valor de bilhetes ja pagos na compra e NAO se "
               "soma ao relatorio de Vendas, senao conta-se o mesmo dinheiro "
               "duas vezes.",
    ),
    ONBOARDING[0]: ReportSpec(
        *ONBOARDING, _rows_onboardings,
        escopo="Conta registos de passageiros com cartao. Nao e receita de transporte.",
    ),
    RECOVERIES[0]: ReportSpec(
        *RECOVERIES, _rows_recoveries,
        escopo="Conta recuperacoes de cartao perdido. Nao e receita de transporte.",
    ),
    TICKETS[0]: ReportSpec(
        *TICKETS, _rows_tickets,
        escopo="Uma linha por passageiro que viaja. Uma ida-e-volta e UMA linha "
               "com as duas datas. Nao inclui embarques pagos do saldo a bordo.",
    ),
}



def aggregate_totals(spec: ReportSpec, rows: list[dict]) -> dict:
    """Compute headline totals for the report header. Specific per kind."""
    totals = {"count": len(rows)}
    if spec.key == "tickets":
        # Cancelados e reembolsados nao somam: um bilhete devolvido nao e
        # receita, e um total que os conte da sempre mais do que a conta.
        validos = [r for r in rows if r.get("status") in {"active", "used", "expired"}]
        totals["confirmed_count"] = len(validos)
        totals["total_amount"] = str(
            sum((Decimal(r["fare_amount"]) for r in validos), Decimal("0.00"))
        )
    elif spec.key in {"sales", "topups", "onboarding", "recoveries"}:
        ok = [r for r in rows if r.get("status") == "confirmed"]
        totals["confirmed_count"] = len(ok)
        totals["total_amount"] = str(sum((Decimal(r["amount"]) for r in ok), Decimal("0.00")))
    elif spec.key == "validations":
        # O `amount_debited` quer dizer duas coisas conforme o tipo, por isso um
        # total unico mente a metade dos casos. Num passe digital o bilhete foi
        # pago na compra: aquele valor e quanto o passageiro valia a bordo, nao
        # um debito. Somar os dois num numero chamado «Total debitado» foi como
        # a receita da TPM-TUR apareceu inflacionada em 10 900,00 MZN.
        from apps.validations.models import COBRA_NO_EMBARQUE

        cobrados = {str(t) for t in COBRA_NO_EMBARQUE}
        ok = [r for r in rows if r.get("status") == "approved"]
        totals["approved_count"] = len(ok)
        totals["total_debited"] = str(sum(
            (Decimal(r["amount_debited"]) for r in ok
             if r.get("validation_type") in cobrados), Decimal("0.00")))
        totals["total_embarcado"] = str(sum(
            (Decimal(r["amount_debited"]) for r in ok
             if r.get("validation_type") not in cobrados), Decimal("0.00")))
    return totals
