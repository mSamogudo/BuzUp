from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BrandingSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("key", models.CharField(default="default", editable=False, max_length=32, unique=True)),
                ("platform_name", models.CharField(blank=True, default="BuzUp", max_length=120)),
                ("primary_logo", models.FileField(blank=True, upload_to="branding/")),
                ("sidebar_logo", models.FileField(blank=True, upload_to="branding/")),
                ("sidebar_mark", models.FileField(blank=True, upload_to="branding/")),
                ("auth_logo", models.FileField(blank=True, upload_to="branding/")),
                ("pos_logo", models.FileField(blank=True, upload_to="branding/")),
                ("mobile_logo", models.FileField(blank=True, upload_to="branding/")),
                ("report_logo", models.FileField(blank=True, upload_to="branding/")),
                ("powered_by_logo", models.FileField(blank=True, upload_to="branding/")),
                ("favicon", models.FileField(blank=True, upload_to="branding/")),
            ],
            options={
                "verbose_name": "Configuracao de marca",
                "verbose_name_plural": "Configuracao de marca",
            },
        ),
    ]
