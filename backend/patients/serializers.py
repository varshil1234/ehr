from typing import cast
from rest_framework import serializers
from .models import Patient, PatientVital, MedicalHistory, MedicalFollowUp, FollowUpMedicine
from datetime import date
import re
from .utils import calculate_bmi, bmi_category, target_weight_range
from utils.encryption import *
from django.conf import settings
from utils.encryption import (
    decrypt_safe,
    decrypt_int_safe,
    decrypt_float_safe,
    encrypt_safe
)

cipher = AESCipher(settings.SECRET_KEY.encode()[:32])

def values_equal(a, b):
    return str(a) == str(b)

class PatientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Patient
        fields = (
            "id",
            "first_name",
            "last_name",
            "dob",
            "gender",
            "pincode",
        )
        
    # FIELD VALIDATIONS
    def validate_dob(self, value):
        if value > date.today():
            raise serializers.ValidationError(
                "DOB cannot be in the future"
            )
        return value

    def validate_pincode(self, value):
        if not re.match(r"^\d{6}$", value):
            raise serializers.ValidationError(
                "Pincode must be exactly 6 digits"
            )
        return value
    
    # OBJECT LEVEL VALIDATION
    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None

        if self.instance is None:
            if hasattr(user, "patient"):
                raise serializers.ValidationError(
                    "Patient profile already exists"
                )

        if self.instance is not None:
            if "gender" in self.initial_data:
                raise serializers.ValidationError(
                    {"gender": "Gender cannot be updated once set"}
                )
        return attrs
    
    # CREATE
    def create(self, validated_data):
        user = self.context["request"].user

        if user.role != "patient":
            user.role = "patient"
            user.save(update_fields=["role"])

        return Patient.objects.create(user=user, **validated_data)
    
    # UPDATE
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
    
def get_last_non_empty(vitals, field_name):
    """
    Iterate vitals in descending order
    and return first non-empty decrypted value
    """
    for vital in vitals:
        value = cipher.decrypt(getattr(vital, field_name))
        if value not in ("", None):
            return value
    return ""

# Patient vitlas serializers
class PatientVitalSerializer(serializers.ModelSerializer):
    """
    SINGLE serializer:
    - GET + POST
    - Encrypted DB fields
    - Previous vitals fallback
    - BMI auto calculate
    - Duplicate vitals prevention
    - Clean response keys
    """

    height_cm = serializers.FloatField(required=False, write_only=True)
    weight_kg = serializers.FloatField(required=False, write_only=True)
    blood_pressure = serializers.IntegerField(required=False, write_only=True)
    heart_rate_bpm = serializers.IntegerField(required=False, write_only=True)
    temperature_celsius = serializers.FloatField(required=False, write_only=True)

    bmi_category = serializers.SerializerMethodField()
    target_weight_range = serializers.SerializerMethodField()

    class Meta:
        model = PatientVital
        fields = (
            "id",
            "height_cm",
            "weight_kg",
            "blood_pressure",
            "heart_rate_bpm",
            "temperature_celsius",
            "bmi",
            "bmi_category",
            "target_weight_range",
            "created_at",
        )
        read_only_fields = ("bmi", "created_at")

    # CREATE → always NEW record (unless duplicate)
    def create(self, validated_data):
        patient = self.context["request"].user.patient
        vitals_qs = patient.vitals.all()

        # helper → get last non-empty decrypted value
        def last_value(field):
            for v in vitals_qs:
                val = decrypt_safe(cipher, getattr(v, field))
                if val is not None:
                    return val
            return None

        # ---------- HEIGHT ----------
        height = validated_data.get("height_cm")
        if height is None:
            last = last_value("height_cm")
            height = float(last) if last else None

        # ---------- WEIGHT ----------
        weight = validated_data.get("weight_kg")
        if weight is None:
            last = last_value("weight_kg")
            weight = float(last) if last else None

        # ---------- BLOOD PRESSURE ----------
        bp = validated_data.get("blood_pressure")
        if bp is None:
            last = last_value("blood_pressure")
            bp = int(last) if last else None

        # ---------- HEART RATE ----------
        hr = validated_data.get("heart_rate_bpm")
        if hr is None:
            last = last_value("heart_rate_bpm")
            hr = int(last) if last else None

        # ---------- TEMPERATURE ----------
        temp = validated_data.get("temperature_celsius")
        if temp is None:
            last = last_value("temperature_celsius")
            temp = float(last) if last else None

        # ---------- BMI ----------
        bmi = calculate_bmi(weight, height) if height and weight else 0

        # ---------- DUPLICATE CHECK ----------
        if vitals_qs.exists():
            last = vitals_qs.first()

            def same(field, new_val):
                old_val = decrypt_safe(cipher, getattr(last, field))

                if old_val is None and new_val is None:
                    return True
                if old_val is None or new_val is None:
                    return False

                return str(old_val) == str(new_val)

            if (
                same("height_cm", height)
                and same("weight_kg", weight)
                and same("blood_pressure", bp)
                and same("heart_rate_bpm", hr)
                and same("temperature_celsius", temp)
            ):
                raise serializers.ValidationError(
                    {"detail": "Vitals already up to date"}
                )

        # ---------- CREATE NEW RECORD ----------
        return PatientVital.objects.create(
            patient=patient,
            height_cm=cipher.encrypt(height) if height is not None else "",
            weight_kg=cipher.encrypt(weight) if weight is not None else "",
            blood_pressure=cipher.encrypt(bp) if bp is not None else "",
            heart_rate_bpm=cipher.encrypt(hr) if hr is not None else "",
            temperature_celsius=cipher.encrypt(temp) if temp is not None else "",
            bmi=bmi,
        )

    # RESPONSE → decrypted safely
    def to_representation(self, obj):
        height = decrypt_float_safe(cipher, obj.height_cm)

        return {
            "id": obj.id,
            "height_cm": height,
            "weight_kg": decrypt_float_safe(cipher, obj.weight_kg),
            "blood_pressure": decrypt_int_safe(cipher, obj.blood_pressure),
            "heart_rate_bpm": decrypt_int_safe(cipher, obj.heart_rate_bpm),
            "temperature_celsius": decrypt_float_safe(cipher, obj.temperature_celsius),
            "bmi": obj.bmi,
            "bmi_category": bmi_category(obj.bmi) if obj.bmi else None,
            "target_weight_range": (
                target_weight_range(height) if height else None
            ),
            "created_at": obj.created_at,
        }

    # EXTRA FIELDS
    def get_bmi_category(self, obj):
        return bmi_category(obj.bmi) if obj.bmi else None

    def get_target_weight_range(self, obj):
        height = decrypt_float_safe(cipher, obj.height_cm)
        return target_weight_range(height) if height else None

# patient MedicalHistory serializers
class MedicalHistorySerializer(serializers.ModelSerializer):
    # -------- INPUT (POST / PATCH only) --------
    type_of = serializers.CharField(write_only=True)
    description = serializers.CharField(write_only=True)
    diagnosis_code = serializers.CharField(required=False, write_only=True)
    status = serializers.CharField(write_only=True)
    notes = serializers.CharField(required=False, write_only=True)

    TYPE_OF_CHOICES = ["disease", "surgery", "allergy", "other"]
    STATUS_CHOICES = ["active", "resolved", "chronic"]

    class Meta:
        model = MedicalHistory
        fields = (
            "id",
            "type_of",
            "description",
            "diagnosis_code",
            "event_date",
            "status",
            "notes",
            "created_at",
        )
        read_only_fields = ("created_at",)

    # -------- FIELD VALIDATION --------
    def validate_type_of(self, value):
        if value not in self.TYPE_OF_CHOICES:
            raise serializers.ValidationError("Invalid type_of value.")
        return value

    def validate_status(self, value):
        if value not in self.STATUS_CHOICES:
            raise serializers.ValidationError("Invalid status value.")
        return value

    def validate_event_date(self, value):
        if value > date.today():
            raise serializers.ValidationError(
                "Event date cannot be in the future."
            )
        return value

    # -------- OBJECT VALIDATION --------
    def validate(self, attrs):
        type_of = attrs.get("type_of")
        diagnosis_code = attrs.get("diagnosis_code", "")
        description = attrs.get("description", "")

        if type_of == "disease" and not diagnosis_code:
            raise serializers.ValidationError(
                {"diagnosis_code": "Diagnosis code is required for diseases."}
            )

        if type_of == "allergy" and len(description) < 5:
            raise serializers.ValidationError(
                {"description": "Provide more details for allergies."}
            )

        # -------- DUPLICATE CHECK (ADDED) --------
        request = self.context.get("request")
        if request and hasattr(request.user, "patient"):
            patient = request.user.patient

            for mh in patient.medical_histories.all():
                if (
                    decrypt_safe(cipher, mh.type_of) == type_of
                    and decrypt_safe(cipher, mh.description) == description
                    and decrypt_safe(cipher, mh.diagnosis_code) == diagnosis_code
                    and decrypt_safe(cipher, mh.status) == attrs.get("status")
                    and mh.event_date == attrs.get("event_date")
                ):
                    raise serializers.ValidationError({
                        "detail": "Same medical history already exists."
                    })

        return attrs

    # -------- CREATE --------
    def create(self, validated_data):
        patient = self.context["request"].user.patient

        return MedicalHistory.objects.create(
            patient=patient,
            type_of=cipher.encrypt(validated_data["type_of"]),
            description=cipher.encrypt(validated_data["description"]),
            diagnosis_code=cipher.encrypt(
                validated_data.get("diagnosis_code", "")
            ),
            status=cipher.encrypt(validated_data["status"]),
            notes=cipher.encrypt(validated_data.get("notes", "")),
            event_date=validated_data["event_date"],
        )

    # -------- UPDATE --------
    def update(self, instance, validated_data):
        for field in ["type_of", "description", "diagnosis_code", "status", "notes"]:
            if field in validated_data:
                setattr(
                    instance,
                    field,
                    cipher.encrypt(validated_data[field])
                )

        if "event_date" in validated_data:
            instance.event_date = validated_data["event_date"]

        instance.save()
        return instance

    # -------- RESPONSE (DECRYPT) --------
    def to_representation(self, obj):
        def dec(val):
            return decrypt_safe(cipher, val)

        return {
            "id": obj.id,
            "type_of": dec(obj.type_of),
            "description": dec(obj.description),
            "diagnosis_code": dec(obj.diagnosis_code),
            "event_date": obj.event_date,
            "status": dec(obj.status),
            "notes": dec(obj.notes),
            "created_at": obj.created_at,
        }
        
# patient MedicalFollowUp serializers
class FollowUpMedicineSerializer(serializers.ModelSerializer):

    class Meta:
        model = FollowUpMedicine
        fields = ("id", "name", "dose", "duration", "created_at")
        read_only_fields = ("id", "created_at")

    # -------- CREATE --------
    def create(self, validated_data):
        followup = self.context["followup"]

        name = validated_data["name"]
        dose = validated_data["dose"]
        duration = validated_data["duration"]

        # -------- DUPLICATE CHECK (ADDED) --------
        for med in followup.medicines.all():
            if (
                decrypt_safe(cipher, med.name) == name
                and decrypt_safe(cipher, med.dose) == dose
                and decrypt_safe(cipher, med.duration) == duration
            ):
                raise serializers.ValidationError({
                    "detail": "Same medicine already added for this follow-up."
                })

        return FollowUpMedicine.objects.create(
            followup=followup,
            name=encrypt_safe(cipher, name),
            dose=encrypt_safe(cipher, dose),
            duration=encrypt_safe(cipher, duration),
        )

    # -------- UPDATE --------
    def update(self, instance, validated_data):
        for field in ["name", "dose", "duration"]:
            if field in validated_data:
                setattr(
                    instance,
                    field,
                    encrypt_safe(cipher, validated_data[field])
                )
        instance.save()
        return instance

    # -------- RESPONSE --------
    def to_representation(self, obj):
        return {
            "id": obj.id,
            "name": decrypt_safe(cipher, obj.name),
            "dose": decrypt_safe(cipher, obj.dose),
            "duration": decrypt_safe(cipher, obj.duration),
            "created_at": obj.created_at,
        }


class MedicalFollowUpSerializer(serializers.ModelSerializer):

    class Meta:
        model = MedicalFollowUp
        fields = (
            "id",
            "medical_history",
            "patient_complaints",
            "clinical_findings",
            "diagnosis",
            "advice",
            "followup_date",
            "created_at",
        )
        read_only_fields = ("id", "created_at", "medical_history")

    # -------- FIELD VALIDATIONS --------
    def validate_patient_complaints(self, value):
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Patient complaints must be at least 10 characters."
            )
        return value

    def validate_clinical_findings(self, value):
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Clinical findings must be at least 10 characters."
            )
        return value

    def validate_diagnosis(self, value):
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Diagnosis must be meaningful."
            )
        return value

    # -------- CREATE --------
    def create(self, validated_data):
        history = self.context["medical_history"]
        followup_date = validated_data["followup_date"]

        # SAME DATE BLOCK
        if history.followups.filter(followup_date=followup_date).exists():
            raise serializers.ValidationError({
                "detail": "Follow-up for this date already exists for this medical history."
            })

        # SAME DATA BLOCK
        for f in history.followups.all():
            if (
                decrypt_safe(cipher, f.patient_complaints) == validated_data["patient_complaints"]
                and decrypt_safe(cipher, f.clinical_findings) == validated_data["clinical_findings"]
                and decrypt_safe(cipher, f.diagnosis) == validated_data["diagnosis"]
                and decrypt_safe(cipher, f.advice) == validated_data.get("advice", "")
            ):
                raise serializers.ValidationError({
                    "detail": "Same follow-up data already exists."
                })

        return MedicalFollowUp.objects.create(
            medical_history=history,
            patient_complaints=encrypt_safe(cipher, validated_data["patient_complaints"]),
            clinical_findings=encrypt_safe(cipher, validated_data["clinical_findings"]),
            diagnosis=encrypt_safe(cipher, validated_data["diagnosis"]),
            advice=encrypt_safe(cipher, validated_data.get("advice", "")),
            followup_date=followup_date,
        )

    # -------- RESPONSE --------
    def to_representation(self, obj):
        return {
            "id": obj.id,
            "patient_complaints": decrypt_safe(cipher, obj.patient_complaints),
            "clinical_findings": decrypt_safe(cipher, obj.clinical_findings),
            "diagnosis": decrypt_safe(cipher, obj.diagnosis),
            "advice": decrypt_safe(cipher, obj.advice),
            "followup_date": obj.followup_date,
            "created_at": obj.created_at,
        }
 