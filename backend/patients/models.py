from django.db import models
from users.models import User

class Patient(models.Model):

    GENDER_CHOICES = (
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="patient"
    )

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    dob = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    pincode = models.CharField(max_length=6)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

# Patient Vitals
class PatientVital(models.Model):

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="vitals"
    )

    # encrypted values
    height_cm = models.TextField(blank=True, null=True)
    weight_kg = models.TextField(blank=True, null=True)
    blood_pressure = models.TextField(blank=True, null=True)
    heart_rate_bpm = models.TextField(blank=True, null=True)
    temperature_celsius = models.TextField(blank=True, null=True)

    # derived
    bmi = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["patient"]),
            models.Index(fields=["created_at"]),
        ]

    def heart_rate(self):
        from backend.utils.encryption import decrypt_int
        return decrypt_int(self.heart_rate_bpm)

    def __str__(self):
        return f"Vitals {self.id} - Patient {self.patient_id}"

# Medical History
class MedicalHistory(models.Model):

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="medical_histories"
    )

    # encrypted text values
    type_of = models.TextField()
    description = models.TextField()
    diagnosis_code = models.TextField(blank=True, null=True)
    event_date = models.DateField()
    status = models.TextField()
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-event_date", "-created_at"]
        indexes = [
            models.Index(fields=["patient"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"MedicalHistory({self.id}) - Patient({self.patient_id})"

# Medical Follow Up
class MedicalFollowUp(models.Model):

    medical_history = models.ForeignKey(
        MedicalHistory,
        on_delete=models.CASCADE,
        related_name="followups"
    )

    patient_complaints = models.TextField(blank=True, null=True)
    clinical_findings = models.TextField(blank=True, null=True)
    diagnosis = models.TextField(blank=True, null=True)
    advice = models.TextField(blank=True, null=True)

    followup_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["medical_history"]),
            models.Index(fields=["created_at"]),
        ]

# Follow Up Medicines
class FollowUpMedicine(models.Model):

    followup = models.ForeignKey(
        MedicalFollowUp,
        on_delete=models.CASCADE,
        related_name="medicines"
    )

    name = models.TextField()
    dose = models.TextField()
    duration = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["followup"]),
            models.Index(fields=["created_at"]),
        ]
