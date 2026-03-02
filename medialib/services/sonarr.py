import requests
from django.conf import settings


def _headers():
    return {"X-Api-Key": settings.SONARR_API_KEY}


def _url(path):
    return f"{settings.SONARR_URL.rstrip('/')}/api/v3{path}"


def get_all_series():
    resp = requests.get(_url("/series"), headers=_headers(), timeout=30)
    resp.raise_for_status()
    results = {}
    for s in resp.json():
        imdb_id = s.get("imdbId", "")
        results[imdb_id] = {
            "sonarr_id": s["id"],
            "imdb_id": imdb_id,
            "imdb_rating": s.get("ratings", {}).get("value"),
            "title": s.get("title", ""),
            "path": s.get("path", ""),
        }
    return results


def delete_series(sonarr_id, delete_files=True):
    resp = requests.delete(
        _url(f"/series/{sonarr_id}"),
        headers=_headers(),
        params={"deleteFiles": str(delete_files).lower()},
        timeout=30,
    )
    resp.raise_for_status()
