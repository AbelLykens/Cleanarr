from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("movies/", views.movies_list, name="movies"),
    path("series/", views.series_list, name="series"),
    path("delete/", views.confirm_delete, name="confirm_delete"),
    path("delete/execute/", views.execute_delete, name="execute_delete"),
    path("toggle-protected/", views.toggle_protected, name="toggle_protected"),
]
