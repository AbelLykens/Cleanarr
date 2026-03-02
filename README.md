# Opruimarr

A Django web app that helps manage your Plex media library by identifying low-quality, unwatched content for cleanup. It syncs with Radarr, Sonarr, Plex, and Tautulli to build a unified view of your library, then auto-flags items that meet all deletion criteria.

## How it works

Opruimarr syncs your library daily (04:00) using Radarr/Sonarr as the source of truth, enriched with watch history from Tautulli and file info from Plex. Items are auto-flagged for deletion when **all** of the following are true:

- Has files on disk (size > 0)
- Never watched (no Tautulli play history)
- IMDB rating below threshold (default: 5.0)
- Popularity score <= 10 (movies only)
- Added more than N months ago (default: 6)
- Released more than N months ago (default: 6)

Flagged items are pre-selected for batch deletion through the web UI. Deletion goes through Radarr/Sonarr APIs, which also removes files from disk.

## Requirements

- Python 3.10+
- Plex Media Server with Tautulli
- Radarr and Sonarr
- All services accessible from the machine running Opruimarr

## Quick install (Debian 13)

```bash
git clone <repo-url> /opt/opruimarr
cd /opt/opruimarr
cp .env.example .env
# Edit .env with your API keys and settings
./install.sh
```

Or manually:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## Configuration

Copy `.env.example` to `.env` and fill in your values:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key (generate a random one) | `change-me` |
| `DEBUG` | Enable debug mode | `False` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated trusted origins for CSRF | *(empty)* |
| `PLEX_URL` | Plex server URL | `http://localhost:32400` |
| `PLEX_TOKEN` | Plex authentication token | |
| `SONARR_URL` | Sonarr URL | `http://localhost:8989` |
| `SONARR_API_KEY` | Sonarr API key | |
| `RADARR_URL` | Radarr URL | `http://localhost:7878` |
| `RADARR_API_KEY` | Radarr API key | |
| `TAUTULLI_URL` | Tautulli URL | `http://localhost:8181` |
| `TAUTULLI_API_KEY` | Tautulli API key | |
| `IMDB_RATING_THRESHOLD` | Flag items rated below this (fallback for both types) | `5.0` |
| `IMDB_RATING_THRESHOLD_MOVIES` | Flag movies rated below this | value of `IMDB_RATING_THRESHOLD` |
| `IMDB_RATING_THRESHOLD_SERIES` | Flag series rated below this | value of `IMDB_RATING_THRESHOLD` |
| `RECENTLY_ADDED_MONTHS` | Protect items added/released within this many months | `6` |
| `SEERR_URL` | Jellyseerr/Overseerr URL (leave empty to disable) | *(empty)* |
| `SEERR_API_KEY` | Seerr API key | *(empty)* |
| `SEERR_BLOCKLIST_ON_DELETE` | Blocklist deleted items in Seerr to prevent re-requests | `True` |

## Manual sync

```bash
source venv/bin/activate
python manage.py sync_library
```

## Production

For production use behind a reverse proxy, see `nginx/plexclean.conf` for an example nginx config and `gunicorn.conf.py` for the Gunicorn setup.
