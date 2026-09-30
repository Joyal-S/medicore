from django.contrib import admin
from .models import (
    tbl_complaints,
    tbl_request,
    tbl_prescription,
    tbl_booking,
    tbl_cart,
    tbl_rating,
)


@admin.register(tbl_complaints)
class ComplaintsAdmin(admin.ModelAdmin):
    list_display = ('id', 'complaints_subject', 'user', 'complaints_status', 'complaints_date')
    search_fields = ('complaints_subject', 'user__registration_name', 'user__registration_email')
    list_filter = ('complaints_status', 'complaints_date')
    ordering = ('-complaints_date',)


@admin.register(tbl_request)
class ConsultationRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'dotor', 'request_status', 'request_date')
    search_fields = ('user__registration_name', 'dotor__doctor_name', 'request_details')
    list_filter = ('request_status', 'request_date')
    ordering = ('-request_date',)


@admin.register(tbl_prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'requestpres', 'prescription_date')
    search_fields = ('requestpres__user__registration_name', 'requestpres__dotor__doctor_name')
    ordering = ('-prescription_date',)


@admin.register(tbl_booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'booking_amount', 'booking_status', 'booking_date')
    search_fields = ('user__registration_name', 'user__registration_email')
    list_filter = ('booking_status', 'booking_date')
    ordering = ('-booking_date',)


@admin.register(tbl_cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'medicine', 'cart_quantity', 'unit_price', 'cart_status')
    search_fields = ('medicine__medicine_name', 'booking__user__registration_name')
    list_filter = ('cart_status',)
    ordering = ('-id',)


@admin.register(tbl_rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'doctor', 'user', 'rating_data', 'datetime')
    search_fields = ('doctor__doctor_name', 'user__registration_name', 'user_name')
    list_filter = ('rating_data', 'datetime')
    ordering = ('-datetime',)
