from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("process/<slug:slug>/save/", views.toggle_saved_view, name="toggle_saved"),
    path("deadlines/", views.deadlines_view, name="deadlines"),
    path("notifications/", views.notifications_view, name="notifications"),
    path("notifications/<int:pk>/dismiss/", views.dismiss_notification_view, name="dismiss_notification"),
    path("notifications/<int:pk>/read/", views.mark_notification_read_view, name="mark_notification_read"),
    path("notifications/mark-all-read/", views.mark_all_notifications_read_view, name="mark_all_read"),
    path("documents/create/", views.document_create_view, name="create_document"),
    path("documents/<int:pk>/delete/", views.document_delete_view, name="delete_document"),
    path("documents/<int:pk>/file/", views.document_file_view, name="document_file"),
]
