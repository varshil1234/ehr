from rest_framework import serializers
from .models import Insurance, InsuranceDocument
from datetime import date
from django.conf import settings
from utils.encryption import (
    AESCipher,
    decrypt_safe,
    encrypt_safe
)

cipher = AESCipher(settings.SECRET_KEY.encode()[:32])

class InsuranceDocumentSerializer(serializers.ModelSerializer):

    class Meta:
        model = InsuranceDocument
        fields = ("id", "document", "document_name", "uploaded_at")
        read_only_fields = ("id", "uploaded_at")


    def create(self, validated_data):
        insurance = self.context["insurance"]
        return InsuranceDocument.objects.create(
            insurance=insurance,
            **validated_data
        )


class InsuranceSerializer(serializers.ModelSerializer):
    documents = InsuranceDocumentSerializer(many=True, read_only=True)


    provider_name = serializers.CharField(write_only=True)
    policy_number = serializers.CharField(write_only=True)
    coverage_type = serializers.CharField(write_only=True)
    coverage_amount = serializers.CharField(write_only=True)

    class Meta:
        model = Insurance
        fields = (
            "id",
            "provider_name",
            "policy_number",
            "coverage_type",
            "coverage_amount",
            "validity_start",
            "validity_end",
            "documents",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "documents")

    
    def validate(self, attrs):
        start = attrs.get("validity_start")
        end = attrs.get("validity_end")
        if start and end and start >= end:
            raise serializers.ValidationError(
                {"validity_end": "Expire date must be after start date."}
            )
        return attrs

   
    def create(self, validated_data):
        patient = self.context["request"].user.patient

        return Insurance.objects.create(
            patient=patient,
            provider_name=encrypt_safe(cipher, validated_data["provider_name"]),
            policy_number=encrypt_safe(cipher, validated_data["policy_number"]),
            coverage_type=encrypt_safe(cipher, validated_data["coverage_type"]),
            coverage_amount=encrypt_safe(cipher, validated_data["coverage_amount"]),
            validity_start=validated_data["validity_start"],
            validity_end=validated_data["validity_end"],
        )

   
    def update(self, instance, validated_data):
        for field in ["provider_name", "policy_number", "coverage_type", "coverage_amount"]:
            if field in validated_data:
                setattr(
                    instance,
                    field,
                    encrypt_safe(cipher, validated_data[field])
                )

        if "validity_start" in validated_data:
            instance.validity_start = validated_data["validity_start"]
        if "validity_end" in validated_data:
            instance.validity_end = validated_data["validity_end"]

        instance.save()
        return instance


    def to_representation(self, obj):
        def dec(val):
            return decrypt_safe(cipher, val)

        return {
            "id": obj.id,
            "provider_name": dec(obj.provider_name),
            "policy_number": dec(obj.policy_number),
            "coverage_type": dec(obj.coverage_type),
            "coverage_amount": dec(obj.coverage_amount),
            "validity_start": obj.validity_start,
            "validity_end": obj.validity_end,
            "documents": InsuranceDocumentSerializer(obj.documents.all(), many=True).data,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
        }