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

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.sms.models import SmsMessage
from apps.sms.services.sender import send_sms

# Erros que não melhoram com uma segunda tentativa.
PERMANENT_ERRORS = ("missing_phone", "invalid_msisdn")

DEFAULT_MAX_ATTEMPTS = 3
# Passada essa janela, o SMS já não tem utilidade prática (a viagem foi ou o
# código de OTP expirou há muito) e reenviar só confunde quem o recebe.
DEFAULT_WINDOW_HOURS = 12


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
            .order_by("created_at")[:options["limit"]]
        )

        skipped = resent = recovered = 0
        for sms in candidates:
            error = str((sms.metadata or {}).get("error") or "")
            if any(perm in error for perm in PERMANENT_ERRORS):
                skipped += 1
                # Marcar como esgotado para não voltar a aparecer na procura.
                sms.attempts = options["max_attempts"]
                sms.save(update_fields=["attempts"])
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
