from django.conf import settings
from plexapi.server import PlexServer


def _get_server():
    return PlexServer(settings.PLEX_URL, settings.PLEX_TOKEN)


def get_all_movies():
    server = _get_server()
    results = []
    for section in server.library.sections():
        if section.type != "movie":
            continue
        for movie in section.all():
            media = movie.media[0] if movie.media else None
            part = media.parts[0] if media and media.parts else None
            results.append({
                "title": movie.title,
                "year": movie.year,
                "rating_key": movie.ratingKey,
                "added_at": movie.addedAt,
                "file_path": part.file if part else "",
                "size_bytes": part.size if part else 0,
            })
    return results


def get_all_series():
    server = _get_server()
    results = []
    for section in server.library.sections():
        if section.type != "show":
            continue
        for show in section.all():
            total_size = 0
            total_episodes = 0
            file_path = ""
            for episode in show.episodes():
                total_episodes += 1
                media = episode.media[0] if episode.media else None
                part = media.parts[0] if media and media.parts else None
                if part:
                    total_size += part.size or 0
                    if not file_path:
                        file_path = part.file
            results.append({
                "title": show.title,
                "year": show.year,
                "rating_key": show.ratingKey,
                "added_at": show.addedAt,
                "total_episodes": total_episodes,
                "file_path": file_path,
                "size_bytes": total_size,
            })
    return results
