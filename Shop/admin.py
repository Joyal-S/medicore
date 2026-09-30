from django.contrib import admin
from .models import tbl_category, tbl_medicine, tbl_stock


@admin.register(tbl_category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'category_name')
    search_fields = ('category_name',)
    ordering = ('category_name',)


@admin.register(tbl_medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('id', 'medicine_name', 'medicine_price', 'medicine_status', 'category', 'shop')
    search_fields = ('medicine_name', 'shop__shop_name', 'category__category_name')
    list_filter = ('medicine_status', 'category', 'shop')
    ordering = ('medicine_name',)


@admin.register(tbl_stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('id', 'medicine', 'stock_qty')
    search_fields = ('medicine__medicine_name', 'medicine__shop__shop_name')
    list_filter = ('medicine__shop',)
    ordering = ('-id',)
