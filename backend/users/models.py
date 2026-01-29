from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from .managers import UserManager
from django.utils import timezone
from datetime import timedelta

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
    ("patient", "Patient"),
    ("doctor", "Doctor"),
    ("labtechnician", "Lab Technician"),
)

    role = models.CharField(
    max_length=20,
    choices=ROLE_CHOICES,
    null=True,
    blank=True   
)
    username = models.CharField(max_length=150, unique=True)
    mobile_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    relative_mobile_number = models.CharField(max_length=15, null=True, blank=True)

    is_verified = models.BooleanField(default=False)

    failed_login_attempts = models.PositiveIntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def is_locked(self):
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False

    def lock_account(self):
        self.account_locked_until = timezone.now() + timedelta(minutes=15)
        self.save(update_fields=['account_locked_until'])

    def reset_login_attempts(self):
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.save(update_fields=['failed_login_attempts', 'account_locked_until'])

class OTP(models.Model):
    PURPOSE_CHOICES = (
        ('verification', 'Verification'),
        ('password_reset', 'Password Reset'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.purpose}"
