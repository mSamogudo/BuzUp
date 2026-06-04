from django.db import migrations


def seed_driver_role(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    Role.objects.get_or_create(
        code="driver",
        defaults={
            "name": "Motorista",
            "permissions": [],
            "description": "Motorista de autocarro com acesso ao portal de actividades.",
            "is_system": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_otpchallenge"),
    ]

    operations = [
        migrations.RunPython(seed_driver_role, migrations.RunPython.noop),
    ]
