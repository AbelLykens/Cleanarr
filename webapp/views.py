from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from medialib.managers import delete_movies, delete_series
from medialib.models import Movie, Series


def dashboard(request):
    movie_count = Movie.objects.count()
    series_count = Series.objects.count()
    flagged_movies = Movie.objects.filter(flagged=True).count()
    flagged_series = Series.objects.filter(flagged=True).count()
    reclaimable = (
        (Movie.objects.filter(flagged=True).aggregate(s=Sum("size_bytes"))["s"] or 0)
        + (Series.objects.filter(flagged=True).aggregate(s=Sum("size_bytes"))["s"] or 0)
    )
    last_synced = None
    latest_movie = Movie.objects.order_by("-last_synced").first()
    latest_series = Series.objects.order_by("-last_synced").first()
    if latest_movie:
        last_synced = latest_movie.last_synced
    if latest_series and (not last_synced or latest_series.last_synced > last_synced):
        last_synced = latest_series.last_synced

    return render(request, "webapp/dashboard.html", {
        "movie_count": movie_count,
        "series_count": series_count,
        "flagged_movies": flagged_movies,
        "flagged_series": flagged_series,
        "reclaimable_bytes": reclaimable,
        "reclaimable_display": _size_display(reclaimable),
        "last_synced": last_synced,
    })



def movies_list(request):
    sort = request.GET.get("sort", "title")
    direction = request.GET.get("dir", "asc")
    allowed_sorts = {
        "title": "title",
        "year": "year",
        "imdb_rating": "imdb_rating",
        "added_at": "added_at",
        "size_bytes": "size_bytes",
        "watched": "watched",
        "flagged": "flagged",
    }
    order_field = allowed_sorts.get(sort, "title")
    if direction == "desc":
        order_field = f"-{order_field}"
    movies = Movie.objects.all().order_by("-flagged", order_field)
    return render(request, "webapp/movies.html", {
        "movies": movies,
        "current_sort": sort,
        "current_dir": direction,
    })


def series_list(request):
    sort = request.GET.get("sort", "title")
    direction = request.GET.get("dir", "asc")
    allowed_sorts = {
        "title": "title",
        "year": "year",
        "imdb_rating": "imdb_rating",
        "added_at": "added_at",
        "size_bytes": "size_bytes",
        "any_episode_watched": "any_episode_watched",
        "flagged": "flagged",
    }
    order_field = allowed_sorts.get(sort, "title")
    if direction == "desc":
        order_field = f"-{order_field}"
    all_series = Series.objects.all().order_by("-flagged", order_field)
    return render(request, "webapp/series.html", {
        "series_list": all_series,
        "current_sort": sort,
        "current_dir": direction,
    })


@require_POST
def confirm_delete(request):
    movie_ids = request.POST.getlist("movie_ids")
    series_ids = request.POST.getlist("series_ids")
    selected_movies = Movie.objects.filter(id__in=movie_ids)
    selected_series = Series.objects.filter(id__in=series_ids)
    total_size = (
        (selected_movies.aggregate(s=Sum("size_bytes"))["s"] or 0)
        + (selected_series.aggregate(s=Sum("size_bytes"))["s"] or 0)
    )
    return render(request, "webapp/confirm_delete.html", {
        "movies": selected_movies,
        "series": selected_series,
        "total_size_display": _size_display(total_size),
        "movie_ids": movie_ids,
        "series_ids": series_ids,
    })


@require_POST
def execute_delete(request):
    movie_ids = request.POST.getlist("movie_ids")
    series_ids = request.POST.getlist("series_ids")
    total_deleted = 0
    all_errors = []

    if movie_ids:
        result = delete_movies([int(i) for i in movie_ids])
        total_deleted += result["deleted"]
        all_errors.extend(result["errors"])

    if series_ids:
        result = delete_series([int(i) for i in series_ids])
        total_deleted += result["deleted"]
        all_errors.extend(result["errors"])

    messages.success(request, f"Deleted {total_deleted} item(s).")
    for err in all_errors:
        messages.error(request, f"Delete error: {err}")

    return redirect("dashboard")


def _size_display(size_bytes):
    if size_bytes >= 1_099_511_627_776:
        return f"{size_bytes / 1_099_511_627_776:.1f} TB"
    if size_bytes >= 1_073_741_824:
        return f"{size_bytes / 1_073_741_824:.1f} GB"
    return f"{size_bytes / 1_048_576:.0f} MB"
