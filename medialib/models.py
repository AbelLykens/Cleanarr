from django.db import models


class MovieCollection(models.Model):
    tmdb_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=500)
    protected = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Movie(models.Model):
    title = models.CharField(max_length=500)
    year = models.IntegerField(null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    plex_rating_key = models.CharField(max_length=100, null=True, blank=True)
    radarr_id = models.IntegerField(unique=True)
    imdb_id = models.CharField(max_length=20, null=True, blank=True)
    imdb_rating = models.FloatField(null=True, blank=True)
    popularity = models.FloatField(default=0)
    added_at = models.DateTimeField(null=True, blank=True)
    watched = models.BooleanField(default=False)
    file_path = models.TextField(blank=True, default="")
    size_bytes = models.BigIntegerField(default=0)
    tags = models.TextField(blank=True, default="")
    flagged = models.BooleanField(default=False)
    collection = models.ForeignKey(
        "MovieCollection", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="movies",
    )
    protected = models.BooleanField(default=False)
    last_synced = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.year})"

    @property
    def is_protected(self):
        return self.protected or (self.collection is not None and self.collection.protected)

    @property
    def size_display(self):
        return f"{round(self.size_bytes / 1_073_741_824)}"

    @property
    def tags_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()] if self.tags else []


class Series(models.Model):
    title = models.CharField(max_length=500)
    year = models.IntegerField(null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    plex_rating_key = models.CharField(max_length=100, null=True, blank=True)
    sonarr_id = models.IntegerField(unique=True)
    imdb_id = models.CharField(max_length=20, null=True, blank=True)
    imdb_rating = models.FloatField(null=True, blank=True)
    added_at = models.DateTimeField(null=True, blank=True)
    any_episode_watched = models.BooleanField(default=False)
    total_episodes = models.IntegerField(default=0)
    watched_episodes = models.IntegerField(default=0)
    file_path = models.TextField(blank=True, default="")
    size_bytes = models.BigIntegerField(default=0)
    tags = models.TextField(blank=True, default="")
    flagged = models.BooleanField(default=False)
    protected = models.BooleanField(default=False)
    last_synced = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        verbose_name_plural = "series"

    def __str__(self):
        return f"{self.title} ({self.year})"

    @property
    def size_display(self):
        return f"{round(self.size_bytes / 1_073_741_824)}"

    @property
    def tags_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()] if self.tags else []


class DeletionLog(models.Model):
    MOVIE = "movie"
    SERIES = "series"
    MEDIA_TYPES = [(MOVIE, "Movie"), (SERIES, "Series")]

    title = models.CharField(max_length=500)
    year = models.IntegerField(null=True, blank=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    size_bytes = models.BigIntegerField(default=0)
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-deleted_at"]

    def __str__(self):
        return f"{self.title} ({self.year})"

    @property
    def size_display(self):
        return f"{round(self.size_bytes / 1_073_741_824)}"
