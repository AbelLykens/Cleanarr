import requests
from django.conf import settings


def _headers():
    return {"X-Api-Key": settings.SONARR_API_KEY}


def _url(path):
    return f"{settings.SONARR_URL.rstrip('/')}/api/v3{path}"


def get_all_tags():
    resp = requests.get(_url("/tag"), headers=_headers(), timeout=30)
    resp.raise_for_status()
    return {t["id"]: t["label"] for t in resp.json()}


def get_all_series():
    tag_map = get_all_tags()
    resp = requests.get(_url("/series"), headers=_headers(), timeout=30)
    resp.raise_for_status()
    results = {}
    for s in resp.json():
        imdb_id = s.get("imdbId", "")
        tag_ids = s.get("tags", [])
        tags = [tag_map[tid] for tid in tag_ids if tid in tag_map]
        results[s["id"]] = {
            "sonarr_id": s["id"],
            "imdb_id": imdb_id,
            "imdb_rating": s.get("ratings", {}).get("value"),
            "title": s.get("title", ""),
            "year": s.get("year"),
            "path": s.get("path", ""),
            "tags": ", ".join(sorted(tags)),
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
