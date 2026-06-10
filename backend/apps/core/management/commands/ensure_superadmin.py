from django.core.management.base import BaseCommand

from apps.users.models import User


class Command(BaseCommand):
    help = "Ensure at least one superadmin user exists."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--email", default="admin@buzup.co.mz")
        parser.add_argument("--password", default="admin")

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        password = options["password"]

        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.SUCCESS("Superadmin already exists."))
            return

        # NB: the custom User model has no `role` field (roles are M2M via
        # UserRole); passing role= here raised TypeError. is_superuser already
        # bypasses capability checks, so a plain superuser is enough for portal access.
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(self.style.SUCCESS(f"Superadmin '{username}' created."))
