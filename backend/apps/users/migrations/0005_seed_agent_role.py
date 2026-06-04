from django.db import migrations


def seed_agent_role(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    Role.objects.get_or_create(
        code="agent",
        defaults={
            "name": "Agente/Cobrador",
            "permissions": ["pos.operate", "validations.read"],
            "description": "Agente que opera POS para validacoes e recargas.",
            "is_system": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_seed_driver_role"),
    ]

    operations = [
        migrations.RunPython(seed_agent_role, migrations.RunPython.noop),
    ]
