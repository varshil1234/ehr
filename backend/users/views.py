from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, LoginSerializer,UserSerializer
from rest_framework.viewsets import ModelViewSet
from .models import User, OTP
from .utils import generate_otp, send_otp, can_send_otp, is_otp_expired

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({
            "message": "User registered successfully",
            "user_id": user.id
        }, status=201)

class SendVerificationOTP(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get("user_id")

        if not user_id:
            return Response({"error": "user_id is required"}, status=400)

        user = get_object_or_404(User, id=user_id)

        if user.is_verified:
            return Response({"error": "User already verified"}, status=400)

        mobile = user.mobile_number or user.relative_mobile_number
        if not mobile:
            return Response(
                {"error": "No mobile number available"},
                status=400
            )

        allowed, error = can_send_otp(user, "verification")
        if not allowed:
            return Response({"error": error}, status=429)

        otp_code = generate_otp()

        OTP.objects.create(
            user=user,
            otp=otp_code,
            purpose="verification"
        )

        send_otp(mobile, otp_code)

        return Response({"message": "OTP sent successfully"})

class VerifyOTP(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get("user_id")
        otp = request.data.get("otp")

        if not user_id or not otp:
            return Response(
                {"error": "user_id and otp are required"},
                status=400
            )

        user = get_object_or_404(User, id=user_id)

        otp_obj = OTP.objects.filter(
            user=user,
            otp=otp,
            purpose="verification",
            is_used=False
        ).first()

        if not otp_obj:
            return Response(
                {"error": "Invalid OTP"},
                status=400
            )

        if is_otp_expired(otp_obj):
            return Response(
                {"error": "OTP expired"},
                status=400
            )

        otp_obj.is_used = True
        otp_obj.save(update_fields=["is_used"])

        user.is_verified = True
        user.save(update_fields=["is_verified"])

        return Response({"message": "OTP verified successfully"})

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "username": user.username,
                "is_verified": user.is_verified,
                "mobile_number": user.mobile_number,
            }
        }, status=status.HTTP_200_OK)

class PasswordResetOTP(APIView):
    def post(self, request):
        username = request.data.get('username')
        user = User.objects.filter(username=username).first()

        if not user:
            return Response({"error": "User not found"}, status=404)
        
        allowed, error = can_send_otp(user, "password_reset")
        if not allowed:
            return Response({"error": error}, status=429)

        otp = generate_otp()
        OTP.objects.create(user=user, otp=otp, purpose='password_reset')

        send_otp(user.mobile_number or user.relative_mobile_number, otp)
        return Response({"message": "OTP sent"})
    
class ResetPassword(APIView):
    def post(self, request):
        username = request.data.get('username')
        otp = request.data.get('otp')
        new_password = request.data.get('password')

        user = User.objects.filter(username=username).first()

        otp_obj = OTP.objects.filter(
            user=user,
            otp=otp,
            purpose='password_reset',
            is_used=False
        ).first()

        if not otp_obj:
            return Response({"error": "Invalid OTP"}, status=400)
        
        if is_otp_expired(otp_obj):
            return Response({"error": "OTP expired"}, status=400)
        
        if not new_password:
            return Response({"error": "Password is required"}, status=400)
        
        if len(new_password) < 8:
            return Response({"error": "Password too short"}, status=400)

        user.set_password(new_password)
        user.save()

        otp_obj.is_used = True
        otp_obj.save()

        return Response({"message": "Password reset successful"})

class UserModelView(ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch"]

    def get_queryset(self):
        return User.objects.filter(
            is_staff=False,
            is_superuser=False
        )

    def get_serializer_class(self):
        return UserSerializer

    # 🔹 GET
    def list(self, request, *args, **kwargs):
        user_id = request.query_params.get("id")
        queryset = self.get_queryset()

        # 🔹 Single user
        if user_id:
            user = get_object_or_404(queryset, id=user_id)
            serializer = self.get_serializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # 🔹 ALL REGISTERED USERS (NO MESSAGE)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 🔹 PATCH
    def partial_update(self, request, *args, **kwargs):
        user_id = request.query_params.get("id")

        if not user_id:
            return Response(
                {"message": "id query param required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = get_object_or_404(self.get_queryset(), id=user_id)

        serializer = self.get_serializer(
            user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "User updated successfully"},
            status=status.HTTP_200_OK
        )