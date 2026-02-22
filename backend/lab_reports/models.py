from django.db import models
from patients.models import Patient
import os

class LabReport(models.Model):
    
    # TEST TYPE CHOICES
    TEST_TYPE_CHOICES = (
        ("cbc", "CBC Report"),
        ("mri", "MRI Report"),
        ("xray", "X-Ray Report"),
        ("blood", "Blood Test"),
        ("urine", "Urine Test"),
        ("other", "Other"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("ready", "Ready"),
    )

    PRIORITY_CHOICES = (
        ("routine", "Routine"),
        ("urgent", "Urgent"),
    )

    # MAIN FIELDS
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="lab_reports"
    )

    test_type = models.CharField(
        max_length=20,
        choices=TEST_TYPE_CHOICES,
        null=True,
        blank=True
    )

    lab_name = models.CharField(
        max_length=150,
        null=True,
        blank=True
    )

    report_date = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="routine"
    )

    notes = models.TextField(
        blank=True,
        null=True
    )

    # FILE UPLOAD FIELD
    report_file = models.FileField(
        upload_to="lab_reports/%Y/%m/",
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    # DELETE METHOD (REMOVE FILE FROM MEDIA)
    def delete(self, *args, **kwargs):

        if self.report_file:
            file_path = self.report_file.path

            if os.path.isfile(file_path):
                os.remove(file_path)

        super().delete(*args, **kwargs)

    # SAVE METHOD (REPLACE OLD FILE SAFELY)
    def save(self, *args, **kwargs):

        try:
            old_instance = LabReport.objects.get(pk=self.pk)

            if old_instance.report_file and old_instance.report_file != self.report_file:
                if os.path.isfile(old_instance.report_file.path):
                    os.remove(old_instance.report_file.path)

        except LabReport.DoesNotExist:
            pass

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.test_type} - Patient {self.patient_id}"
