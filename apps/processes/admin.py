from django.contrib import admin, messages
from django.utils import timezone

from . import services
from .models import (
    Process,
    ProcessCategory,
    ProcessExperience,
    ProcessFAQ,
    ProcessRequirement,
    ProcessSource,
    ProcessStep,
    ProcessVersion,
    UserProcessProgress,
    UserRequirementProgress,
    UserStepProgress,
)


class ProcessStepInline(admin.TabularInline):
    model = ProcessStep
    extra = 1
    ordering = ("order",)


class ProcessRequirementInline(admin.TabularInline):
    model = ProcessRequirement
    extra = 1
    ordering = ("order",)


class ProcessSourceInline(admin.TabularInline):
    model = ProcessSource
    extra = 1


class ProcessFAQInline(admin.TabularInline):
    model = ProcessFAQ
    extra = 1
    ordering = ("order",)


@admin.register(ProcessCategory)
class ProcessCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "last_verified_at", "current_version_number")
    list_filter = ("category", "status")
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ProcessStepInline, ProcessRequirementInline, ProcessSourceInline, ProcessFAQInline]
    actions = ["publish_new_version"]

    @admin.action(description="Publish new version")
    def publish_new_version(self, request, queryset):
        for process in queryset:
            try:
                version = services.publish_new_version(process, request.user)
            except services.PublishError as exc:
                self.message_user(request, f"{process}: {exc}", level=messages.ERROR)
            else:
                self.message_user(request, f"{process}: published as v{version.version_number}")


@admin.register(ProcessSource)
class ProcessSourceAdmin(admin.ModelAdmin):
    list_display = ("title", "process", "url", "last_verified_date", "verified_by")
    list_filter = ("process",)
    search_fields = ("title", "url")
    actions = ["mark_verified_today"]

    @admin.action(description="Mark sources verified today")
    def mark_verified_today(self, request, queryset):
        updated = queryset.update(last_verified_date=timezone.localdate(), verified_by=request.user)
        self.message_user(request, f"{updated} source(s) marked verified today.")


class UserStepProgressInline(admin.TabularInline):
    model = UserStepProgress
    extra = 0
    can_delete = False
    fields = ("step", "is_completed", "completed_at", "notes")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class UserRequirementProgressInline(admin.TabularInline):
    model = UserRequirementProgress
    extra = 0
    can_delete = False
    fields = ("requirement", "is_completed", "completed_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(UserProcessProgress)
class UserProcessProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "process", "status", "variant_selected", "started_at", "completed_at")
    list_filter = ("status", "process")
    search_fields = ("user__email", "process__title")
    inlines = [UserStepProgressInline, UserRequirementProgressInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProcessExperience)
class ProcessExperienceAdmin(admin.ModelAdmin):
    list_display = ("user", "process", "is_published", "created_at")
    list_filter = ("is_published", "process")
    search_fields = ("user__email", "process__title", "body")
    actions = ["publish", "unpublish"]

    @admin.action(description="Publish selected experiences")
    def publish(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"{updated} experience(s) published.")

    @admin.action(description="Unpublish selected experiences")
    def unpublish(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"{updated} experience(s) unpublished.")


@admin.register(ProcessVersion)
class ProcessVersionAdmin(admin.ModelAdmin):
    list_display = ("process", "version_number", "published_by", "published_at")
    list_filter = ("process",)

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
