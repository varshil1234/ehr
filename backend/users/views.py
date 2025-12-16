import logging
from datetime import timedelta
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import ValidationError
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from .serializers import (
    RegisterSerializer,
    GetOTPSerializer,
    VerifyOTPSerializer,
    LoginSerializer,
    UserDetailSerializer,
    ForgotPasswordMobileSerializer,
    PasswordResetOTPVerifySerializer,
    SetNewPasswordSerializer
)

User = get_user_model()
logger = logging.getLogger("users")
# PAGINATION
class UserPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 50
# USER CRUD (SAFE)
class UserViewSet(viewsets.ModelViewSet):
    """
    SAFE USER LIST:
    - Authenticated only
    - No staff/superuser
    - Paginated
    - No sensitive data
    """
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = UserPagination
    http_method_names = ["get"]

    def get_queryset(self):
        return User.objects.filter(
            is_staff=False,
            is_superuser=False
        ).order_by("id")
# REGISTER
class RegisterAPIView(APIView):

    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        logger.info(
            "USER_REGISTERED",
            extra={"user_id": user.id}
        )

        return Response(UserDetailSerializer(user).data, status=201)

# OTP (VERIFY MOBILE)
class UserOTPAPIView(APIView):

    def post(self, request, user_id):
        serializer = GetOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValidationError({"detail": "User not found"})

        if user.is_verified:
            return Response({"detail": "User already verified"}, status=400)

        if (
            user.last_otp_sent_at and
            timezone.now() - user.last_otp_sent_at < timedelta(minutes=1)
        ):
            return Response(
                {"detail": "Please wait 1 minute before requesting new OTP"},
                status=429
            )

        user.mobile = serializer.validated_data["mobile"]
        otp_data = user.generate_otp()
        user.save(update_fields=["mobile"])

        logger.info(
            "OTP_SENT",
            extra={
                "user_id": user.id,
                "mobile_last_2": user.mobile[-2:] if user.mobile else None
            }
        )

        response = {"detail": "OTP sent"}

        #  DEV MODE → show OTP
        if otp_data:
            response["otp_plain"] = otp_data["plain_otp"]
            response["otp_hashed"] = otp_data["hashed_otp"]

        return Response(response, status=200)


class VerifyOTPAPIView(APIView):

    def post(self, request, user_id):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValidationError({"detail": "User not found"})

        if not user.verify_otp(serializer.validated_data["otp"]):
            logger.warning(
                "OTP_FAILED",
                extra={"user_id": user.id}
            )
            return Response({"detail": "Invalid or expired OTP"}, status=400)

        user.is_verified = True
        user.otp = None
        user.otp_expires_at = None
        user.save()

        return Response(UserDetailSerializer(user).data)
# LOGIN
class LoginAPIView(APIView):

    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"]
        )

        if not user:
            logger.warning(
                "LOGIN_FAILED",
                extra={
                    "username": serializer.validated_data.get("username"),
                    "ip": request.META.get("REMOTE_ADDR")
                }
            )
            return Response({"detail": "Invalid credentials"}, status=401)

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserDetailSerializer(user).data
        })
# FORGOT PASSWORD
class ForgotPasswordOTPAPIView(APIView):

    def post(self, request):
        serializer = ForgotPasswordMobileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(mobile=serializer.validated_data["mobile"])
        except User.DoesNotExist:
            return Response({"detail": "Mobile not found"}, status=400)

        otp_data = user.generate_otp()

        logger.info(
            "OTP_SENT_FORGOT_PASSWORD",
            extra={"user_id": user.id}
        )

        response = {"detail": "OTP sent"}

        #  DEV MODE → show OTP
        if otp_data:
            response["otp_plain"] = otp_data["plain_otp"]
            response["otp_hashed"] = otp_data["hashed_otp"]

        return Response(response)


class ForgotPasswordVerifyAPIView(APIView):

    def post(self, request):
        serializer = PasswordResetOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(mobile=serializer.validated_data["mobile"])
        except User.DoesNotExist:
            return Response({"detail": "Invalid mobile"}, status=400)

        if not user.verify_otp(serializer.validated_data["otp"]):
            logger.warning(
                "OTP_FAILED_FORGOT_PASSWORD",
                extra={"user_id": user.id}
            )
            return Response({"detail": "Invalid OTP"}, status=400)

        return Response({"user_id": user.id})


class SetNewPasswordAPIView(APIView):

    def post(self, request):
        serializer = SetNewPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(id=request.data.get("user_id"))
        except User.DoesNotExist:
            return Response({"detail": "Invalid user"}, status=400)

        user.password = make_password(serializer.validated_data["new_password"])
        user.save()

        logger.info(
            "PASSWORD_RESET_SUCCESS",
            extra={"user_id": user.id}
        )

        return Response({"detail": "Password reset successful"})
