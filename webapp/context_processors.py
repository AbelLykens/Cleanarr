from datetime import timedelta

from django.conf import settings
from django.utils import timezone


def thresholds(request):
    cutoff = timezone.now() - timedelta(days=settings.RECENTLY_ADDED_MONTHS * 30)
    release_cutoff = (timezone.now() - timedelta(days=settings.RECENTLY_ADDED_MONTHS * 30)).date()
    return {
        "IMDB_RATING_THRESHOLD": settings.IMDB_RATING_THRESHOLD,
        "POPULARITY_THRESHOLD": settings.POPULARITY_THRESHOLD,
        "RECENTLY_ADDED_MONTHS": settings.RECENTLY_ADDED_MONTHS,
        "AGE_CUTOFF": cutoff,
        "RELEASE_CUTOFF": release_cutoff,
    }
