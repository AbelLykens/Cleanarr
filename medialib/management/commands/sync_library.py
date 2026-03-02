from django.core.management.base import BaseCommand

from medialib.managers import sync_library


class Command(BaseCommand):
    help = "Sync media library from Radarr, Sonarr, Plex, and Tautulli"

    def add_arguments(self, parser):
        parser.add_argument(
            "--quiet", action="store_true",
            help="Suppress progress output",
        )

    def handle(self, *args, **options):
        quiet = options["quiet"]
        if not quiet:
            self.stdout.write("Starting library sync...")

        progress = None if quiet else lambda msg: self.stdout.write(msg)
        stats = sync_library(progress=progress)

        if not quiet:
            self.stdout.write(
                f"Synced {stats['movies_synced']} movies and "
                f"{stats['series_synced']} series."
            )
        for err in stats.get("errors", []):
            self.stderr.write(f"Warning: {err}")
        if not quiet:
            self.stdout.write(self.style.SUCCESS("Sync complete."))
