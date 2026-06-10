from __future__ import annotations

import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)

# Headers a partir dos quais aceitamos a prova de autenticidade do webhook.
# (META usa o prefixo HTTP_ e maiusculas com underscores.)
_SIGNATURE_HEADERS = ("HTTP_X_WEBHOOK_SIGNATURE", "HTTP_X_SIGNATURE", "HTTP_X_HUB_SIGNATURE_256")
_TOKEN_HEADERS = ("HTTP_X_WEBHOOK_TOKEN", "HTTP_X_WEBHOOK_SECRET", "HTTP_X_API_KEY")


def _const_eq(a: str, b: str) -> bool:
    """Comparacao em tempo constante (evita timing-attacks no token)."""
    return hmac.compare_digest(str(a or ""), str(b or ""))


def verify_webhook_signature(request, secret: str) -> tuple[bool, str]:
    """Confirma que o callback de pagamento veio mesmo do provedor.

    Aceita, por ordem de forca:
      1) HMAC-SHA256 do corpo cru num header de assinatura (prova criptografica);
      2) token partilhado num header dedicado;
      3) token partilhado no query-string (?token=...), para provedores que so
         permitem configurar o URL de callback (ex.: dashboard do Payless).

    Devolve ``(ok, metodo)``. Sem ``secret`` configurado devolve ``(False, "no-secret")``.
    """
    if not secret:
        return False, "no-secret"

    # 1) HMAC do corpo cru — a prova mais forte (so o detentor do segredo a produz).
    try:
        raw_body = request.body or b""
    except Exception:  # pragma: no cover - corpo ja consumido sem cache
        raw_body = b""
    expected_hmac = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    for header in _SIGNATURE_HEADERS:
        provided = request.META.get(header, "")
        if provided:
            # alguns provedores prefixam o algoritmo: "sha256=<hex>"
            candidate = provided.split("=", 1)[1] if "=" in provided else provided
            if _const_eq(candidate.lower(), expected_hmac.lower()):
                return True, "hmac"

    # 2) token partilhado em header dedicado
    for header in _TOKEN_HEADERS:
        provided = request.META.get(header, "")
        if provided and _const_eq(provided, secret):
            return True, "token-header"

    # 3) token partilhado no query-string (fallback p/ URL de callback)
    provided = request.GET.get("token", "") or request.GET.get("secret", "")
    if provided and _const_eq(provided, secret):
        return True, "token-query"

    return False, "invalid"
