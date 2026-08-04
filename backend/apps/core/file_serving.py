"""Entrega de ficheiros grandes sem ocupar um worker do gunicorn.

Um APK tem ~40 MB. Servido pelo Django, o worker fica preso durante todo o
download — e o `--timeout` do gunicorn (120s) mata-o a meio quando o telefone
está numa ligação fraca, entregando um ficheiro truncado que a app rejeita.
Pior: o staging corre 2 workers *sync*; dois downloads lentos ao mesmo tempo
param a API inteira — vendas, validações e pagamentos incluídos.

`X-Accel-Redirect` resolve as duas coisas: o Django valida as permissões e
responde num milissegundo com um cabeçalho; quem envia os bytes é o nginx,
que é feito para isso e aguenta clientes lentos sem custo. De caminho, o
nginx serve pedidos `Range`, portanto um download interrompido retoma em vez
de recomeçar — o que numa rede móvel moçambicana não é detalhe.

Fora do nginx (runserver, testes) cai no `FileResponse` de sempre.
"""

from __future__ import annotations

from urllib.parse import quote

from django.conf import settings
from django.http import FileResponse, HttpResponse

# Prefixo `internal` no nginx: não é alcançável de fora, só através do
# cabeçalho que esta função devolve.
INTERNAL_MEDIA_PREFIX = "/protected-media/"


def _x_accel_enabled() -> bool:
    """Há um nginx à frente capaz de honrar o cabeçalho?

    Ligado por omissão em produção/staging (onde o gateway monta o volume de
    media) e desligado no `dev`, onde o Django serve sozinho.
    """
    return bool(getattr(settings, "USE_X_ACCEL_REDIRECT", False))


def serve_file_field(file_field, *, filename: str, content_type: str,
                     cache_control: str = "no-store") -> HttpResponse:
    """Devolve `file_field` ao cliente, pelo nginx quando possível."""
    disposition = f'attachment; filename="{filename}"'
    # RFC 5987 para nomes com acentos; os APKs não têm, mas isto também serve
    # relatórios e bilhetes.
    if any(ord(ch) > 127 for ch in filename):
        disposition += f"; filename*=UTF-8''{quote(filename)}"

    if _x_accel_enabled():
        response = HttpResponse(status=200)
        # `file_field.name` é o caminho relativo ao MEDIA_ROOT
        # (ex. "app-releases/buzup-pos-1.4.3-universal.apk").
        response["X-Accel-Redirect"] = INTERNAL_MEDIA_PREFIX + quote(file_field.name)
        # O nginx precisa de calcular o Content-Length a partir do ficheiro;
        # um Content-Length a zero vindo daqui truncava a resposta.
        del response["Content-Length"]
        response["Content-Type"] = content_type
    else:
        response = FileResponse(file_field.open("rb"), content_type=content_type)

    response["Content-Disposition"] = disposition
    response["Cache-Control"] = cache_control
    return response
