from datetime import timedelta

from django.conf import settings
from django.utils import timezone


def thresholds(request):
    cutoff = timezone.now() - timedelta(days=settings.RECENTLY_ADDED_MONTHS * 30)
    return {
        "IMDB_RATING_THRESHOLD": settings.IMDB_RATING_THRESHOLD,
        "AGE_CUTOFF": cutoff,
    }
