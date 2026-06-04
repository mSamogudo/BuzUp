# Generated for Agent model + Trip.agent + RouteSchedule.agent

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('trips', '0004_driver_user_trip_activity_closed_at_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Agent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('full_name', models.CharField(max_length=255)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('status', models.CharField(choices=[('active', 'Activo'), ('inactive', 'Inactivo'), ('suspended', 'Suspenso')], default='active', max_length=16)),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='agent_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('full_name',),
            },
        ),
        migrations.AddField(
            model_name='trip',
            name='agent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='trips', to='trips.agent'),
        ),
        migrations.AddField(
            model_name='routeschedule',
            name='agent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='schedules', to='trips.agent'),
        ),
    ]
