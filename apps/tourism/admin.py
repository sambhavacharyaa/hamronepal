from django.contrib import admin
from django.utils import timezone

from .models import (
    Destination,
    DestinationCategory,
    DestinationHighlight,
    RecentlyViewedDestination,
    SavedPlace,
    Trip,
    TripDestination,
)


class DestinationHighlightInline(admin.TabularInline):
    model = DestinationHighlight
    extra = 1
    ordering = ("kind", "order")


@admin.register(DestinationCategory)
class DestinationCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "region", "status", "best_season", "last_verified_at")
    list_filter = ("category", "status", "best_season")
    search_fields = ("title", "region", "summary")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("related_processes",)
    inlines = [DestinationHighlightInline]
    actions = ["mark_verified_today", "publish"]

    @admin.action(description="Mark verified today")
    def mark_verified_today(self, request, queryset):
        updated = queryset.update(last_verified_at=timezone.localdate())
        self.message_user(request, f"{updated} destination(s) marked verified today.")

    @admin.action(description="Publish selected destinations")
    def publish(self, request, queryset):
        updated = queryset.update(status=Destination.Status.PUBLISHED)
        self.message_user(request, f"{updated} destination(s) published.")


@admin.register(SavedPlace)
class SavedPlaceAdmin(admin.ModelAdmin):
    list_display = ("user", "destination", "created_at")
    list_filter = ("destination",)
    search_fields = ("user__email", "destination__title")


@admin.register(RecentlyViewedDestination)
class RecentlyViewedDestinationAdmin(admin.ModelAdmin):
    list_display = ("user", "destination", "updated_at")
    list_filter = ("destination",)
    search_fields = ("user__email", "destination__title")


class TripDestinationInline(admin.TabularInline):
    model = TripDestination
    extra = 0
    ordering = ("order",)


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "start_date", "end_date", "created_at")
    search_fields = ("title", "user__email")
    inlines = [TripDestinationInline]
