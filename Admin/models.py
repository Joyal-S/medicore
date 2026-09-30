from django.db import models


class tbl_district(models.Model):
    district_name = models.CharField(max_length=50)

    def __str__(self):
        return self.district_name


class tbl_adminregistration(models.Model):
    registration_name = models.CharField(max_length=50)
    registration_email = models.CharField(max_length=50)
    registration_photo = models.FileField(upload_to="Assets/Files/admin", null=True, blank=True)
    registration_password = models.CharField(max_length=128)

    def __str__(self):
        return self.registration_name


class tbl_categary(models.Model):
    categary_name = models.CharField(max_length=50)

    @property
    def category_name(self):
        return self.categary_name

    def __str__(self):
        return self.categary_name


class tbl_place(models.Model):
    place_name = models.CharField(max_length=50)
    district = models.ForeignKey(tbl_district, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.place_name} ({self.district.district_name})"


class tbl_scategary(models.Model):
    scategary_name = models.CharField(max_length=50)
    categary = models.ForeignKey(tbl_categary, on_delete=models.CASCADE)

    @property
    def subcategory_name(self):
        return self.scategary_name

    def __str__(self):
        return self.scategary_name
