import requests
from django.conf import settings


def _params(cmd, **kwargs):
    params = {
        "apikey": settings.TAUTULLI_API_KEY,
        "cmd": cmd,
    }
    params.update(kwargs)
    return params


def _url():
    return f"{settings.TAUTULLI_URL.rstrip('/')}/api/v2"


def was_ever_watched(rating_key):
    """Check if a movie was ever watched (has any play history)."""
    resp = requests.get(
        _url(),
        params=_params("get_history", rating_key=rating_key, length=1),
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json().get("response", {}).get("data", {})
    total = data.get("recordsFiltered", 0)
    return total > 0


def any_episode_watched(rating_key):
    """Check if any episode of a series was ever watched."""
    resp = requests.get(
        _url(),
        params=_params(
            "get_history",
            grandparent_rating_key=rating_key,
            length=1,
        ),
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json().get("response", {}).get("data", {})
    total = data.get("recordsFiltered", 0)
    return total > 0
