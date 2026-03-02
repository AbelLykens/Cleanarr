from fnmatch import fnmatch

from django.core.management.base import BaseCommand

from medialib.managers import delete_movies, delete_series
from medialib.models import Movie, Series


class Command(BaseCommand):
    help = "Delete all flagged media from Radarr/Sonarr (with files). Logs deletions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Show what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--filter-tag",
            help="Only delete flagged items that have this tag",
        )

    def _size_display(self, size_bytes):
        if size_bytes >= 1_099_511_627_776:
            return f"{size_bytes / 1_099_511_627_776:.1f} TB"
        if size_bytes >= 1_073_741_824:
            return f"{size_bytes / 1_073_741_824:.1f} GB"
        return f"{size_bytes / 1_048_576:.0f} MB"

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        filter_tag = options["filter_tag"]

        movies = Movie.objects.filter(flagged=True, protected=False).exclude(collection__protected=True)
        series = Series.objects.filter(flagged=True, protected=False)

        if filter_tag:
            matches = lambda tags: any(fnmatch(t, filter_tag) for t in tags)
            movies = [m for m in movies if matches(m.tags_list)]
            series = [s for s in series if matches(s.tags_list)]

        movie_ids = [m.id for m in movies]
        series_ids = [s.id for s in series]
        total_items = len(movie_ids) + len(series_ids)
        total_bytes = sum(m.size_bytes for m in movies) + sum(s.size_bytes for s in series)

        if total_items == 0:
            self.stdout.write("Nothing to delete — no flagged items match.")
            return

        prefix = "[DRY RUN] " if dry_run else ""

        self.stdout.write(f"\n{prefix}Flagged movies ({len(movie_ids)}):")
        for m in movies:
            self.stdout.write(f"  {m.title} ({m.year}) — {self._size_display(m.size_bytes)}")

        self.stdout.write(f"\n{prefix}Flagged series ({len(series_ids)}):")
        for s in series:
            self.stdout.write(f"  {s.title} ({s.year}) — {self._size_display(s.size_bytes)}")

        if dry_run:
            self.stdout.write(
                f"\n{prefix}Would delete {total_items} items, "
                f"freeing {self._size_display(total_bytes)}."
            )
            return

        deleted = 0
        errors = []

        if movie_ids:
            result = delete_movies(movie_ids)
            deleted += result["deleted"]
            errors.extend(result["errors"])

        if series_ids:
            result = delete_series(series_ids)
            deleted += result["deleted"]
            errors.extend(result["errors"])

        for err in errors:
            self.stderr.write(self.style.ERROR(f"Error: {err}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDeleted {deleted} items, freed {self._size_display(total_bytes)}. "
                f"{len(errors)} error(s)."
            )
        )
