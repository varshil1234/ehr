from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from .serializers import LoginSerializer, UserSerializer
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class LoginViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data
        
        # Create JWT tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        return Response(
            {
                "type": "success",
                "detail": "Login successful",
                "data": {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role,
                    "refresh_token": str(refresh),
                    "access_token": str(access),
                },
            },
            status=status.HTTP_200_OK,
        )
    
    @action(detail=False, methods=['post'])
    def refresh(self, request):
        # Custom refresh endpoint similar to /api/token/refresh/
        refresh_token = request.data.get("refresh_token")

        if not refresh_token:
            return Response(
                {"type": "error", "detail": "Refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(refresh_token)
            new_access = refresh.access_token
            return Response(
                {
                    "type": "success",
                    "detail": "Token refreshed successfully",
                    "access_token": str(new_access),
                },
                status=status.HTTP_200_OK,
            )
        except TokenError:
            return Response(
                {"type": "error", "detail": "Invalid or expired refresh token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['email', 'role']
    ordering_fields = ['id', 'name']
    search_fields = ['id']

    def get_queryset(self):
        return User.objects.filter(is_superuser=False, is_staff=False)

    def get_permissions(self):
        # Allow anyone to create, but restrict other actions to authenticated users
        if self.action in ["create", "resend_otp", "verify_otp"]:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=["post"], url_path="verify-otp")
    def verify_otp(self, request, pk=None):
        # Verify OTP for account activation
        user = self.get_object()
        otp = request.data.get("otp")

        if not otp:
            raise ValidationError({"detail": "OTP is required"})

        if not user.verify_otp(otp):
            raise ValidationError({"detail": "OTP is invalid or expired"})

        user.is_active = True
        user.is_verified = True
        user.otp = None
        user.otp_expires_at = None
        user.save()

        return Response({"detail": "User verified successfully."}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=["post"], url_path="resend-otp")
    def resend_otp(self, request, pk=None):
        # Fetch the user using the URL pk
        user = self.get_object()

        # Prevent OTP spam — allow resend only after 10 minute
        if (
            user.otp_expires_at
            and user.otp_expires_at > timezone.now()
            and user.otp_expires_at - timedelta(minutes=9) > timezone.now()
        ):
            return Response(
                {"detail": "OTP was recently sent. Please wait before resending."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        if user.is_verified:
            return Response(
                {"detail": "User is already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate a new OTP
        otp = user.generate_otp()

        # TODO: Send OTP via email to user.email
        # send_email(subject="Your OTP", message=f"Your OTP is {otp}", recipient_list=[user.email])

        return Response(
            {"detail": "A new OTP has been sent to your registered email."},
            status=status.HTTP_200_OK
        )
    

class MyAccountViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    ordering_fields = ['id']
    search_fields = ['id']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)
    
    def get_object(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            raise NotFound(detail="User not found", code="user_not_found")
        return user
    
    @action(detail=False, methods=["patch", "put"])
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    @action(detail=False, methods=["delete"])
    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user.delete()
        return Response(
            {"type": "success", "detail": "Your account has been deleted."},
            status=status.HTTP_204_NO_CONTENT
        )
    
    def handle_exception(self, exc):
        """
        Customize error responses for this viewset only
        """
        if hasattr(exc, "status_code"):
            if exc.status_code == 401:
                return Response(
                    {"type": "error", "detail": "Authentication credentials were not provided or invalid."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            elif exc.status_code == 404:
                return Response(
                    {"type": "error", "detail": "User not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # fallback to default behavior for other errors (400, 500, etc.)
        return super().handle_exception(exc)
