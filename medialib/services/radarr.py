import requests
from django.conf import settings


def _headers():
    return {"X-Api-Key": settings.RADARR_API_KEY}


def _url(path):
    return f"{settings.RADARR_URL.rstrip('/')}/api/v3{path}"


def get_all_movies():
    resp = requests.get(_url("/movie"), headers=_headers(), timeout=30)
    resp.raise_for_status()
    results = {}
    for m in resp.json():
        imdb_id = m.get("imdbId", "")
        results[imdb_id] = {
            "radarr_id": m["id"],
            "imdb_id": imdb_id,
            "imdb_rating": (m.get("ratings", {}).get("imdb", {}).get("value")),
            "title": m.get("title", ""),
            "path": m.get("path", ""),
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
