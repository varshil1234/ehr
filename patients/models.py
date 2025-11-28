from django.db import models
from django.conf import settings
from utils.encryption import AESCipher, is_base64
import base64

class Patient(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    GENDER_CHOICES = [("male","Male"), ("female","Female"), ("Other","Other")]
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES)
    contact_number = models.CharField(max_length=512, null=True, blank=True)  # store encrypted text
    address = models.TextField(null=True, blank=True)
    aadhar_number = models.CharField(max_length=512, unique=True)  # store encrypted text
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="patient_profile", null=True, blank=True)

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
        # If we have a key and contact_number is plain (not base64-like), encrypt it.
        # We try to avoid double-encrypting by detecting base64-looking strings:
        if key:
            cipher = AESCipher(key)
            # encrypt contact_number if it's not already an encrypted blob (heuristic)
            if self.contact_number:
                try:
                    # If it decodes as base64 and has expected structure, assume encrypted -> skip
                    base64.b64decode(self.contact_number)
                    # We won't attempt decrypt here; assume it's already encrypted.
                    # If you want stricter checks, try decrypting here and on failure re-encrypt.
                except Exception:
                    # not base64 -> encrypt
                    self.contact_number = cipher.encrypt(self.contact_number)
            if self.aadhar_number:
                try:
                    base64.b64decode(self.aadhar_number)
                except Exception:
                    self.aadhar_number = cipher.encrypt(self.aadhar_number)
        # else: no user key available; you may choose to deny save or store plaintext (not recommended)
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
    def contact_number_decrypted(self):
        return self._decrypt_field(self.contact_number)

    @property
    def aadhar_number_decrypted(self):
        return self._decrypt_field(self.aadhar_number)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Vital(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="vitals")
    recorded_at = models.DateTimeField(auto_now_add=True)
    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    blood_pressure = models.IntegerField(null=True, blank=True)
    heart_rate_bpm = models.IntegerField(null=True, blank=True)
    temperature_celsius = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Vitals for {self.patient}"


class MedicalHistory(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="medical_histories")
    TYPE_OF_CHOICES = [("disease","Disease"), ("surgery","Surgery"), ("allergy","Allergy"), ("Other","Other")]
    type_of = models.CharField(max_length=256, choices=TYPE_OF_CHOICES)
    description = models.TextField()
    diagnosis_code = models.CharField(max_length=256, null=True, blank=True)
    event_date = models.DateField()
    STATUS_CHOICES = [("active","Active"), ("resolved","Resolved"), ("chronic","Chronic")]
    status = models.CharField(max_length=256, choices=STATUS_CHOICES)
    notes = models.TextField(null=True, blank=True)

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
            for field in ['type_of', 'description', 'diagnosis_code', 'status', 'notes']:
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
    def type_of_decrypted(self):
        return self._decrypt_field(self.type_of)

    @property
    def description_decrypted(self):
        return self._decrypt_field(self.description)

    @property
    def diagnosis_code_decrypted(self):
        return self._decrypt_field(self.diagnosis_code)

    @property
    def status_decrypted(self):
        return self._decrypt_field(self.status)

    @property
    def notes_decrypted(self):
        return self._decrypt_field(self.notes)

    def __str__(self):
        return f"{self.patient}"