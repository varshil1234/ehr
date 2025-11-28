from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.contrib.auth.base_user import BaseUserManager
from cryptography.fernet import Fernet
from django.conf import settings
from patients.models import Patient
from doctors.models import Doctor
import base64
import os
import random
import string
from datetime import timedelta
from django.utils import timezone

# Custom User Manager
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


# Custom User Model
class CustomUser(AbstractUser):
    # remove default fields
    username = None
    first_name = None
    last_name = None
    
    email = models.EmailField(_("email"), unique=True)

    # Role field
    ROLE_CHOICES = [
        ("patient", "Patient"),
        ("family_head", "Family Head"),
        ("doctor", "Doctor"),
        ("lab_admin", "Lab Admin"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, null=True, blank=True)
    user_key = models.CharField(max_length=256, editable=False, unique=True, blank=True, null=True)
    linked_patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True)
    linked_doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_expires_at = models.DateTimeField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def generate_user_key(self):
        # Generate a 32-byte AES key and store it encrypted
        user_key = os.urandom(32)
        f = Fernet(settings.MASTER_KEY.encode())
        encrypted = f.encrypt(base64.b64encode(user_key))
        self.user_key = encrypted.decode()
        return user_key

    def get_user_key(self):
        # Decrypt and return the user's AES key
        if not self.user_key:
            return None
        f = Fernet(settings.MASTER_KEY.encode())
        decrypted = f.decrypt(self.user_key.encode())
        return base64.b64decode(decrypted)
    
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
            self.otp == str(otp) and
            self.otp_expires_at and
            timezone.now() <= self.otp_expires_at
        )

    # Auth setup
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.email}"
    
    def save(self, *args, **kwargs):
        # Ensure user_key is generated on save if not present
        if not self.user_key:
            self.generate_user_key()
        super().save(*args, **kwargs)

