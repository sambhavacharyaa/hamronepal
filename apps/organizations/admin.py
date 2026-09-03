from django.contrib import admin

from .models import GovernmentOffice, GovernmentOrganization


class GovernmentOfficeInline(admin.TabularInline):
    model = GovernmentOffice
    extra = 1


@admin.register(GovernmentOrganization)
class GovernmentOrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "website_url")
    list_filter = ("type",)
    search_fields = ("name", "name_ne")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [GovernmentOfficeInline]


@admin.register(GovernmentOffice)
class GovernmentOfficeAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "municipality", "phone")
    list_filter = ("organization",)
    search_fields = ("name", "address")
