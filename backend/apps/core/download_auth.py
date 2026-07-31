"""Autenticacao por bilhete de descarga, para as vistas que servem ficheiros.

Substitui as quatro copias de "aceitar o JWT em `?token=`" espalhadas pelo
backend. Ver `download_tokens.py` para o porque.
"""

from __future__ import annotations

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.download_tokens import InvalidDownloadTicket, resolve_download_ticket


def _legacy_jwt_allowed() -> bool:
    """O JWT no URL ainda e aceite?

    Fica ligado durante a transicao: ha apps instaladas que so sabem construir
    o link antigo, e desliga-lo hoje tirava-lhes o extracto em PDF. Passar a
    False assim que as versoes novas estiverem distribuidas — enquanto estiver
    True, o problema que os bilhetes resolvem continua de pe.
    """
    return bool(getattr(settings, "ALLOW_JWT_IN_QUERY_STRING", True))


class DownloadTicketAuthentication(BaseAuthentication):
    """Aceita `Authorization: Bearer`, senao `?t=<bilhete>` do `scope` da vista.

    A vista declara o seu ambito em `download_scope`; um bilhete emitido para
    outro ambito nao serve, para um link de QR nao poder ser trocado por um
    relatorio financeiro.
    """

    def authenticate(self, request):
        jwt_auth = JWTAuthentication()
        result = jwt_auth.authenticate(request)
        if result is not None:
            return result

        scope = getattr(getattr(request, "parser_context", {}).get("view", None),
                        "download_scope", "") or ""
        params = request.query_params if hasattr(request, "query_params") else request.GET

        ticket = params.get("t")
        if ticket:
            try:
                return (resolve_download_ticket(ticket, scope), None)
            except InvalidDownloadTicket as e:
                raise AuthenticationFailed(str(e)) from e

        legacy = params.get("token")
        if legacy and _legacy_jwt_allowed():
            validated = jwt_auth.get_validated_token(legacy)
            return (jwt_auth.get_user(validated), validated)
        return None
