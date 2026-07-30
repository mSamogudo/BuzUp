"""Tradutor de excepções de domínio em respostas HTTP legíveis.

Não havia `EXCEPTION_HANDLER` configurado: qualquer excepção que escapasse a
uma view virava 500 com corpo vazio. Num validador a bordo, um 500 lê-se como
"o sistema avariou" — o agente não sabe se deve deixar embarcar. A diferença
entre "erro de servidor" e "terminal bloqueado" ou "partida esgotada" é a
diferença entre parar a operação e resolver a situação.

Aqui traduzem-se as excepções que o nosso próprio código levanta, e registam-se
as que não são esperadas para que deixem de ser silenciosas.
"""

from __future__ import annotations

import logging

from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def buzup_exception_handler(exc, context):
    # Primeiro o tratamento normal do DRF (validação, permissões, 404…).
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    view = context.get("view").__class__.__name__ if context.get("view") else "?"

    # Terminal bloqueado: decisão administrativa, não avaria.
    from apps.agent_api.permissions import DeviceBlocked

    if isinstance(exc, DeviceBlocked):
        logger.info("terminal bloqueado recusado em %s", view)
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

    # Lotação: o agente tem de saber que a partida encheu, não que houve erro.
    from apps.guest_checkouts.capacity import SeatsUnavailable

    if isinstance(exc, SeatsUnavailable):
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    if isinstance(exc, IntegrityError):
        # Tipicamente uma corrida numa restrição de unicidade (chave de
        # idempotência, referência). 409 diz ao cliente que o pedido colidiu
        # com outro — repetir com a mesma chave é seguro, ao contrário do 500.
        logger.warning("IntegrityError em %s: %s", view, exc, exc_info=True)
        return Response(
            {"detail": "O pedido colidiu com outro em curso. Tente novamente."},
            status=status.HTTP_409_CONFLICT,
        )

    # Não reconhecida: deixa o Django devolver 500, mas com rasto. Sem isto (e
    # sem LOGGING) estes erros desapareciam por completo.
    logger.exception("excepcao nao tratada em %s", view)
    return None
