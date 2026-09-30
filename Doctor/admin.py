from django.contrib import admin
from .models import tbl_disease


@admin.register(tbl_disease)
class DiseasePredictionAdmin(admin.ModelAdmin):
    list_display = ('id', 'disease_name', 'doctor', 'reqpre')
    search_fields = ('disease_name', 'doctor__doctor_name', 'disease_symptoms')
    list_filter = ('doctor',)
    ordering = ('-id',)
