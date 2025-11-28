from django.urls import path
from .views import LoginViewSet, UserViewSet, MyAccountViewSet

myaccount = MyAccountViewSet.as_view({
    'get': 'list',
    'patch': 'update'
})

users = UserViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

urlpatterns = [
    # Authentication endpoints
    path('login/', LoginViewSet.as_view({'post': 'login'})),

    # Refresh token endpoint
    path('token/refresh/', LoginViewSet.as_view({'post': 'refresh'})),

    # User management endpoints
    path('', users, name='users'),
    path('<int:pk>/verify-otp/', UserViewSet.as_view({'post': 'verify_otp'}), name='verify-otp'),
    path('<int:pk>/resend-otp/', UserViewSet.as_view({'post': 'resend_otp'}), name='resend-otp'),

    # My account endpoints
    path("my-account/", myaccount, name="myaccount"),
]
