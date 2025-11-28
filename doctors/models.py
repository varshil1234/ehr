from django.db import models
from django.conf import settings
from django.utils import timezone
from patients.models import Patient
from datetime import timedelta
from utils.encryption import AESCipher, is_base64
import random

# Create your models here.
class Doctor(models.Model):
    name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)
    hospital = models.CharField(max_length=100)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="doctor_profile", null=True, blank=True)

    def __str__(self):
        return self.name


class AccessRequest(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="access_requests")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="access_requests")
    is_approved = models.BooleanField(default=False)
    requested_at = models.DateTimeField(auto_now_add=True)

    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_expires_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['doctor', 'patient'],
                name='unique_doctor_patient_request'
            )
        ]

    def generate_otp(self):
        # Generate and store a 6-digit OTP with 10-min expiry
        otp = str(random.randint(100000, 999999))
        self.otp = otp
        self.otp_expires_at = timezone.now() + timedelta(minutes=10)
        self.save()
        return otp

    def verify_otp(self, otp):
        # Return True if OTP matches and is valid
        return (
            self.otp == otp and
            self.otp_expires_at and
            timezone.now() <= self.otp_expires_at
        )

    def __str__(self):
        return f"Access Request by {self.doctor.name} for Patient {self.patient}"


class Encounter(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="encounters")
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="encounters")
    date = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, null=True)
    summary = models.TextField(blank=True, null=True)

    @property
    def user(self):
        # Shortcut to access user from patient
        return getattr(self.patient, "user", None)
    
    def _get_user_key_bytes(self) -> bytes:
        """
        Return bytes key for AES. Ensure your `get_user_key()` returns appropriate bytes.
        If it returns hex or str, adapt accordingly.
        """
        # Example: assume user.get_user_key() returns a bytes object of correct length.
        if self.user and hasattr(self.user, "get_user_key"):
            return self.user.get_user_key()
        return None
    
    def save(self, *args, **kwargs):
        key = self._get_user_key_bytes()
        if key:
            cipher = AESCipher(key)
            for field in ['reason', 'summary']:
                val = getattr(self, field, None)
                if val and not is_base64(val):
                    setattr(self, field, cipher.encrypt(val))
        super().save(*args, **kwargs)

    # decrypted properties (never modify DB)
    def _decrypt_field(self, encrypted_value):
        key = self._get_user_key_bytes()
        if not encrypted_value or not key:
            return None
        cipher = AESCipher(key)
        try:
            return cipher.decrypt(encrypted_value)
        except Exception:
            # MAC check failed or corrupted value
            return "[Decryption Error]"

    @property
    def reason_decrypted(self):
        return self._decrypt_field(self.reason)

    @property
    def summary_decrypted(self):
        return self._decrypt_field(self.summary)

    def __str__(self):
        return f"Encounter on {self.date} between Dr. {self.doctor} and Patient {self.patient}"

    
class ClinicalNote(models.Model):
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name="clinical_notes")
    subjective = models.TextField(blank=True, null=True)
    objective = models.TextField(blank=True, null=True)
    assessment = models.TextField(blank=True, null=True)
    plan = models.TextField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def user(self):
        # Shortcut to access user from patient
        return getattr(self.encounter.patient, "user", None)
    
    def _get_user_key_bytes(self) -> bytes:
        """
        Return bytes key for AES. Ensure your `get_user_key()` returns appropriate bytes.
        If it returns hex or str, adapt accordingly.
        """
        # Example: assume user.get_user_key() returns a bytes object of correct length.
        if self.user and hasattr(self.user, "get_user_key"):
            return self.user.get_user_key()
        return None
    
    def save(self, *args, **kwargs):
        key = self._get_user_key_bytes()
        if key:
            cipher = AESCipher(key)
            for field in ['subjective', 'objective', 'assessment', 'plan', 'note']:
                val = getattr(self, field, None)
                if val and not is_base64(val):
                    setattr(self, field, cipher.encrypt(val))
        super().save(*args, **kwargs)

    # decrypted properties (never modify DB)
    def _decrypt_field(self, encrypted_value):
        key = self._get_user_key_bytes()
        if not encrypted_value or not key:
            return None
        cipher = AESCipher(key)
        try:
            return cipher.decrypt(encrypted_value)
        except Exception:
            # MAC check failed or corrupted value
            return "[Decryption Error]"

    @property
    def subjective_decrypted(self):
        return self._decrypt_field(self.subjective)

    @property
    def objective_decrypted(self):
        return self._decrypt_field(self.objective)
    
    @property
    def assessment_decrypted(self):
        return self._decrypt_field(self.assessment)
    
    @property
    def plan_decrypted(self):
        return self._decrypt_field(self.plan)
    
    @property
    def note_decrypted(self):
        return self._decrypt_field(self.note)

    def __str__(self):
        return f"Clinical Note for Encounter {self.encounter.id} created at {self.created_at}"
    