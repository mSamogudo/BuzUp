import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


def seed_default_fees(apps, schema_editor):
    AdminFee = apps.get_model("fares", "AdminFee")
    defaults = [
        {
            "code": "card-issuance-default",
            "name": "Taxa de adesao de cartao",
            "kind": "card_issuance",
            "amount": Decimal("50.00"),
            "description": "Cobrada ao passageiro na emissao de novo cartao fisico.",
        },
        {
            "code": "card-recovery-default",
            "name": "Taxa de recuperacao de cartao",
            "kind": "card_recovery",
            "amount": Decimal("100.00"),
            "description": "Cobrada ao passageiro quando o cartao fisico e perdido / substituido.",
        },
    ]
    for d in defaults:
        AdminFee.objects.get_or_create(code=d["code"], defaults=d)


def unseed(apps, schema_editor):
    AdminFee = apps.get_model("fares", "AdminFee")
    AdminFee.objects.filter(code__in=[
        "card-issuance-default", "card-recovery-default",
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("fares", "0002_fare_rule_distance_range"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminFee",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("code", models.SlugField(max_length=32, unique=True)),
                ("name", models.CharField(max_length=128)),
                ("kind", models.CharField(max_length=24, choices=[
                    ("card_issuance", "Taxa de adesao de cartao"),
                    ("card_recovery", "Taxa de recuperacao de cartao"),
                    ("fine", "Multa"),
                    ("other", "Outra"),
                ])),
                ("amount", models.DecimalField(
                    max_digits=10, decimal_places=2,
                    validators=[MinValueValidator(Decimal("0.00"))],
                )),
                ("currency", models.CharField(default="MZN", max_length=3)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ("kind", "name"),
                "indexes": [models.Index(fields=["kind", "is_active"], name="adminfee_kind_idx")],
            },
        ),
        migrations.RunPython(seed_default_fees, unseed),
    ]
