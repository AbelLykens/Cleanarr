from django.conf import settings


def thresholds(request):
    return {
        "IMDB_RATING_THRESHOLD": settings.IMDB_RATING_THRESHOLD,
    }
