import logging
from datetime import date, datetime, timedelta, timezone as dt_tz

from django.conf import settings
from django.utils import timezone

from .models import DeletionLog, Movie, Series
from .services import plex, radarr, sonarr, tautulli

logger = logging.getLogger(__name__)


def _make_aware(dt):
    """Ensure a datetime is timezone-aware (assume UTC if naive)."""
    if dt is not None and isinstance(dt, datetime) and dt.tzinfo is None:
        return dt.replace(tzinfo=dt_tz.utc)
    return dt


def _should_flag(watched, imdb_rating, added_at, size_bytes=0, popularity=0, release_date=None):
    """Return True if item meets all auto-flag criteria."""
    if size_bytes == 0:
        return False
    if watched:
        return False
    if imdb_rating is None:
        return False
    threshold = settings.IMDB_RATING_THRESHOLD
    if imdb_rating >= threshold:
        return False
    if popularity > 10:
        return False
    release_cutoff = date.today() - timedelta(days=settings.RECENTLY_ADDED_MONTHS * 30)
    if release_date and release_date > release_cutoff:
        return False
    if added_at is None:
        return True
    cutoff = timezone.now() - timedelta(days=settings.RECENTLY_ADDED_MONTHS * 30)
    return added_at < cutoff


def _find_plex_match_by_path(arr_path, plex_by_path):
    """Find Plex item whose file path starts with the Radarr/Sonarr directory path."""
    for plex_path, plex_item in plex_by_path.items():
        if plex_path.startswith(arr_path):
            return plex_item
    return None


def sync_library(progress=None):
    """Fetch data from Radarr/Sonarr (authoritative), enrich with Plex/Tautulli."""
    stats = {"movies_synced": 0, "series_synced": 0, "errors": []}

    # --- Movies ---
    if progress:
        progress("Fetching movies from Radarr...")
    radarr_ok = False
    try:
        radarr_movies = radarr.get_all_movies()
        radarr_ok = True
    except Exception as e:
        stats["errors"].append(f"Radarr: {e}")
        radarr_movies = {}

    if progress:
        progress(f"Fetched {len(radarr_movies)} movies from Radarr.")
        progress("Fetching movies from Plex...")
    try:
        plex_movies_by_path = plex.get_movies_by_path()
    except Exception as e:
        stats["errors"].append(f"Plex movies: {e}")
        plex_movies_by_path = {}

    seen_radarr_ids = set()
    for radarr_info in radarr_movies.values():
        rid = radarr_info["radarr_id"]
        seen_radarr_ids.add(rid)

        arr_path = radarr_info.get("path", "")
        plex_match = _find_plex_match_by_path(arr_path, plex_movies_by_path) if arr_path else None

        rating_key = None
        added_at = None
        file_path = arr_path
        size_bytes = 0
        if plex_match:
            rating_key = str(plex_match["rating_key"])
            added_at = _make_aware(plex_match.get("added_at"))
            file_path = plex_match.get("file_path", arr_path)
            size_bytes = plex_match.get("size_bytes", 0)

        watched = False
        if rating_key:
            try:
                watched = tautulli.was_ever_watched(rating_key)
            except Exception as e:
                logger.warning("Tautulli check failed for movie %s: %s", rating_key, e)

        imdb_rating = radarr_info.get("imdb_rating")
        imdb_id = radarr_info.get("imdb_id")
        popularity = radarr_info.get("popularity", 0)
        release_date = radarr_info.get("release_date")
        flagged = _should_flag(watched, imdb_rating, added_at, size_bytes, popularity, release_date)

        Movie.objects.update_or_create(
            radarr_id=rid,
            defaults={
                "title": radarr_info.get("title", ""),
                "year": radarr_info.get("year"),
                "release_date": release_date,
                "plex_rating_key": rating_key,
                "imdb_id": imdb_id,
                "imdb_rating": imdb_rating,
                "popularity": popularity,
                "tags": radarr_info.get("tags", ""),
                "added_at": added_at,
                "watched": watched,
                "file_path": file_path,
                "size_bytes": size_bytes,
                "flagged": flagged,
            },
        )
        stats["movies_synced"] += 1
        if progress and stats["movies_synced"] % 100 == 0:
            progress(f"  Synced {stats['movies_synced']} movies...")

    # Only delete DB movies not in Radarr if Radarr fetch succeeded
    if radarr_ok:
        Movie.objects.exclude(radarr_id__in=seen_radarr_ids).delete()

    # --- Series ---
    if progress:
        progress("Fetching series from Sonarr...")
    sonarr_ok = False
    try:
        sonarr_series = sonarr.get_all_series()
        sonarr_ok = True
    except Exception as e:
        stats["errors"].append(f"Sonarr: {e}")
        sonarr_series = {}

    if progress:
        progress(f"Fetched {len(sonarr_series)} series from Sonarr.")
        progress("Fetching series from Plex...")
    try:
        plex_series_by_path = plex.get_series_by_path()
    except Exception as e:
        stats["errors"].append(f"Plex series: {e}")
        plex_series_by_path = {}

    seen_sonarr_ids = set()
    for sonarr_info in sonarr_series.values():
        sid = sonarr_info["sonarr_id"]
        seen_sonarr_ids.add(sid)

        arr_path = sonarr_info.get("path", "")
        plex_match = _find_plex_match_by_path(arr_path, plex_series_by_path) if arr_path else None

        rating_key = None
        added_at = None
        file_path = arr_path
        size_bytes = 0
        total_episodes = 0
        if plex_match:
            rating_key = str(plex_match["rating_key"])
            added_at = _make_aware(plex_match.get("added_at"))
            file_path = plex_match.get("file_path", arr_path)
            size_bytes = plex_match.get("size_bytes", 0)
            total_episodes = plex_match.get("total_episodes", 0)

        watched = False
        if rating_key:
            try:
                watched = tautulli.any_episode_watched(rating_key)
            except Exception as e:
                logger.warning("Tautulli check failed for series %s: %s", rating_key, e)

        imdb_rating = sonarr_info.get("imdb_rating")
        imdb_id = sonarr_info.get("imdb_id")
        release_date = sonarr_info.get("release_date")
        flagged = _should_flag(watched, imdb_rating, added_at, size_bytes, release_date=release_date)

        Series.objects.update_or_create(
            sonarr_id=sid,
            defaults={
                "title": sonarr_info.get("title", ""),
                "year": sonarr_info.get("year"),
                "release_date": release_date,
                "plex_rating_key": rating_key,
                "imdb_id": imdb_id,
                "imdb_rating": imdb_rating,
                "tags": sonarr_info.get("tags", ""),
                "added_at": added_at,
                "any_episode_watched": watched,
                "total_episodes": total_episodes,
                "watched_episodes": 0,
                "file_path": file_path,
                "size_bytes": size_bytes,
                "flagged": flagged,
            },
        )
        stats["series_synced"] += 1
        if progress and stats["series_synced"] % 100 == 0:
            progress(f"  Synced {stats['series_synced']} series...")

    # Only delete DB series not in Sonarr if Sonarr fetch succeeded
    if sonarr_ok:
        Series.objects.exclude(sonarr_id__in=seen_sonarr_ids).delete()

    return stats


def delete_movies(movie_ids):
    """Delete movies via Radarr API and remove from local DB."""
    results = {"deleted": 0, "errors": []}
    movies = Movie.objects.filter(id__in=movie_ids)
    for movie in movies:
        try:
            radarr.delete_movie(movie.radarr_id, delete_files=True)
            DeletionLog.objects.create(
                title=movie.title,
                year=movie.year,
                media_type=DeletionLog.MOVIE,
                size_bytes=movie.size_bytes,
            )
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
        try:
            sonarr.delete_series(s.sonarr_id, delete_files=True)
            DeletionLog.objects.create(
                title=s.title,
                year=s.year,
                media_type=DeletionLog.SERIES,
                size_bytes=s.size_bytes,
            )
            s.delete()
            results["deleted"] += 1
        except Exception as e:
            results["errors"].append(f"{s.title}: {e}")
    return results
