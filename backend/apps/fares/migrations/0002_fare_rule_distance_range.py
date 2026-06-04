from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fares", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="farerule",
            name="distance_min_km",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="farerule",
            name="distance_max_km",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddIndex(
            model_name="farerule",
            index=models.Index(fields=["route", "calculation_method", "passenger_class"], name="fare_rule_lookup_idx"),
        ),
    ]
