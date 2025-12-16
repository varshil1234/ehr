from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()
class AuthenticationFlowTests(APITestCase):
 
    """
    Tests for:
    - OTP generation & expiry
    - Login with verified / unverified users
    - Password reset flow
    """

    def setUp(self):
        # Unverified user
        self.user = User.objects.create_user(
            username="testuser",
            password="Test@123"
        )

        # Verified user
        self.verified_user = User.objects.create_user(
            username="verifieduser",
            password="Test@123",
            is_verified=True
        )
    # OTP GENERATION & EXPIRY
    def test_otp_generation(self):
        self.user.generate_otp()

        self.assertIsNotNone(self.user.otp)
        self.assertIsNotNone(self.user.otp_expires_at)
        self.assertTrue(self.user.otp_expires_at > timezone.now())

    def test_otp_expiry(self):
        self.user.generate_otp()
        
        self.user.otp_expires_at = timezone.now() - timedelta(minutes=1)
        self.user.save()

        is_valid = self.user.verify_otp(self.user.otp)
        self.assertFalse(is_valid)
    # LOGIN TESTS
    def test_login_unverified_user_fails(self):
        url = "login/"
        data = {
            "username": "testuser",
            "password": "Test@123"
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_verified_user_success(self):
        url = "login/"
        data = {
            "username": "verifieduser",
            "password": "Test@123"
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
    # PASSWORD RESET FLOW
    def test_forgot_password_flow(self):
        # Step 1: Send OTP
        send_otp_url = "forgot-password/"
        response = self.client.post(
            send_otp_url,
            {"mobile": self.verified_user.mobile},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.verified_user.refresh_from_db()
        otp = self.verified_user.otp

        # Step 2: Verify OTP
        verify_otp_url = "forgot-password-verify/"
        response = self.client.post(
            verify_otp_url,
            {
                "mobile": self.verified_user.mobile,
                "otp": otp
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_id = response.data["user_id"]

        # Step 3: Set new password
        set_password_url = "set-new-password/"
        response = self.client.post(
            set_password_url,
            {
                "user_id": user_id,
                "new_password": "NewPass@123",
                "confirm_new_password": "NewPass@123"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Step 4: Login with new password
        login_url = "login/"
        response = self.client.post(
            login_url,
            {
                "username": self.verified_user.username,
                "password": "NewPass@123"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
