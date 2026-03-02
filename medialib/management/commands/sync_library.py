from django.core.management.base import BaseCommand

from medialib.managers import sync_library


class Command(BaseCommand):
    help = "Sync media library from Plex, Sonarr, Radarr, and Tautulli"

    def handle(self, *args, **options):
        self.stdout.write("Starting library sync...")
        stats = sync_library()
        self.stdout.write(
            f"Synced {stats['movies_synced']} movies and {stats['series_synced']} series."
        )
        for err in stats.get("errors", []):
            self.stderr.write(f"Warning: {err}")
        self.stdout.write(self.style.SUCCESS("Sync complete."))
