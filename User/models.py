from django.db import models
from Guest.models import tbl_registration, tbl_doctor, tbl_shop
from Shop.models import tbl_medicine



class tbl_complaints(models.Model):
    STATUS_PENDING = 0
    STATUS_REPLIED = 1
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_REPLIED, 'Replied'),
    )

    complaints_subject = models.CharField(max_length=255)
    complaints_content = models.TextField()
    complaints_status = models.IntegerField(default=0, choices=STATUS_CHOICES, db_index=True)
    complaints_date = models.DateTimeField(auto_now_add=True)
    complaints_reply = models.TextField(blank=True, null=True)
    complaints_reply_date = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey(tbl_registration, on_delete=models.CASCADE, related_name='complaints')

    class Meta:
        verbose_name = "User Complaint"
        verbose_name_plural = "User Complaints"
        ordering = ['-complaints_date']

    def __str__(self):
        return f"{self.complaints_subject} - {self.user.registration_name}"


class tbl_request(models.Model):
    STATUS_PENDING = 0
    STATUS_ACCEPTED = 1
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Prescribed / Accepted'),
    )

    request_details = models.CharField(max_length=255)
    request_date = models.DateTimeField(auto_now_add=True)
    request_status = models.IntegerField(default=0, choices=STATUS_CHOICES, db_index=True)
    user = models.ForeignKey(tbl_registration, on_delete=models.CASCADE, related_name='consultation_requests')
    dotor = models.ForeignKey(tbl_doctor, on_delete=models.CASCADE, related_name='consultation_requests')

    class Meta:
        verbose_name = "Consultation Request"
        verbose_name_plural = "Consultation Requests"
        ordering = ['-request_date']

    @property
    def doctor(self):
        return self.dotor

    def __str__(self):
        return f"Request by {self.user.registration_name} to Dr. {self.dotor.doctor_name}"


class tbl_prescription(models.Model):
    prescription_file = models.FileField(upload_to="Assets/Files/Doctor/Prescription")
    prescription_date = models.DateTimeField(auto_now_add=True)
    requestpres = models.ForeignKey(tbl_request, on_delete=models.CASCADE, related_name='prescriptions')

    class Meta:
        verbose_name = "Doctor Prescription"
        verbose_name_plural = "Doctor Prescriptions"
        ordering = ['-prescription_date']

    @property
    def request(self):
        return self.requestpres

    def __str__(self):
        return f"Prescription for {self.requestpres}"


class tbl_booking(models.Model):
    STATUS_CART = 0
    STATUS_CHECKOUT = 1
    STATUS_PAID = 2
    STATUS_PACKING = 3
    STATUS_DELIVERED = 4
    STATUS_CHOICES = (
        (STATUS_CART, 'Active Cart'),
        (STATUS_CHECKOUT, 'Checkout Initiated'),
        (STATUS_PAID, 'Paid / Placed'),
        (STATUS_PACKING, 'Packing'),
        (STATUS_DELIVERED, 'Delivered'),
    )

    booking_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    booking_date = models.DateTimeField(auto_now_add=True)
    booking_status = models.IntegerField(default=0, choices=STATUS_CHOICES, db_index=True)
    prescription = models.FileField(upload_to="Assets/Files/User/Prescription", null=True, blank=True)
    user = models.ForeignKey(tbl_registration, on_delete=models.CASCADE, related_name='bookings')

    class Meta:
        verbose_name = "Order / Booking"
        verbose_name_plural = "Orders / Bookings"
        ordering = ['-booking_date']
        constraints = [
            models.CheckConstraint(condition=models.Q(booking_amount__gte=0), name='valid_booking_amount')
        ]

    def __str__(self):
        return f"Booking #{self.id} by {self.user.registration_name} - Rs. {self.booking_amount}"


class tbl_cart(models.Model):
    STATUS_CART = 0
    STATUS_ORDERED = 1
    STATUS_CHOICES = (
        (STATUS_CART, 'In Cart'),
        (STATUS_ORDERED, 'Ordered'),
    )

    cart_status = models.IntegerField(default=0, choices=STATUS_CHOICES, db_index=True)
    cart_quantity = models.PositiveIntegerField(default=1)
    medicine = models.ForeignKey(tbl_medicine, on_delete=models.CASCADE)
    booking = models.ForeignKey(tbl_booking, on_delete=models.CASCADE)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        ordering = ['-id']
        constraints = [
            models.CheckConstraint(condition=models.Q(cart_quantity__gte=1), name='valid_cart_quantity'),
            models.UniqueConstraint(fields=['booking', 'medicine'], name='unique_medicine_per_booking')
        ]

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
    doctor = models.ForeignKey(tbl_doctor, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(tbl_registration, on_delete=models.CASCADE, null=True, blank=True, related_name='doctor_ratings')
    datetime = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Doctor Rating & Review"
        verbose_name_plural = "Doctor Ratings & Reviews"
        ordering = ['-datetime']
        indexes = [
            models.Index(fields=['doctor', '-datetime'], name='rating_doc_date_idx')
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(rating_data__gte=1) & models.Q(rating_data__lte=5), name='valid_rating_range')
        ]

    def __str__(self):
        return f"Rating {self.rating_data}/5 for Dr. {self.doctor.doctor_name} by {self.user_name}"


class tbl_notification(models.Model):
    user = models.ForeignKey(tbl_registration, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    doctor = models.ForeignKey(tbl_doctor, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    shop = models.ForeignKey(tbl_shop, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, default='info')
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "System Notification"
        verbose_name_plural = "System Notifications"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

