from django.contrib import admin

from .models import District, Municipality, Province, Ward


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ("name", "name_ne", "code")
    search_fields = ("name", "name_ne", "code")


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "province", "code")
    list_filter = ("province",)
    search_fields = ("name", "name_ne", "code")


@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ("name", "district", "type", "code")
    list_filter = ("district__province", "type")
    search_fields = ("name", "name_ne", "code")


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ("municipality", "number")
    list_filter = ("municipality__district__province",)
