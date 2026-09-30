from django.db import models
from Guest.models import tbl_registration, tbl_doctor
from Shop.models import tbl_medicine


class tbl_complaints(models.Model):
    complaints_subject = models.CharField(max_length=255)
    complaints_content = models.TextField()
    complaints_status = models.IntegerField(default=0)  # 0: Pending, 1: Replied
    complaints_date = models.DateTimeField(auto_now_add=True)
    complaints_reply = models.TextField(blank=True, null=True)
    complaints_reply_date = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey(tbl_registration, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.complaints_subject} - {self.user.registration_name}"


class tbl_request(models.Model):
    request_details = models.CharField(max_length=255)
    request_date = models.DateTimeField(auto_now_add=True)
    request_status = models.IntegerField(default=0)  # 0: Pending, 1: Prescribed/Accepted
    user = models.ForeignKey(tbl_registration, on_delete=models.CASCADE)
    dotor = models.ForeignKey(tbl_doctor, on_delete=models.CASCADE)

    @property
    def doctor(self):
        return self.dotor

    def __str__(self):
        return f"Request by {self.user.registration_name} to Dr. {self.dotor.doctor_name}"


class tbl_prescription(models.Model):
    prescription_file = models.FileField(upload_to="Assets/Files/Doctor/Prescription")
    prescription_date = models.DateTimeField(auto_now_add=True)
    requestpres = models.ForeignKey(tbl_request, on_delete=models.CASCADE)

    def __str__(self):
        return f"Prescription for {self.requestpres}"


class tbl_booking(models.Model):
    booking_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    booking_date = models.DateTimeField(auto_now_add=True)
    booking_status = models.IntegerField(default=0)  # 0: Cart, 1: Checkout/Prescription, 2: Paid/Placed, 3: Packing, 4: Delivered
    prescription = models.FileField(upload_to="Assets/Files/User/Prescription", null=True, blank=True)
    user = models.ForeignKey(tbl_registration, on_delete=models.CASCADE)

    def __str__(self):
        return f"Booking #{self.id} by {self.user.registration_name} - Rs. {self.booking_amount}"


class tbl_cart(models.Model):
    cart_status = models.IntegerField(default=0)
    cart_quantity = models.PositiveIntegerField(default=1)
    medicine = models.ForeignKey(tbl_medicine, on_delete=models.CASCADE)
    booking = models.ForeignKey(tbl_booking, on_delete=models.CASCADE)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    @property
    def subtotal(self):
        price = self.unit_price if self.unit_price is not None else self.medicine.medicine_price
        return float(price) * self.cart_quantity

    def __str__(self):
        return f"{self.medicine.medicine_name} x {self.cart_quantity} (Booking #{self.booking_id})"


class tbl_rating(models.Model):
    rating_data = models.IntegerField(default=5)
    user_name = models.CharField(max_length=100, blank=True)
    user_review = models.TextField()
    doctor = models.ForeignKey(tbl_doctor, on_delete=models.CASCADE)
    user = models.ForeignKey(tbl_registration, on_delete=models.CASCADE, null=True, blank=True)
    datetime = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating {self.rating_data}/5 for Dr. {self.doctor.doctor_name} by {self.user_name}"
