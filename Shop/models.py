from django.db import models
from Guest.models import tbl_shop


class tbl_category(models.Model):
    category_name = models.CharField(max_length=50)

    def __str__(self):
        return self.category_name


class tbl_medicine(models.Model):
    medicine_name = models.CharField(max_length=100)
    medicine_details = models.CharField(max_length=255)
    medicine_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    medicine_photo = models.FileField(upload_to="Assets/Files/medicine/")
    medicine_status = models.IntegerField(default=0)  # 0: Over-The-Counter, 1: Prescription Required
    shop = models.ForeignKey(tbl_shop, on_delete=models.CASCADE)
    category = models.ForeignKey(tbl_category, on_delete=models.CASCADE)

    @property
    def requires_prescription(self):
        return self.medicine_status == 1

    def __str__(self):
        return f"{self.medicine_name} (Rs. {self.medicine_price})"


class tbl_stock(models.Model):
    stock_qty = models.PositiveIntegerField(default=0)
    medicine = models.ForeignKey(tbl_medicine, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.medicine.medicine_name}: {self.stock_qty} in stock"
