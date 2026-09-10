"""Reenvia SMS que falharam por causa do provedor.

Uma falha no envio era definitiva: o bilhete ficava emitido, o pagamento
confirmado, e o passageiro nunca recebia o link. O caso mais grave é quem
compra sem smartphone e depende do SMS para ter o bilhete — fica sem nada,
tendo pago.

Só reenvia o que vale a pena reenviar. Um número inválido não melhora com
tentativas; um provedor que devolveu 500 ou não respondeu, sim.

Correr a cada 10 minutos:
    python manage.py retry_failed_sms
"""

from __future__ import annotations

import re
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.sms.models import SmsMessage
from apps.sms.services.sender import send_sms

# Erros nossos, escritos antes de haver pedido nenhum ao provedor.
ERROS_NOSSOS = ("missing_phone", "missing_sender_id")

# O provedor RESPONDEU a dizer que o destinatário não presta. Repetir dá o
# mesmo, sempre.
#
# Lê-se o `response_body`, e não o `error`: a `send_sms` só escreve `error`
# nas falhas ANTERIORES ao pedido; quando o provedor recusa, o que fica é o
# corpo da resposta dele. A lista antiga era `("missing_phone",
# "invalid_msisdn")` e o `invalid_msisdn` não era escrito em lado nenhum —
# nunca batia certo com nada.
#
# A Bluteki responde em português e com HTTP 500, não 400:
#   {"success":false,"message":"Internal error: Número de telefone inválido: 078229722"}
MARCAS_DE_DESTINO_INVALIDO = (
    "telefone inv", "telefone invál", "número inválido", "numero invalido",
    "invalid phone", "invalid msisdn", "invalid number", "invalid recipient",
    "destinatário inválido", "destinatario invalido", "not a valid",
)

# Um número móvel moçambicano: 84/85 (Vodacom), 86/87 (Movitel/Tmcel), mais
# sete dígitos. Com ou sem o indicativo 258.
PADRAO_MSISDN = re.compile(r"^(?:258)?8[4-7]\d{7}$")

DEFAULT_MAX_ATTEMPTS = 3
# Passada essa janela, o SMS já não tem utilidade prática (a viagem foi ou o
# código de OTP expirou há muito) e reenviar só confunde quem o recebe.
DEFAULT_WINDOW_HOURS = 12


def falha_definitiva(sms) -> tuple[bool, str]:
    """Uma segunda tentativa muda alguma coisa? Devolve `(sim, motivo)`.

    Repetir só faz sentido quando a falha foi do CAMINHO — o provedor não
    respondeu, deu 500 genérico, a rede caiu. Quando ele respondeu a dizer que
    o destinatário não presta, a resposta será a mesma daqui a dez minutos e
    daqui a dez dias.
    """
    md = sms.metadata or {}

    erro = str(md.get("error") or "")
    if erro in ERROS_NOSSOS:
        return True, erro

    # Número que nunca podia ter sido enviado. `078229722` — nove dígitos
    # começados por zero — foi o que encheu a fila; nenhuma operadora
    # moçambicana o aceita.
    numero = re.sub(r"\D", "", str(sms.phone_number or ""))
    if not PADRAO_MSISDN.match(numero):
        return True, "msisdn_invalido"

    corpo = str(md.get("response_body") or "").lower()
    if any(m in corpo for m in MARCAS_DE_DESTINO_INVALIDO):
        return True, "destino_recusado"

    # 4xx é "o teu pedido está mal" — repeti-lo igual dá igual. Excepto 408
    # (esgotou o tempo) e 429 (devagar), que são convites a tentar de novo.
    estado = int(md.get("response_status") or 0)
    if 400 <= estado < 500 and estado not in (408, 429):
        return True, f"http_{estado}"

    return False, ""


class Command(BaseCommand):
    help = "Reenvia SMS falhados por erro transitorio do provedor."

    def add_arguments(self, parser):
        parser.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
        parser.add_argument("--window-hours", type=int, default=DEFAULT_WINDOW_HOURS)
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=options["window_hours"])
        candidates = list(
            SmsMessage.objects
            .filter(
                status=SmsMessage.Status.FAILED,
                created_at__gte=cutoff,
                attempts__lt=options["max_attempts"],
            )
            # Uma tentativa de reenvio que também falhou NÃO volta a ser
            # candidata. Sem isto, cada reenvio falhado criava um registo novo
            # com `attempts=0` — e a fila alimentava-se a si própria em vez de
            # drenar. A 2026-09-10 estavam 100 mensagens a ser tentadas de 10
            # em 10 minutos, indefinidamente, sem nenhuma ser entregue.
            .exclude(metadata__has_key="retry_of")
            .order_by("created_at")[:options["limit"]]
        )

        skipped = resent = recovered = 0
        for sms in candidates:
            definitiva, motivo = falha_definitiva(sms)
            if definitiva:
                skipped += 1
                # Marcar como esgotado para não voltar a aparecer na procura,
                # e deixar escrito PORQUÊ — senão, daqui a um mês, ninguém
                # sabe se foi decisão ou acidente.
                sms.attempts = options["max_attempts"]
                sms.metadata = {**(sms.metadata or {}), "falha_definitiva": motivo}
                sms.save(update_fields=["attempts", "metadata"])
                continue

            if options["dry_run"]:
                resent += 1
                continue

            new_sms = send_sms(
                sms.phone_number,
                sms.body,
                purpose=sms.purpose,
                metadata={
                    **(sms.metadata or {}),
                    "retry_of": sms.pk,
                    "retry_attempt": sms.attempts + 1,
                },
            )
            resent += 1
            if new_sms.status == SmsMessage.Status.SENT:
                recovered += 1
                # O original deixa de ser um problema em aberto, mas fica como
                # registo de que houve falha — a auditoria de entrega precisa
                # de ver as duas linhas.
                sms.metadata = {**(sms.metadata or {}), "recovered_by": new_sms.pk}
            sms.attempts += 1
            sms.save(update_fields=["attempts", "metadata"])

        line = (
            f"candidatos={len(candidates)} reenviados={resent} "
            f"entregues={recovered} permanentes={skipped}"
        )
        if options["dry_run"]:
            self.stdout.write(f"[dry-run] {line}")
        elif recovered < resent:
            self.stdout.write(self.style.WARNING(line))
        else:
            self.stdout.write(self.style.SUCCESS(line))
