from django.db import models


class Movie(models.Model):
    title = models.CharField(max_length=500)
    year = models.IntegerField(null=True, blank=True)
    plex_rating_key = models.CharField(max_length=100, unique=True)
    radarr_id = models.IntegerField(null=True, blank=True)
    imdb_id = models.CharField(max_length=20, null=True, blank=True)
    imdb_rating = models.FloatField(null=True, blank=True)
    added_at = models.DateTimeField(null=True, blank=True)
    watched = models.BooleanField(default=False)
    file_path = models.TextField(blank=True, default="")
    size_bytes = models.BigIntegerField(default=0)
    flagged = models.BooleanField(default=False)
    last_synced = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.year})"

    @property
    def size_display(self):
        if self.size_bytes >= 1_073_741_824:
            return f"{self.size_bytes / 1_073_741_824:.1f} GB"
        return f"{self.size_bytes / 1_048_576:.0f} MB"


class Series(models.Model):
    title = models.CharField(max_length=500)
    year = models.IntegerField(null=True, blank=True)
    plex_rating_key = models.CharField(max_length=100, unique=True)
    sonarr_id = models.IntegerField(null=True, blank=True)
    imdb_id = models.CharField(max_length=20, null=True, blank=True)
    imdb_rating = models.FloatField(null=True, blank=True)
    added_at = models.DateTimeField(null=True, blank=True)
    any_episode_watched = models.BooleanField(default=False)
    total_episodes = models.IntegerField(default=0)
    watched_episodes = models.IntegerField(default=0)
    file_path = models.TextField(blank=True, default="")
    size_bytes = models.BigIntegerField(default=0)
    flagged = models.BooleanField(default=False)
    last_synced = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        verbose_name_plural = "series"

    def __str__(self):
        return f"{self.title} ({self.year})"

    @property
    def size_display(self):
        if self.size_bytes >= 1_073_741_824:
            return f"{self.size_bytes / 1_073_741_824:.1f} GB"
        return f"{self.size_bytes / 1_048_576:.0f} MB"
