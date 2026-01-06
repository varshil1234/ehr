from django.utils import timezone
from datetime import timedelta
from .models import OTP
from .constants import (
    OTP_EXPIRY_TIME,
    OTP_RESEND_INTERVAL,
    OTP_MAX_PER_HOUR
)
import random

def generate_otp():
    return str(random.randint(100000, 999999))


def can_send_otp(user, purpose):
    now = timezone.now()

    # 1️⃣ Cooldown check (1 OTP per minute)
    recent_otp = OTP.objects.filter(
        user=user,
        purpose=purpose,
        created_at__gte=now - OTP_RESEND_INTERVAL
    ).exists()

    if recent_otp:
        return False, "OTP already sent recently. Please wait before retrying."

    # 2️⃣ Hourly limit
    hourly_count = OTP.objects.filter(
        user=user,
        purpose=purpose,
        created_at__gte=now - timedelta(hours=1)
    ).count()

    if hourly_count >= OTP_MAX_PER_HOUR:
        return False, "OTP limit exceeded. Try again later."

    return True, None


def is_otp_expired(otp_obj):
    return otp_obj.created_at < timezone.now() - OTP_EXPIRY_TIME


def send_otp(mobile, otp):
    # Integrate SMS gateway here
    print(f"Sending OTP {otp} to {mobile}")
