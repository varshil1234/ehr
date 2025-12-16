from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    RegisterAPIView,
    LoginAPIView,
    UserOTPAPIView,
    VerifyOTPAPIView,
    ForgotPasswordOTPAPIView,
    ForgotPasswordVerifyAPIView,
    SetNewPasswordAPIView,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    # User CRUD (list, retrieve) → ModelViewSet
    path('', include(router.urls)),

    # Auth / Account
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),

    # OTP (User verification)
    path('otp/<int:user_id>/', UserOTPAPIView.as_view(), name='get-otp'),
    path('otp-verify/<int:user_id>/', VerifyOTPAPIView.as_view(), name='verify-otp'),

    # Forgot password
    path('forgot-password/', ForgotPasswordOTPAPIView.as_view(), name='forgot-password-send-otp'),
    path('forgot-password-verify/', ForgotPasswordVerifyAPIView.as_view(), name='forgot-password-verify-otp'),
    path('set-new-password/', SetNewPasswordAPIView.as_view(), name='set-new-password'),
]
