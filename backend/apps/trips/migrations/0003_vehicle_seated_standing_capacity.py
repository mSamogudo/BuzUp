from django.db import migrations, models


def copy_capacity_to_seated(apps, schema_editor):
    Vehicle = apps.get_model("trips", "Vehicle")
    for v in Vehicle.objects.all():
        v.seated_capacity = v.capacity
        v.save(update_fields=["seated_capacity"])


class Migration(migrations.Migration):

    dependencies = [
        ("trips", "0002_routeschedule_trip_schedule"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicle",
            name="seated_capacity",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="vehicle",
            name="standing_capacity",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(copy_capacity_to_seated, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="vehicle",
            name="capacity",
        ),
    ]
