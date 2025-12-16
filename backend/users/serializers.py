from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.contrib.auth import authenticate, get_user_model
from django.core.validators import RegexValidator

User = get_user_model()
# REGISTER SERIALIZER
class RegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "username",
            "password",
            "confirm_password",
        )
        extra_kwargs = {
            "password": {"write_only": True}
        }

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"]
        )
        return user
# GET OTP SERIALIZER
class GetOTPSerializer(serializers.Serializer):
    mobile = serializers.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r"^\d{10}$",
                message="Enter valid 10 digit mobile number"
            )
        ]
    )
# VERIFY OTP (USER VERIFY)
class VerifyOTPSerializer(serializers.Serializer):
    otp = serializers.CharField(
        min_length=4,
        max_length=6
    )
# LOGIN SERIALIZER
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs.get("username"),
            password=attrs.get("password")
        )

        if not user:
            raise ValidationError("Invalid username or password.")

        if not user.is_verified:
            raise ValidationError("User is not verified. Please verify OTP.")

        attrs["user"] = user
        return attrs
# USER DETAIL SERIALIZER
class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "mobile",
            "is_verified",
        )
# CHANGE PASSWORD SERIALIZER
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise ValidationError(
                {"confirm_new_password": "New passwords do not match."}
            )
        return attrs
# FORGOT PASSWORD (MOBILE INPUT)
class ForgotPasswordMobileSerializer(serializers.Serializer):
    mobile = serializers.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r"^\d{10}$",
                message="Enter valid 10 digit mobile number"
            )
        ]
    )
# PASSWORD RESET OTP VERIFY 
class PasswordResetOTPVerifySerializer(serializers.Serializer):
    mobile = serializers.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r"^\d{10}$",
                message="Enter valid 10 digit mobile number"
            )
        ]
    )
    otp = serializers.CharField(
        min_length=4,
        max_length=6
    )
# SET NEW PASSWORD AFTER OTP VERIFIED
class SetNewPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise ValidationError(
                {"confirm_new_password": "Passwords do not match."}
            )
        return attrs
