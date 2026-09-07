from django.contrib import admin
from django.utils import timezone

from .models import Notification, RecentlyViewedProcess, SavedProcess, UserDocument


@admin.register(SavedProcess)
class SavedProcessAdmin(admin.ModelAdmin):
    list_display = ("user", "process", "created_at")
    list_filter = ("process",)
    search_fields = ("user__email", "process__title")


@admin.register(RecentlyViewedProcess)
class RecentlyViewedProcessAdmin(admin.ModelAdmin):
    list_display = ("user", "process", "updated_at")
    list_filter = ("process",)
    search_fields = ("user__email", "process__title")


@admin.register(UserDocument)
class UserDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "document_type", "expiry_date")
    list_filter = ("document_type",)
    search_fields = ("title", "user__email")

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_module_permission(self, request):
        return request.user.is_superuser


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("message", "user", "category", "level", "is_read", "is_dismissed", "created_at")
    list_filter = ("category", "level", "is_read", "is_dismissed")
    search_fields = ("message", "user__email")
    actions = ["mark_dismissed"]

    @admin.action(description="Mark selected notifications dismissed")
    def mark_dismissed(self, request, queryset):
        updated = queryset.update(is_dismissed=True, dismissed_at=timezone.now())
        self.message_user(request, f"{updated} notification(s) dismissed.")
