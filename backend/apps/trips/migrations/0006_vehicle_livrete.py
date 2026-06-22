from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("trips", "0005_agent"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicle",
            name="livrete",
            field=models.FileField(blank=True, upload_to="vehicles/livrete/"),
        ),
    ]
