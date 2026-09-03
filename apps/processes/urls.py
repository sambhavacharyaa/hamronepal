from django.urls import path

from . import views

app_name = "processes"

urlpatterns = [
    path("search/", views.search_view, name="search"),
    path("processes/", views.process_list_view, name="process_list"),
    path("processes/<slug:slug>/", views.process_detail_view, name="process_detail"),
    path("processes/<slug:slug>/start/", views.start_tracking_view, name="start_tracking"),
    path("processes/<slug:slug>/track/", views.track_progress_view, name="track_progress"),
    path("processes/<slug:slug>/track/advance/", views.advance_status_view, name="advance_status"),
    path(
        "processes/<slug:slug>/track/step/<int:step_id>/toggle/",
        views.toggle_step_view,
        name="toggle_step",
    ),
    path(
        "processes/<slug:slug>/track/requirement/<int:requirement_id>/toggle/",
        views.toggle_requirement_view,
        name="toggle_requirement",
    ),
]
