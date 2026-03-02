import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _headers():
    return {"X-Api-Key": settings.SEERR_API_KEY}


def _url(path):
    return f"{settings.SEERR_URL.rstrip('/')}/api/v1{path}"


def is_configured():
    return bool(settings.SEERR_URL and settings.SEERR_API_KEY)


def get_media(tmdb_id, media_type):
    """Look up media in Seerr by TMDB ID.

    media_type: "movie" or "tv"
    Returns the mediaInfo dict (contains Seerr internal ID and requests), or None on 404/403.
    """
    endpoint = "movie" if media_type == "movie" else "tv"
    resp = requests.get(_url(f"/{endpoint}/{tmdb_id}"), headers=_headers(), timeout=30)
    if resp.status_code == 404:
        return None
    if resp.status_code == 403:
        logger.warning("Seerr returned 403 for %s/%s — check API key permissions", endpoint, tmdb_id)
        return None
    resp.raise_for_status()
    return resp.json().get("mediaInfo")


def decline_requests(media_info):
    """Decline any pending or approved requests for the given media."""
    if not media_info:
        return
    for req in media_info.get("requests", []):
        status = req.get("status")
        # 1 = PENDING, 2 = APPROVED
        if status in (1, 2):
            req_id = req["id"]
            try:
                resp = requests.post(
                    _url(f"/request/{req_id}/decline"),
                    headers=_headers(),
                    timeout=30,
                )
                resp.raise_for_status()
                logger.info("Declined Seerr request %s", req_id)
            except Exception:
                logger.warning("Failed to decline Seerr request %s", req_id, exc_info=True)


def blocklist_add(tmdb_id, title):
    """Add a TMDB ID to the Seerr blocklist."""
    resp = requests.post(
        _url("/blocklist"),
        headers=_headers(),
        json={"tmdbId": tmdb_id, "title": title},
        timeout=30,
    )
    if resp.status_code == 403:
        logger.warning("Seerr returned 403 for blocklist add — check API key permissions")
        return
    if resp.status_code == 412:
        logger.info("Already blocklisted in Seerr: %s (tmdb=%s)", title, tmdb_id)
        return
    resp.raise_for_status()
    logger.info("Added to Seerr blocklist: %s (tmdb=%s)", title, tmdb_id)


def notify_deletion(tmdb_id, title, media_type):
    """Notify Seerr that a media item has been deleted.

    Called from managers after successful Radarr/Sonarr deletion.
    Catches all exceptions so Seerr errors never block the deletion flow.
    """
    if not is_configured():
        return
    if tmdb_id is None:
        logger.debug("Skipping Seerr notification for %s: no tmdb_id", title)
        return
    try:
        media_info = get_media(tmdb_id, media_type)
        decline_requests(media_info)
        if settings.SEERR_BLOCKLIST_ON_DELETE:
            blocklist_add(tmdb_id, title)
    except Exception:
        logger.warning("Seerr notification failed for %s (tmdb=%s)", title, tmdb_id, exc_info=True)
