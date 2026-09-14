"""Pergunta a operadora se algum pagamento dado como falhado foi afinal cobrado.

A reconciliacao normal so olha para os PENDENTES. Um pagamento marcado FAILED
nunca mais e olhado — e "falhado" nem sempre quer dizer "nao pago": ate
2026-09-10 o nosso proprio timeout marcava assim, com a operadora a debitar o
passageiro nesse momento.

A 2026-09-14 uma auditoria a mao encontrou dois casos: 1.650 MZN e 3.300 MZN,
cobrados, sem bilhete, 17 e 14 dias sem ninguem dar por nada. Este comando e
essa auditoria feita sozinha.

Correr uma vez por dia:
    python manage.py auditar_pagamentos_falhados
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.payments.services.reconciliation import (
    DIAS_A_REVER,
    auditar_pagamentos_falhados,
)


class Command(BaseCommand):
    help = "Procura pagamentos dados como falhados que a operadora diz ter cobrado."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dias", type=int, default=DIAS_A_REVER,
            help=f"Quantos dias para tras rever (default: {DIAS_A_REVER}).",
        )
        parser.add_argument(
            "--limit", type=int, default=100,
            help="Maximo de consultas a operadora por execucao (default: 100).",
        )

    def handle(self, *args, **options):
        report = auditar_pagamentos_falhados(dias=options["dias"], limit=options["limit"])
        linha = report.as_line()

        if report.pagos_sem_bilhete:
            # Nao e um aviso: e dinheiro de alguem parado no sistema.
            self.stdout.write(self.style.ERROR(linha))
        elif report.erros:
            self.stdout.write(self.style.WARNING(linha))
        else:
            self.stdout.write(self.style.SUCCESS(linha))

        for erro in report.erros[:10]:
            self.stdout.write(self.style.ERROR(f"  {erro}"))
