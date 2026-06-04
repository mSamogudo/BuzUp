from django.core.management.base import BaseCommand

from apps.core.permissions.base import DEFAULT_ROLES
from apps.users.models import Role


class Command(BaseCommand):
    help = "Seed default system roles."

    def handle(self, *args, **options):
        for code, data in DEFAULT_ROLES.items():
            role, created = Role.objects.get_or_create(
                code=code,
                defaults={
                    "name": data["name"],
                    "permissions": data["permissions"],
                    "is_system": True,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created role: {role.name}"))
            else:
                self.stdout.write(f"Role exists: {role.name}")
