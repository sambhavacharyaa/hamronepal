from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("create/", views.task_create_view, name="create"),
    path("<int:pk>/toggle/", views.task_toggle_view, name="toggle"),
    path("<int:pk>/delete/", views.task_delete_view, name="delete"),
]
