from rest_framework import serializers
from datetime import date
from .models import Patient, Vital, MedicalHistory
import re

class PatientSerializer(serializers.ModelSerializer):
    contact_number = serializers.SerializerMethodField()
    aadhar_number = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = '__all__'
        read_only_fields = ["user"]

    # Field-level validations
    def validate_first_name(self, value):
        if not value.isalpha():
            raise serializers.ValidationError("First name should contain only letters.")
        return value.capitalize()

    def validate_last_name(self, value):
        if not value.isalpha():
            raise serializers.ValidationError("Last name should contain only letters.")
        return value.capitalize()

    def validate_date_of_birth(self, value):
        if value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        age = (date.today() - value).days / 365
        if age > 120:
            raise serializers.ValidationError("Age cannot be more than 120 years.")
        return value

    def validate_gender(self, value):
        valid_choices = [choice[0] for choice in Patient.GENDER_CHOICES]
        if value.lower() not in valid_choices:
            raise serializers.ValidationError(f"Gender must be one of: {', '.join(valid_choices)}")
        return value.lower()

    def validate_contact_number(self, value):
        if value:
            pattern = r'^[6-9]\d{9}$'  # Indian mobile number pattern
            if not re.match(pattern, value):
                raise serializers.ValidationError("Enter a valid 10-digit Indian mobile number.")
        return value

    def validate_aadhar_number(self, value):
        pattern = r'^\d{12}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError("Aadhar number must be a 12-digit numeric value.")
        return value

    # Object-level validation (cross-field)
    def validate(self, attrs):
        if attrs.get('first_name') == attrs.get('last_name'):
            raise serializers.ValidationError("First and last name cannot be the same.")
        return attrs

    def get_contact_number(self, obj):
        return obj.contact_number_decrypted

    def get_aadhar_number(self, obj):
        return obj.aadhar_number_decrypted

    def create(self, validated_data):
        # validated_data won't include contact_number/aadhar_number here because we replaced them with method fields.
        # If you want to accept plaintext on create, read from self.initial_data:
        user = self.context["request"].user
        p = Patient(user=user)
        # set plaintext values from initial_data if present
        if "contact_number" in self.initial_data:
            p.contact_number = self.initial_data["contact_number"]
        if "aadhar_number" in self.initial_data:
            p.aadhar_number = self.initial_data["aadhar_number"]
        # set other simple fields
        for field in ("first_name","last_name","date_of_birth","gender","address"):
            if field in validated_data:
                setattr(p, field, validated_data[field])
        p.save()
        return p

    def update(self, instance, validated_data):
        # similar: update plaintext fields from validated_data or initial_data then save
        for attr, value in validated_data.items():
            if attr in ("contact_number","aadhar_number"):
                # if passed plaintext (you may accept from initial_data)
                continue
            setattr(instance, attr, value)
        # If client passed new contact_number/aadhar_number as plaintext in initial_data:
        if "contact_number" in self.initial_data:
            instance.contact_number = self.initial_data["contact_number"]
        if "aadhar_number" in self.initial_data:
            instance.aadhar_number = self.initial_data["aadhar_number"]
        instance.save()
        return instance


class VitalsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vital
        fields = '__all__'
        read_only_fields = ['recorded_at']

    def validate_height_cm(self, value):
        # Validate height in centimeters
        if value is not None:
            if value <= 0 or value > 300:
                raise serializers.ValidationError("Height must be between 1 cm and 300 cm.")
        return value

    def validate_weight_kg(self, value):
        # Validate weight in kilograms
        if value is not None:
            if value <= 0 or value > 500:
                raise serializers.ValidationError("Weight must be between 1 kg and 500 kg.")
        return value

    def validate_blood_pressure(self, value):
        # Validate systolic blood pressure
        if value is not None:
            if value < 40 or value > 300:
                raise serializers.ValidationError("Blood pressure must be between 40 and 300 mmHg.")
        return value

    def validate_heart_rate_bpm(self, value):
        # Validate heart rate
        if value is not None:
            if value < 30 or value > 250:
                raise serializers.ValidationError("Heart rate must be between 30 and 250 bpm.")
        return value

    def validate_temperature_celsius(self, value):
        # Validate body temperature
        if value is not None:
            if value < 25 or value > 45:
                raise serializers.ValidationError("Temperature must be between 25°C and 45°C.")
        return value

    def validate(self, attrs):
        # Cross-field validation (optional)
        height = attrs.get('height_cm')
        weight = attrs.get('weight_kg')

        # Example: ensure both height and weight are given if one is provided
        if (height and not weight) or (weight and not height):
            raise serializers.ValidationError("Both height and weight should be provided together.")

        return attrs


class MedicalHistorySerializer(serializers.ModelSerializer):
    type_of = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    diagnosis_code = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()

    class Meta:
        model = MedicalHistory
        fields = '__all__'

    # --- Field-level validation ---
    def validate_type_of(self, value):
        valid_choices = [choice[0] for choice in self.Meta.model.TYPE_OF_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError("Invalid type_of value.")
        return value

    def validate_status(self, value):
        valid_choices = [choice[0] for choice in self.Meta.model.STATUS_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError("Invalid status value.")
        return value

    def validate_event_date(self, value):
        # Ensure event date is not in the future
        if value > date.today():
            raise serializers.ValidationError("Event date cannot be in the future.")
        return value

    # --- Object-level validation ---
    def validate(self, attrs):
        type_of = attrs.get("type_of")
        diagnosis_code = attrs.get("diagnosis_code")

        # If it's a disease and no diagnosis code provided
        if type_of == "disease" and not diagnosis_code:
            raise serializers.ValidationError({
                "diagnosis_code": "Diagnosis code is required for diseases."
            })

        # If allergy → description must contain the allergen
        if type_of == "allergy" and len(attrs.get("description", "")) < 5:
            raise serializers.ValidationError({
                "description": "Please provide a more detailed description for allergies."
            })

        return attrs

    def get_type_of(self, obj):
        return obj.type_of_decrypted
    
    def get_description(self, obj):
        return obj.description_decrypted
    
    def get_diagnosis_code(self, obj):
        return obj.diagnosis_code_decrypted
    
    def get_status(self, obj):
        return obj.status_decrypted
    
    def get_notes(self, obj):
        return obj.notes_decrypted
    
    def create(self, validated_data):
        user = self.context["request"].user
        patient = user.linked_patient
        mh = MedicalHistory(patient=patient)
        # set plaintext values from initial_data if present
        if "type_of" in self.initial_data:
            mh.type_of = self.initial_data["type_of"]
        if "description" in self.initial_data:
            mh.description = self.initial_data["description"]
        if "diagnosis_code" in self.initial_data:
            mh.diagnosis_code = self.initial_data["diagnosis_code"]
        if "status" in self.initial_data:
            mh.status = self.initial_data["status"]
        if "notes" in self.initial_data:
            mh.notes = self.initial_data["notes"]
            
        # set other simple fields
        for field in ("patient","event_date"):
            if field in validated_data:
                setattr(mh, field, validated_data[field])
        mh.save()
        return mh

    def update(self, instance, validated_data):
        # similar: update plaintext fields from validated_data or initial_data then save
        for attr, value in validated_data.items():
            if attr in ("type_of","description","diagnosis_code","status","notes"):
                # if passed plaintext (you may accept from initial_data)
                continue
            setattr(instance, attr, value)
        
        if "type_of" in self.initial_data:
            instance.type_of = self.initial_data["type_of"]
        if "description" in self.initial_data:
            instance.description = self.initial_data["description"]
        if "diagnosis_code" in self.initial_data:
            instance.diagnosis_code = self.initial_data["diagnosis_code"]
        if "status" in self.initial_data:
            instance.status = self.initial_data["status"]
        if "notes" in self.initial_data:
            instance.notes = self.initial_data["notes"]
        instance.save()
        return instance
