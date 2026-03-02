import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import Movie, Series
from .services import plex, radarr, sonarr, tautulli

logger = logging.getLogger(__name__)


def _should_flag(watched, imdb_rating, added_at):
    """Return True if item meets all auto-flag criteria."""
    if watched:
        return False
    threshold = settings.IMDB_RATING_THRESHOLD
    if imdb_rating is not None and imdb_rating >= threshold:
        return False
    if added_at is None:
        return True
    cutoff = timezone.now() - timedelta(days=settings.RECENTLY_ADDED_MONTHS * 30)
    return added_at < cutoff


def sync_library():
    """Fetch data from Plex, Sonarr/Radarr, and Tautulli. Update local DB."""
    stats = {"movies_synced": 0, "series_synced": 0, "errors": []}

    # --- Movies ---
    try:
        plex_movies = plex.get_all_movies()
    except Exception as e:
        stats["errors"].append(f"Plex movies: {e}")
        plex_movies = []

    try:
        radarr_movies = radarr.get_all_movies()
    except Exception as e:
        stats["errors"].append(f"Radarr: {e}")
        radarr_movies = {}

    # Build lookup: match by file path (most reliable cross-service match)
    radarr_by_path = {}
    for info in radarr_movies.values():
        path = info.get("path", "")
        if path:
            radarr_by_path[path] = info

    seen_keys = set()
    for pm in plex_movies:
        rk = str(pm["rating_key"])
        seen_keys.add(rk)

        # Match to Radarr by IMDB ID first, then by path prefix
        radarr_info = None
        file_path = pm.get("file_path", "")
        for rpath, rinfo in radarr_by_path.items():
            if file_path and file_path.startswith(rpath):
                radarr_info = rinfo
                break

        # Check Tautulli watch status
        try:
            watched = tautulli.was_ever_watched(rk)
        except Exception as e:
            logger.warning("Tautulli check failed for movie %s: %s", rk, e)
            watched = False

        imdb_rating = radarr_info["imdb_rating"] if radarr_info else None
        imdb_id = radarr_info["imdb_id"] if radarr_info else None
        radarr_id = radarr_info["radarr_id"] if radarr_info else None

        flagged = _should_flag(watched, imdb_rating, pm.get("added_at"))

        Movie.objects.update_or_create(
            plex_rating_key=rk,
            defaults={
                "title": pm["title"],
                "year": pm.get("year"),
                "radarr_id": radarr_id,
                "imdb_id": imdb_id,
                "imdb_rating": imdb_rating,
                "added_at": pm.get("added_at"),
                "watched": watched,
                "file_path": file_path,
                "size_bytes": pm.get("size_bytes", 0),
                "flagged": flagged,
            },
        )
        stats["movies_synced"] += 1

    # Remove movies no longer in Plex
    Movie.objects.exclude(plex_rating_key__in=seen_keys).delete()

    # --- Series ---
    try:
        plex_series = plex.get_all_series()
    except Exception as e:
        stats["errors"].append(f"Plex series: {e}")
        plex_series = []

    try:
        sonarr_series = sonarr.get_all_series()
    except Exception as e:
        stats["errors"].append(f"Sonarr: {e}")
        sonarr_series = {}

    sonarr_by_path = {}
    for info in sonarr_series.values():
        path = info.get("path", "")
        if path:
            sonarr_by_path[path] = info

    seen_keys = set()
    for ps in plex_series:
        rk = str(ps["rating_key"])
        seen_keys.add(rk)

        sonarr_info = None
        file_path = ps.get("file_path", "")
        for spath, sinfo in sonarr_by_path.items():
            if file_path and file_path.startswith(spath):
                sonarr_info = sinfo
                break

        try:
            watched = tautulli.any_episode_watched(rk)
        except Exception as e:
            logger.warning("Tautulli check failed for series %s: %s", rk, e)
            watched = False

        imdb_rating = sonarr_info["imdb_rating"] if sonarr_info else None
        imdb_id = sonarr_info["imdb_id"] if sonarr_info else None
        sonarr_id = sonarr_info["sonarr_id"] if sonarr_info else None

        flagged = _should_flag(watched, imdb_rating, ps.get("added_at"))

        Series.objects.update_or_create(
            plex_rating_key=rk,
            defaults={
                "title": ps["title"],
                "year": ps.get("year"),
                "sonarr_id": sonarr_id,
                "imdb_id": imdb_id,
                "imdb_rating": imdb_rating,
                "added_at": ps.get("added_at"),
                "any_episode_watched": watched,
                "total_episodes": ps.get("total_episodes", 0),
                "watched_episodes": 0,
                "file_path": file_path,
                "size_bytes": ps.get("size_bytes", 0),
                "flagged": flagged,
            },
        )
        stats["series_synced"] += 1

    Series.objects.exclude(plex_rating_key__in=seen_keys).delete()

    return stats


def delete_movies(movie_ids):
    """Delete movies via Radarr API and remove from local DB."""
    results = {"deleted": 0, "errors": []}
    movies = Movie.objects.filter(id__in=movie_ids)
    for movie in movies:
        if not movie.radarr_id:
            results["errors"].append(f"{movie.title}: no Radarr ID")
            continue
        try:
            radarr.delete_movie(movie.radarr_id, delete_files=True)
            movie.delete()
            results["deleted"] += 1
        except Exception as e:
            results["errors"].append(f"{movie.title}: {e}")
    return results


def delete_series(series_ids):
    """Delete series via Sonarr API and remove from local DB."""
    results = {"deleted": 0, "errors": []}
    all_series = Series.objects.filter(id__in=series_ids)
    for s in all_series:
        if not s.sonarr_id:
            results["errors"].append(f"{s.title}: no Sonarr ID")
            continue
        try:
            sonarr.delete_series(s.sonarr_id, delete_files=True)
            s.delete()
            results["deleted"] += 1
        except Exception as e:
            results["errors"].append(f"{s.title}: {e}")
    return results
