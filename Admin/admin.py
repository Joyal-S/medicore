from django.contrib import admin
from .models import (
    tbl_district,
    tbl_place,
    tbl_categary,
    tbl_scategary,
    tbl_adminregistration,
)


@admin.register(tbl_district)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('id', 'district_name')
    search_fields = ('district_name',)
    ordering = ('district_name',)


@admin.register(tbl_place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ('id', 'place_name', 'district')
    search_fields = ('place_name', 'district__district_name')
    list_filter = ('district',)
    ordering = ('place_name',)


@admin.register(tbl_categary)
class AdminCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'categary_name')
    search_fields = ('categary_name',)
    ordering = ('categary_name',)


@admin.register(tbl_scategary)
class AdminSubcategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'scategary_name', 'categary')
    search_fields = ('scategary_name', 'categary__categary_name')
    list_filter = ('categary',)
    ordering = ('scategary_name',)


@admin.register(tbl_adminregistration)
class AdminRegistrationAdmin(admin.ModelAdmin):
    list_display = ('id', 'registration_name', 'registration_email')
    search_fields = ('registration_name', 'registration_email')
    readonly_fields = ('registration_password',)
