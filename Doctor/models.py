from django.db import models
from User.models import tbl_request
from Guest.models import tbl_doctor


class tbl_disease(models.Model):
    disease_name = models.CharField(max_length=100)
    disease_symptoms = models.TextField()
    reqpre = models.ForeignKey(tbl_request, on_delete=models.CASCADE)
    doctor = models.ForeignKey(tbl_doctor, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.disease_name} (Patient Request #{self.reqpre_id})"
