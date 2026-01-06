from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import User

from django.db import IntegrityError
from rest_framework import serializers

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "password", "mobile_number", "relative_mobile_number")

    def create(self, validated_data):
        try:
            password = validated_data.pop("password")

            user = User.objects.create_user(
                username=validated_data["username"],
                password=password
            )

            user.mobile_number = validated_data.get("mobile_number") or None
            user.relative_mobile_number = validated_data.get("relative_mobile_number")
            user.save()

            return user

        except IntegrityError as e:
            # Convert DB error → DRF error
            if "mobile_number" in str(e):
                raise serializers.ValidationError({
                    "mobile_number": "This mobile number is already in use."
                })

            if "username" in str(e):
                raise serializers.ValidationError({
                    "username": "This username already exists."
                })

            raise serializers.ValidationError("Invalid data.")

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")

        # Fetch user FIRST
        user = User.objects.filter(username=username).first()

        if not user:
            raise serializers.ValidationError("Invalid credentials")

        # Check account lock
        if user.is_locked():
            raise serializers.ValidationError(
                "Account locked due to multiple failed attempts"
            )

        # Block unverified users
        if not user.is_verified:
            raise serializers.ValidationError(
                "Account not verified. Please verify OTP first."
            )

        # Authenticate password
        authenticated_user = authenticate(
            username=username,
            password=password
        )

        if not authenticated_user:
            # user EXISTS here, safe to update
            user.failed_login_attempts += 1

            if user.failed_login_attempts >= 5:
                user.lock_account()

            user.save(update_fields=[
                "failed_login_attempts",
                "account_locked_until"
            ])

            raise serializers.ValidationError("Invalid credentials")

        # Check active status
        if not user.is_active:
            raise serializers.ValidationError("Account disabled")

        # Reset counters on success
        user.reset_login_attempts()

        data["user"] = user
        return data
