from django.urls import path
from .views import *

users = UserViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('send-otp/', SendVerificationOTP.as_view()),
    path('verify-otp/', VerifyOTP.as_view()),
    path('login/', LoginView.as_view(), name='login'),
    path('password-reset-otp/', PasswordResetOTP.as_view()),
    path('reset-password/', ResetPassword.as_view()),
    path('', users, name='users'),
    path('<int:pk>/', UserViewSet.as_view({'patch': 'partial_update'}), name='update-user')
]
