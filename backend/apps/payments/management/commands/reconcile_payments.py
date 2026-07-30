"""Pergunta ao gateway o que aconteceu aos pagamentos que ficaram pendentes.

Sem isto, um webhook perdido (rede móvel a oscilar) significa que o passageiro
pagou e nunca recebe bilhete — e ninguém repara.

Correr a cada 5 minutos:
    python manage.py reconcile_payments
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.payments.services.reconciliation import (
    DEFAULT_MIN_AGE_MINUTES,
    reconcile_pending_payments,
)


class Command(BaseCommand):
    help = "Reconcilia pagamentos pendentes consultando o gateway."

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-age-minutes", type=int, default=DEFAULT_MIN_AGE_MINUTES,
            help=(
                "Idade minima do pagamento para ser consultado. Um pagamento "
                "acabado de iniciar esta legitimamente pendente enquanto o "
                f"passageiro digita o PIN (default: {DEFAULT_MIN_AGE_MINUTES})."
            ),
        )
        parser.add_argument(
            "--limit", type=int, default=200,
            help="Maximo de pagamentos por execucao (default: 200).",
        )

    def handle(self, *args, **options):
        report = reconcile_pending_payments(
            min_age_minutes=options["min_age_minutes"],
            limit=options["limit"],
        )

        line = report.as_line()
        if report.needs_review or report.errors:
            self.stdout.write(self.style.WARNING(line))
        else:
            self.stdout.write(self.style.SUCCESS(line))

        for err in report.errors[:10]:
            self.stdout.write(self.style.ERROR(f"  {err}"))
