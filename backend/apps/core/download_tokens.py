"""Bilhetes de descarga: credenciais de uso unico para links que abrem ficheiros.

Um `<a href>` ou um `launchUrl()` nao leva cabecalho `Authorization`, por isso
os downloads (PDF, XLSX, QR PNG) passavam o **JWT de acesso** no URL. Um URL
nao e sitio para uma credencial: fica no log de acessos do nginx, no historico
do browser e em qualquer backup desses logs. Quem leia o log passa a poder agir
como aquele utilizador ate o token expirar — e o JWT de acesso da acesso a tudo
o que o utilizador pode fazer, nao so ao ficheiro que ele quis descarregar.

Um bilhete resolve as duas coisas: vale **poucos minutos** e vale **so para
aquele tipo de ficheiro**. Encontrado num log, ja expirou; se nao expirou, so
serve para repetir a mesma descarga.

Nao guarda estado: e um valor assinado com a SECRET_KEY, validado na hora.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core import signing

_SALT = "buzup.download.ticket"

# Tempo entre pedir o bilhete e o browser comecar a descarga. Curto de
# proposito: e um clique, nao uma sessao.
DEFAULT_MAX_AGE = 180


class InvalidDownloadTicket(Exception):
    """Bilhete em falta, adulterado, expirado ou de outro tipo de ficheiro."""


def make_download_ticket(user, scope: str) -> str:
    """Emite um bilhete para `user` descarregar ficheiros de `scope`."""
    if not scope:
        raise ValueError("scope obrigatorio")
    return signing.dumps({"u": user.pk, "s": scope}, salt=_SALT)


def resolve_download_ticket(ticket: str, scope: str, max_age: int = DEFAULT_MAX_AGE):
    """Devolve o utilizador do bilhete, se ele servir para `scope`.

    Levanta `InvalidDownloadTicket` em qualquer outro caso — incluindo um
    bilhete valido mas emitido para outro tipo de ficheiro, que senao seria uma
    forma de trocar um download de QR por um relatorio financeiro.
    """
    if not ticket:
        raise InvalidDownloadTicket("Bilhete em falta.")
    try:
        data = signing.loads(ticket, salt=_SALT, max_age=max_age)
    except signing.SignatureExpired as e:
        raise InvalidDownloadTicket("Bilhete expirado.") from e
    except signing.BadSignature as e:
        raise InvalidDownloadTicket("Bilhete invalido.") from e

    if data.get("s") != scope:
        raise InvalidDownloadTicket("Bilhete emitido para outro ficheiro.")

    user = get_user_model().objects.filter(pk=data.get("u"), is_active=True).first()
    if user is None:
        # Conta apagada ou desactivada depois de o bilhete ser emitido: um
        # bilhete nao pode sobreviver ao despedimento de quem o pediu.
        raise InvalidDownloadTicket("Utilizador sem acesso.")
    return user
