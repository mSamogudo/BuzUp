"""Segundo factor do portal: criacao do desafio e envio do codigo."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.users.models import PortalLoginChallenge
from apps.users.otp import OTP_TTL_MINUTES, generate_otp


def mascarar_telefone(telefone: str) -> str:
    """`258841234567` -> `+258 84 *** 4567`.

    Diz ao utilizador para onde foi o codigo sem publicar o numero inteiro a
    quem so acertou na senha.
    """
    digitos = "".join(ch for ch in str(telefone or "") if ch.isdigit())
    if len(digitos) < 6:
        return "***"
    return f"+{digitos[:3]} {digitos[3:5]} *** {digitos[-4:]}"


def criar_desafio_portal(utilizador, telefone: str, request=None) -> PortalLoginChallenge:
    """Fecha desafios pendentes e cria um novo, com o codigo enviado por SMS.

    Fechar os anteriores importa: sem isso, um codigo pedido ha dez minutos
    continuava a servir, e pedir um codigo novo passava a ser uma forma de
    somar tentativas em vez de as gastar.
    """
    PortalLoginChallenge.objects.filter(
        user=utilizador, status=PortalLoginChallenge.Status.PENDING,
    ).update(status=PortalLoginChallenge.Status.EXPIRED, updated_at=timezone.now())

    codigo, code_hash = generate_otp()
    ip = None
    if request is not None:
        try:
            from apps.audit.services import client_ip
            ip = client_ip(request) or None
        except Exception:
            ip = None

    desafio = PortalLoginChallenge.objects.create(
        user=utilizador,
        code_hash=code_hash,
        phone=telefone,
        expires_at=timezone.now() + timedelta(minutes=OTP_TTL_MINUTES),
        ip_address=ip,
    )

    from apps.sms.services.sender import send_sms
    send_sms(
        telefone,
        f"BuzUp: codigo de acesso ao portal {codigo}. Valido {OTP_TTL_MINUTES} minutos. "
        "Se nao foi voce, mude a senha.",
        purpose="PORTAL_2FA",
    )
    return desafio
