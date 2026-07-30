"""Fecha o que expirou: checkouts, intenções de pagamento e pacotes.

Sem isto, um checkout que ficou em `payment_pending` (o passageiro fechou o
browser, o gateway nunca respondeu) continua a ocupar lugar na viagem e a
aparecer no painel como pagamento a decorrer — indistinguível de um pagamento
real em curso. E as subscrições de pacote expiradas continuavam a ser
encontradas por `find_active_package_for_route` até alguém as tocar à mão.

Correr a cada 5 minutos (cron/systemd timer):
    python manage.py expire_stale
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.guest_checkouts.models import GuestCheckout
from apps.packages.services import expire_subscriptions
from apps.payments.models import PaymentIntent


class Command(BaseCommand):
    help = "Expira checkouts, intencoes de pagamento e subscricoes vencidas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Mostra o que seria expirado sem gravar.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        dry = options["dry_run"]

        stale_checkouts = GuestCheckout.objects.filter(
            status=GuestCheckout.Status.PAYMENT_PENDING,
            expires_at__lt=now,
        )
        stale_intents = PaymentIntent.objects.filter(
            status=PaymentIntent.Status.PENDING,
            expires_at__lt=now,
        )
        n_checkouts = stale_checkouts.count()
        n_intents = stale_intents.count()

        if dry:
            self.stdout.write(
                f"[dry-run] checkouts={n_checkouts} intents={n_intents}"
            )
            return

        with transaction.atomic():
            # Ordem importa: expirar a intenção antes do checkout evita uma
            # janela em que o checkout já está EXPIRED e um webhook atrasado
            # ainda encontra a intenção PENDING e tenta emitir o bilhete.
            stale_intents.update(status=PaymentIntent.Status.EXPIRED, updated_at=now)
            stale_checkouts.update(status=GuestCheckout.Status.EXPIRED, updated_at=now)

        n_packages = expire_subscriptions()

        self.stdout.write(self.style.SUCCESS(
            f"expirados: checkouts={n_checkouts} intents={n_intents} pacotes={n_packages}"
        ))
