import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("agent_api", "0001_initial"),
        ("passengers", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RecoverySession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("challenge_id", models.CharField(db_index=True, max_length=64, unique=True)),
                ("phone", models.CharField(db_index=True, max_length=20)),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("code_hash", models.CharField(max_length=128)),
                ("status", models.CharField(choices=[
                    ("pending", "Pendente"), ("verified", "Verificada"),
                    ("consumed", "Consumida"), ("expired", "Expirada"),
                ], default="pending", max_length=16)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("expires_at", models.DateTimeField()),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("recovery_token", models.CharField(blank=True, db_index=True, max_length=64)),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                ("agent_user", models.ForeignKey(
                    on_delete=models.deletion.PROTECT,
                    related_name="recovery_sessions",
                    to=settings.AUTH_USER_MODEL)),
                ("passenger", models.ForeignKey(
                    on_delete=models.deletion.PROTECT,
                    related_name="recovery_sessions",
                    to="passengers.passengeraccount")),
            ],
            options={
                "ordering": ("-created_at",),
                "indexes": [
                    models.Index(fields=["status", "expires_at"], name="recov_status_idx"),
                    models.Index(fields=["recovery_token"], name="recov_token_idx"),
                ],
            },
        ),
    ]
