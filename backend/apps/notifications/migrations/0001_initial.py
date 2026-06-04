import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("kind", models.CharField(choices=[
                    ("payment_confirmed", "Pagamento Confirmado"),
                    ("payment_failed", "Pagamento Falhado"),
                    ("ticket_issued", "Bilhete Emitido"),
                    ("trip_update", "Actualizacao de Viagem"),
                    ("card_update", "Actualizacao de Cartao"),
                    ("system", "Sistema"),
                ], max_length=32)),
                ("title", models.CharField(max_length=255)),
                ("body", models.TextField(blank=True)),
                ("data", models.JSONField(blank=True, default=dict)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name="notifications",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["user", "read_at"], name="notifications_user_read_idx"),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["user", "kind"], name="notifications_user_kind_idx"),
        ),
    ]
