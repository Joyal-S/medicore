from django.contrib import admin
from .models import tbl_registration, tbl_doctor, tbl_shop


@admin.register(tbl_registration)
class UserRegistrationAdmin(admin.ModelAdmin):
    list_display = ('id', 'registration_name', 'registration_email', 'registration_contact', 'place')
    search_fields = ('registration_name', 'registration_email', 'registration_contact')
    list_filter = ('place__district',)
    readonly_fields = ('registration_password',)
    ordering = ('registration_name',)


@admin.register(tbl_doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('id', 'doctor_name', 'doctor_email', 'doctor_contact', 'doctor_status', 'place')
    search_fields = ('doctor_name', 'doctor_email', 'doctor_contact')
    list_filter = ('doctor_status', 'place__district')
    readonly_fields = ('doctor_password',)
    ordering = ('doctor_name',)


@admin.register(tbl_shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('id', 'shop_name', 'shop_email', 'shop_contact', 'shop_status', 'place')
    search_fields = ('shop_name', 'shop_email', 'shop_contact')
    list_filter = ('shop_status', 'place__district')
    readonly_fields = ('shop_password',)
    ordering = ('shop_name',)
