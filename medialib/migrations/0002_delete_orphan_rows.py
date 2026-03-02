from django.db import migrations


def delete_orphans(apps, schema_editor):
    """Clear all rows — the new sync will rebuild from Radarr/Sonarr as source of truth."""
    Movie = apps.get_model("medialib", "Movie")
    Series = apps.get_model("medialib", "Series")
    Movie.objects.all().delete()
    Series.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("medialib", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(delete_orphans, migrations.RunPython.noop),
    ]
