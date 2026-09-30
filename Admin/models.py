from django.db import models


class tbl_district(models.Model):
    district_name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "District"
        verbose_name_plural = "Districts"
        ordering = ['district_name']

    def __str__(self):
        return self.district_name


class tbl_adminregistration(models.Model):
    registration_name = models.CharField(max_length=50)
    registration_email = models.CharField(max_length=50, db_index=True)
    registration_photo = models.FileField(upload_to="Assets/Files/admin", null=True, blank=True)
    registration_password = models.CharField(max_length=128)

    class Meta:
        verbose_name = "Admin Account"
        verbose_name_plural = "Admin Accounts"
        ordering = ['registration_name']

    def __str__(self):
        return self.registration_name


class tbl_categary(models.Model):
    categary_name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Admin Category"
        verbose_name_plural = "Admin Categories"
        ordering = ['categary_name']

    @property
    def category_name(self):
        return self.categary_name

    def __str__(self):
        return self.categary_name


class tbl_place(models.Model):
    place_name = models.CharField(max_length=50)
    district = models.ForeignKey(tbl_district, on_delete=models.CASCADE, related_name='places')

    class Meta:
        verbose_name = "Place"
        verbose_name_plural = "Places"
        ordering = ['place_name']
        constraints = [
            models.UniqueConstraint(fields=['place_name', 'district'], name='unique_place_per_district')
        ]

    def __str__(self):
        return f"{self.place_name} ({self.district.district_name})"


class tbl_scategary(models.Model):
    scategary_name = models.CharField(max_length=50)
    categary = models.ForeignKey(tbl_categary, on_delete=models.CASCADE, related_name='subcategories')

    class Meta:
        verbose_name = "Admin Subcategory"
        verbose_name_plural = "Admin Subcategories"
        ordering = ['scategary_name']

    @property
    def subcategory_name(self):
        return self.scategary_name

    def __str__(self):
        return self.scategary_name
