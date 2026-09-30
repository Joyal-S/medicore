from django.db import models
from Guest.models import tbl_shop


class tbl_category(models.Model):
    category_name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Medicine Category"
        verbose_name_plural = "Medicine Categories"
        ordering = ['category_name']

    def __str__(self):
        return self.category_name


class tbl_medicine(models.Model):
    STATUS_OTC = 0
    STATUS_PRESCRIPTION = 1
    STATUS_CHOICES = (
        (STATUS_OTC, 'Over-The-Counter'),
        (STATUS_PRESCRIPTION, 'Prescription Required'),
    )

    medicine_name = models.CharField(max_length=100)
    medicine_details = models.CharField(max_length=255)
    medicine_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    medicine_photo = models.FileField(upload_to="Assets/Files/medicine/")
    medicine_status = models.IntegerField(default=0, choices=STATUS_CHOICES, db_index=True)
    shop = models.ForeignKey(tbl_shop, on_delete=models.CASCADE, related_name='medicines')
    category = models.ForeignKey(tbl_category, on_delete=models.CASCADE, related_name='medicines')

    class Meta:
        verbose_name = "Medicine"
        verbose_name_plural = "Medicines"
        ordering = ['medicine_name']
        constraints = [
            models.CheckConstraint(condition=models.Q(medicine_price__gte=0), name='valid_medicine_price')
        ]

    @property
    def requires_prescription(self):
        return self.medicine_status == self.STATUS_PRESCRIPTION

    def get_available_stock(self):
        """Calculate and return currently available stock for this medicine."""
        from django.db.models import Sum
        total_stock = self.tbl_stock_set.aggregate(total=Sum('stock_qty'))['total'] or 0
        sold_qty = self.tbl_cart_set.filter(
            cart_status=1,
            booking__booking_status__in=[2, 3, 4]
        ).aggregate(total=Sum('cart_quantity'))['total'] or 0
        return max(0, total_stock - sold_qty)

    def __str__(self):
        return f"{self.medicine_name} (Rs. {self.medicine_price})"


class tbl_stock(models.Model):
    stock_qty = models.PositiveIntegerField(default=0)
    medicine = models.ForeignKey(tbl_medicine, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Stock Entry"
        verbose_name_plural = "Stock Entries"
        ordering = ['-id']
        constraints = [
            models.CheckConstraint(condition=models.Q(stock_qty__gte=0), name='valid_stock_qty')
        ]

    def __str__(self):
        return f"{self.medicine.medicine_name}: {self.stock_qty} in stock"
