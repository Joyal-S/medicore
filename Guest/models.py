from django.db import models
from Admin.models import tbl_place


class tbl_registration(models.Model):
    registration_name = models.CharField(max_length=100)
    registration_email = models.CharField(max_length=100, db_index=True)
    registration_contact = models.CharField(max_length=30)
    registration_address = models.CharField(max_length=255)
    place = models.ForeignKey(tbl_place, on_delete=models.CASCADE, related_name='registrations')
    registration_photo = models.FileField(upload_to="Assets/Files/User")
    registration_password = models.CharField(max_length=128)

    class Meta:
        verbose_name = "User / Patient"
        verbose_name_plural = "Users / Patients"
        ordering = ['registration_name']

    def __str__(self):
        return f"{self.registration_name} ({self.registration_email})"


class tbl_doctor(models.Model):
    STATUS_PENDING = 0
    STATUS_APPROVED = 1
    STATUS_REJECTED = 2
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    )

    doctor_name = models.CharField(max_length=100)
    doctor_email = models.CharField(max_length=100, db_index=True)
    doctor_contact = models.CharField(max_length=30)
    doctor_status = models.IntegerField(default=0, choices=STATUS_CHOICES, db_index=True)
    doctor_photo = models.FileField(upload_to="Assets/Files/doctor")
    doctor_licese = models.FileField(upload_to="Assets/Files/doctor")
    place = models.ForeignKey(tbl_place, on_delete=models.CASCADE, related_name='doctors')
    doctor_password = models.CharField(max_length=128)

    class Meta:
        verbose_name = "Doctor"
        verbose_name_plural = "Doctors"
        ordering = ['doctor_name']

    @property
    def doctor_license(self):
        return self.doctor_licese

    def __str__(self):
        return f"Dr. {self.doctor_name}"


class tbl_shop(models.Model):
    STATUS_PENDING = 0
    STATUS_APPROVED = 1
    STATUS_REJECTED = 2
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    )

    shop_name = models.CharField(max_length=100)
    shop_email = models.CharField(max_length=100, db_index=True)
    shop_contact = models.CharField(max_length=30)
    shop_address = models.CharField(max_length=255)
    shop_status = models.IntegerField(default=0, choices=STATUS_CHOICES, db_index=True)
    shop_photo = models.FileField(upload_to="Assets/Files/shop")
    shop_licese = models.FileField(upload_to="Assets/Files/shop")
    place = models.ForeignKey(tbl_place, on_delete=models.CASCADE, related_name='shops')
    shop_password = models.CharField(max_length=128)

    class Meta:
        verbose_name = "Shop / Pharmacy"
        verbose_name_plural = "Shops / Pharmacies"
        ordering = ['shop_name']

    @property
    def shop_license(self):
        return self.shop_licese

    def __str__(self):
        return self.shop_name