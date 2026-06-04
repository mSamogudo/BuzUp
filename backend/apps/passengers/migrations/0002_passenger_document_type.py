from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("passengers", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="passengeraccount",
            name="document_type",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("bi", "B.I."),
                    ("passport", "Passaporte"),
                    ("driving_license", "Carta de Conducao"),
                ],
                blank=True,
                default="",
            ),
        ),
    ]
