from datetime import timedelta

OTP_EXPIRY_TIME = timedelta(minutes=5)
OTP_RESEND_INTERVAL = timedelta(seconds=60)
OTP_MAX_PER_HOUR = 5