from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.hashers import make_password

User = get_user_model()

class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            raise ValidationError({"type": "error", "detail": "Must include both email and password."})

        user = authenticate(username=email, password=password)
        if not user:
            raise AuthenticationFailed({"type": "error", "detail": "Unable to log in with provided credentials."})
        
        if not user.is_active:
            raise PermissionDenied({"type": "error", "detail": "User account is disabled."})

        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # TODO: remove "otp" from fields in production
        fields = ['id', 'email', 'password', 'otp', 'date_joined', 'role', 'is_active']
        extra_kwargs = {
            "email": {"required": True},
            'password': {'write_only': True}
        }
        read_only_fields = ["is_active", "date_joined"]

    def create(self, validated_data):
        validated_data['is_staff'] = False
        validated_data['is_superuser'] = False
        validated_data['is_active'] = False  # User is not active until OTP verification

        if "password" in validated_data:
            validated_data["password"] = make_password(validated_data["password"])

        user = super().create(validated_data)

        # Generate and send OTP
        otp = user.generate_otp()
        # TODO: Create send email function to send OTP

        return user
    
    def update(self, instance, validated_data):
        if "password" in validated_data:
            validated_data["password"] = make_password(validated_data["password"])
        if "username" in validated_data:
            validated_data.pop('username')
        return super().update(instance, validated_data)
