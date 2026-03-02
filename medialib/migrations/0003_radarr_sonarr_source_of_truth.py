from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("medialib", "0002_delete_orphan_rows"),
    ]

    operations = [
        # Movie: plex_rating_key → nullable, not unique
        migrations.AlterField(
            model_name="movie",
            name="plex_rating_key",
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        # Movie: radarr_id → required, unique
        migrations.AlterField(
            model_name="movie",
            name="radarr_id",
            field=models.IntegerField(unique=True),
        ),
        # Series: plex_rating_key → nullable, not unique
        migrations.AlterField(
            model_name="series",
            name="plex_rating_key",
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        # Series: sonarr_id → required, unique
        migrations.AlterField(
            model_name="series",
            name="sonarr_id",
            field=models.IntegerField(unique=True),
        ),
    ]
