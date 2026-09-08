"""Pagamento por cartao (Visa/Mastercard) atraves do DPO Pay.

O M-Pesa e um *push*: pedimos, o passageiro digita o PIN, a operadora responde.
O cartao e um *redirect*: criamos um token, mandamos o passageiro para a
pagina do DPO, ele paga la, e volta a uma URL nossa. Por isso o
`initiate_payment` daqui nunca devolve sucesso — devolve PENDENTE com a
`redirect_url`, e o desfecho aprende-se depois pelo `verifyToken`.

**Nunca se acredita no regresso.** O DPO reencaminha o passageiro com
`TransID` e `CCDapproval` no URL, mas isso e um URL que qualquer pessoa pode
escrever. O unico juiz e o `verifyToken`, chamado de servidor para servidor —
pela pagina de regresso, pela notificacao do DPO, ou pela reconciliacao de 2
em 2 minutos, que e a mesma que ja salva os M-Pesa sem webhook. As tres
portas chegam a `reconcile_payment`; nenhuma confirma sozinha.

A API do DPO e XML (v6). Usa-se `xml.etree` da biblioteca padrao; as
respostas sao planas e pequenas.

Porque DPO e nao Stripe: a Stripe nao serve uma empresa mocambicana (nem por
extensao via Paystack). O DPO opera em Mocambique, liquida em MZN, tem
sandbox proprio e e o habitual em transporte e turismo na regiao.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from apps.payments.services.gateway import PaymentGatewayResult

logger = logging.getLogger(__name__)

PROVIDER = "DPO"

#: Codigos do `Result` do DPO. Os que interessam a uma decisao de dinheiro.
#: Qualquer outro e "nao sei" — fica pendente, e a reconciliacao volta a
#: perguntar. Em dinheiro, na duvida, nao se confirma nem se cancela.
RESULT_PAID = "000"
RESULT_NOT_PAID = "900"          # token criado, ninguem pagou (ainda)
RESULTS_FAILED = {
    "901": "Pagamento recusado pelo banco.",
    "902": "Dados do pagamento nao conferem.",
    "903": "O prazo para pagar terminou.",
    "904": "Pagamento cancelado pelo cliente.",
    "950": "Pedido rejeitado pelo operador de cartoes.",
}


@dataclass
class DpoConfig:
    company_token: str
    service_type: str
    api_url: str
    payment_url: str
    currency: str
    ptl_minutes: int
    timeout: int

    @property
    def configured(self) -> bool:
        return bool(self.company_token and self.service_type)


def _config() -> DpoConfig:
    base = str(getattr(settings, "DPO_BASE_URL", "") or "https://secure.3gdirectpay.com").rstrip("/")
    return DpoConfig(
        company_token=str(getattr(settings, "DPO_COMPANY_TOKEN", "") or "").strip(),
        service_type=str(getattr(settings, "DPO_SERVICE_TYPE", "") or "").strip(),
        api_url=f"{base}/API/v6/",
        payment_url=f"{base}/payv2.php?ID=",
        currency=str(getattr(settings, "DPO_CURRENCY", "MZN") or "MZN").upper(),
        # Dentro dos 30 min da reserva do lugar (`GuestCheckout.expires_at`):
        # um token que vive mais do que a reserva deixa o DPO cobrar um
        # lugar que ja foi devolvido a lotacao.
        ptl_minutes=int(getattr(settings, "DPO_PTL_MINUTES", 25) or 25),
        timeout=int(getattr(settings, "DPO_TIMEOUT_SECONDS", 20) or 20),
    )


def usando_sandbox_dpo(config: DpoConfig | None = None) -> bool:
    return "sandbox" in (config or _config()).api_url.lower()


def _xml(tag: str, children: dict | list) -> str:
    """XML minimo, sem dependencias. Os valores sao escapados."""
    from xml.sax.saxutils import escape

    def render(items) -> str:
        if isinstance(items, dict):
            items = list(items.items())
        out = []
        for k, v in items:
            if isinstance(v, (dict, list)):
                out.append(f"<{k}>{render(v)}</{k}>")
            elif v is None:
                continue
            else:
                out.append(f"<{k}>{escape(str(v))}</{k}>")
        return "".join(out)

    return f'<?xml version="1.0" encoding="utf-8"?><{tag}>{render(children)}</{tag}>'


def parse_dpo_xml(raw: str) -> dict:
    """A resposta do DPO como dicionario plano: `{"Result": "000", ...}`.

    Uma resposta que nao seja XML (pagina de erro, corpo vazio) vem como
    `{"raw_response": ...}` — e le-se como "nao sei", nunca como pago.
    """
    texto = (raw or "").strip()
    if not texto:
        return {}
    try:
        root = ET.fromstring(texto)
    except ET.ParseError:
        return {"raw_response": texto[:500]}
    out: dict = {}
    for child in root:
        out[child.tag] = (child.text or "").strip()
    return out


def _post_xml(url: str, body: str, timeout: int) -> tuple[int, dict]:
    import socket
    import urllib.error
    import urllib.request

    request = urllib.request.Request(
        url, data=body.encode("utf-8"), method="POST",
        headers={"Content-Type": "application/xml", "Accept": "application/xml"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(getattr(response, "status", 200)), parse_dpo_xml(response.read().decode("utf-8", "replace"))
    except socket.timeout:
        return 408, {"detail": "Request timed out.", "_timeout_local": True}
    except urllib.error.HTTPError as exc:
        return int(exc.code or 400), parse_dpo_xml(exc.read().decode("utf-8", "replace"))
    except urllib.error.URLError as exc:
        return 502, {"detail": str(getattr(exc, "reason", "Unable to reach payment gateway."))}


def _company_ref(reference: str) -> str:
    """A nossa referencia tal como o DPO a aceita (alfanumerica, ate 100)."""
    return re.sub(r"[^A-Za-z0-9\-]", "", reference or "")[:100]


def _nome(buyer_name: str) -> tuple[str, str]:
    partes = (buyer_name or "").strip().split()
    if not partes:
        return "Passageiro", "BuzUp"
    return partes[0], (" ".join(partes[1:]) or partes[0])


class DpoCardGateway:
    """O contrato dos outros gateways, com o redirect por cima."""

    provider = PROVIDER

    def __init__(self, config: DpoConfig | None = None):
        self.config = config or _config()

    # ----- iniciar --------------------------------------------------------

    def initiate_payment(self, reference: str, amount, payer_phone: str, description: str = "",
                         *, redirect_url: str = "", back_url: str = "",
                         buyer_name: str = "", buyer_email: str = "",
                         service_date=None) -> PaymentGatewayResult:
        if not self.config.configured:
            return PaymentGatewayResult(
                success=False, provider=PROVIDER,
                error="Pagamento por cartao nao esta configurado.",
                detail_message="Pagamento por cartao indisponivel. Use M-Pesa ou e-Mola.",
            )
        # Mesma guarda do M-Pesa: producao nao pode "cobrar" pelo sandbox, que
        # aceita qualquer cartao e da tudo por pago.
        if usando_sandbox_dpo(self.config) and not getattr(settings, "PAYMENTS_ALLOW_SANDBOX", False):
            logger.error("[PAY][sandbox_em_producao] provider=DPO url=%s — venda recusada", self.config.api_url)
            return PaymentGatewayResult(
                success=False, provider=PROVIDER,
                error="Pagamentos por cartao indisponiveis: o sistema esta ligado ao simulador.",
                detail_message="Pagamentos por cartao indisponiveis. Contacte o administrador.",
            )

        primeiro, ultimo = _nome(buyer_name)
        quando = service_date or timezone.localtime()
        body = _xml("API3G", [
            ("CompanyToken", self.config.company_token),
            ("Request", "createToken"),
            ("Transaction", [
                ("PaymentAmount", f"{Decimal(str(amount)):.2f}"),
                ("PaymentCurrency", self.config.currency),
                ("CompanyRef", _company_ref(reference)),
                ("RedirectURL", redirect_url),
                ("BackURL", back_url or redirect_url),
                # Referencia UNICA: repetir o createToken para o mesmo
                # pagamento nao pode criar uma segunda transaccao.
                ("CompanyRefUnique", "1"),
                ("PTL", str(self.config.ptl_minutes)),
                ("PTLtype", "minutes"),
                ("customerFirstName", primeiro),
                ("customerLastName", ultimo),
                ("customerPhone", re.sub(r"\D", "", payer_phone or "")),
                ("customerEmail", buyer_email or None),
            ]),
            ("Services", [("Service", [
                ("ServiceType", self.config.service_type),
                ("ServiceDescription", (description or "Bilhete BuzUp")[:200]),
                ("ServiceDate", quando.strftime("%Y/%m/%d %H:%M")),
            ])]),
        ])
        status_code, payload = _post_xml(self.config.api_url, body, self.config.timeout)
        pedido = {"CompanyRef": _company_ref(reference), "PaymentAmount": f"{Decimal(str(amount)):.2f}",
                  "PaymentCurrency": self.config.currency, "RedirectURL": redirect_url}

        token = payload.get("TransToken", "")
        if status_code == 200 and payload.get("Result") == RESULT_PAID and token:
            return PaymentGatewayResult(
                success=False, pending=True, provider=PROVIDER,
                provider_reference=token,
                redirect_url=f"{self.config.payment_url}{token}",
                detail_message="Vai ser encaminhado para a pagina segura de pagamento.",
                request_payload=pedido, response_payload=payload, status_code=status_code,
                supports_query=True,
            )

        detalhe = payload.get("ResultExplanation") or payload.get("detail") or "Nao foi possivel iniciar o pagamento por cartao."
        logger.warning("[PAY][dpo] createToken falhou status=%s result=%s: %s",
                       status_code, payload.get("Result"), detalhe)
        return PaymentGatewayResult(
            success=False, pending=False, provider=PROVIDER,
            error=detalhe, detail_message=detalhe,
            request_payload=pedido, response_payload=payload, status_code=status_code,
        )

    # ----- consultar ------------------------------------------------------

    def query_payment(self, transaction_token: str) -> PaymentGatewayResult:
        """`verifyToken`: o unico sitio onde se aprende se houve dinheiro."""
        if not self.config.configured:
            return PaymentGatewayResult(success=False, provider=PROVIDER, error="Query not supported.")
        if not transaction_token:
            return PaymentGatewayResult(success=False, pending=True, provider=PROVIDER,
                                        detail_message="Sem token para consultar.")

        body = _xml("API3G", [
            ("CompanyToken", self.config.company_token),
            ("Request", "verifyToken"),
            ("TransactionToken", transaction_token),
        ])
        status_code, payload = _post_xml(self.config.api_url, body, self.config.timeout)
        return interpretar_verify(payload, status_code, transaction_token)


def interpretar_verify(payload: dict, status_code: int, token: str) -> PaymentGatewayResult:
    """O `Result` do verifyToken em sucesso / pendente / falha.

    Separado do gateway para se testar com as respostas reais sem rede.
    """
    result = str(payload.get("Result", "")).strip()
    if status_code != 200 or not result:
        # Sem resposta util (timeout nosso, 5xx, corpo sem XML): nao se decide.
        return PaymentGatewayResult(
            success=False, pending=True, provider=PROVIDER, provider_reference=token,
            detail_message="Sem resposta do operador de cartoes; volta a tentar-se.",
            response_payload=payload, status_code=status_code,
        )
    if result == RESULT_PAID:
        # A referencia que fica gravada e a do DPO, que e o que aparece no
        # extracto deles — o token e nosso ponto de partida, nao o deles.
        ref = payload.get("TransactionRef") or payload.get("TransID") or token
        return PaymentGatewayResult(
            success=True, provider=PROVIDER, provider_reference=ref,
            detail_message="Pagamento por cartao confirmado.",
            response_payload=payload, status_code=status_code,
        )
    if result == RESULT_NOT_PAID:
        return PaymentGatewayResult(
            success=False, pending=True, provider=PROVIDER, provider_reference=token,
            detail_message="Pagamento por cartao ainda nao concluido.",
            response_payload=payload, status_code=status_code,
        )
    if result in RESULTS_FAILED:
        return PaymentGatewayResult(
            success=False, pending=False, provider=PROVIDER, provider_reference=token,
            error=RESULTS_FAILED[result],
            detail_message=payload.get("ResultExplanation") or RESULTS_FAILED[result],
            response_payload=payload, status_code=status_code,
        )
    # Codigo que nao conhecemos: fica pendente e fica no log, para se
    # acrescentar a lista com conhecimento de causa.
    logger.warning("[PAY][dpo] verifyToken com Result desconhecido=%s token=%s", result, token)
    return PaymentGatewayResult(
        success=False, pending=True, provider=PROVIDER, provider_reference=token,
        detail_message=payload.get("ResultExplanation") or "Estado do pagamento por cartao desconhecido.",
        response_payload=payload, status_code=status_code,
    )
