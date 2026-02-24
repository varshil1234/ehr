import os
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from patients.models import Patient

class Insurance(models.Model):

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="insurances"
    )

    provider_name = models.TextField()
    policy_number = models.TextField()
    coverage_type = models.TextField()
    coverage_amount = models.TextField()

    validity_start = models.DateField()
    validity_end = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-validity_end", "-created_at"]
        indexes = [
            models.Index(fields=["patient"]),
            models.Index(fields=["validity_end"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Insurance({self.id}) - Patient({self.patient_id})"


class InsuranceDocument(models.Model):
    insurance = models.ForeignKey(
        Insurance,
        on_delete=models.CASCADE,
        related_name="documents"
    )

    # FIX: Saves exactly to media/insurance/<FILENAME.pdf>
    document = models.FileField(upload_to="insurance/")
    document_name = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["insurance"]),
        ]

    def __str__(self):
        return f"Doc {self.id} for Insurance {self.insurance_id}"

@receiver(post_delete, sender=InsuranceDocument)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    #Delete file from filepath
    if instance.document:
        if os.path.isfile(instance.document.path):
            os.remove(instance.document.path)