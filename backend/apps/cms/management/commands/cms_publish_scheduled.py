"""Publica as publicacoes agendadas cuja hora ja passou.

Pensado para cron: `python manage.py cms_publish_scheduled` de minuto a minuto.
O caminho de leitura publica tem a mesma rede de seguranca (ver
`apps.cms.services.run_due_publications_throttled`), portanto o agendamento
funciona mesmo sem cron — o comando existe para o fazer em tempo previsivel.
"""

from django.core.management.base import BaseCommand

from apps.cms.services import run_due_publications


class Command(BaseCommand):
    help = "Publica o conteudo do CMS agendado para uma hora ja passada."

    def handle(self, *args, **options):
        done = run_due_publications()
        if not done:
            self.stdout.write("Nada agendado para agora.")
            return
        for job in done:
            self.stdout.write(f"{job.target_type}#{job.target_id}: {job.status} — {job.result}")
        self.stdout.write(self.style.SUCCESS(f"{len(done)} publicacoes tratadas."))
