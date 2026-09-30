from django.db import models
from User.models import tbl_request
from Guest.models import tbl_doctor


class tbl_disease(models.Model):
    disease_name = models.CharField(max_length=100)
    disease_symptoms = models.TextField()
    reqpre = models.ForeignKey(tbl_request, on_delete=models.CASCADE, related_name='disease_predictions')
    doctor = models.ForeignKey(tbl_doctor, on_delete=models.CASCADE, related_name='disease_predictions')

    class Meta:
        verbose_name = "Disease Prediction Record"
        verbose_name_plural = "Disease Prediction Records"
        ordering = ['-id']

    @property
    def consultation_request(self):
        return self.reqpre

    def __str__(self):
        return f"{self.disease_name} (Patient Request #{self.reqpre_id})"
