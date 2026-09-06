from django.urls import path

from . import views

app_name = "tourism"

urlpatterns = [
    path("", views.tourism_home_view, name="home"),
    path("destinations/", views.destination_list_view, name="destination_list"),
    path("destinations/<slug:slug>/", views.destination_detail_view, name="destination_detail"),
    path("destinations/<slug:slug>/save/", views.toggle_saved_view, name="toggle_saved"),
    path("saved/", views.saved_places_view, name="saved_places"),
    path("trips/", views.trip_list_view, name="trip_list"),
    path("trips/create/", views.trip_create_view, name="trip_create"),
    path("trips/<int:pk>/", views.trip_detail_view, name="trip_detail"),
    path("trips/<int:pk>/delete/", views.trip_delete_view, name="trip_delete"),
    path(
        "trips/<int:pk>/add/<slug:destination_slug>/",
        views.trip_add_destination_view,
        name="trip_add_destination",
    ),
    path(
        "trips/<int:trip_pk>/remove/<int:pk>/",
        views.trip_remove_destination_view,
        name="trip_remove_destination",
    ),
]
