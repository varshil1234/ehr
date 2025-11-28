from rest_framework import serializers
from django.db import IntegrityError
from .models import Doctor, AccessRequest, Encounter, ClinicalNote
from datetime import date
import re

class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = '__all__'
        read_only_fields = ["user"]

    # --- Field-level validation ---
    def validate_name(self, value):
        # Validate doctor's name (letters and spaces only)
        if not re.match(r"^[A-Za-z\s.]+$", value):
            raise serializers.ValidationError("Name must contain only letters, spaces, or periods.")
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Name must be at least 3 characters long.")
        return value.strip()

    def validate_specialty(self, value):
        # Validate specialty field
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Specialty must be at least 2 characters long.")
        if not re.match(r"^[A-Za-z\s,&/-]+$", value):
            raise serializers.ValidationError("Specialty can only contain letters, spaces, commas, and basic symbols like / & -.")
        return value.strip()

    def validate_contact_number(self, value):
        # Allow +91, country codes, or 10-digit Indian numbers
        pattern = r'^[6-9]\d{9}$'  # Indian mobile number pattern
        if not re.match(pattern, value):
            raise serializers.ValidationError("Enter a valid contact number (e.g., +919876543210 or 9876543210).")
        return value.strip()

    def validate_hospital(self, value):
        # Validate hospital name
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Hospital name must be at least 3 characters long.")
        return value.strip()

    # --- Object-level validation (optional cross-checks) ---
    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user

        # Only doctors can create doctor profile
        if not user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")
        if user.role != "doctor":
            raise serializers.ValidationError("Only users with doctor role can create doctor profiles.")
        
        name = attrs.get("name", "").lower()
        hospital = attrs.get("hospital", "").lower()

        # Example: prevent duplicate doctor entries (same name & hospital)
        if Doctor.objects.filter(name__iexact=name, hospital__iexact=hospital).exists():
            raise serializers.ValidationError("A doctor with this name already exists in this hospital.")

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["user"] = user
        doctor = Doctor.objects.create(**validated_data)
        return doctor

class AccessRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRequest
        # TODO: remove "otp" from fields in production
        fields = ['id', 'doctor', 'patient', "otp", 'is_approved', 'requested_at']
        read_only_fields = ['is_approved', 'requested_at']

    def validate(self, attrs):
        """
        Pre-check to return a friendly validation message if a duplicate exists.
        This avoids the generic DB-level error being shown to the client most of the time.
        """
        doctor = attrs.get('doctor') or self.context.get('request').user.linked_doctor
        patient = attrs.get('patient')

        if doctor is None or patient is None:
            # Let ModelSerializer field validations handle missing fields
            return attrs

        exists = AccessRequest.objects.filter(doctor=doctor, patient=patient).exists()
        if exists:
            raise serializers.ValidationError({
                "detail": "Access request already given for the patient."
            })

        return attrs

    def create(self, validated_data):
        # Ensure doctor is attached from request if not provided in payload
        request = self.context.get('request')
        if request and hasattr(request.user, 'linked_doctor'):
            validated_data["doctor"] = request.user.linked_doctor

        try:
            access_request = AccessRequest.objects.create(**validated_data)
        except IntegrityError:
            # This covers the rare race condition where two requests are created concurrently
            raise serializers.ValidationError({
                "detail": "Access request already given for the patient."
            })

        # Generate and send OTP (existing logic)
        otp = access_request.generate_otp()
        # TODO: create send email funtion to send OTP to patient's email id
        return access_request
    
    def run_validation(self, data=serializers.empty):
    # Override to skip built-in UniqueTogetherValidator
        try:
            self.Meta.model._meta.constraints = [
                c for c in self.Meta.model._meta.constraints
                if c.name != 'unique_doctor_patient_request'
            ]
        except Exception:
            pass
        return super().run_validation(data)

class AccessRequestVerifySerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6)

    def validate(self, attrs):
        otp = attrs.get("otp")
        access_request = self.context.get("access_request")

        if not access_request.verify_otp(otp):
            raise serializers.ValidationError({"detail": "OTP is invalid or expired"})
        return attrs

    def save(self, **kwargs):
        access_request = self.context.get("access_request")
        access_request.is_approved = True
        access_request.otp = None
        access_request.otp_expires_at = None
        access_request.save()
        return access_request

class EncounterSerializer(serializers.ModelSerializer):
    reason = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Encounter
        fields = '__all__'
        read_only_fields = ['date']

    def validate_date(self, value):
        # Ensure event date is not in the future
        if value > date.today():
            raise serializers.ValidationError("Event date cannot be in the future.")
        return value

    def get_reason(self, obj):
        return obj.reason_decrypted
    
    def get_summary(self, obj):
        return obj.summary_decrypted
    
    def create(self, validated_data):
        patient = validated_data.get("patient")
        e = Encounter(patient=patient)
        # set plaintext values from initial_data if present
        if "reason" in self.initial_data:
            e.reason = self.initial_data["reason"]
        if "summary" in self.initial_data:
            e.summary = self.initial_data["summary"]
            
        # set other simple fields
        for field in ("patient", "doctor", "date"):
            if field in validated_data:
                setattr(e, field, validated_data[field])
        e.save()
        return e
    
    def update(self, instance, validated_data):
        # similar: update plaintext fields from validated_data or initial_data then save
        for attr, value in validated_data.items():
            if attr in ("reason","summary"):
                # if passed plaintext (you may accept from initial_data)
                continue
            setattr(instance, attr, value)
        
        if "reason" in self.initial_data:
            instance.reason = self.initial_data["reason"]
        if "summary" in self.initial_data:
            instance.summary = self.initial_data["summary"]

        instance.save()
        return instance

class ClinicalNoteSerializer(serializers.ModelSerializer):
    subjective = serializers.SerializerMethodField()
    objective = serializers.SerializerMethodField()
    assessment = serializers.SerializerMethodField()
    plan = serializers.SerializerMethodField()
    note = serializers.SerializerMethodField()
    
    class Meta:
        model = ClinicalNote
        fields = '__all__'
        read_only_fields = ['created_at']

    def validate_created_at(self, value):
        # Ensure event date is not in the future
        if value > date.today():
            raise serializers.ValidationError("Event date cannot be in the future.")
        return value

    def get_subjective(self, obj):
        return obj.subjective_decrypted
    
    def get_objective(self, obj):
        return obj.objective_decrypted

    def get_assessment(self, obj):
        return obj.assessment_decrypted
    
    def get_plan(self, obj):
        return obj.plan_decrypted
    
    def get_note(self, obj):
        return obj.note_decrypted
    
    def create(self, validated_data):
        cn = ClinicalNote()
        # set plaintext values from initial_data if present
        if "subjective" in self.initial_data:
            cn.subjective = self.initial_data["subjective"]
        if "objective" in self.initial_data:
            cn.objective = self.initial_data["objective"]
        if "assessment" in self.initial_data:
            cn.assessment = self.initial_data["assessment"]
        if "plan" in self.initial_data:
            cn.plan = self.initial_data["plan"]
        if "note" in self.initial_data:
            cn.note = self.initial_data["note"]
            
        # set other simple fields
        for field in ("encounter", "created_at"):
            if field in validated_data:
                setattr(cn, field, validated_data[field])
        cn.save()
        return cn
    
    def update(self, instance, validated_data):
        # similar: update plaintext fields from validated_data or initial_data then save
        for attr, value in validated_data.items():
            if attr in ('subjective', 'objective', 'assessment', 'plan', 'note'):
                # if passed plaintext (you may accept from initial_data)
                continue
            setattr(instance, attr, value)
        
        if "subjective" in self.initial_data:
            instance.subjective = self.initial_data["subjective"]
        if "objective" in self.initial_data:
            instance.objective = self.initial_data["objective"]
        if "assessment" in self.initial_data:
            instance.assessment = self.initial_data["assessment"]
        if "plan" in self.initial_data:
            instance.plan = self.initial_data["plan"]
        if "note" in self.initial_data:
            instance.note = self.initial_data["note"]

        instance.save()
        return instance
