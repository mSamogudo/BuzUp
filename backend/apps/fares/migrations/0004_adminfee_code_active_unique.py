# Drop the plain unique on AdminFee.code and replace it with a partial unique
# scoped to active (non-soft-deleted) rows, so a code freed by a soft-delete
# can be reused. Intentionally surgical: it does NOT carry the unrelated
# BaseModel index/field drift that makemigrations also detected.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fares', '0003_admin_fee'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adminfee',
            name='code',
            field=models.SlugField(max_length=32),
        ),
        migrations.AddConstraint(
            model_name='adminfee',
            constraint=models.UniqueConstraint(
                condition=models.Q(('deleted_at__isnull', True)),
                fields=('code',),
                name='uq_admin_fee_code_active',
            ),
        ),
    ]
