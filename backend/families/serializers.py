import re
import logging
from rest_framework import serializers
from .models import Family, FamilyMember
import random
from django.utils import timezone
from users.models import OTP
from patients.models import Patient

logger = logging.getLogger(__name__)

# Family Serializer
class FamilySerializer(serializers.ModelSerializer):

    class Meta:
        model = Family
        fields = (
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate_name(self, value):

        if not value or not value.strip():
            raise serializers.ValidationError(
                "Family name cannot be empty."
            )

        pattern = r"^[A-Za-z\s\-]+$"

        if not re.match(pattern, value.strip()):
            raise serializers.ValidationError(
                "Family name can contain only letters, spaces and hyphens."
            )

        return value.strip().title()

    def validate(self, attrs):

        request = self.context.get("request")

        if not hasattr(request.user, "patient"):
            raise serializers.ValidationError(
                "Only patients can create families."
            )

        patient = request.user.patient
        name = attrs.get("name")

        qs = Family.objects.filter(
            head_of_family=patient,
            name__iexact=name
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError({
                "name": "You already have a family with this name."
            })

        return attrs

# Send OTP Serializer
class SendFamilyMemberOTPSerializer(serializers.Serializer):

    patient_id = serializers.IntegerField()
    family_id = serializers.IntegerField()

    def create(self, validated_data):

        request = self.context["request"]

        patient = Patient.objects.select_related(
            "user"
        ).filter(
            id=validated_data["patient_id"]
        ).first()

        family = Family.objects.filter(
            id=validated_data["family_id"]
        ).first()

        if not patient or not family:
            raise serializers.ValidationError(
                "Invalid patient or family."
            )

        # Only family head can send OTP
        if family.head_of_family != request.user.patient:
            raise serializers.ValidationError(
                "Only family head can send OTP."
            )

        # Head does not need OTP
        if patient == family.head_of_family:
            raise serializers.ValidationError(
                "Family head does not require OTP."
            )

        # Already in family
        if FamilyMember.objects.filter(
            patient=patient
        ).exists():
            raise serializers.ValidationError(
                "Patient already belongs to a family."
            )

        user = patient.user

        mobile = (
            user.mobile_number
            or user.relative_mobile_number
        )

        if not mobile:
            raise serializers.ValidationError(
                "No mobile number found."
            )

        otp = str(random.randint(100000, 999999))

        OTP.objects.create(
            user=user,
            otp=otp,
            purpose="family_member_add"
        )

        print(f"[FAMILY OTP] {mobile} → OTP: {otp}")

        return {"detail": "OTP sent successfully."}

# Verify OTP Serializer
class VerifyFamilyMemberOTPSerializer(serializers.Serializer):

    patient_id = serializers.IntegerField()
    family_id = serializers.IntegerField()
    otp = serializers.CharField()

    def validate(self, attrs):

        patient = Patient.objects.select_related(
            "user"
        ).filter(
            id=attrs["patient_id"]
        ).first()

        family = Family.objects.filter(
            id=attrs["family_id"]
        ).first()

        if not patient or not family:
            raise serializers.ValidationError(
                "Invalid patient or family."
            )

        otp_obj = OTP.objects.filter(
            user=patient.user,
            otp=attrs["otp"],
            purpose="family_member_add",
            is_used=False
        ).order_by("-created_at").first()

        if not otp_obj:
            raise serializers.ValidationError(
                "Invalid OTP."
            )

        expiry_time = otp_obj.created_at + timezone.timedelta(minutes=5)

        if timezone.now() > expiry_time:
            raise serializers.ValidationError(
                "OTP expired."
            )

        attrs["otp_obj"] = otp_obj
        attrs["patient"] = patient
        attrs["family"] = family

        return attrs

    def create(self, validated_data):

        otp_obj = validated_data["otp_obj"]

        otp_obj.is_used = True

        otp_obj.save(
            update_fields=["is_used"]
        )

        return {
            "detail": "OTP verified successfully."
        }

# Add Family Member Serializer
class AddFamilyMemberSerializer(serializers.ModelSerializer):

    class Meta:
        model = FamilyMember
        fields = (
            "id",
            "family",
            "patient",
            "relation"
        )

    def validate(self, attrs):

        request = self.context["request"]

        family = attrs["family"]
        patient = attrs["patient"]

        if family.head_of_family != request.user.patient:
            raise serializers.ValidationError(
                "Only family head can add members."
            )

        if patient == family.head_of_family:
            raise serializers.ValidationError(
                "Family head already exists."
            )

        otp_used = OTP.objects.filter(
            user=patient.user,
            purpose="family_member_add",
            is_used=True
        ).exists()

        if not otp_used:
            raise serializers.ValidationError(
                "OTP verification required."
            )

        if FamilyMember.objects.filter(
            patient=patient
        ).exists():
            raise serializers.ValidationError(
                "Patient already belongs to a family."
            )

        return attrs

    def create(self, validated_data):

        return FamilyMember.objects.create(
            **validated_data,
            is_verified=True
        )
      