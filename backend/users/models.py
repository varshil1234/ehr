from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from datetime import timedelta
import random

from django.contrib.auth.hashers import make_password, check_password

from django.conf import settings
# CUSTOM USER MANAGER
class CustomUserManager(BaseUserManager):

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required")

        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(username, password, **extra_fields)

# CUSTOM USER MODEL (FINAL)
class CustomUser(AbstractUser):

    # ✅ Explicitly redefine base fields (DO NOT set to None)
    email = models.EmailField(blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    # Custom fields
    username = models.CharField(max_length=150, unique=True)
    mobile = models.CharField(max_length=15, unique=True, null=True, blank=True)

    # OTP fields
    otp = models.CharField(max_length=128, null=True, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    last_otp_sent_at = models.DateTimeField(null=True, blank=True) 

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.username
    # GENERATE OTP (HASHED)
    def generate_otp(self):
        otp = str(random.randint(100000, 999999))
        self.otp = make_password(otp)
        self.otp_expires_at = timezone.now() + timedelta(minutes=10)
        self.save(update_fields=["otp", "otp_expires_at"])
        
        
        if settings.DEBUG:
         return {
                "plain_otp": otp,
                "hashed_otp": self.otp
                }

        return None
          # VERIFY OTP
    def verify_otp(self, otp):
        if not self.otp or not self.otp_expires_at:
            return False

        if timezone.now() > self.otp_expires_at:
            return False

        return check_password(otp, self.otp)

