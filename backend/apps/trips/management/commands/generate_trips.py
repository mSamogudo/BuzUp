from django.core.management.base import BaseCommand

from apps.trips.services import generate_all_daily_trips


class Command(BaseCommand):
    help = "Generate daily trips from active route schedules."

    def handle(self, *args, **options):
        count = generate_all_daily_trips()
        self.stdout.write(self.style.SUCCESS(f"{count} viagens geradas."))
