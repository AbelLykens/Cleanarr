from datetime import date

import requests
from django.conf import settings


def _headers():
    return {"X-Api-Key": settings.RADARR_API_KEY}


def _url(path):
    return f"{settings.RADARR_URL.rstrip('/')}/api/v3{path}"


def get_all_tags():
    resp = requests.get(_url("/tag"), headers=_headers(), timeout=30)
    resp.raise_for_status()
    return {t["id"]: t["label"] for t in resp.json()}


def _parse_date(iso_str):
    """Parse an ISO date string (e.g. '2025-09-15T00:00:00Z') to a date, or None."""
    if not iso_str:
        return None
    try:
        return date.fromisoformat(iso_str[:10])
    except (ValueError, TypeError):
        return None


def get_all_movies():
    tag_map = get_all_tags()
    resp = requests.get(_url("/movie"), headers=_headers(), timeout=30)
    resp.raise_for_status()
    results = {}
    for m in resp.json():
        imdb_id = m.get("imdbId", "")
        tag_ids = m.get("tags", [])
        tags = [tag_map[tid] for tid in tag_ids if tid in tag_map]
        release_date = (
            _parse_date(m.get("digitalRelease"))
            or _parse_date(m.get("physicalRelease"))
            or _parse_date(m.get("inCinemas"))
        )
        collection = m.get("collection") or {}
        results[m["id"]] = {
            "radarr_id": m["id"],
            "imdb_id": imdb_id,
            "imdb_rating": (m.get("ratings", {}).get("imdb", {}).get("value")),
            "title": m.get("title", ""),
            "year": m.get("year"),
            "popularity": m.get("popularity", 0) or 0,
            "release_date": release_date,
            "path": m.get("path", ""),
            "tags": ", ".join(sorted(tags)),
            "collection_tmdb_id": collection.get("tmdbId"),
            "collection_name": collection.get("name") or collection.get("title", ""),
        }
    return results


def delete_movie(radarr_id, delete_files=True):
    resp = requests.delete(
        _url(f"/movie/{radarr_id}"),
        headers=_headers(),
        params={"deleteFiles": str(delete_files).lower()},
        timeout=30,
    )
    resp.raise_for_status()
