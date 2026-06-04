from decimal import Decimal
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("trips", "0005_agent"),
    ]

    operations = [
        migrations.CreateModel(
            name="AgentDayClose",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("closed_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("date", models.DateField(db_index=True)),
                ("total_revenue", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("sales_total", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("topups_total", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("validations_revenue", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("tickets_count", models.PositiveIntegerField(default=0)),
                ("validations_count", models.PositiveIntegerField(default=0)),
                ("confirmed_count", models.PositiveIntegerField(default=0)),
                ("pending_count", models.PositiveIntegerField(default=0)),
                ("failed_count", models.PositiveIntegerField(default=0)),
                ("sessions_closed", models.PositiveIntegerField(default=0)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("agent_user", models.ForeignKey(on_delete=models.deletion.PROTECT, related_name="day_closes", to=settings.AUTH_USER_MODEL)),
                ("agent_profile", models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="day_closes", to="trips.agent")),
            ],
            options={
                "ordering": ("-closed_at",),
            },
        ),
        migrations.AddIndex(
            model_name="agentdayclose",
            index=models.Index(fields=["agent_user", "date"], name="adc_agent_date_idx"),
        ),
        migrations.AddIndex(
            model_name="agentdayclose",
            index=models.Index(fields=["date", "agent_user"], name="adc_date_agent_idx"),
        ),
    ]
