from django.conf import settings
from django.contrib import messages
from django.db.models import Avg, BooleanField, Case, Count, OuterRef, Q, Subquery, Sum, Value, When
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from medialib.managers import delete_movies, delete_series
from medialib.models import DeletionLog, Movie, MovieCollection, Series
from medialib.services import seerr


def dashboard(request):
    movie_count = Movie.objects.count()
    series_count = Series.objects.count()
    flagged_movies_qs = Movie.objects.filter(flagged=True, protected=False).exclude(collection__protected=True)
    flagged_movies = flagged_movies_qs.count()
    flagged_series = Series.objects.filter(flagged=True, protected=False).count()
    reclaimable = (
        (flagged_movies_qs.aggregate(s=Sum("size_bytes"))["s"] or 0)
        + (Series.objects.filter(flagged=True, protected=False).aggregate(s=Sum("size_bytes"))["s"] or 0)
    )
    total_reclaimed = DeletionLog.objects.aggregate(s=Sum("size_bytes"))["s"] or 0
    total_deleted_count = DeletionLog.objects.count()
    recent_deletions = DeletionLog.objects.all()[:20]

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
        "total_reclaimed_display": _size_display(total_reclaimed),
        "total_deleted_count": total_deleted_count,
        "recent_deletions": recent_deletions,
        "last_synced": last_synced,
        "seerr_configured": seerr.is_configured(),
        "seerr_blocklist": settings.SEERR_BLOCKLIST_ON_DELETE,
    })



def movies_list(request):
    explicit_sort = "sort" in request.GET
    sort = request.GET.get("sort", "title")
    direction = request.GET.get("dir", "asc")
    allowed_sorts = {
        "title": "title",
        "year": "year",
        "imdb_rating": "imdb_rating",
        "popularity": "popularity",
        "added_at": "added_at",
        "size_bytes": "size_bytes",
        "watched": "watched",
        "flagged": "flagged",
        "tags": "tags",
    }
    order_field = allowed_sorts.get(sort, "title")
    if direction == "desc":
        order_field = f"-{order_field}"
    ordering = ("-effective_flagged", order_field) if not explicit_sort else (order_field,)
    collection_counts = MovieCollection.objects.filter(
        pk=OuterRef("collection_id"),
    ).annotate(c=Count("movies")).values("c")
    movies = Movie.objects.select_related("collection").annotate(
        effective_flagged=Case(
            When(Q(flagged=True, protected=False) & ~Q(collection__protected=True), then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        ),
        collection_size=Subquery(collection_counts),
    ).order_by(*ordering)
    tag_filter = request.GET.get("tag", "").strip()
    if tag_filter:
        if tag_filter == "NOTAG":
            movies = movies.filter(tags="")
        else:
            movies = movies.filter(tags__icontains=tag_filter)
    return render(request, "webapp/movies.html", {
        "movies": movies,
        "current_sort": sort,
        "current_dir": direction,
        "tag_filter": tag_filter,
    })


def series_list(request):
    explicit_sort = "sort" in request.GET
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
        "tags": "tags",
    }
    order_field = allowed_sorts.get(sort, "title")
    if direction == "desc":
        order_field = f"-{order_field}"
    ordering = ("-effective_flagged", order_field) if not explicit_sort else (order_field,)
    all_series = Series.objects.annotate(
        effective_flagged=Case(
            When(flagged=True, protected=False, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        ),
    ).order_by(*ordering)
    tag_filter = request.GET.get("tag", "").strip()
    if tag_filter:
        if tag_filter == "NOTAG":
            all_series = all_series.filter(tags="")
        else:
            all_series = all_series.filter(tags__icontains=tag_filter)
    return render(request, "webapp/series.html", {
        "series_list": all_series,
        "current_sort": sort,
        "current_dir": direction,
        "tag_filter": tag_filter,
    })


@require_POST
def confirm_delete(request):
    movie_ids = request.POST.getlist("movie_ids")
    series_ids = request.POST.getlist("series_ids")
    selected_movies = list(Movie.objects.select_related("collection").filter(id__in=movie_ids))
    selected_series = list(Series.objects.filter(id__in=series_ids))
    has_protected = any(m.is_protected for m in selected_movies) or any(s.protected for s in selected_series)
    total_size = sum(m.size_bytes for m in selected_movies if not m.is_protected) + sum(s.size_bytes for s in selected_series if not s.protected)
    return render(request, "webapp/confirm_delete.html", {
        "movies": selected_movies,
        "series": selected_series,
        "total_size_display": _size_display(total_size),
        "movie_ids": movie_ids,
        "series_ids": series_ids,
        "has_protected": has_protected,
    })


@require_POST
def execute_delete(request):
    movie_ids = request.POST.getlist("movie_ids")
    series_ids = request.POST.getlist("series_ids")
    total_deleted = 0
    total_protected = 0
    all_errors = []

    if movie_ids:
        result = delete_movies([int(i) for i in movie_ids])
        total_deleted += result["deleted"]
        total_protected += result.get("protected", 0)
        all_errors.extend(result["errors"])

    if series_ids:
        result = delete_series([int(i) for i in series_ids])
        total_deleted += result["deleted"]
        total_protected += result.get("protected", 0)
        all_errors.extend(result["errors"])

    messages.success(request, f"Deleted {total_deleted} item(s).")
    if total_protected:
        messages.warning(request, f"Skipped {total_protected} protected item(s).")
    for err in all_errors:
        messages.error(request, f"Delete error: {err}")

    return redirect("dashboard")


@require_POST
def toggle_protected(request):
    movie_id = request.POST.get("movie_id")
    series_id = request.POST.get("series_id")
    redirect_url = request.POST.get("next", "/")
    if movie_id:
        movie = Movie.objects.filter(id=movie_id).first()
        if movie:
            movie.protected = not movie.protected
            movie.save(update_fields=["protected"])
    if series_id:
        s = Series.objects.filter(id=series_id).first()
        if s:
            s.protected = not s.protected
            s.save(update_fields=["protected"])
    return redirect(redirect_url)


def collections_list(request):
    explicit_sort = "sort" in request.GET
    sort = request.GET.get("sort", "name")
    direction = request.GET.get("dir", "asc")
    allowed_sorts = {
        "name": "name",
        "movie_count": "movie_count",
        "avg_rating": "avg_rating",
        "total_size": "total_size",
    }
    order_field = allowed_sorts.get(sort, "name")
    if direction == "desc":
        order_field = f"-{order_field}"

    flagged_movie_count = Count(
        "movies",
        filter=Q(movies__flagged=True, movies__protected=False, protected=False),
    )
    collections = MovieCollection.objects.prefetch_related("movies").annotate(
        movie_count=Count("movies"),
        avg_rating=Avg("movies__imdb_rating"),
        total_size=Sum("movies__size_bytes"),
        flagged_count=flagged_movie_count,
    ).filter(movie_count__gt=1)

    if explicit_sort:
        collections = collections.order_by(order_field)
    else:
        collections = collections.order_by("-flagged_count", order_field)

    collection_data = []
    for c in collections:
        movies = c.movies.all()
        collection_data.append({
            "collection": c,
            "movie_count": c.movie_count,
            "avg_rating": round(c.avg_rating, 1) if c.avg_rating is not None else None,
            "total_size_display": _size_display(c.total_size or 0),
            "has_flagged": c.flagged_count > 0,
            "movies": movies,
        })
    return render(request, "webapp/collections.html", {
        "collection_data": collection_data,
        "current_sort": sort,
        "current_dir": direction,
    })


@require_POST
def toggle_collection_protected(request):
    collection_id = request.POST.get("collection_id")
    redirect_url = request.POST.get("next", "/collections/")
    if collection_id:
        c = MovieCollection.objects.filter(id=collection_id).first()
        if c:
            c.protected = not c.protected
            c.save(update_fields=["protected"])
    return redirect(redirect_url)


def _size_display(size_bytes):
    if size_bytes >= 1_099_511_627_776:
        return f"{size_bytes / 1_099_511_627_776:.1f} TB"
    if size_bytes >= 1_073_741_824:
        return f"{size_bytes / 1_073_741_824:.1f} GB"
    return f"{size_bytes / 1_048_576:.0f} MB"
