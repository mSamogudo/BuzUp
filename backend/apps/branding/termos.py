"""Aceitacao dos Termos e Condicoes, no acto da compra.

A regra vive aqui e nao em cada vista porque ha mais do que uma porta para
comprar um bilhete — o site publico, a app por carteira, a app por M-Pesa. Cada
copia da regra e uma porta que um dia deixa de a aplicar.

Guarda-se a VERSAO e nao apenas um sim: sem ela sabia-se que o passageiro
aceitou "os termos", mas nao QUAIS, e uns termos alterados na semana seguinte
passariam a valer para tras. Numa disputa sobre um cancelamento ou uma bagagem,
e a versao que diz o que estava escrito nesse dia.
"""

from __future__ import annotations

from django.utils import timezone


class TermosNaoAceites(Exception):
    """A compra nao pode seguir: falta aceitar, ou aceitou-se outra versao."""

    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def registar_aceitacao(*, aceitou: bool, versao_enviada: str = "") -> tuple:
    """(quando, versao) para gravar na compra.

    Devolve `(None, "")` quando o operador ainda nao publicou termos — nao se
    inventa uma barreira onde ele nao pos nenhuma.
    """
    from apps.branding.models import BrandingSettings

    marca = BrandingSettings.load()
    if not marca.has_terms:
        return None, ""

    if not aceitou:
        raise TermosNaoAceites(
            "Aceite os Termos e Condicoes para concluir a compra."
        )

    enviada = (versao_enviada or "").strip()
    # Versao diferente da publicada: o passageiro tem a pagina (ou o ecra)
    # aberto desde antes de os termos mudarem. Aceitou outra coisa.
    if enviada and marca.terms_version and enviada != marca.terms_version:
        raise TermosNaoAceites(
            "Os Termos e Condicoes foram actualizados. Recarregue e leia a "
            "versao em vigor.",
            status_code=409,
        )

    return timezone.now(), marca.terms_version or ""
